from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUTPUT = Path(__file__).with_name("eleves_100_informations_completes_avec_tuteurs.xlsx")
HEADERS = [
    "matricule", "nom", "prenoms", "genre", "date_naissance", "moyenne",
    "statut", "cycle", "niveau", "serie", "classe", "telephone_tuteur",
    "nom_tuteur", "prenoms_tuteur", "profession_tuteur",
    "allergies_et_soucis_de_sante",
]
CLASSES = [
    ("Lycée", "Seconde", "CD", "2NDE CD-1"),
    ("Lycée", "Seconde", "CD", "2NDE CD-2"),
    ("Lycée", "Seconde", "A4", "2NDE A4-1"),
    ("Lycée", "Seconde", "A4", "2NDE A4-2"),
    ("Lycée", "Première", "D", "1ERE D-1"),
    ("Lycée", "Première", "D", "1ERE D-2"),
    ("Lycée", "Première", "A4", "1ERE A4-1"),
    ("Lycée", "Première", "A4", "1ERE A4-2"),
    ("Lycée", "Première", "C4", "1ERE C4"),
    ("Lycée", "Terminale", "D", "TLE D"),
]
LEVELS = [
    ("Primaire", "CP1", ""), ("Primaire", "CP2", ""),
    ("Primaire", "CE1", ""), ("Primaire", "CE2", ""),
    ("Primaire", "CM1", ""), ("Primaire", "CM2", ""),
    ("Collège", "6ème", ""), ("Collège", "5ème", ""),
    ("Collège", "4ème", ""), ("Collège", "3ème", ""),
    ("Lycée", "Seconde", "CD"), ("Lycée", "Seconde", "A4"),
    ("Lycée", "Première", "D"), ("Lycée", "Première", "A4"),
    ("Lycée", "Première", "C4"), ("Lycée", "Terminale", "D"),
    ("Lycée", "Terminale", "A4"), ("Lycée", "Terminale", "C4"),
]
LAST_NAMES = ["ADJOVI", "AGBESSI", "AKAKPO", "AMOUZOU", "ATCHA", "AYENA", "DOSSOU", "EDOH", "GBEDE", "KOFFI", "LAWSON", "MENSAH", "SODJI", "TCHALLA", "YAO"]
FIRST_NAMES = ["Ama", "Kossi", "Afi", "Komlan", "Essi", "Kodjo", "Mawuli", "Yawa", "Sena", "Dela", "Akouvi", "Elom", "Déborah", "David", "Esther"]
PROFESSIONS = ["Commerçant", "Enseignante", "Agriculteur", "Infirmière", "Artisan", "Comptable", "Chauffeur", "Couturière"]
HEALTH_INFO = ["", "Aucune allergie connue", "Allergie aux arachides", "Asthme léger", "Drépanocytose AS", "Allergie à la pénicilline"]


def column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def cell(reference, value, style=0):
    return f'<c r="{reference}" t="inlineStr" s="{style}"><is><t>{escape(str(value))}</t></is></c>'


rows = [HEADERS]
for index in range(1, 101):
    if index <= len(CLASSES):
        cycle, level, series, school_class = CLASSES[index - 1]
    else:
        cycle, level, series = LEVELS[(index - 11) % len(LEVELS)]
        school_class = ""
    guardian_index = (index - 1) // 2 + 1
    guardian_last_name = LAST_NAMES[(guardian_index - 1) % len(LAST_NAMES)]
    status = "abandon" if index % 25 == 0 else "redoublant" if index % 7 == 0 else "nouveau"
    average = f"{8 + ((index * 37) % 1200) / 100:.2f}"
    rows.append([
        f"MAT-{index:04d}",
        LAST_NAMES[(index - 1) % len(LAST_NAMES)],
        f"{FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]} Exemple{index}",
        "Féminin" if index % 2 else "Masculin",
        date(2007 + index % 8, index % 12 + 1, index % 27 + 1).isoformat(),
        average,
        status,
        cycle,
        level,
        series,
        school_class,
        f"+2289{guardian_index:07d}",
        guardian_last_name,
        f"Parent {FIRST_NAMES[(guardian_index - 1) % len(FIRST_NAMES)]}",
        PROFESSIONS[(guardian_index - 1) % len(PROFESSIONS)],
        HEALTH_INFO[index % len(HEALTH_INFO)],
    ])

sheet_rows = []
for row_index, row in enumerate(rows, 1):
    cells = "".join(cell(f"{column_name(column_index)}{row_index}", value, 1 if row_index == 1 else 0) for column_index, value in enumerate(row, 1))
    sheet_rows.append(f'<row r="{row_index}">{cells}</row>')

widths = [14, 18, 25, 12, 17, 12, 14, 13, 14, 10, 18, 20, 18, 22, 20, 34]
sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{''.join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i, width in enumerate(widths, 1))}</cols>
  <sheetData>{''.join(sheet_rows)}</sheetData><autoFilter ref="A1:P101"/>
</worksheet>'''

files = {
    "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
    "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
    "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Élèves et tuteurs" sheetId="1" r:id="rId1"/></sheets></workbook>''',
    "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
    "xl/styles.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs></styleSheet>''',
    "xl/worksheets/sheet1.xml": sheet,
}

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    for filename, content in files.items():
        archive.writestr(filename, content)

print(OUTPUT)
