"""Annulation d'une clôture d'année académique.

Une clôture se déclenche d'un bouton et fait beaucoup : elle recopie les
classes et les barèmes sur l'année suivante, y réinscrit les élèves selon leur
résultat, change leur statut et transforme les impayés en dettes reportées.
Une clôture lancée trop tôt — un bulletin oublié, une note fausse — doit donc
pouvoir se défaire, sinon il faudrait tout ressaisir à la main.

Trois garde-fous encadrent ce retour en arrière :

1. **une seule à la fois** — on n'annule que la dernière clôture de
   l'établissement ; remonter deux années d'un coup laisserait l'année
   intermédiaire suspendue à des inscriptions disparues ;
2. **on ne défait que ce que la clôture a fait** — l'archive de la clôture
   note chaque objet créé et l'état de chaque élève avant modification ; ce
   qui a été saisi ailleurs dans l'année neuve n'est pas touché ;
3. **on refuse plutôt que d'effacer du travail** — une note saisie, un
   écolage encaissé, un emploi du temps généré dans l'année suivante bloquent
   l'annulation, en disant lequel.

Ce que la clôture avait figé mais n'avait pas créé — bulletins, notes,
discipline, appels de l'année close — n'a jamais bougé et n'a rien à
retrouver : l'annulation rouvre simplement l'année.
"""

from django.db import transaction

from .models import (
    AcademicYear,
    AttendanceRecord,
    AttendanceSession,
    CarriedDebt,
    CarriedDebtPayment,
    ClassSubject,
    CustomUser,
    DisciplineRecord,
    FeeModule,
    FeePayment,
    GradeEntry,
    ReportCard,
    SchoolClass,
    StudentEnrollment,
    SubjectCategoryOrder,
    TimetableSlot,
    TuitionFeePlan,
    YearClosure,
)


class YearReopenError(Exception):
    """Annulation impossible : l'année n'est pas en état d'être rouverte."""


# ── Ce que la clôture avait créé ─────────────────────────────────────────────

def latest_closure(school):
    """Dernière année clôturée de l'établissement, ou `None`."""
    return (
        YearClosure.objects
        .filter(academic_year__school=school)
        .select_related("academic_year")
        .order_by("-academic_year__start_date")
        .first()
    )


def ensure_reopenable(year):
    """Vérifie qu'on peut revenir en arrière, avec un message qui dit pourquoi."""
    closure = YearClosure.objects.filter(academic_year=year).first()
    if closure is None:
        raise YearReopenError("Cette année n'a pas été clôturée.")
    latest = latest_closure(year.school)
    if latest is not None and latest.academic_year_id != year.id:
        raise YearReopenError(
            f"Annulez d'abord la clôture de {latest.academic_year.name} : "
            "on ne revient en arrière que d'une année à la fois."
        )
    return closure


def created_ids(closure, key):
    """Identifiants notés par la reconduction, sous une clé donnée.

    Les clôtures antérieures à la reconduction n'ont rien recopié : leur
    archive ne porte pas ces listes, et il n'y a donc rien à supprimer.
    """
    return closure.payload.get("copied", {}).get(key) or []


def closure_enrollments(closure):
    """Inscriptions que la clôture a créées dans l'année suivante."""
    identifiers = [
        row["next_enrollment"]
        for row in closure.payload.get("students", [])
        if row.get("next_enrollment")
    ]
    return StudentEnrollment.objects.filter(id__in=identifiers)


# ── Ce qui empêche de revenir en arrière ─────────────────────────────────────

def blockers(closure):
    """Travail fait depuis la clôture que l'annulation détruirait.

    Chaque motif est une phrase telle qu'elle s'affichera : l'utilisateur doit
    savoir quoi défaire lui-même avant de réessayer.
    """
    reasons = []
    enrollments = closure_enrollments(closure)
    classes = SchoolClass.objects.filter(id__in=created_ids(closure, "created_classes"))
    subjects = ClassSubject.objects.filter(
        id__in=created_ids(closure, "created_class_subjects"),
    )

    checks = [
        (FeePayment.objects.filter(enrollment__in=enrollments),
         "des écolages ont été encaissés dans l'année suivante"),
        (GradeEntry.objects.filter(enrollment__in=enrollments),
         "des notes ont été saisies dans l'année suivante"),
        (ReportCard.objects.filter(enrollment__in=enrollments),
         "des bulletins ont été édités dans l'année suivante"),
        (DisciplineRecord.objects.filter(enrollment__in=enrollments),
         "de la discipline a été saisie dans l'année suivante"),
        (AttendanceRecord.objects.filter(enrollment__in=enrollments),
         "des appels ont été faits dans l'année suivante"),
        (CarriedDebtPayment.objects.filter(debt__origin_year=closure.academic_year),
         "des impayés reportés ont déjà reçu un versement"),
        (StudentEnrollment.objects.filter(school_class__in=classes).exclude(id__in=enrollments),
         "des élèves ont été inscrits à la main dans les classes reconduites"),
        (TimetableSlot.objects.filter(school_class__in=classes),
         "un emploi du temps a été généré sur les classes reconduites"),
        (AttendanceSession.objects.filter(school_class__in=classes),
         "des appels ont été ouverts dans les classes reconduites"),
        (GradeEntry.objects.filter(class_subject__in=subjects),
         "des notes ont été saisies sur les matières reconduites"),
        (FeePayment.objects.filter(
            class_fee__plan_id__in=created_ids(closure, "created_fee_plans")),
         "des versements ont été enregistrés sur les barèmes reconduits"),
    ]
    for queryset, reason in checks:
        if queryset.exists():
            reasons.append(reason)
    return reasons


# ── Retour en arrière ────────────────────────────────────────────────────────

def restore_students(closure):
    """Rend à chaque élève le statut et le résultat qu'il avait avant.

    Les clôtures antérieures à ce relevé n'ont pas gardé l'état d'avant : leurs
    élèves conservent le statut reçu à la clôture, et le bilan le dit.
    """
    rows = {
        row["student_id"]: row
        for row in closure.payload.get("students", [])
        if row.get("student_id") and "status_before" in row
    }
    if not rows:
        return 0
    restored = 0
    for student in CustomUser.objects.filter(id__in=rows):
        row = rows[student.id]
        student.student_status = row["status_before"] or CustomUser.StudentStatus.NEW
        # « Aucun résultat » se note `None` : une chaîne vide n'est pas un choix.
        student.year_result = row.get("year_result_before") or None
        student.save(update_fields=["student_status", "year_result"])
        restored += 1
    return restored


def detach_report_card_rules(closure):
    """Retire des règles de bulletin les classes que la reconduction y avait ajoutées."""
    additions = created_ids(closure, "rule_additions")
    rules = {
        rule.id: rule
        for rule in SubjectCategoryOrder.objects.filter(
            id__in={rule_id for rule_id, _ in additions},
        )
    }
    for rule_id, class_id in additions:
        rule = rules.get(rule_id)
        if rule is not None:
            rule.classes.remove(class_id)
    return len({rule_id for rule_id, _ in additions})


def reactivate(year):
    """Rend l'année active, si aucune autre ne l'est déjà.

    L'établissement n'a qu'une année active à la fois. Si la suivante a déjà
    pris la main, l'année rouverte reste en retrait : c'est à l'utilisateur de
    choisir laquelle il veut mener.
    """
    taken = AcademicYear.objects.filter(
        school=year.school, is_active=True,
    ).exclude(pk=year.pk).exists()
    year.is_closed = False
    year.is_active = not taken
    year.save(update_fields=["is_closed", "is_active"])
    return year.is_active


@transaction.atomic
def reopen_year(year):
    """Annule la clôture d'une année et retourne le bilan de ce qui a été défait.

    L'ordre compte : les inscriptions partent avant les classes, qui les
    protègent ; les barèmes avant les modules de frais, qui les protègent de
    même. Tout tient dans une transaction — une annulation à moitié faite
    serait pire que la clôture qu'elle défait.
    """
    closure = ensure_reopenable(year)
    reasons = blockers(closure)
    if reasons:
        raise YearReopenError(
            "Annulation impossible : " + " ; ".join(reasons)
            + ". Reprenez ces saisies avant de réessayer."
        )

    def wipe(queryset):
        """Supprime et retourne le nombre d'objets visés, cascades non comptées."""
        total = queryset.count()
        queryset.delete()
        return total

    report = {
        "next_year": closure.next_year.name if closure.next_year else "",
        # Élèves archivés par la clôture, et ceux dont on a pu rendre le statut
        # d'avant : l'écart signale une clôture antérieure au relevé d'état.
        "students": len(closure.payload.get("students", [])),
        "statuses_restored": restore_students(closure),
    }

    report["enrollments"] = wipe(closure_enrollments(closure))
    report["debts"] = wipe(CarriedDebt.objects.filter(origin_year=year))
    report["report_card_rules"] = detach_report_card_rules(closure)
    report["class_subjects"] = wipe(ClassSubject.objects.filter(
        id__in=created_ids(closure, "created_class_subjects"),
    ))
    report["fee_plans"] = wipe(TuitionFeePlan.objects.filter(
        id__in=created_ids(closure, "created_fee_plans"),
    ))
    report["classes"] = wipe(SchoolClass.objects.filter(
        id__in=created_ids(closure, "created_classes"),
    ))
    # Un module encore utilisé par un barème saisi à la main reste en place :
    # le supprimer emporterait des montants que la clôture n'a pas créés.
    report["fee_modules"] = wipe(FeeModule.objects.filter(
        id__in=created_ids(closure, "created_fee_modules"), class_fee_items__isnull=True,
    ))

    report["is_active"] = reactivate(year)
    closure.delete()
    return report
