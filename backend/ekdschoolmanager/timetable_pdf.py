"""Édition PDF des emplois du temps.

Deux vues du même emploi du temps :

* par classe — ce que les élèves affichent en salle ;
* par enseignant — ce que chaque professeur emporte.

Chaque grille tient sur une page, en paysage : les jours en colonnes, les
créneaux horaires en lignes, pauses comprises pour que la journée se lise
sans rupture.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .timetable import DAY_LABELS

# Palette : sobre à l'impression, y compris en noir et blanc.
HEADER_BACKGROUND = colors.HexColor("#1d4ed8")
HEADER_TEXT = colors.white
HOUR_BACKGROUND = colors.HexColor("#eef2f9")
BREAK_BACKGROUND = colors.HexColor("#f8d7b8")
GRID_LINE = colors.HexColor("#b9c2d0")
EMPTY_TEXT = colors.HexColor("#9aa5b4")

TITLE_STYLE = ParagraphStyle(
    "TimetableTitle", fontName="Helvetica-Bold", fontSize=15, leading=18,
    alignment=TA_CENTER, spaceAfter=2,
)
SUBTITLE_STYLE = ParagraphStyle(
    "TimetableSubtitle", fontName="Helvetica", fontSize=9.5, leading=12,
    alignment=TA_CENTER, textColor=colors.HexColor("#54607a"), spaceAfter=6,
)
CELL_STYLE = ParagraphStyle(
    "TimetableCell", fontName="Helvetica-Bold", fontSize=7.6, leading=9,
    alignment=TA_CENTER,
)
CELL_SUB_STYLE = ParagraphStyle(
    "TimetableCellSub", fontName="Helvetica", fontSize=6.6, leading=8,
    alignment=TA_CENTER, textColor=colors.HexColor("#44506a"),
)
EMPTY_STYLE = ParagraphStyle(
    "TimetableEmpty", fontName="Helvetica", fontSize=7, leading=9,
    alignment=TA_CENTER, textColor=EMPTY_TEXT,
)


def _short(value):
    """08:50:00 -> 08:50"""
    return value.strftime("%H:%M")


def _cell(lines):
    """Une case de la grille : intitulé en gras, précisions en dessous."""
    if not lines:
        return Paragraph("—", EMPTY_STYLE)
    blocks = [Paragraph(lines[0], CELL_STYLE)]
    blocks.extend(Paragraph(line, CELL_SUB_STYLE) for line in lines[1:] if line)
    return blocks[0] if len(blocks) == 1 else blocks


def _grid(timetable, entries, days):
    """Construit le tableau : une ligne par créneau, une colonne par jour.

    `entries` associe (jour, ordre du créneau) au contenu de la case.
    """
    periods = list(timetable.periods.all())
    header = ["Horaire"] + [DAY_LABELS.get(day, f"Jour {day + 1}") for day in days]

    rows = [header]
    break_rows = []
    for position, period in enumerate(periods, start=1):
        label = f"{_short(period.start_time)}\n{_short(period.end_time)}"
        row = [Paragraph(label.replace("\n", "<br/>"), CELL_SUB_STYLE)]
        if period.is_break:
            break_rows.append(position)
            # Une pause traverse la semaine : son intitulé suffit.
            row.append(Paragraph(period.label, CELL_STYLE))
            row.extend([""] * (len(days) - 1))
        else:
            for day in days:
                row.append(_cell(entries.get((day, period.order))))
        rows.append(row)

    available = landscape(A4)[0] - 22 * mm
    time_column = 20 * mm
    day_column = (available - time_column) / max(1, len(days))
    table = Table(
        rows,
        colWidths=[time_column] + [day_column] * len(days),
        repeatRows=1,
    )

    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_LINE),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BACKGROUND),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BACKGROUND", (0, 1), (0, -1), HOUR_BACKGROUND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
    ]
    for row_index in break_rows:
        style.append(("BACKGROUND", (0, row_index), (-1, row_index), BREAK_BACKGROUND))
        # L'intitulé de la pause s'étend sur toute la largeur.
        style.append(("SPAN", (1, row_index), (-1, row_index)))
    table.setStyle(TableStyle(style))
    return table


def _page(title, subtitle, table):
    return KeepTogether([
        Paragraph(title, TITLE_STYLE),
        Paragraph(subtitle, SUBTITLE_STYLE),
        table,
        Spacer(1, 4 * mm),
    ])


def _document(buffer, title):
    return SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=11 * mm, rightMargin=11 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title=title, author="EKD School Manager",
    )


def _slots(timetable, **filters):
    return timetable.slots.filter(**filters).select_related(
        "school_class", "school_class__level", "class_subject__subject", "teacher",
    )


def class_timetables_pdf(timetable, school_classes):
    """Une page par classe : matière, enseignant."""
    buffer = BytesIO()
    document = _document(buffer, "Emplois du temps par classe")
    days = list(range(timetable.days_per_week))
    school = timetable.school
    year = timetable.academic_year

    story = []
    for position, school_class in enumerate(school_classes):
        entries = {}
        for slot in _slots(timetable, school_class=school_class):
            lines = [slot.class_subject.subject.name]
            if slot.teacher:
                lines.append(slot.teacher.get_full_name())
            entries[(slot.day, _order_of(timetable, slot))] = lines

        if position:
            story.append(PageBreak())
        story.append(_page(
            f"Emploi du temps — {school_class.group}",
            f"{school.name} · {school_class.level.name} · Année {year.name}",
            _grid(timetable, entries, days),
        ))

    if not story:
        story.append(Paragraph("Aucune classe sélectionnée.", SUBTITLE_STYLE))
    document.build(story)
    return buffer.getvalue()


def teacher_timetables_pdf(timetable, teachers):
    """Une page par enseignant : matière, classe.

    Les classes réunies pour une même séance apparaissent sur une seule ligne,
    l'enseignant n'assurant qu'un cours.
    """
    buffer = BytesIO()
    document = _document(buffer, "Emplois du temps par enseignant")
    days = list(range(timetable.days_per_week))
    school = timetable.school
    year = timetable.academic_year

    story = []
    for position, teacher in enumerate(teachers):
        grouped = {}
        for slot in _slots(timetable, teacher=teacher):
            key = (slot.day, _order_of(timetable, slot))
            entry = grouped.setdefault(key, {"subject": slot.class_subject.subject.name, "classes": []})
            entry["classes"].append(slot.school_class.group)

        entries = {
            key: [value["subject"], ", ".join(sorted(set(value["classes"])))]
            for key, value in grouped.items()
        }
        # Un créneau partagé par deux classes réunies reste une heure de cours.
        hours = len(grouped)

        if position:
            story.append(PageBreak())
        story.append(_page(
            f"Emploi du temps — {teacher.get_full_name()}",
            f"{school.name} · Année {year.name} · {hours} heure(s) de cours par semaine",
            _grid(timetable, entries, days),
        ))

    if not story:
        story.append(Paragraph("Aucun enseignant sélectionné.", SUBTITLE_STYLE))
    document.build(story)
    return buffer.getvalue()


def _order_of(timetable, slot):
    """Retrouve l'ordre du créneau à partir de son heure de début.

    Les créneaux sont stockés avec leurs horaires ; la grille, elle, raisonne
    en numéros de période.
    """
    cache = getattr(timetable, "_period_order_cache", None)
    if cache is None:
        cache = {period.start_time: period.order for period in timetable.periods.all()}
        timetable._period_order_cache = cache
    return cache.get(slot.start_time)
