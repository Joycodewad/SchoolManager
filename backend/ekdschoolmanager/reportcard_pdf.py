"""Édition PDF des bulletins, au format officiel togolais.

La page reprend la disposition d'un bulletin d'établissement : mentions
d'État à gauche, coordonnées de l'école à droite, identité de l'élève, tableau
des matières regroupées par type avec sous-totaux, puis synthèse et
appréciations.

Un bulletin par page ; le contenu vient de l'instantané figé à la génération,
jamais d'un recalcul — ce qui a été remis aux familles ne doit pas bouger.
"""

from decimal import Decimal, InvalidOperation
from io import BytesIO
from math import atan2, degrees

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

LINE = colors.HexColor("#111827")
SOFT_LINE = colors.HexColor("#9aa3b2")
GROUP_BACKGROUND = colors.HexColor("#dfe6f0")
HEADER_BACKGROUND = colors.HexColor("#eef1f6")


def style(name, size, leading=None, bold=False, align=TA_LEFT, color=LINE):
    return ParagraphStyle(
        name, fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading or size + 2, alignment=align, textColor=color,
    )

STATE_STYLE = style("state", 6.6, 8.4, align=TA_CENTER)
SCHOOL_STYLE = style("school", 6.6, 8.4, align=TA_CENTER)
SCHOOL_NAME_STYLE = style("schoolName", 8.4, 10, bold=True, align=TA_CENTER)
TITLE_STYLE = style("title", 12.5, 15, bold=True, align=TA_CENTER)
SUBTITLE_STYLE = style("subtitle", 8, 10, align=TA_CENTER)
IDENTITY_STYLE = style("identity", 7.4, 9.4)
CELL_STYLE = style("cell", 7, 8.6)
CELL_BOLD = style("cellBold", 7, 8.6, bold=True)
CELL_CENTER = style("cellCenter", 7, 8.6, align=TA_CENTER)
GROUP_STYLE = style("group", 6.8, 8.4, bold=True)
FOOT_STYLE = style("foot", 7.2, 9.4)


def decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def show(value, dash="-"):
    return dash if value in (None, "") else str(value)


# Abréviations usuelles des colonnes de notes sur un bulletin togolais.
COLUMN_ABBREVIATIONS = {
    "interrogation": "Note inter.",
    "note d’interrogation": "Note inter.",
    "note d'interrogation": "Note inter.",
    "note de classe": "Note de classe",
    "devoir": "Note dev.",
    "note de devoir": "Note dev.",
    "composition": "Note comp.",
    "note de composition": "Note comp.",
    "examen": "Examen",
}

# Une note de composition clôt le trimestre ; tout le reste (interrogations,
# devoirs) forme le travail de classe, dont la moyenne s'intercale avant elle.
COMPOSITION_KEYWORDS = ("composition", "comp.", "examen")


def abbreviate(name):
    """Titre de colonne assez court pour tenir sans césure."""
    key = (name or "").strip().lower()
    if key in COLUMN_ABBREVIATIONS:
        return COLUMN_ABBREVIATIONS[key]
    letters = (name or "").upper()
    return letters if len(letters) <= 6 else letters[:5] + "."


def ordinal(rank):
    """Rang à la française : « 1er », « 2ème »… vide si non classé."""
    if rank in (None, ""):
        return ""
    return "1er" if int(rank) == 1 else f"{int(rank)}ème"


def is_composition(column):
    """La colonne porte-t-elle la note de composition ?"""
    key = (column.get("name") or "").strip().lower()
    return any(word in key for word in COMPOSITION_KEYWORDS)


def class_work_average(subject, columns):
    """Moyenne des notes de classe : tout sauf la composition.

    Ramenée sur 20 comme le reste du bulletin, pour qu'une ligne notée sur 10
    ne pèse pas le double d'une ligne sur 20. Retourne None tant qu'une note
    manque : une moyenne partielle induirait en erreur.
    """
    marks = []
    for column in columns:
        if is_composition(column):
            continue
        value = decimal_or_none(subject["scores"].get(str(column["id"])))
        if value is None:
            return None
        maximum = decimal_or_none(column.get("max_score")) or Decimal("20")
        if not maximum:
            return None
        marks.append(value * Decimal("20") / maximum)
    if not marks:
        return None
    return (sum(marks) / len(marks)).quantize(Decimal("0.01"))


def header_block(school, logo_path):
    """Bandeau officiel : État à gauche, école à droite, logo entre les deux.

    Chaque ligne vient du paramétrage ; une ligne vide est simplement omise,
    sans laisser de blanc dans le bandeau.
    """
    state = []
    if school.get("country"):
        state.append(Paragraph(f"<b>{school['country'].upper()}</b>", STATE_STYLE))
    if school.get("country_motto"):
        state.append(Paragraph(f"<i>{school['country_motto']}</i>", STATE_STYLE))
    for key in ("ministry", "cabinet", "general_secretariat", "education_direction"):
        if school.get(key):
            state.append(Paragraph(school[key].upper(), STATE_STYLE))
    if school.get("direction_city"):
        state.append(Paragraph(school["direction_city"].upper(), STATE_STYLE))
    if school.get("inspection"):
        state.append(Paragraph(school["inspection"].upper(), STATE_STYLE))

    right = [Paragraph("<b>ÉTABLISSEMENT SCOLAIRE</b>", SCHOOL_STYLE),
             Paragraph(school["name"].upper(), SCHOOL_NAME_STYLE)]
    if school.get("motto"):
        right.append(Paragraph(f"<i>{school['motto']}</i>", SCHOOL_STYLE))
    contact = " · ".join(part for part in (school.get("phone"), school.get("postal_box"),
                                           school.get("city")) if part)
    if contact:
        right.append(Paragraph(contact, SCHOOL_STYLE))

    middle = ""
    if logo_path:
        try:
            middle = Image(logo_path, width=16 * mm, height=16 * mm)
        except Exception:
            # Un logo illisible ne doit pas empêcher d'éditer le bulletin.
            middle = ""

    table = Table([[state, middle, right]], colWidths=[68 * mm, 22 * mm, 68 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def identity_block(card, session, school_class, headcount):
    left = [
        f"<b>NOM &amp; PRÉNOMS :</b> {card['student_name']}",
        f"<b>DATE DE NAISSANCE :</b> {show(card.get('date_of_birth'), 'N/A')}",
        f"<b>SEXE :</b> {show(card.get('gender'), 'N/A')}",
    ]
    right = [
        f"<b>MATRICULE :</b> {show(card.get('matricule'), 'N/A')}",
        f"<b>CLASSE :</b> {school_class}",
        f"<b>EFFECTIF :</b> {headcount} élèves",
    ]
    rows = [[Paragraph(a, IDENTITY_STYLE), Paragraph(b, IDENTITY_STYLE)]
            for a, b in zip(left, right)]
    table = Table(rows, colWidths=[105 * mm, 73 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SOFT_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table


def subjects_table(card, options):
    """Tableau des matières, éventuellement regroupées par type."""
    columns = card.get("line_columns", []) if options.get("show_score_detail") else []

    header = ["MATIÈRES"]
    # Les colonnes de notes sont étroites : on abrège plutôt que de laisser
    # ReportLab couper un mot au milieu (« INTERROGA / TION »).
    header += [abbreviate(column["name"]) for column in columns]
    header += ["MOY.", "COEF"]
    if options.get("show_rank"):
        header.append("RANG")
    if options.get("show_teacher"):
        header.append("PROFESSEUR")
    if options.get("show_appreciation"):
        header.append("APPRÉCIATION")

    rows = [[Paragraph(f"<b>{title}</b>", CELL_CENTER) for title in header]]
    spans, shaded = [], []

    for group in card.get("groups", []):
        if group.get("name"):
            spans.append(len(rows))
            rows.append([Paragraph(group["name"].upper(), GROUP_STYLE)]
                        + [""] * (len(header) - 1))

        for subject in group["subjects"]:
            line = [Paragraph(subject["subject"], CELL_STYLE)]
            for column in columns:
                line.append(Paragraph(show(subject["scores"].get(str(column["id"]))), CELL_CENTER))
            line.append(Paragraph(show(subject["average"]), CELL_BOLD))
            line.append(Paragraph(show(subject["coefficient"]), CELL_CENTER))
            if options.get("show_rank"):
                line.append(Paragraph("", CELL_CENTER))
            if options.get("show_teacher"):
                line.append(Paragraph(subject.get("teacher", ""), CELL_STYLE))
            if options.get("show_appreciation"):
                line.append(Paragraph(subject.get("appreciation", ""), CELL_STYLE))
            rows.append(line)

        # Sans la colonne CAF, une ligne « Sous-Total » n'aurait aucune valeur
        # à porter : le titre du groupe suffit à séparer les blocs.

    shaded.append(len(rows))
    rows.append([Paragraph("<b>TOTAL GÉNÉRAL DES COEFFICIENTS</b>", GROUP_STYLE)]
                + [""] * (len(header) - 2)
                + [Paragraph(f"<b>{card['coefficient_total']}</b>", CELL_CENTER)])

    subject_width = 40 * mm
    tail = [11 * mm] * len(columns) + [12 * mm, 11 * mm]
    if options.get("show_rank"):
        tail.append(11 * mm)
    remaining = 178 * mm - subject_width - sum(tail)
    extras = sum(1 for key in ("show_teacher", "show_appreciation") if options.get(key))
    widths = [subject_width] + tail + [remaining / extras] * extras if extras else [subject_width] + tail

    table = Table(rows, colWidths=widths, repeatRows=1)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.3, SOFT_LINE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BACKGROUND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for row in spans:
        commands += [("SPAN", (0, row), (-1, row)),
                     ("BACKGROUND", (0, row), (-1, row), GROUP_BACKGROUND)]
    for row in shaded:
        # L'intitulé court jusqu'à l'avant-dernière colonne ; la dernière
        # reçoit le total des coefficients (vide pour un sous-total de groupe).
        commands += [("SPAN", (0, row), (-2, row)),
                     ("BACKGROUND", (0, row), (-1, row), HEADER_BACKGROUND)]
    table.setStyle(TableStyle(commands))
    return table


def summary_block(card, options):
    """Synthèse : moyenne, rang, sessions précédentes et repères de la classe."""
    statistics = card.get("statistics") or {}
    history = card.get("history") or {}
    rows = [["MOYENNE GÉNÉRALE :", show(card.get("general_average"))]]
    if options.get("show_rank"):
        rows.append(["RANG :", show(card.get("rank"))])

    # Rappel des sessions déjà éditées cette année, la courante exclue : elle
    # figure déjà en tête sous « MOYENNE GÉNÉRALE ».
    for term in history.get("terms", []):
        if not term.get("is_current"):
            rows.append([f"Moyenne — {term['name']} :", show(term.get("average"))])
    # La moyenne annuelle n'apparaît qu'à la dernière session de l'année.
    if history.get("is_final"):
        rows.append(["MOYENNE ANNUELLE :", show(history.get("annual_average"))])

    if options.get("show_class_statistics"):
        rows += [
            ["Plus forte moyenne :", show(statistics.get("highest"))],
            ["Plus faible moyenne :", show(statistics.get("lowest"))],
            ["Moyenne générale de la classe :", show(statistics.get("class_average"))],
        ]
    if options.get("show_appreciation"):
        rows.append(["APPRÉCIATION :", show(card.get("appreciation"), "")])

    body = [[Paragraph(f"<b>{label}</b>", CELL_STYLE), Paragraph(f"<b>{value}</b>", CELL_CENTER)]
            for label, value in rows]
    table = Table(body, colWidths=[60 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, SOFT_LINE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def footer_block(school, council_note, homeroom_teacher=""):
    city = school.get("city") or ""
    # Sans ville renseignée, on n'imprime pas une virgule orpheline.
    place = f"Fait à {city}, le ……………………" if city else "Fait le ……………………"
    titulaire = (
        f"<br/><br/><b>Professeur titulaire :</b> {homeroom_teacher}"
        if homeroom_teacher else ""
    )
    rows = [[
        Paragraph("<b>Décision du conseil :</b><br/><br/>" + (council_note or "") + titulaire,
                  FOOT_STYLE),
        Paragraph(f"{place}<br/><br/><b>LE DIRECTEUR / PROVISEUR</b>", FOOT_STYLE),
    ]]
    table = Table(rows, colWidths=[110 * mm, 68 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SOFT_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return table


# ── Modèle officiel ──────────────────────────────────────────────────────────
#
# Reprend la maquette administrative : le bandeau d'État et l'identité tiennent
# sur la même bande que le titre, la grille des matières porte toutes les notes
# et se ferme par une ligne « TOTAUX », puis un pied récapitulatif met en
# regard les trimestres, les repères de classe et le relevé d'absences.

OFFICIAL_STATE_STYLE = style("officialState", 5.9, 7.2, align=TA_CENTER)
OFFICIAL_TITLE_STYLE = style("officialTitle", 13, 15, bold=True, align=TA_CENTER)
OFFICIAL_SUBTITLE_STYLE = style("officialSubtitle", 9, 11, bold=True, align=TA_CENTER)
OFFICIAL_CELL = style("officialCell", 6.2, 7.6)
OFFICIAL_CELL_CENTER = style("officialCellCenter", 6.2, 7.6, align=TA_CENTER)
OFFICIAL_CELL_BOLD = style("officialCellBold", 6.2, 7.6, bold=True, align=TA_CENTER)
OFFICIAL_HEAD = style("officialHead", 5.6, 6.8, bold=True, align=TA_CENTER)
OFFICIAL_FOOT = style("officialFoot", 6.4, 8)

# Lignes du relevé de vie scolaire, à remplir à la main après édition.
DISCIPLINE_ROWS = [
    ("Absence", "0 Heure(s)"),
    ("Retard", "0 Heure(s)"),
    ("Punition", "0 Heure(s)"),
    ("Exclusion", ""),
    ("Félicitation", ""),
    ("Encouragement", ""),
    ("Tableau d’honneur", ""),
    ("Avertissement", ""),
    ("Blâme", ""),
]


def session_caption(card, session):
    """Nom de la session, suivi de son rang dans l'année quand il est connu.

    La dernière session est annoncée comme telle : c'est celle qui porte la
    moyenne annuelle, et le lecteur doit savoir qu'il tient le bulletin de fin
    d'année. Une classe qui n'a qu'une session ne mérite pas cette précision.
    """
    history = card.get("history") or {}
    name = session["name"]
    total = history.get("total") or 0
    if total < 2:
        return name
    if history.get("is_final"):
        return f"{name} — dernière session de l’année ({total}/{total})"
    current = next(
        (term["order"] for term in history.get("terms", []) if term.get("is_current")),
        None,
    )
    return f"{name} ({current}/{total})" if current else name


def official_header(card, school, session, year_name, logo_path):
    """Bandeau du modèle officiel : État, logo et titre, école et identité."""
    state = []
    for key in ("ministry", "cabinet", "general_secretariat", "education_direction"):
        if school.get(key):
            state.append(Paragraph(school[key].upper(), OFFICIAL_STATE_STYLE))
    for key in ("direction_city", "inspection"):
        if school.get(key):
            state.append(Paragraph(school[key].upper(), OFFICIAL_STATE_STYLE))

    logo = ""
    if logo_path:
        try:
            logo = Image(logo_path, width=18 * mm, height=18 * mm)
        except Exception:
            # Un logo illisible ne doit pas empêcher d'éditer le bulletin.
            logo = ""

    right = []
    if school.get("country"):
        right.append(Paragraph(f"<b>{school['country'].upper()}</b>", OFFICIAL_STATE_STYLE))
    if school.get("country_motto"):
        right.append(Paragraph(school["country_motto"], OFFICIAL_STATE_STYLE))
    right.append(Spacer(1, 2 * mm))
    right.append(Paragraph(school["name"].upper(), TITLE_STYLE))

    banner = Table([[state, logo, right]], colWidths=[62 * mm, 24 * mm, 72 * mm])
    banner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    statistics = card.get("statistics") or {}
    # Colonne de droite du titre : effectif, année, puis sexe et statut encadrés.
    facts = Table(
        [[Paragraph(f"<b>Effectif :</b> {statistics.get('headcount', 0)}", OFFICIAL_FOOT)],
         [Paragraph(f"<b>Année scolaire :</b> {year_name}", OFFICIAL_FOOT)],
         [Paragraph(f"<b>Sexe :</b> {show(card.get('gender'), '')}", OFFICIAL_FOOT)],
         [Paragraph(f"<b>Matricule :</b> {show(card.get('matricule'), '')}", OFFICIAL_FOOT)]],
        colWidths=[46 * mm],
    )
    facts.setStyle(TableStyle([
        ("BOX", (0, 2), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 2), (-1, -1), 0.3, SOFT_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    title = Table(
        [[[Paragraph("BULLETIN DE NOTES", OFFICIAL_TITLE_STYLE),
           Paragraph(f"<i>{session_caption(card, session).upper()}</i>",
                     OFFICIAL_SUBTITLE_STYLE)], facts]],
        colWidths=[112 * mm, 46 * mm],
    )
    title.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    identity = Table(
        [[Paragraph(f"<b>{card['student_name'].upper()}</b>", style("officialName", 9.5, 11, bold=True)),
          Paragraph(f"<b>{card.get('class_name', '')}</b>",
                    style("officialClass", 9.5, 11, bold=True, align=TA_CENTER))]],
        colWidths=[100 * mm, 78 * mm],
    )
    identity.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 20),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return [banner, Spacer(1, 1.5 * mm), title, Spacer(1, 1 * mm), identity]


def official_subjects_table(card, options):
    """Grille des matières du modèle officiel, close par la ligne « TOTAUX ».

    Les colonnes suivent l'ordre du bulletin administratif : les notes de
    classe (interrogation, devoir), leur moyenne, puis la composition.
    """
    columns = card.get("line_columns", []) if options.get("show_score_detail") else []

    # La moyenne des notes de classe s'intercale juste avant la composition.
    class_work = [column for column in columns if not is_composition(column)]
    compositions = [column for column in columns if is_composition(column)]
    # Sans composition identifiée, la colonne n'aurait rien à séparer : on la
    # laisse alors de côté plutôt que de répéter la moyenne trimestrielle.
    with_class_average = bool(class_work) and bool(compositions)

    header = ["Matière"]
    header += [abbreviate(column["name"]) for column in class_work]
    if with_class_average:
        header.append("MOY. note de classe")
    header += [abbreviate(column["name"]) for column in compositions]
    header += ["MOY. trimest.", "Coeff", "Note définitif", "Rang"]
    header += ["Chargé du cours", "Apprée", "Signature"]

    rows = [[Paragraph(title, OFFICIAL_HEAD) for title in header]]
    group_rows = []
    # Nombre de colonnes de notes, la moyenne de classe comprise : sert au
    # calage de la ligne « TOTAUX » et au partage des largeurs.
    score_columns = len(columns) + (1 if with_class_average else 0)

    for group in card.get("groups", []):
        if group.get("name"):
            group_rows.append(len(rows))
            rows.append([Paragraph(group["name"].upper(), GROUP_STYLE)]
                        + [""] * (len(header) - 1))
        for subject in group["subjects"]:
            line = [Paragraph(subject["subject"], OFFICIAL_CELL)]
            for column in class_work:
                line.append(Paragraph(show(subject["scores"].get(str(column["id"]))),
                                      OFFICIAL_CELL_CENTER))
            if with_class_average:
                line.append(Paragraph(show(class_work_average(subject, columns)),
                                      OFFICIAL_CELL_BOLD))
            for column in compositions:
                line.append(Paragraph(show(subject["scores"].get(str(column["id"]))),
                                      OFFICIAL_CELL_CENTER))
            line += [
                Paragraph(show(subject["average"]), OFFICIAL_CELL_BOLD),
                Paragraph(show(subject["coefficient"]), OFFICIAL_CELL_CENTER),
                # « Note définitif » : moyenne × coefficient, le report du barème.
                Paragraph(show(subject.get("weighted")), OFFICIAL_CELL_CENTER),
                Paragraph(ordinal(subject.get("rank")), OFFICIAL_CELL_CENTER),
                Paragraph(subject.get("teacher", ""), OFFICIAL_CELL),
                Paragraph(subject.get("appreciation", ""), OFFICIAL_CELL),
                Paragraph("", OFFICIAL_CELL),
            ]
            rows.append(line)

    total_row = len(rows)
    # Tant qu'aucune note n'est saisie, le total des notes définitives vaut
    # zéro : on imprime un tiret, qui se lit « rien à totaliser » plutôt que
    # « total nul ». Le total des coefficients, lui, est toujours connu.
    definitive_total = decimal_or_none(card.get("weighted_total"))
    rows.append(
        [Paragraph("<b>TOTAUX</b>", OFFICIAL_CELL_BOLD)]
        + [""] * score_columns
        + [Paragraph("", OFFICIAL_CELL_CENTER),
           Paragraph(f"<b>{show(card.get('coefficient_total'))}</b>", OFFICIAL_CELL_BOLD),
           Paragraph(f"<b>{show(card.get('weighted_total')) if definitive_total else '-'}</b>",
                     OFFICIAL_CELL_BOLD),
           Paragraph("", OFFICIAL_CELL_CENTER),
           Paragraph("", OFFICIAL_CELL),
           Paragraph("", OFFICIAL_CELL),
           Paragraph("", OFFICIAL_CELL)]
    )

    # Largeurs : la matière et les trois dernières colonnes fixes, le reste
    # partagé entre les notes pour que le tableau occupe toute la justification.
    fixed = [30 * mm] + [11 * mm, 9 * mm, 12 * mm, 9 * mm] + [26 * mm, 14 * mm, 16 * mm]
    scores_width = (178 * mm - sum(fixed)) / score_columns if score_columns else 0
    widths = [fixed[0]] + [scores_width] * score_columns + fixed[1:]

    table = Table(rows, colWidths=widths, repeatRows=1)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        # La ligne « TOTAUX » court jusqu'à la colonne des coefficients.
        ("SPAN", (0, total_row), (score_columns, total_row)),
    ]
    for row in group_rows:
        commands += [("SPAN", (0, row), (-1, row)),
                     ("BACKGROUND", (0, row), (-1, row), GROUP_BACKGROUND)]
    table.setStyle(TableStyle(commands))
    return table


def official_recap(card, options):
    """Pied récapitulatif : sessions de l'année à gauche, vie scolaire à droite."""
    statistics = card.get("statistics") or {}
    history = card.get("history") or {}

    # Séquence réelle de la classe : les sessions déjà éditées, la courante
    # comprise. Une classe à son premier trimestre n'affiche que celui-ci — le
    # bulletin ne préannonce pas des trimestres qui n'existent pas encore.
    rows = [["", "Moyenne", "Rang"]]
    for term in history.get("terms", []):
        rows.append([
            f"Moy. {term['name']}",
            show(term.get("average"), ""),
            ordinal(term.get("rank")),
        ])
    if not history.get("terms"):
        # Sans historique (bulletin édité hors séquence), on retombe sur la
        # session courante seule, qui reste toujours imprimable.
        rows.append(["Moyenne de la session",
                     show(card.get("general_average"), ""), ordinal(card.get("rank"))])

    # La moyenne annuelle n'a de sens qu'une fois la dernière session éditée :
    # une moyenne « annuelle » calculée à mi-parcours induirait en erreur.
    if history.get("is_final"):
        rows.append(["Moyenne Annuelle", show(history.get("annual_average"), ""), ""])

    middle_rows = []
    if options.get("show_class_statistics"):
        middle_rows += [
            ("Moy. la plus forte", show(statistics.get("highest"), "")),
            ("Moy. la plus faible", show(statistics.get("lowest"), "")),
            # « Annuelle » seulement quand l'année est complète ; le reste du
            # temps c'est la moyenne de la classe sur la session en cours.
            (
                "Moy. Annuelle de la classe" if history.get("is_final")
                else "Moy. de la classe",
                show(statistics.get("class_average"), ""),
            ),
        ]
    if options.get("show_appreciation"):
        middle_rows.append(("Appréciation", show(card.get("appreciation"), "")))
    # Les deux blocs se terminent à la même hauteur. Le nombre de sessions
    # varie d'une classe à l'autre : c'est le plus long des deux qui donne la
    # hauteur, et l'autre est complété par des lignes vides.
    height = max(len(rows), len(middle_rows))
    middle_rows += [("", "")] * (height - len(middle_rows))
    rows += [["", "", ""]] * (height - len(rows))

    left = [[Paragraph(f"<b>{label}</b>" if label else "", OFFICIAL_FOOT),
             Paragraph(value, OFFICIAL_CELL_BOLD),
             Paragraph(position, OFFICIAL_CELL_BOLD)] for label, value, position in rows]
    left_table = Table(left, colWidths=[34 * mm, 16 * mm, 14 * mm])

    middle = [[Paragraph(f"<b>{label}</b>" if label else "", OFFICIAL_FOOT),
               Paragraph(value, OFFICIAL_CELL_BOLD)] for label, value in middle_rows]
    middle_table = Table(middle, colWidths=[38 * mm, 16 * mm])

    right = [[Paragraph(label, OFFICIAL_FOOT), Paragraph(value, OFFICIAL_CELL_CENTER)]
             for label, value in DISCIPLINE_ROWS]
    right_table = Table(right, colWidths=[32 * mm, 18 * mm])

    grid = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])
    for table in (left_table, middle_table, right_table):
        table.setStyle(grid)
    # L'en-tête « Moyenne / Rang » se distingue des lignes de trimestres.
    left_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BACKGROUND),
        ("ALIGN", (1, 0), (-1, 0), "CENTER"),
    ]))

    outer = Table([[left_table, middle_table, right_table]],
                  colWidths=[64 * mm, 64 * mm, 50 * mm])
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return outer


def official_footer(school, council_note, homeroom_teacher="", is_final=False):
    """Décision du conseil, puis les deux signatures de la maquette.

    `is_final` : la case « moyenne annuelle en lettre », à remplir à la main,
    n'est réservée qu'au bulletin de fin d'année — ailleurs elle appellerait
    une valeur qui n'existe pas encore.
    """
    city = school.get("city") or ""
    place = f"{city.upper()}, le ……………………" if city else "Le ……………………"

    decision = Table(
        [[Paragraph("<b>Décision et observation du conseil de classe</b>", OFFICIAL_FOOT)],
         [Paragraph(council_note or "", OFFICIAL_FOOT)]],
        colWidths=[178 * mm], rowHeights=[7 * mm, 12 * mm],
    )
    decision.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    signatures = Table(
        [[Paragraph(
            "<b>Professeur titulaire</b>"
            # Le nom du titulaire sous l'intitulé, comme sur la maquette papier.
            + (f"<br/>{homeroom_teacher}" if homeroom_teacher else ""),
            OFFICIAL_FOOT),
          Paragraph("<i>Moy. annuelle en lettre</i>" if is_final else "",
                    style("officialWords", 6.4, 8, align=TA_CENTER)),
          Paragraph(f"{place}<br/><b>Le Proviseur</b>",
                    style("officialSign", 6.4, 8, align=TA_CENTER))]],
        colWidths=[54 * mm, 62 * mm, 62 * mm], rowHeights=[20 * mm],
    )
    signatures.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [decision, Spacer(1, 1 * mm), signatures]


def official_story(card, school, session, year_name, options, logo_path):
    """Une page au modèle officiel."""
    return [
        *official_header(card, school, session, year_name, logo_path),
        official_subjects_table(card, options),
        Spacer(1, 1.5 * mm),
        official_recap(card, options),
        Spacer(1, 1.5 * mm),
        *official_footer(school, options.get("council_note", ""),
                         card.get("homeroom_teacher", ""),
                         is_final=(card.get("history") or {}).get("is_final", False)),
    ]


def standard_story(card, school, session, year_name, options, logo_path):
    """Une page au modèle standard, celui d'origine."""
    statistics = card.get("statistics") or {}
    return [
        header_block(school, logo_path),
        Spacer(1, 3 * mm),
        identity_block(card, session, card.get("class_name", ""),
                       statistics.get("headcount", 0)),
        Spacer(1, 3 * mm),
        KeepTogether([
            Paragraph(f"BULLETIN DE NOTES DU {session_caption(card, session).upper()}",
                      TITLE_STYLE),
            Paragraph(f"Année scolaire : {year_name}", SUBTITLE_STYLE),
        ]),
        Spacer(1, 2 * mm),
        subjects_table(card, options),
        Spacer(1, 3 * mm),
        summary_block(card, options),
        Spacer(1, 3 * mm),
        footer_block(school, options.get("council_note", ""),
                     card.get("homeroom_teacher", "")),
    ]


# ── Filigrane ────────────────────────────────────────────────────────────────
#
# Dessiné sur le canevas avant le contenu : la marque reste en fond, sans
# jamais recouvrir une note. Le gris est volontairement très clair — assez
# visible pour décourager la photocopie, assez pâle pour rester lisible.

WATERMARK_COLOR = colors.Color(0, 0, 0, alpha=0.07)
WATERMARK_TILE_SIZE = 7
WATERMARK_TILE_STEP_X = 46 * mm
WATERMARK_TILE_STEP_Y = 11 * mm

# Serrage du motif en mosaïque. `gap` est l'espace minimal entre deux textes
# d'une même ligne, `step_y` la hauteur entre deux lignes ; l'alpha baisse à
# mesure que le motif se densifie, sinon la page saturée deviendrait illisible.
WATERMARK_DENSITIES = {
    "normale": {"gap": 8 * mm, "step_x": WATERMARK_TILE_STEP_X, "step_y": WATERMARK_TILE_STEP_Y, "alpha": 0.07},
    "pleine": {"gap": 4 * mm, "step_x": 26 * mm, "step_y": 7 * mm, "alpha": 0.055},
    "max": {"gap": 2 * mm, "step_x": 14 * mm, "step_y": 4.6 * mm, "alpha": 0.045},
}


def watermark_text(school, source):
    """Texte du filigrane : nom ou code de l'établissement."""
    value = school.get("code") if source == "code" else school.get("name")
    return (value or school.get("name") or "").strip().upper()


def draw_tiled(canvas, text, page_width, page_height, density="normale"):
    """Texte répété en lignes serrées, comme sur un bulletin officiel.

    `density` choisit le serrage : « normale » laisse respirer la page,
    « pleine » resserre le motif et « max » la sature.
    """
    shape = WATERMARK_DENSITIES.get(density) or WATERMARK_DENSITIES["normale"]
    step_y = shape["step_y"]
    canvas.setFont("Helvetica-Bold", WATERMARK_TILE_SIZE)
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=shape["alpha"]))
    width = canvas.stringWidth(text, "Helvetica-Bold", WATERMARK_TILE_SIZE)
    # Le texte ne doit jamais se chevaucher : sa largeur réelle prime sur le
    # pas voulu, qui n'est qu'un minimum d'aération.
    step_x = max(width + shape["gap"], shape["step_x"])

    row = 0
    y = -step_y
    while y < page_height + step_y:
        # Une ligne sur deux est décalée : le motif ne forme pas de colonnes.
        x = -step_x + (step_x / 2 if row % 2 else 0)
        while x < page_width:
            canvas.drawString(x, y, text)
            x += step_x
        y += step_y
        row += 1


def draw_diagonal(canvas, text, page_width, page_height):
    """Un seul bandeau en travers de la page."""
    # Le bandeau suit la vraie diagonale de la page, pas un 45° arbitraire :
    # sur un A4 l'angle vaut ~34°, et un 45° laisserait le texte déborder d'un
    # côté. On ajuste ensuite la police pour tenir dans cette longueur.
    diagonal = (page_width ** 2 + page_height ** 2) ** 0.5
    # Angle de la diagonale montante (~35° sur A4). `atan2(hauteur, largeur)`
    # donnerait la pente vue depuis l'axe vertical, bien trop redressée.
    angle = degrees(atan2(page_width, page_height))
    available = diagonal * 0.82
    size = 60
    while size > 10 and canvas.stringWidth(text, "Helvetica-Bold", size) > available:
        size -= 2

    canvas.saveState()
    canvas.translate(page_width / 2, page_height / 2)
    canvas.rotate(angle)
    canvas.setFont("Helvetica-Bold", size)
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
    # Le repère est déjà au centre de la page : on centre autour de l'origine.
    canvas.drawCentredString(0, -size / 3, text)
    canvas.restoreState()


def draw_logo(canvas, logo_path, page_width, page_height):
    """Logo centré, très pâle."""
    canvas.saveState()
    canvas.setFillAlpha(0.06)
    canvas.setStrokeAlpha(0.06)
    side = 110 * mm
    try:
        canvas.drawImage(
            logo_path, (page_width - side) / 2, (page_height - side) / 2,
            width=side, height=side, mask="auto", preserveAspectRatio=True,
        )
    except Exception:
        # Un logo illisible ne doit pas empêcher d'éditer le bulletin.
        pass
    canvas.restoreState()


def watermark_kinds(options):
    """Filigranes demandés, du fond vers le dessus, sans doublon ni « aucun ».

    Le paramétrage peut en combiner plusieurs (mosaïque + diagonale + logo).
    On accepte encore l'ancienne clé à choix unique, pour les appels qui n'ont
    pas été mis à jour.
    """
    chosen = options.get("watermarks")
    if not isinstance(chosen, (list, tuple)):
        chosen = [options.get("watermark", "aucun")]
    # Ordre d'empilement imposé : le logo et le bandeau doivent rester
    # lisibles par-dessus la mosaïque, quel que soit l'ordre de saisie.
    order = ("mosaique", "diagonale", "logo")
    return [kind for kind in order if kind in chosen]


def watermark_painter(school, options, logo_path):
    """Fonction de page qui dessine les filigranes, ou None si aucun n'est demandé."""
    kinds = watermark_kinds(options)
    if not logo_path:
        kinds = [kind for kind in kinds if kind != "logo"]

    text = watermark_text(school, options.get("watermark_source", "nom"))
    if not text:
        kinds = [kind for kind in kinds if kind == "logo"]
    if not kinds:
        return None

    density = options.get("watermark_density", "normale")

    def paint(canvas, document):
        page_width, page_height = document.pagesize
        canvas.saveState()
        for kind in kinds:
            if kind == "logo":
                draw_logo(canvas, logo_path, page_width, page_height)
            elif kind == "diagonale":
                draw_diagonal(canvas, text, page_width, page_height)
            else:
                draw_tiled(canvas, text, page_width, page_height, density)
        canvas.restoreState()

    return paint


def report_cards_pdf(cards, school, session, year_name, options, logo_path=None):
    """Assemble un PDF, une page par bulletin, selon le modèle paramétré."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title=f"Bulletins — {session['name']}", author="EKD School Manager",
    )

    page = official_story if options.get("template") == "officiel" else standard_story

    story = []
    for position, card in enumerate(cards):
        if position:
            story.append(PageBreak())
        story += page(card, school, session, year_name, options, logo_path)

    if not story:
        story.append(Paragraph("Aucun bulletin à éditer.", SUBTITLE_STYLE))

    paint = watermark_painter(school, options, logo_path)
    if paint:
        document.build(story, onFirstPage=paint, onLaterPages=paint)
    else:
        document.build(story)
    return buffer.getvalue()
