"""Clôture d'une session académique (trimestre ou semestre).

Clôturer, c'est arrêter les comptes de la période : on fige les bulletins, on
archive ce qui les alimente, puis on verrouille l'écriture. La session reste
entièrement consultable — une session close est en lecture seule, pas masquée.

Le périmètre archivé est celui que porte la session :

- les **bulletins** sont générés s'ils ne l'ont pas encore été ; leur `payload`
  contient déjà le détail des notes, les moyennes, les rangs et les
  statistiques de classe ;
- les **notes** brutes sont archivées à part, car un élève sorti en cours de
  période n'a pas de bulletin et disparaîtrait sinon de la trace ;
- la **discipline** et les **appels** sont rattachés à l'année, pas à la
  session : on les rapporte à la période par l'intervalle de dates de la
  session, croisé avec ses classes.

L'écolage et les dépenses restent hors du périmètre : ils suivront un contrôle
de caisse et un compte d'exploitation, sur une logique de trésorerie qui n'est
pas celle de l'année scolaire.
"""

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    AttendanceSession,
    DisciplineRecord,
    GradeEntry,
    ReportCard,
    SchoolClass,
    SessionClosure,
)
from .reportcards import generate_school, scheme_for


class ClosureError(Exception):
    """Clôture impossible : la session n'est pas en état d'être arrêtée."""


# ── Périmètre de la session ──────────────────────────────────────────────────

def session_classes(session):
    """Classes rattachées à la session."""
    return SchoolClass.objects.filter(academic_sessions=session)


def discipline_queryset(session):
    """Discipline de la période, pour les classes de la session.

    `DisciplineRecord` ne connaît que l'année : on le ramène à la session par
    la date de l'incident et par la classe de l'inscription.
    """
    return DisciplineRecord.objects.filter(
        academic_year=session.academic_year,
        enrollment__school_class__in=session_classes(session),
        occurred_on__range=(session.start_date, session.end_date),
    )


def attendance_queryset(session):
    """Appels de la période, pour les classes de la session."""
    return AttendanceSession.objects.filter(
        academic_year=session.academic_year,
        school_class__in=session_classes(session),
        taken_on__range=(session.start_date, session.end_date),
    )


def grade_entry_queryset(session):
    """Notes de la session, via le barème qui lui est propre."""
    scheme = scheme_for(session)
    if scheme is None:
        return GradeEntry.objects.none()
    return GradeEntry.objects.filter(line__scheme=scheme)


# ── Construction de l'archive ────────────────────────────────────────────────

def build_grade_archive(session):
    """Notes brutes, sous forme compacte.

    Une ligne par note : inscription, matière de classe, ligne de barème,
    valeur. Les libellés sont repris à côté pour que l'archive se relise sans
    dépendre de tables qui auront pu bouger.
    """
    entries = (
        grade_entry_queryset(session)
        .select_related(
            "enrollment__student", "class_subject__subject",
            "class_subject__school_class", "line",
        )
        .order_by("enrollment_id", "class_subject_id", "line_id")
    )
    return [
        {
            "enrollment_id": entry.enrollment_id,
            "matricule": entry.enrollment.enrollment_number or "",
            "student": entry.enrollment.student.get_full_name(),
            "class": entry.class_subject.school_class.group,
            "class_subject_id": entry.class_subject_id,
            "subject": entry.class_subject.subject.name,
            "line_id": entry.line_id,
            "line": entry.line.name,
            "max_score": str(entry.line.max_score),
            "score": str(entry.score),
        }
        for entry in entries
    ]


def build_discipline_archive(session):
    records = (
        discipline_queryset(session)
        .select_related("enrollment__student", "enrollment__school_class")
        .order_by("occurred_on", "id")
    )
    return [
        {
            "id": record.id,
            "enrollment_id": record.enrollment_id,
            "matricule": record.enrollment.enrollment_number or "",
            "student": record.enrollment.student.get_full_name(),
            "class": (
                record.enrollment.school_class.group
                if record.enrollment.school_class_id else ""
            ),
            "entry_type": record.entry_type,
            "entry_type_label": record.get_entry_type_display(),
            "occurred_on": record.occurred_on.isoformat(),
            "late_hours": str(record.late_hours),
            "incident_type": record.incident_type,
            "severity": record.severity,
            "description": record.description,
            "action_taken": record.action_taken,
        }
        for record in records
    ]


def build_attendance_archive(session):
    """Appels et leur détail élève.

    Un appel sans aucune ligne reste archivé : il atteste que l'appel a bien
    été fait, ce qu'une classe sans absence ne dit pas autrement.
    """
    sessions = (
        attendance_queryset(session)
        .select_related("school_class", "class_subject__subject")
        .prefetch_related("records__enrollment__student")
        .order_by("taken_on", "id")
    )
    archive = []
    for call in sessions:
        archive.append({
            "id": call.id,
            "taken_on": call.taken_on.isoformat(),
            "class": call.school_class.group,
            "school_class_id": call.school_class_id,
            "subject": call.class_subject.subject.name if call.class_subject_id else "",
            "period": call.period,
            "note": call.note,
            "records": [
                {
                    "enrollment_id": record.enrollment_id,
                    "matricule": record.enrollment.enrollment_number or "",
                    "student": record.enrollment.student.get_full_name(),
                    "status": record.status,
                    "status_label": record.get_status_display(),
                    "minutes_late": record.minutes_late,
                    "comment": record.comment,
                }
                for record in call.records.all()
            ],
        })
    return archive


def build_scheme_archive(session):
    """Instantané du barème en vigueur à la clôture.

    Le barème appartient à l'école et reste modifiable après coup : sans cette
    copie, rouvrir un trimestre clos l'afficherait avec les poids du jour et
    des moyennes qui ne seraient plus celles des bulletins remis.
    """
    scheme = scheme_for(session)
    if scheme is None:
        return None
    groups = {
        group.id: {"id": group.id, "name": group.name,
                   "weight": str(group.weight) if group.weight is not None else None,
                   "order": group.order}
        for group in scheme.groups.all()
    }
    return {
        "id": scheme.id,
        "calculation_method": scheme.calculation_method,
        "groups": [groups[key] for key in sorted(groups, key=lambda k: groups[k]["order"])],
        "lines": [
            {
                "id": line.id,
                "name": line.name,
                "max_score": str(line.max_score),
                "weight": str(line.weight) if line.weight is not None else None,
                "order": line.order,
                "group_id": line.group_id,
            }
            for line in scheme.lines.all()
        ],
    }


def scheme_snapshot_for(session):
    """Barème figé d'une session clôturée, ou None si elle est encore ouverte."""
    closure = getattr(session, "closure", None)
    if closure is None:
        return None
    return (closure.payload or {}).get("scheme")


def build_archive(session):
    return {
        "session": {
            "id": session.id,
            "name": session.name,
            "label": session.label,
            "start_date": session.start_date.isoformat(),
            "end_date": session.end_date.isoformat(),
            "academic_year": session.academic_year.name,
            "classes": sorted(
                session_classes(session).values_list("group", flat=True)
            ),
        },
        "archived_at": timezone.now().isoformat(),
        "scheme": build_scheme_archive(session),
        "grades": build_grade_archive(session),
        "discipline": build_discipline_archive(session),
        "attendance": build_attendance_archive(session),
    }


# ── Clôture ──────────────────────────────────────────────────────────────────

@transaction.atomic
def close_session(session, user=None):
    """Génère les bulletins manquants, archive la session, puis la verrouille.

    Tout tient dans une transaction : une archive à moitié écrite laisserait
    une session close dont on ne pourrait plus reconstituer l'état.
    """
    if session.is_closed:
        raise ClosureError("Cette session est déjà clôturée.")

    school = session.academic_year.school

    if scheme_for(session) is None:
        raise ClosureError(
            "Les lignes de notes ne sont pas configurées pour cette session : "
            "les bulletins ne peuvent pas être générés."
        )

    # Les bulletins déjà générés font foi : on ne régénère pas, sans quoi une
    # correction faite après coup sur une classe serait écrasée.
    cards = ReportCard.objects.filter(session=session, school_class__school=school)
    if not cards.exists():
        generate_school(session, school, user=user)

    archive = build_archive(session)

    closure = SessionClosure.objects.create(
        session=session,
        closed_by=user,
        report_card_count=cards.count(),
        grade_entry_count=len(archive["grades"]),
        discipline_count=len(archive["discipline"]),
        attendance_session_count=len(archive["attendance"]),
        attendance_record_count=sum(
            len(call["records"]) for call in archive["attendance"]
        ),
        payload=archive,
    )

    session.is_closed = True
    session.is_active = False
    session.save(update_fields=["is_closed", "is_active"])
    return closure


# ── Verrouillage ─────────────────────────────────────────────────────────────

def closed_session_for_date(academic_year, school_class, day):
    """Session close couvrant ce jour pour cette classe, s'il y en a une.

    Sert aux écritures qui ne connaissent pas la session — discipline et
    appels sont datés, pas rattachés.
    """
    if day is None or school_class is None:
        return None
    if isinstance(day, str):
        # L'API accepte la date en chaîne ; une valeur illisible est laissée
        # aux validateurs du sérialiseur plutôt que traitée comme « non close ».
        day = parse_date(day)
        if day is None:
            return None
    return (
        academic_year.sessions.filter(
            is_closed=True,
            classes=school_class,
            start_date__lte=day,
            end_date__gte=day,
        )
        .first()
    )
