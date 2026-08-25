"""Clôture d'une année académique : arrêt des comptes et passage des élèves.

Clôturer une année, c'est quatre choses en un seul geste :

1. **arrêter** — l'année et ses sessions passent en lecture seule, et l'état
   d'avant (classes, inscriptions, écolage) est recopié dans une archive qui
   ne bougera plus ;
2. **reconduire** — les classes et leur configuration, les barèmes de
   scolarité et la portée des règles de bulletin sont recopiés sur l'année
   suivante (voir `yearcopy`) ; c'est ce qui donne aux admis une classe où
   aller ;
3. **reporter les impayés** — le reste dû de chaque élève quitte l'inscription
   close, qui se fige, pour devenir une dette qui suit l'élève et se règle
   pendant n'importe quelle année ;
4. **faire passer** — chaque élève est réinscrit dans l'année suivante selon
   son résultat, ou quitte l'établissement avec son diplôme.

Deux conditions avant tout cela : plus aucune session ouverte — un trimestre
en cours n'a pas de résultats définitifs — et une année suivante déjà créée,
puisque c'est elle qui reçoit les inscriptions.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    AcademicYear,
    AttendanceRecord,
    AttendanceSession,
    CarriedDebt,
    ClassFeeItem,
    CustomUser,
    DisciplineRecord,
    SchoolClass,
    SchoolLevel,
    StudentEnrollment,
    TuitionFeePlan,
    YearClosure,
)
from .reportcards import promotion_decision
from .yearcopy import copy_year_settings

CENTS = Decimal("0.01")

# Diplôme obtenu selon l'examen du niveau. La clé est le nom de l'examen mis
# en minuscules ; un examen inconnu retombe sur le statut générique.
DIPLOMA_STATUSES = {
    "cepd": CustomUser.StudentStatus.CEPD_HOLDER,
    "bepc": CustomUser.StudentStatus.BEPC_HOLDER,
    "baccalauréat deuxième partie": CustomUser.StudentStatus.BACHELOR,
    "baccalaureat deuxieme partie": CustomUser.StudentStatus.BACHELOR,
    "bac 2": CustomUser.StudentStatus.BACHELOR,
}


class YearClosureError(Exception):
    """Clôture impossible : l'année n'est pas en état d'être arrêtée."""


# ── Conditions préalables ────────────────────────────────────────────────────

def open_sessions(year):
    """Sessions encore ouvertes : elles bloquent la clôture de l'année.

    Une session en cours n'a pas de résultats définitifs — ses bulletins
    peuvent encore être régénérés. Faire passer des élèves sur cette base
    reviendrait à décider avant la fin.
    """
    return list(year.sessions.filter(is_closed=False).order_by("start_date"))


def following_year(year):
    """Année qui suit celle-ci dans le même établissement, ou `None`."""
    return (
        AcademicYear.objects
        .filter(school=year.school, start_date__gt=year.start_date)
        .order_by("start_date")
        .first()
    )


def ensure_closable(year):
    """Vérifie les deux conditions, avec un message qui dit quoi faire."""
    if year.is_closed:
        raise YearClosureError("Cette année est déjà clôturée.")
    still_open = open_sessions(year)
    if still_open:
        names = ", ".join(session.name for session in still_open)
        raise YearClosureError(
            f"Clôturez d'abord les sessions encore ouvertes : {names}."
        )
    following = following_year(year)
    if following is None:
        raise YearClosureError(
            "Créez d'abord l'année suivante : c'est elle qui reçoit les élèves "
            "qui passent."
        )
    return following


# ── Passage d'un niveau au suivant ───────────────────────────────────────────

def next_level(level):
    """Niveau immédiatement supérieur dans l'établissement, ou `None`."""
    return (
        SchoolLevel.objects
        .filter(school=level.school, is_active=True, order__gt=level.order)
        .order_by("order")
        .first()
    )


def class_rank(school_class):
    """Rang d'une classe parmi celles de son niveau et de sa série.

    C'est ce rang, et non le nom, qui fait correspondre une classe à celle du
    niveau supérieur : la troisième cinquième va dans la troisième quatrième.
    Les noms de groupe portent le niveau (« 5A », « 4A ») et ne peuvent donc
    pas se comparer directement d'un niveau à l'autre.
    """
    peers = list(
        SchoolClass.objects
        .filter(
            academic_year=school_class.academic_year,
            level=school_class.level,
            series=school_class.series,
        )
        .order_by("group")
        .values_list("id", flat=True)
    )
    return peers.index(school_class.id) if school_class.id in peers else None


def matching_class(target_year, level, series, rank):
    """Classe de même rang au niveau visé, ou `None` si elle n'existe pas.

    Une cinquième D dont la quatrième n'a que trois classes n'a pas de place
    attitrée : l'élève rejoint alors les élèves sans classe, au bon niveau, et
    l'établissement l'affecte lui-même.
    """
    if rank is None:
        return None
    peers = list(
        SchoolClass.objects
        .filter(academic_year=target_year, level=level, series=series, is_active=True)
        .order_by("group")
    )
    return peers[rank] if rank < len(peers) else None


def diploma_status(level):
    """Statut décerné par l'examen d'un niveau."""
    return DIPLOMA_STATUSES.get(
        (level.exam_name or "").strip().lower(), CustomUser.StudentStatus.GRADUATED,
    )


def student_outcome(enrollment, decision, target_year):
    """Ce que devient un élève à la clôture : niveau, classe, statut.

    Retourne un dictionnaire décrivant la suite, jamais `None` : même un élève
    sans décision a un sort — il reste à son niveau, en attendant que
    l'établissement tranche.
    """
    level = enrollment.level or (enrollment.school_class.level if enrollment.school_class else None)
    if level is None:
        return {
            "kind": "indécis", "level": None, "school_class": None, "status": None,
            "detail": "Inscription sans niveau : rien à faire passer.",
        }

    passed = bool(decision and decision["passed"])
    if decision is None:
        # Pas de bulletin de fin d'année : on ne fait pas passer par défaut.
        return {
            "kind": "indécis", "level": level, "school_class": enrollment.school_class,
            "status": None,
            "detail": "Aucune décision de fin d'année : l'élève reste à son niveau.",
        }

    if not passed:
        rank = class_rank(enrollment.school_class) if enrollment.school_class else None
        return {
            "kind": "redouble", "level": level,
            "school_class": matching_class(target_year, level, enrollment.series, rank),
            "status": CustomUser.StudentStatus.REPEATING,
            "detail": "Redouble son niveau.",
        }

    upper = next_level(level)
    if upper is None:
        # Fin du cursus de l'établissement : l'élève sort avec son titre.
        return {
            "kind": "diplômé", "level": None, "school_class": None,
            "status": diploma_status(level) if level.is_exam_level else CustomUser.StudentStatus.GRADUATED,
            "detail": f"Quitte l'établissement : aucun niveau après {level.name}.",
        }

    if level.is_exam_level:
        # Après un examen, l'orientation change — série, filière : la classe se
        # décide à l'inscription, pas ici.
        return {
            "kind": "passe", "level": upper, "school_class": None,
            "status": CustomUser.StudentStatus.NEW,
            "detail": f"Reçu à l'examen : passe en {upper.name}, à affecter.",
        }

    rank = class_rank(enrollment.school_class) if enrollment.school_class else None
    target = matching_class(target_year, upper, enrollment.series, rank)
    return {
        "kind": "passe", "level": upper, "school_class": target,
        "status": CustomUser.StudentStatus.NEW,
        "detail": (
            f"Passe en {target.group}." if target
            else f"Passe en {upper.name}, sans classe correspondante."
        ),
    }


# ── Écolage resté dû ─────────────────────────────────────────────────────────

def outstanding_for(enrollment):
    """Reste dû d'un élève sur l'année : barème de sa classe moins ses versements.

    Le barème dépend du genre — les établissements togolais pratiquent des
    montants distincts. Une classe sans barème ne doit rien : on ne fabrique
    pas une dette faute de configuration.
    """
    if enrollment.school_class_id is None:
        return Decimal("0")
    plan = TuitionFeePlan.objects.filter(school_class=enrollment.school_class).first()
    if plan is None:
        return Decimal("0")

    female = enrollment.student.gender == CustomUser.Gender.FEMALE
    due = sum(
        (item.female_amount if female else item.male_amount)
        for item in ClassFeeItem.objects.filter(plan=plan)
    ) or Decimal("0")
    paid = sum(
        (payment.amount for payment in enrollment.fee_payments.all()), Decimal("0"),
    )
    return max(Decimal("0"), (Decimal(due) - paid).quantize(CENTS))


def carry_debt(enrollment, year):
    """Reporte le reste dû d'une inscription, s'il y en a un."""
    amount = outstanding_for(enrollment)
    if amount <= 0:
        return None
    debt, _ = CarriedDebt.objects.get_or_create(
        origin_enrollment=enrollment,
        defaults={
            "school": enrollment.school,
            "student": enrollment.student,
            "origin_year": year,
            "amount": amount,
        },
    )
    return debt


# ── Réinscription dans l'année suivante ──────────────────────────────────────

def next_enrollment_number(school, year, taken):
    """Matricule libre pour l'année visée.

    Le matricule est unique par établissement, pas par année : un élève
    réinscrit en reçoit un nouveau. `taken` porte ceux déjà attribués pendant
    cette clôture, que la base ne connaît pas encore.
    """
    sequence = StudentEnrollment.objects.filter(school=school).count() + len(taken) + 1
    while True:
        number = f"{year.start_date.year}-{sequence:04d}"
        if number not in taken and not StudentEnrollment.objects.filter(
            school=school, enrollment_number__iexact=number,
        ).exists():
            taken.add(number)
            return number
        sequence += 1


def reenroll(enrollment, outcome, target_year, taken):
    """Inscrit l'élève dans l'année suivante, au niveau et à la classe retenus.

    Une inscription déjà saisie à la main pour cette année-là fait foi : la
    clôture ne la remplace pas, elle passe son chemin.
    """
    existing = StudentEnrollment.objects.filter(
        academic_year=target_year, student=enrollment.student,
    ).first()
    if existing is not None:
        return existing
    return StudentEnrollment.objects.create(
        school=enrollment.school,
        academic_year=target_year,
        student=enrollment.student,
        guardian=enrollment.guardian,
        level=outcome["level"],
        school_class=outcome["school_class"],
        series=outcome["school_class"].series if outcome["school_class"] else enrollment.series,
        previous_average=enrollment.previous_average,
        enrollment_number=next_enrollment_number(enrollment.school, target_year, taken),
        status=StudentEnrollment.Status.ACTIVE,
    )


# ── Décision de fin d'année, lue sur les bulletins ───────────────────────────

def final_decisions(year):
    """Décision de passage de chaque inscription, par identifiant.

    Elle se lit sur le bulletin de la session marquée « dernière de l'année »
    pour la classe de l'élève. Une classe sans session finale, ou un élève
    sans bulletin, n'ont pas de décision : la clôture les laisse en attente
    plutôt que de les faire redoubler d'office.
    """
    from .models import ReportCard  # importé ici : dépendance seulement locale
    from .reportcards import student_history, term_history

    decisions = {}
    for session in year.sessions.filter(is_final=True).prefetch_related("classes"):
        for school_class in session.classes.select_related("level"):
            cards = list(
                ReportCard.objects.filter(session=session, school_class=school_class)
                .select_related("enrollment__student")
            )
            if not cards:
                continue
            history = term_history(
                session, school_class, [card.enrollment_id for card in cards],
            )
            for card in cards:
                student = student_history(history, card.enrollment_id)
                decisions[card.enrollment_id] = promotion_decision(
                    school_class.level, student["annual_average"], card.exam_average,
                    gender=card.enrollment.student.gender,
                )
    return decisions


# ── Clôture ──────────────────────────────────────────────────────────────────

@transaction.atomic
def close_year(year, user=None):
    """Clôture l'année : archive, reconduit, reporte les impayés, fait passer.

    Tout tient dans une transaction : une clôture qui échoue à mi-chemin
    laisserait des classes recopiées, des élèves réinscrits et d'autres non,
    sans moyen de reprendre.
    """
    target_year = ensure_closable(year)
    # Reconduire d'abord : les décisions de passage cherchent une classe dans
    # l'année suivante, qui n'en a encore aucune tant que rien n'y a été copié.
    copied = copy_year_settings(year, target_year)
    decisions = final_decisions(year)

    enrollments = list(
        StudentEnrollment.objects
        .filter(academic_year=year, status=StudentEnrollment.Status.ACTIVE)
        .select_related("student", "school_class__level", "level")
        .prefetch_related("fee_payments")
        .order_by("school_class__level__order", "school_class__group",
                  "student__last_name", "student__first_name")
    )

    counters = {"passe": 0, "redouble": 0, "diplômé": 0, "indécis": 0}
    unassigned = 0
    debt_total = Decimal("0")
    taken_numbers = set()
    archive = []

    for enrollment in enrollments:
        decision = decisions.get(enrollment.id)
        outcome = student_outcome(enrollment, decision, target_year)
        counters[outcome["kind"]] = counters.get(outcome["kind"], 0) + 1

        debt = carry_debt(enrollment, year)
        if debt is not None:
            debt_total += debt.amount

        student = enrollment.student
        # Relevé avant modification : c'est la seule trace de ce qu'était
        # l'élève, et donc le seul moyen de revenir en arrière si la clôture
        # est annulée.
        status_before = student.student_status
        year_result_before = student.year_result
        if decision is not None:
            student.year_result = (
                CustomUser.YearResult.PASSED if decision["passed"]
                else CustomUser.YearResult.FAILED
            )
        if outcome["status"]:
            student.student_status = outcome["status"]
        student.save(update_fields=["year_result", "student_status"])

        created = None
        if outcome["kind"] in ("passe", "redouble"):
            created = reenroll(enrollment, outcome, target_year, taken_numbers)
            if created.school_class_id is None:
                unassigned += 1

        archive.append({
            "enrollment": enrollment.id,
            "matricule": enrollment.enrollment_number,
            "student": student.get_full_name(),
            "student_id": student.id,
            "status_before": status_before,
            "year_result_before": year_result_before,
            "class": enrollment.school_class.group if enrollment.school_class else "",
            "level": enrollment.level.name if enrollment.level else "",
            "decision": decision["label"] if decision else "",
            "outcome": outcome["kind"],
            "detail": outcome["detail"],
            "next_level": outcome["level"].name if outcome["level"] else "",
            "next_class": outcome["school_class"].group if outcome["school_class"] else "",
            "next_enrollment": created.id if created else None,
            "debt": str(debt.amount) if debt else "0",
        })

    classes = list(
        SchoolClass.objects.filter(academic_year=year).select_related("level")
    )
    # Discipline et appels sont déjà rattachés à l'année : rien à déplacer ni
    # à effacer, l'année suivante n'en hérite pas. On en garde le décompte
    # pour que la clôture dise ce qu'elle a arrêté.
    discipline = DisciplineRecord.objects.filter(academic_year=year)
    attendance = AttendanceSession.objects.filter(academic_year=year)
    attendance_records = AttendanceRecord.objects.filter(session__academic_year=year)
    closure = YearClosure.objects.create(
        academic_year=year,
        next_year=target_year,
        closed_by=user,
        class_count=len(classes),
        enrollment_count=len(enrollments),
        promoted_count=counters["passe"],
        repeated_count=counters["redouble"],
        graduated_count=counters["diplômé"],
        unassigned_count=unassigned,
        undecided_count=counters["indécis"],
        discipline_count=discipline.count(),
        attendance_session_count=attendance.count(),
        attendance_record_count=attendance_records.count(),
        carried_debt_total=debt_total,
        copied_class_count=copied["classes"],
        copied_subject_count=copied["class_subjects"],
        copied_fee_plan_count=copied["fee_plans"],
        payload={
            "closed_at": timezone.now().isoformat(),
            "next_year": target_year.name,
            "copied": copied,
            "classes": [
                {
                    "id": school_class.id,
                    "level": school_class.level.name,
                    "series": school_class.series,
                    "group": school_class.group,
                    "headcount": sum(
                        1 for item in enrollments
                        if item.school_class_id == school_class.id
                    ),
                }
                for school_class in classes
            ],
            "students": archive,
        },
    )

    year.is_closed = True
    year.is_active = False
    year.save(update_fields=["is_closed", "is_active"])
    year.sessions.update(is_active=False)
    return closure
