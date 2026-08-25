"""Parcours d'un élève dans l'établissement, toutes années confondues.

Les écrans du quotidien ne montrent que l'année active : la classe du moment,
les notes du trimestre en cours. Cette vue-ci fait l'inverse — elle rassemble
ce qu'un élève a laissé derrière lui depuis son arrivée : les classes
traversées, les moyennes et rangs de chaque session, la discipline, les appels
et l'écolage.

Tout se lit sur les inscriptions : c'est l'inscription qui porte l'année, la
classe, les bulletins et la vie scolaire. Un élève sorti de l'établissement
garde donc son dossier entier, même sans inscription courante.
"""

from decimal import Decimal

from django.db.models import Q, Sum

from .models import (
    AttendanceRecord,
    CarriedDebt,
    ClassFeeItem,
    CustomUser,
    DisciplineRecord,
    ReportCard,
    StudentEnrollment,
    TuitionFeePlan,
)
from .reportcards import annual_average

CENTS = Decimal("0.01")


def search_students(school, query, limit=25):
    """Élèves de l'établissement dont le nom ou le matricule correspond.

    La recherche porte sur toutes les années : un ancien élève doit se
    retrouver, c'est même le premier usage d'un dossier de parcours. Un élève
    inscrit plusieurs années n'apparaît qu'une fois, avec sa dernière classe.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []

    enrollments = (
        StudentEnrollment.objects
        .filter(school=school)
        .filter(
            Q(enrollment_number__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(student__first_name__icontains=query)
            | Q(student__username__icontains=query)
        )
        .select_related("student", "school_class__level", "academic_year", "level")
        .order_by("student_id", "-academic_year__start_date")
    )

    seen = {}
    for enrollment in enrollments:
        if enrollment.student_id in seen:
            continue
        seen[enrollment.student_id] = {
            "student": enrollment.student_id,
            "name": enrollment.student.get_full_name(),
            "matricule": enrollment.enrollment_number,
            "status": enrollment.student.student_status,
            "status_label": enrollment.student.get_student_status_display(),
            "last_year": enrollment.academic_year.name,
            "last_class": enrollment.school_class.group if enrollment.school_class else "",
            "last_level": enrollment.level.name if enrollment.level else "",
        }
        if len(seen) >= limit:
            break
    return list(seen.values())


def discipline_summary(enrollment):
    """Retards, absences et incidents d'une inscription, comptés et détaillés."""
    records = list(
        DisciplineRecord.objects.filter(enrollment=enrollment)
        .select_related("recorded_by").order_by("-occurred_on")
    )

    def total(entry_type):
        rows = [row for row in records if row.entry_type == entry_type]
        return {
            "count": len(rows),
            "hours": str(sum((row.late_hours for row in rows), Decimal("0")).quantize(CENTS)),
        }

    return {
        "late": total(DisciplineRecord.EntryType.LATE),
        "absence": total(DisciplineRecord.EntryType.ABSENCE),
        "incident": total(DisciplineRecord.EntryType.INCIDENT),
        "records": [
            {
                "id": row.id,
                "occurred_on": row.occurred_on,
                "type": row.get_entry_type_display(),
                "severity": row.get_severity_display(),
                "hours": str(row.late_hours),
                "description": row.description,
                "recorded_by": row.recorded_by.get_full_name() if row.recorded_by else "",
            }
            for row in records
        ],
    }


def attendance_summary(enrollment):
    """Appels où l'élève était attendu, par statut relevé."""
    counts = dict.fromkeys(
        (status for status, _ in AttendanceRecord.Status.choices), 0,
    )
    for record in AttendanceRecord.objects.filter(enrollment=enrollment):
        counts[record.status] = counts.get(record.status, 0) + 1
    return {
        "sessions": sum(counts.values()),
        "present": counts.get(AttendanceRecord.Status.PRESENT, 0),
        "absent": counts.get(AttendanceRecord.Status.ABSENT, 0),
        "late": counts.get(AttendanceRecord.Status.LATE, 0),
        "excused": counts.get(AttendanceRecord.Status.EXCUSED, 0),
    }


def fees_summary(enrollment):
    """Écolage attendu, encaissé et restant dû sur une inscription."""
    plan = (
        TuitionFeePlan.objects.filter(school_class=enrollment.school_class).first()
        if enrollment.school_class_id else None
    )
    if plan is None:
        return {"due": "0.00", "paid": "0.00", "outstanding": "0.00"}

    female = enrollment.student.gender == CustomUser.Gender.FEMALE
    due = sum(
        (item.female_amount if female else item.male_amount)
        for item in ClassFeeItem.objects.filter(plan=plan)
    ) or Decimal("0")
    paid = enrollment.fee_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return {
        "due": str(Decimal(due).quantize(CENTS)),
        "paid": str(paid.quantize(CENTS)),
        "outstanding": str(max(Decimal("0"), Decimal(due) - paid).quantize(CENTS)),
    }


def session_results(enrollment):
    """Bulletins de l'inscription : une ligne par session éditée."""
    cards = (
        ReportCard.objects.filter(enrollment=enrollment)
        .select_related("session").order_by("session__start_date")
    )
    return [
        {
            "session": card.session.name,
            "label": card.session.label,
            "is_final": card.session.is_final,
            "average": str(card.general_average) if card.general_average is not None else None,
            "rank": card.rank,
            "exam_average": str(card.exam_average) if card.exam_average is not None else None,
            "issued_on": card.issued_on,
        }
        for card in cards
    ]


def student_journey(school, student_id):
    """Dossier complet d'un élève : une entrée par année d'inscription."""
    student = CustomUser.objects.get(pk=student_id)
    enrollments = (
        StudentEnrollment.objects
        .filter(school=school, student=student)
        .select_related("academic_year", "school_class__level", "level", "guardian")
        .prefetch_related("fee_payments")
        .order_by("academic_year__start_date")
    )

    years = []
    for enrollment in enrollments:
        sessions = session_results(enrollment)
        years.append({
            "enrollment": enrollment.id,
            "academic_year": enrollment.academic_year.name,
            "is_closed": enrollment.academic_year.is_closed,
            "matricule": enrollment.enrollment_number,
            "level": enrollment.level.name if enrollment.level else "",
            "series": enrollment.series,
            "class": enrollment.school_class.group if enrollment.school_class else "",
            "status": enrollment.get_status_display(),
            "sessions": sessions,
            # Moyenne de l'année : moyenne des sessions effectivement éditées,
            # même règle que la moyenne annuelle des bulletins.
            "annual_average": annual_average(sessions),
            "discipline": discipline_summary(enrollment),
            "attendance": attendance_summary(enrollment),
            "fees": fees_summary(enrollment),
        })

    debts = CarriedDebt.objects.filter(school=school, student=student).select_related("origin_year")
    return {
        "student": {
            "id": student.id,
            "name": student.get_full_name(),
            "username": student.username,
            "gender": student.get_gender_display() if student.gender else "",
            "date_of_birth": student.date_of_birth,
            "status": student.student_status,
            "status_label": student.get_student_status_display(),
            "year_result": student.get_year_result_display() if student.year_result else "",
            "phone": student.phone or "",
            "email": student.email or "",
            "health_information": student.health_information,
        },
        "years": years,
        "carried_debts": [
            {
                "id": debt.id,
                "origin_year": debt.origin_year.name,
                "amount": str(debt.amount),
                "outstanding": str(debt.outstanding),
            }
            for debt in debts
        ],
        "totals": {
            "years": len(years),
            "classes": [year["class"] for year in years if year["class"]],
            "report_cards": sum(len(year["sessions"]) for year in years),
            "late": sum(year["discipline"]["late"]["count"] for year in years),
            "absence": sum(year["discipline"]["absence"]["count"] for year in years),
            "incident": sum(year["discipline"]["incident"]["count"] for year in years),
            "attendance_absent": sum(year["attendance"]["absent"] for year in years),
            "outstanding": str(sum(
                (Decimal(year["fees"]["outstanding"]) for year in years), Decimal("0"),
            ).quantize(CENTS)),
        },
    }
