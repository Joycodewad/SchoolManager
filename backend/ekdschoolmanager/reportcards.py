"""Construction et figement des bulletins.

Un bulletin est calculé une fois puis conservé tel quel : les moyennes, le
rang et les statistiques de classe sont enregistrés au moment de la
génération. Une note saisie après coup ne modifie pas un bulletin déjà remis
aux familles — il faut le régénérer explicitement.

Le calcul suit toujours la même règle : moyenne de chaque matière ramenée sur
20, puis moyenne pondérée par les coefficients. Ce sont l'affichage et les
seuils d'appréciation qui se paramètrent, pas l'arithmétique.
"""

import os
from decimal import Decimal

from django.db import transaction

from .models import (
    AcademicSession,
    ClassSubject,
    CustomUser,
    GradeEntry,
    GradeGroup,
    GradeLine,
    GradeScheme,
    ReportCard,
    ReportCardAppreciation,
    ReportCardSettings,
    SchoolClass,
    SchoolMembership,
    StudentEnrollment,
    SubjectCategoryOrder,
    TeacherAssignmentSubject,
)

CENTS = Decimal("0.01")
UNGROUPED_LABEL = "Autres matières"

# Barème d'appréciation usuel, posé au premier accès pour qu'un bulletin ne
# sorte jamais sans mention. L'établissement reste libre de le modifier.
DEFAULT_APPRECIATIONS = [
    ("Excellent", Decimal("18")),
    ("Très Bien", Decimal("16")),
    ("Bien", Decimal("14")),
    ("Assez Bien", Decimal("12")),
    ("Passable", Decimal("10")),
    ("Insuffisant", Decimal("0")),
]


def settings_for(school):
    """Paramétrage d'affichage, créé au premier accès."""
    configuration, _ = ReportCardSettings.objects.get_or_create(school=school)
    return configuration


def signatories_for(school, configuration):
    """Signataires du bas de page, dans l'ordre où ils s'impriment.

    Le titre figure toujours sur la maquette ; c'est le nom qui se règle. On
    va le chercher dans les rôles de l'établissement plutôt que de le faire
    ressaisir : un changement de proviseur suit tout seul.

    Un rôle vacant ne produit rien — pas de signature orpheline sur le
    bulletin. Le proviseur passe en dernier : sa signature ferme la page, à
    droite, sous le lieu et la date.
    """
    enabled = {
        "censor": configuration.show_censor_name,
        "founder": configuration.show_founder_name,
        "principal": configuration.show_principal_name,
    }
    return [
        row for row in role_holders(school)
        if enabled[row["key"]] and row["name"]
    ]


# Qui signe quoi, dans l'ordre d'impression : le proviseur ferme la ligne.
SIGNATORY_ROLES = [
    ("censor", "Le Censeur", CustomUser.Role.CENSEUR),
    ("founder", "Le Fondateur", None),
    ("principal", "Le Proviseur", CustomUser.Role.PROVISEUR),
]


def role_holders(school):
    """Qui occupe chaque rôle signataire, que le bulletin l'imprime ou non.

    Le fondateur est le propriétaire de l'établissement ; censeur et proviseur
    se lisent dans les rôles actifs. Un poste vacant rend un nom vide plutôt
    que d'être omis : le paramétrage peut ainsi dire « aucun proviseur ».
    """
    holders = []
    for key, title, role in SIGNATORY_ROLES:
        if role is None:
            holder = school.owner
        else:
            membership = (
                SchoolMembership.objects
                .filter(school=school, role=role, is_active=True)
                .select_related("user")
                .order_by("user__last_name", "user__first_name")
                .first()
            )
            holder = membership.user if membership else None
        holders.append({
            "key": key,
            "title": title,
            "name": holder.get_full_name().strip() if holder else "",
            # Chemin de la signature manuscrite, pour l'édition PDF. Le fichier
            # peut avoir disparu du disque : on ne le retient que s'il est là.
            "signature": signature_path(holder),
        })
    return holders


def teacher_signatures_for(school_class):
    """Signature de l'enseignant de chaque matière, par configuration de classe.

    Résolue à l'édition et non figée dans le bulletin : un enseignant qui
    enregistre sa signature la voit apparaître sur les bulletins déjà générés,
    sans qu'il faille tout régénérer.
    """
    signatures = {}
    for link in TeacherAssignmentSubject.objects.filter(
        class_subject__school_class=school_class,
    ).select_related("assignment__teacher"):
        path = signature_path(link.assignment.teacher)
        if path:
            signatures[link.class_subject_id] = path
    return signatures


def signature_path(holder):
    """Fichier de la signature manuscrite, s'il existe encore sur le disque."""
    if holder is None or not holder.signature:
        return ""
    try:
        path = holder.signature.path
    except (NotImplementedError, ValueError):
        return ""
    return path if os.path.exists(path) else ""


def category_order_for(school, school_class):
    """Ordre des types de matières applicable à une classe.

    Retourne la liste des noms de types, du premier au dernier. La règle
    retenue est la plus spécifique qui vise cette classe : classes choisies,
    puis série, puis cycle, puis l'établissement. Aucune règle : liste vide,
    et le bulletin retombe sur l'ordre alphabétique.
    """
    applicable = [
        rule for rule in SubjectCategoryOrder.objects.filter(school=school).prefetch_related("classes")
        if rule.matches(school_class)
    ]
    if not applicable:
        return []
    best = max(applicable, key=lambda rule: rule.precision)
    return [str(name) for name in (best.categories or [])]


def appreciations_for(school):
    """Seuils de l'école, du plus exigeant au plus bas.

    Une école qui n'a jamais réglé ses bulletins reçoit le barème usuel : sans
    seuil, la colonne « appréciation » resterait vide sur tous les bulletins.

    Dès que le paramétrage a été enregistré une fois, ce dépannage s'arrête :
    une liste vide est alors un choix, et le barème par défaut ne revient plus
    l'écraser. Rien ne modifie le paramétrage en dehors d'une saisie explicite.
    """
    thresholds = list(ReportCardAppreciation.objects.filter(school=school))
    if thresholds or settings_for(school).configured_at:
        return thresholds

    ReportCardAppreciation.objects.bulk_create([
        ReportCardAppreciation(school=school, label=label, minimum=minimum)
        for label, minimum in DEFAULT_APPRECIATIONS
    ])
    return list(ReportCardAppreciation.objects.filter(school=school))


def appreciation_for(average, thresholds):
    """Libellé correspondant à une moyenne, ou vide si aucun seuil ne s'applique.

    `thresholds` est trié du plus exigeant au plus bas : le premier seuil
    atteint gagne.
    """
    if average is None:
        return ""
    for threshold in thresholds:
        if average >= threshold.minimum:
            return threshold.label
    return ""


def subject_average(scheme, scores, lines):
    """Moyenne d'une matière, ou None si toutes les notes ne sont pas saisies."""
    # Import différé : le calcul vit dans la vue des notes, qui importe ce module.
    from .views import GradeSheetView

    if not lines or len(scores) != len(lines):
        return None
    return GradeSheetView.calculate_average(scheme, scores)


def build_class_payload(session, school_class, scheme, configuration, thresholds,
                        category_order=()):
    """Calcule les bulletins d'une classe entière.

    Le rang et les statistiques n'ont de sens qu'à l'échelle de la classe :
    on traite donc toujours la classe complète, même pour corriger un seul
    élève.
    """
    subjects = list(
        ClassSubject.objects.filter(school_class=school_class)
        .select_related("subject", "subject__category")
        .order_by("subject__category__name", "subject__name")
    )
    enrollments = list(
        StudentEnrollment.objects.filter(
            school_class=school_class, status=StudentEnrollment.Status.ACTIVE,
        ).select_related("student").order_by("student__last_name", "student__first_name")
    )

    teachers = {}
    for link in TeacherAssignmentSubject.objects.filter(
        class_subject__school_class=school_class,
    ).select_related("assignment__teacher", "class_subject"):
        teachers[link.class_subject_id] = link.assignment.teacher.get_full_name()

    entries = {}
    for entry in GradeEntry.objects.filter(
        line__scheme=scheme, class_subject__school_class=school_class,
    ):
        entries.setdefault((entry.enrollment_id, entry.class_subject_id), {})[entry.line_id] = entry.score

    lines = list(scheme.lines.all())
    line_columns = [
        {"id": line.id, "name": line.name, "max_score": str(line.max_score)}
        for line in lines
    ]

    students = []
    for enrollment in enrollments:
        rows = []
        weighted_total = Decimal("0")
        # Deux totaux distincts : celui imprimé au bas du bulletin porte sur
        # toutes les matières de la classe, alors que le diviseur de la moyenne
        # ne retient que les matières notées — sinon une matière sans note
        # tirerait la moyenne générale vers le bas.
        coefficient_total = sum((item.coefficient for item in subjects), Decimal("0"))
        graded_coefficients = Decimal("0")

        for item in subjects:
            scores = entries.get((enrollment.id, item.id), {})
            average = subject_average(scheme, scores, lines)
            if average is not None:
                weighted_total += average * item.coefficient
                graded_coefficients += item.coefficient
            rows.append({
                "class_subject_id": item.id,
                "subject": item.subject.name,
                "category": item.subject.category.name if item.subject.category else "",
                "coefficient": str(item.coefficient),
                "scores": {str(key): str(value) for key, value in scores.items()},
                "average": str(average.quantize(CENTS)) if average is not None else None,
                # « CAF » sur le bulletin : moyenne × coefficient.
                "weighted": str((average * item.coefficient).quantize(CENTS)) if average is not None else None,
                "teacher": teachers.get(item.id, ""),
                "appreciation": appreciation_for(average, thresholds),
            })

        general = (
            (weighted_total / graded_coefficients).quantize(CENTS)
            if graded_coefficients else None
        )
        students.append({
            "enrollment_id": enrollment.id,
            "matricule": enrollment.enrollment_number or "",
            "student_name": enrollment.student.get_full_name(),
            "gender": enrollment.student.get_gender_display() if enrollment.student.gender else "",
            "date_of_birth": (
                enrollment.student.date_of_birth.isoformat()
                if enrollment.student.date_of_birth else ""
            ),
            "subjects": rows,
            "groups": group_rows(rows, configuration, category_order),
            # Signataire du bulletin, à côté du proviseur.
            "homeroom_teacher": (
                school_class.homeroom_teacher.get_full_name()
                if school_class.homeroom_teacher else ""
            ),
            "coefficient_total": str(coefficient_total),
            "weighted_total": str(weighted_total.quantize(CENTS)),
            "general_average": str(general) if general is not None else None,
            "appreciation": appreciation_for(general, thresholds),
            "rank": None,
        })

    assign_ranks(students)
    assign_subject_ranks(students)
    statistics = class_statistics(students)
    for student in students:
        student["statistics"] = statistics
        student["line_columns"] = line_columns

    return students, statistics


def group_rows(rows, configuration, category_order=()):
    """Sous-totaux par type de matière, dans l'ordre du bulletin.

    `category_order` liste les types dans l'ordre voulu pour cette classe. Un
    type absent de la liste passe après ceux qui y figurent, par ordre
    alphabétique. Sans regroupement demandé, tout tient dans un seul bloc.
    """
    if not configuration.group_by_category:
        return [{"name": "", "subjects": rows, "weighted_total": subtotal(rows)}]

    grouped = {}
    for row in rows:
        grouped.setdefault(row["category"] or UNGROUPED_LABEL, []).append(row)

    ranks = {name: position for position, name in enumerate(category_order)}
    # Les types listés viennent en tête, dans l'ordre voulu ; les autres
    # suivent par ordre alphabétique. Les matières sans type ferment la liste.
    names = sorted(
        (name for name in grouped if name != UNGROUPED_LABEL),
        key=lambda name: (ranks.get(name, len(ranks)), name),
    )
    if UNGROUPED_LABEL in grouped:
        names.append(UNGROUPED_LABEL)

    return [
        {"name": name, "subjects": grouped[name], "weighted_total": subtotal(grouped[name])}
        for name in names
    ]


def subtotal(rows):
    total = sum(
        (Decimal(row["weighted"]) for row in rows if row["weighted"] is not None),
        Decimal("0"),
    )
    return str(total.quantize(CENTS))


def assign_ranks(students):
    """Rang par moyenne décroissante ; à égalité, même rang."""
    ranked = sorted(
        (student for student in students if student["general_average"] is not None),
        key=lambda student: Decimal(student["general_average"]), reverse=True,
    )
    previous_average = None
    previous_rank = 0
    for position, student in enumerate(ranked, start=1):
        average = Decimal(student["general_average"])
        if previous_average is not None and average == previous_average:
            student["rank"] = previous_rank
        else:
            student["rank"] = position
            previous_rank = position
            previous_average = average


def assign_subject_ranks(students):
    """Rang de chaque élève matière par matière.

    Le classement se fait sur la moyenne de la matière, à l'échelle de la
    classe entière, avec la même règle que le rang général : à moyenne égale,
    même rang. Une matière non notée ne reçoit pas de rang.
    """
    if not students:
        return

    # Les matières sont les mêmes pour toute la classe : on classe colonne par
    # colonne, en repérant chaque matière par son identifiant.
    subject_ids = [row["class_subject_id"] for row in students[0]["subjects"]]
    for position, class_subject_id in enumerate(subject_ids):
        graded = [
            student for student in students
            if student["subjects"][position]["average"] is not None
        ]
        graded.sort(key=lambda student: Decimal(student["subjects"][position]["average"]),
                    reverse=True)

        previous_average = None
        previous_rank = 0
        for index, student in enumerate(graded, start=1):
            average = Decimal(student["subjects"][position]["average"])
            if previous_average is not None and average == previous_average:
                student["subjects"][position]["rank"] = previous_rank
            else:
                student["subjects"][position]["rank"] = index
                previous_rank = index
                previous_average = average

    # Une matière sans note n'a pas de rang : on pose la clé pour que le PDF
    # trouve toujours le champ, sans avoir à tester son absence.
    for student in students:
        for row in student["subjects"]:
            row.setdefault("rank", None)


def class_statistics(students):
    averages = [
        Decimal(student["general_average"])
        for student in students if student["general_average"] is not None
    ]
    if not averages:
        return {"highest": None, "lowest": None, "class_average": None, "graded": 0,
                "headcount": len(students)}
    return {
        "highest": str(max(averages).quantize(CENTS)),
        "lowest": str(min(averages).quantize(CENTS)),
        "class_average": str((sum(averages) / len(averages)).quantize(CENTS)),
        "graded": len(averages),
        "headcount": len(students),
    }


def class_sessions(session, school_class):
    """Sessions de l'année qui concernent cette classe, dans l'ordre du calendrier.

    Les sessions sont rattachées aux classes une par une : une même année peut
    faire cohabiter des classes en trimestres et d'autres en semestres. La
    séquence d'un bulletin est donc celle de sa classe, pas celle de l'école.
    """
    return list(
        AcademicSession.objects
        .filter(academic_year=session.academic_year, classes=school_class)
        .order_by("start_date", "id")
    )


def term_history(session, school_class, enrollment_ids):
    """Résultats de chaque élève sur toutes les sessions déjà éditées.

    Retourne `(termes, resultats)` où `termes` décrit la séquence de la classe
    — nom de la session, session courante ou non — et `resultats` associe
    chaque élève aux moyennes et rangs de ses bulletins, par session.

    Seules les sessions déjà passées et la session courante entrent dans la
    liste : un bulletin du premier trimestre n'annonce pas les trimestres à
    venir, il ne montre que ce qui existe.
    """
    sequence = class_sessions(session, school_class)
    # Une session absente de la séquence (classe retirée de la session après
    # coup) resterait introuvable : on la replace en tête pour que le bulletin
    # courant figure toujours dans son propre récapitulatif.
    if session not in sequence:
        sequence = [session]
        position = 0
    else:
        position = sequence.index(session)

    past = sequence[: position + 1]

    terms = [
        {
            "id": item.id,
            "name": item.name,
            "is_current": item.id == session.id,
        }
        for item in past
    ]

    results = {enrollment_id: {} for enrollment_id in enrollment_ids}
    cards = ReportCard.objects.filter(
        session__in=past, enrollment_id__in=enrollment_ids,
    ).values("session_id", "enrollment_id", "general_average", "rank")
    for card in cards:
        results[card["enrollment_id"]][card["session_id"]] = {
            "average": str(card["general_average"]) if card["general_average"] is not None else None,
            "rank": card["rank"],
        }

    return {
        "terms": terms,
        # Seule une session explicitement désignée comme dernière de l'année
        # porte la moyenne annuelle. Être dernière au calendrier ne suffit
        # pas : une session peut s'ajouter, et une moyenne « annuelle » sur
        # une année incomplète induirait en erreur. Sans désignation, le
        # bulletin se contente du rappel des sessions déjà éditées.
        "is_final": session.is_final,
        "is_first": position == 0,
        "results": results,
    }


def student_history(history, enrollment_id):
    """Récapitulatif d'un élève, tel que le bulletin l'imprime.

    Reprend la séquence de la classe en y plaçant les résultats de cet élève,
    et calcule la moyenne annuelle sur la session désignée comme dernière. Une
    session où l'élève n'a pas de bulletin reste dans la liste, sans valeur :
    l'absence se lit alors sur le bulletin, elle n'est pas masquée.
    """
    results = history["results"].get(enrollment_id, {})
    terms = [
        {**term, **(results.get(term["id"]) or {"average": None, "rank": None})}
        for term in history["terms"]
    ]
    return {
        "terms": terms,
        "is_final": history["is_final"],
        "is_first": history["is_first"],
        "annual_average": annual_average(terms) if history["is_final"] else None,
    }


def annual_average(entries):
    """Moyenne annuelle : moyenne simple des sessions effectivement éditées.

    Chaque session pèse pareil — c'est la règle des bulletins officiels, où la
    moyenne annuelle est la moyenne des trimestres. Une session sans bulletin
    ne compte pas : le calcul porte sur ce qui existe.
    """
    averages = [
        Decimal(entry["average"]) for entry in entries
        if entry and entry.get("average") is not None
    ]
    if not averages:
        return None
    return str((sum(averages) / len(averages)).quantize(CENTS))


def promotion_decision(level, annual_average_value, exam_average_value, gender=""):
    """Décision de fin d'année d'un élève, telle qu'elle s'imprime.

    Deux régimes. Sur un niveau ordinaire, c'est la moyenne annuelle comparée
    au seuil du niveau qui fait passer. Sur un niveau d'examen — CM2, 3ème,
    Première, Terminale — la moyenne annuelle ne décide de rien : seul compte
    le résultat de l'examen officiel, qui tombe après le conseil de classe.

    `gender` accorde la mention à l'élève : « Admise » pour une fille. On
    accepte aussi bien le code enregistré (« F ») que son libellé
    (« Féminin »), pour les bulletins figés avant ce point.

    Retourne `None` tant que la décision n'est pas connue : moyenne annuelle
    absente, ou résultat d'examen pas encore saisi. Le bulletin laisse alors
    la case du conseil de classe libre plutôt que d'annoncer un redoublement
    faute de données.
    """
    threshold = Decimal(str(level.passing_average))
    feminine = str(gender).strip().upper().startswith("F")
    admitted = "Admise" if feminine else "Admis"

    if level.is_exam_level:
        if exam_average_value is None:
            return None
        exam = Decimal(str(exam_average_value))
        passed = exam >= threshold
        label = f"{admitted} au {level.exam_name}" if level.exam_name else f"{admitted} à l'examen"
        return {
            "passed": passed,
            "label": label if passed else ("Échouée à l'examen" if feminine else "Échoué à l'examen"),
            "basis": "examen",
            "value": str(exam.quantize(CENTS)),
            "threshold": str(threshold.quantize(CENTS)),
        }

    if annual_average_value is None:
        return None
    average = Decimal(str(annual_average_value))
    return {
        "passed": average >= threshold,
        # « Redouble » est un verbe : il ne s'accorde pas.
        "label": f"{admitted} en classe supérieure" if average >= threshold else "Redouble",
        "basis": "moyenne annuelle",
        "value": str(average.quantize(CENTS)),
        "threshold": str(threshold.quantize(CENTS)),
    }


def scheme_for(session):
    return (
        GradeScheme.objects
        .prefetch_related("lines", "groups__lines")
        .filter(session=session)
        .first()
    )


class SchemeCopyError(Exception):
    """Copie impossible : source ou destination inadaptée."""


@transaction.atomic
def copy_scheme(source_session, target_session, user=None):
    """Recopie le barème d'une session vers une autre.

    Configurer les mêmes lignes à chaque trimestre est fastidieux et source
    d'écarts involontaires : cette copie reprend le mode de calcul, les groupes
    et les lignes à l'identique. Les notes ne suivent pas — seule la structure
    est copiée, la session de destination repart vierge.
    """
    if source_session.pk == target_session.pk:
        raise SchemeCopyError("La session source et la session de destination sont identiques.")

    source = scheme_for(source_session)
    if source is None:
        raise SchemeCopyError(
            f"La session « {source_session.name} » n'a pas de configuration à copier."
        )
    if target_session.is_closed:
        raise SchemeCopyError(
            f"La session « {target_session.name} » est clôturée : sa configuration est figée."
        )

    existing = scheme_for(target_session)
    if existing is not None and GradeEntry.objects.filter(line__scheme=existing).exists():
        raise SchemeCopyError(
            "Des notes ont déjà été saisies dans cette session : sa configuration "
            "ne peut plus être remplacée."
        )
    if existing is not None:
        existing.delete()

    target = GradeScheme.objects.create(
        session=target_session,
        calculation_method=source.calculation_method,
        created_by=user,
    )
    # Les groupes d'abord : les lignes s'y rattachent.
    group_map = {}
    for group in source.groups.all():
        group_map[group.pk] = GradeGroup.objects.create(
            scheme=target, name=group.name, weight=group.weight, order=group.order,
        )
    for line in source.lines.all():
        GradeLine.objects.create(
            scheme=target,
            group=group_map.get(line.group_id),
            name=line.name,
            weight=line.weight,
            max_score=line.max_score,
            order=line.order,
        )
    return target


@transaction.atomic
def generate_class(session, school_class, user=None, enrollment_ids=None, issued_on=None):
    """Fige les bulletins d'une classe.

    `enrollment_ids` restreint l'écriture à quelques élèves — le calcul, lui,
    porte toujours sur la classe entière, sans quoi le rang et les statistiques
    seraient faux.

    `issued_on` est la date d'établissement imprimée au pied du bulletin,
    choisie par la direction au moment de générer.
    """
    scheme = scheme_for(session)
    if scheme is None:
        raise ValueError("Les lignes de notes ne sont pas configurées pour cette session.")

    school = school_class.school
    configuration = settings_for(school)
    thresholds = appreciations_for(school)

    category_order = category_order_for(school, school_class)
    students, _ = build_class_payload(
        session, school_class, scheme, configuration, thresholds, category_order,
    )
    written = 0
    for student in students:
        if enrollment_ids is not None and student["enrollment_id"] not in enrollment_ids:
            continue
        ReportCard.objects.update_or_create(
            session=session, enrollment_id=student["enrollment_id"],
            defaults={
                "school_class": school_class,
                "payload": student,
                "general_average": (
                    Decimal(student["general_average"])
                    if student["general_average"] is not None else None
                ),
                "rank": student["rank"],
                "issued_on": issued_on,
                "generated_by": user,
            },
        )
        written += 1
    return written


def generate_school(session, school, user=None, issued_on=None):
    """Fige les bulletins de toutes les classes rattachées à la session."""
    classes = SchoolClass.objects.filter(
        academic_sessions=session, school=school,
    ).select_related("level").order_by("level__order", "group")

    total = 0
    for school_class in classes:
        total += generate_class(session, school_class, user=user, issued_on=issued_on)
    return total, classes.count()
