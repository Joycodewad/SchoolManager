"""Charge les données réelles du Lycée d'Amou-Oblo (année scolaire 2025-2026).

Le seed est idempotent : il peut être relancé sans créer de doublons.
Les listes d'élèves proviennent des fichiers Excel du dossier examples/.
"""

import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from ekdschoolmanager.models import (
    AcademicYear,
    ClassSubject,
    CustomUser,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
    TeacherAssignmentSubject,
    TeacherClassAssignment,
)

SCHOOL_NAME = "Lycée d'Amou-Oblo"
SCHOOL_CODE = "lycee-amou-oblo"
YEAR_NAME = "2025-2026"

# Matières : code court utilisé dans les tableaux -> libellé complet.
SUBJECTS = {
    "FR": "Français",
    "ANG": "Anglais",
    "HG": "Histoire-Géographie",
    "ECM": "Éducation Civique et Morale",
    "SVT": "Sciences de la Vie et de la Terre",
    "MATHS": "Mathématiques",
    "PCT": "Physique-Chimie-Technologie",
    "PHILO": "Philosophie",
    "ALL": "Allemand",
    "EPS": "Éducation Physique et Sportive",
    "MUS": "Musique",
}

# Heures hebdomadaires par matière et par niveau du tableau de répartition.
# "-" du tableau = matière non enseignée à ce niveau (absente du dict).
WEEKLY_HOURS = {
    "6eme": {"FR": 6, "ANG": 4, "HG": 2, "ECM": 2, "SVT": 2, "MATHS": 4, "PCT": 3, "EPS": 2, "MUS": 1},
    "5eme": {"FR": 6, "ANG": 4, "HG": 2, "ECM": 2, "SVT": 2, "MATHS": 4, "PCT": 3, "EPS": 2, "MUS": 1},
    "4eme": {"FR": 6, "ANG": 4, "HG": 2, "ECM": 2, "SVT": 3, "MATHS": 4, "PCT": 5, "EPS": 2, "MUS": 1},
    "3eme": {"FR": 6, "ANG": 4, "HG": 3, "ECM": 2, "SVT": 4, "MATHS": 4, "PCT": 5, "EPS": 2, "MUS": 1},
    "2A4": {"FR": 5, "ANG": 4, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 3, "PCT": 3, "PHILO": 2, "ALL": 4, "EPS": 2, "MUS": 1},
    "2CD": {"FR": 4, "ANG": 3, "HG": 3, "ECM": 1, "SVT": 3, "MATHS": 5, "PCT": 5, "PHILO": 2, "EPS": 2, "MUS": 1},
    "1A4": {"FR": 5, "ANG": 4, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 2, "PCT": 2, "PHILO": 2, "ALL": 4, "EPS": 2, "MUS": 1},
    "1C4": {"FR": 4, "ANG": 3, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 7, "PCT": 5, "PHILO": 2, "EPS": 2, "MUS": 1},
    "1D": {"FR": 4, "ANG": 3, "HG": 4, "ECM": 1, "SVT": 5, "MATHS": 5, "PCT": 5, "PHILO": 2, "EPS": 2, "MUS": 1},
    "TA4": {"FR": 4, "ANG": 3, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 2, "PCT": 2, "PHILO": 6, "ALL": 3, "EPS": 2, "MUS": 1},
    "TC4": {"FR": 2, "ANG": 2, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 8, "PCT": 5, "PHILO": 3, "EPS": 2, "MUS": 1},
    "TD": {"FR": 2, "ANG": 2, "HG": 4, "ECM": 1, "SVT": 6, "MATHS": 6, "PCT": 5, "PHILO": 3, "EPS": 2, "MUS": 1},
}

# Classe réelle -> (niveau du référentiel, série, colonne du tableau d'heures).
CLASSES = {
    "6A": ("6ème", "", "6eme"), "6B": ("6ème", "", "6eme"), "6C": ("6ème", "", "6eme"),
    "6D": ("6ème", "", "6eme"), "6E": ("6ème", "", "6eme"),
    "5A": ("5ème", "", "5eme"), "5B": ("5ème", "", "5eme"), "5C": ("5ème", "", "5eme"),
    "4A": ("4ème", "", "4eme"), "4B": ("4ème", "", "4eme"),
    "4C": ("4ème", "", "4eme"), "4D": ("4ème", "", "4eme"),
    "3A": ("3ème", "", "3eme"), "3B": ("3ème", "", "3eme"), "3C": ("3ème", "", "3eme"),
    "2A4": ("Seconde", "A4", "2A4"), "2CD": ("Seconde", "CD", "2CD"),
    "1A4": ("Première", "A4", "1A4"), "1C4": ("Première", "C4", "1C4"), "1D": ("Première", "D", "1D"),
    "TA4": ("Terminale", "A4", "TA4"), "TC4": ("Terminale", "C4", "TC4"), "TD": ("Terminale", "D", "TD"),
}

# Personnel : matricule, nom, prénoms, fonction/spécialité, classe titulaire, contact.
STAFF = [
    ("047511H", "AMAH", "Komla", "PROVISEUR", "", "90389023"),
    ("080580E", "KADOASSO", "Batembana", "CENSEUR", "", "90700806"),
    ("056537T", "ADZUDZOR", "Dotsè", "CPE", "", "91908947"),
    ("071135Z", "SEWA", "Yao", "CPE", "", "91970245"),
    ("APE", "BOURAÏMA", "Méminétou", "Secrétaire", "", "91440697"),
    ("APE", "KOUKOU ADAM", "Faïza", "Secrétaire", "", "91553502"),
    ("101034C", "ABIWA", "Bakoulakpama", "FR/HG", "5C", "98417021"),
    ("APE", "ADJE", "Pouwèdewou", "PCT/MATHS", "", "93115424"),
    ("102736J", "AKOTSU", "Yawo Dovi", "FR/HG/ECM", "6B", "92161204"),
    ("120414G", "AKPAO", "Tchissi", "ANG/FR", "4A", "92466819"),
    ("094459M", "AKPO", "Dawolo Komlanvi", "MATHS/PCT", "4B", "91677698"),
    ("118545B", "ALI", "Pissibanèwè", "ALL", "", "93682782"),
    ("SN", "ALIANG", "Nakpasse", "HG/FR/ECM", "", "91182734"),
    ("124294Q", "AMAKOE", "Akoèté", "PCT/MATHS", "5B", "93444808"),
    ("105970L", "AMEGBLE", "Kodjo Nyawudzi", "FR", "2A4", "91575619"),
    ("111183H", "ATSOU I. K.", "Ayéfoumi", "PHILO", "", "92349241"),
    ("068705T", "ATSU", "Kouma", "ANG/FR", "6E", "97383028"),
    ("105997P", "AYETO", "Afi Ahoéfa", "ANG/FR", "3A", "90732191"),
    ("072789F", "DEROU", "Hiloukou Essokoma", "PC", "1C4", "98038064"),
    ("117512S", "FAYA", "Samuel", "HG/FR/ECM", "6C", "90265485"),
    ("081108E", "HALAOUA", "S. Kiméyalou", "FR/ANG", "6A", "91560787"),
    ("107426U", "KAKOMISSA", "Midaouna", "EPS", "", "90470131"),
    ("1118024J", "KAKOUTA", "Bakpera A", "PHILO", "1A4", "90715983"),
    ("090086Y", "KPEKPASSI", "Abdourofou", "ANG", "TA4", "91130758"),
    ("SN", "LIYABINE", "Mommale", "MATHS/PCT", "", "93369333"),
    ("APE", "MAKIE", "Komi", "SVT/PCT", "4D", "92984982"),
    ("SN", "MANI", "Tchintchane", "MATHS", "", "91138867"),
    ("105969B", "MIDANGA", "Loguéménda", "SVT/PCT", "6D", "90455173"),
    ("078912A", "NAPO", "Gbati", "HG/ECM", "TD", "90378483"),
    ("080452N", "OGBONE", "Sédou", "HG/ECM", "2CD", "90854963"),
    ("116958G", "OHONOU", "Kokou Atitso", "FR/HG/ECM", "3C", "91078651"),
    ("115880S", "OLANIYAN", "Rachid", "MATHS/PCT", "TC4", "91934465"),
    ("119018U", "PAFALIKI", "Essolaki Baba", "MUS", "", "72190614"),
    ("APE", "SODJI", "Soménou", "EPS", "", "91621990"),
    ("124460W", "TCHAGBA", "Kpakpadja", "PCT/MATHS", "4C", "91317528"),
    ("072767Z", "TEBIE", "Alowougnim", "SVT/MATHS", "3B", "96140018"),
    ("100067V", "TOUGNON", "Koffi Evègnon", "SVT", "1D", "92442777"),
    ("117618C", "YOBE", "Kossi", "HG/FR/ECM", "5A", "93880693"),
]

NON_TEACHING = {
    "PROVISEUR": CustomUser.Role.PROVISEUR,
    "CENSEUR": CustomUser.Role.CENSEUR,
    "CPE": CustomUser.Role.SURVEILLANT,
    "Secrétaire": CustomUser.Role.SECRETARY,
}

# Répartition : quel enseignant assure quelle matière dans quelle classe.
# Les noms renvoient à la colonne NOM du personnel ci-dessus.
ASSIGNMENTS = {
    "6A": {"FR": "HALAOUA", "ANG": "ATSU", "HG": "ALIANG", "ECM": "AKOTSU", "MATHS": "TCHAGBA", "PCT": "ADJE", "SVT": "MIDANGA", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "6B": {"FR": "AKOTSU", "ANG": "AYETO", "HG": "ALIANG", "ECM": "YOBE", "MATHS": "LIYABINE", "PCT": "ADJE", "SVT": "MAKIE", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "6C": {"FR": "AKPAO", "ANG": "ATSU", "HG": "FAYA", "ECM": "ABIWA", "MATHS": "TCHAGBA", "PCT": "LIYABINE", "SVT": "MAKIE", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "6D": {"FR": "ALIANG", "ANG": "AYETO", "HG": "YOBE", "ECM": "AKOTSU", "MATHS": "TEBIE", "PCT": "LIYABINE", "SVT": "MIDANGA", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "6E": {"FR": "AKOTSU", "ANG": "ATSU", "HG": "ALIANG", "ECM": "ABIWA", "MATHS": "AKPO", "PCT": "ADJE", "SVT": "MAKIE", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "5A": {"FR": "FAYA", "ANG": "AKPAO", "HG": "YOBE", "ECM": "ABIWA", "MATHS": "TEBIE", "PCT": "AMAKOE", "SVT": "MAKIE", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "5B": {"FR": "OHONOU", "ANG": "ATSU", "HG": "FAYA", "ECM": "OGBONE", "MATHS": "AMAKOE", "PCT": "ADJE", "SVT": "MIDANGA", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "5C": {"FR": "ALIANG", "ANG": "AKPAO", "HG": "YOBE", "ECM": "ABIWA", "MATHS": "TEBIE", "PCT": "OLANIYAN", "SVT": "MAKIE", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "4A": {"FR": "HALAOUA", "ANG": "AKPAO", "HG": "FAYA", "ECM": "YOBE", "MATHS": "LIYABINE", "PCT": "ADJE", "SVT": "MIDANGA", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "4B": {"FR": "ABIWA", "ANG": "AYETO", "HG": "YOBE", "ECM": "AKOTSU", "MATHS": "ADJE", "PCT": "AKPO", "SVT": "MAKIE", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "4C": {"FR": "OHONOU", "ANG": "ATSU", "HG": "FAYA", "ECM": "ABIWA", "MATHS": "MANI", "PCT": "TCHAGBA", "SVT": "TEBIE", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "4D": {"FR": "HALAOUA", "ANG": "AYETO", "HG": "ALIANG", "ECM": "YOBE", "MATHS": "AKPO", "PCT": "TCHAGBA", "SVT": "MAKIE", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "3A": {"FR": "HALAOUA", "ANG": "AYETO", "HG": "FAYA", "ECM": "YOBE", "MATHS": "AKPO", "PCT": "TCHAGBA", "SVT": "MIDANGA", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "3B": {"FR": "ABIWA", "ANG": "AKPAO", "HG": "YOBE", "ECM": "AKOTSU", "MATHS": "OLANIYAN", "PCT": "AMAKOE", "SVT": "TEBIE", "EPS": "SODJI", "MUS": "PAFALIKI"},
    "3C": {"FR": "OHONOU", "ANG": "ATSU", "HG": "FAYA", "ECM": "YOBE", "MATHS": "AKPO", "PCT": "MAKIE", "SVT": "MIDANGA", "EPS": "KAKOMISSA", "MUS": "PAFALIKI"},
    "2A4": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "OGBONE", "ECM": "NAPO", "MATHS": "MANI", "PCT": "AMAKOE", "SVT": "MIDANGA", "EPS": "SODJI", "MUS": "PAFALIKI", "ALL": "ALI", "PHILO": "ATSOU I. K."},
    "2CD": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "NAPO", "ECM": "OGBONE", "MATHS": "MANI", "PCT": "DEROU", "SVT": "TOUGNON", "EPS": "KAKOMISSA", "MUS": "PAFALIKI", "PHILO": "KAKOUTA"},
    "1A4": {"FR": "OHONOU", "ANG": "KPEKPASSI", "HG": "OGBONE", "ECM": "NAPO", "MATHS": "MANI", "PCT": "MIDANGA", "SVT": "TEBIE", "EPS": "SODJI", "MUS": "PAFALIKI", "ALL": "ALI", "PHILO": "KAKOUTA"},
    "1C4": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "NAPO", "ECM": "OGBONE", "MATHS": "OLANIYAN", "PCT": "DEROU", "SVT": "TOUGNON", "EPS": "KAKOMISSA", "MUS": "PAFALIKI", "PHILO": "ATSOU I. K."},
    "1D": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "NAPO", "ECM": "OGBONE", "MATHS": "LIYABINE", "PCT": "AMAKOE", "SVT": "TOUGNON", "EPS": "KAKOMISSA", "MUS": "PAFALIKI", "PHILO": "ATSOU I. K."},
    "TA4": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "NAPO", "ECM": "OGBONE", "MATHS": "LIYABINE", "PCT": "AMAKOE", "SVT": "TOUGNON", "EPS": "KAKOMISSA", "MUS": "PAFALIKI", "ALL": "ALI", "PHILO": "ATSOU I. K."},
    "TC4": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "NAPO", "ECM": "OGBONE", "MATHS": "OLANIYAN", "PCT": "DEROU", "SVT": "TOUGNON", "EPS": "SODJI", "MUS": "PAFALIKI", "PHILO": "KAKOUTA"},
    "TD": {"FR": "AMEGBLE", "ANG": "KPEKPASSI", "HG": "OGBONE", "ECM": "NAPO", "MATHS": "MANI", "PCT": "DEROU", "SVT": "TOUGNON", "EPS": "SODJI", "MUS": "PAFALIKI", "PHILO": "ATSOU I. K."},
}

WORKBOOKS = {
    "LISTES DE CLASSES PREMIER CYCLE.xls": ["6A", "6B", "6C", "6D", "6E", "5A", "5B", "5C", "4A", "4B", "4C", "4D", "3A", "3B", "3C"],
    "LISTES DE CLASSES SECOND CYCLE.xls": ["2A4", "2CD", "1A4", "1C4", "1D", "TA4", "TD", "TC4"],
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def find_header(sheet):
    """Repère la ligne et les colonnes d'en-tête : la mise en page varie d'une feuille à l'autre."""
    for row in range(min(30, sheet.nrows)):
        cells = [clean(cell.value).upper() for cell in sheet.row(row)]
        name_col = surname_col = sex_col = None
        for index, value in enumerate(cells):
            if "NOM" in value and name_col is None:
                name_col = index
            elif "PRENOM" in value and surname_col is None:
                surname_col = index
            elif value.startswith("SEXE") and sex_col is None:
                sex_col = index
        if name_col is not None and surname_col is not None:
            return row, name_col, surname_col, sex_col
    return None


def read_students(path, sheet_name):
    import xlrd

    workbook = xlrd.open_workbook(path)
    sheet = workbook.sheet_by_name(sheet_name)
    header = find_header(sheet)
    if not header:
        return []
    header_row, name_col, surname_col, sex_col = header
    students = []
    for row in range(header_row + 1, sheet.nrows):
        last_name = clean(sheet.cell_value(row, name_col))
        first_names = clean(sheet.cell_value(row, surname_col)) if surname_col < sheet.ncols else ""
        sex = ""
        if sex_col is not None and sex_col < sheet.ncols:
            sex = clean(sheet.cell_value(row, sex_col)).upper()[:1]
        if not last_name and not first_names:
            continue
        if re.match(r"^(N°|NOMS?|TOTAL|EFFECTIF)", last_name.upper()):
            continue
        # Certaines lignes regroupent « NOM Prénoms » dans la seule colonne des noms.
        if not first_names and " " in last_name:
            parts = last_name.split()
            last_name, first_names = parts[0], " ".join(parts[1:])
        students.append((last_name, first_names, sex if sex in ("M", "F") else ""))
    return students


def unique_username(base):
    base = slugify(base).replace("-", "") or "user"
    candidate = base
    suffix = 1
    while CustomUser.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


class Command(BaseCommand):
    help = "Charge les données du Lycée d'Amou-Oblo (2025-2026) : personnel, classes, matières, horaires et élèves."

    def add_arguments(self, parser):
        parser.add_argument(
            "--examples-dir",
            default=str(Path(settings.BASE_DIR).parent / "examples"),
            help="Dossier contenant les fichiers Excel des listes de classes.",
        )
        parser.add_argument(
            "--skip-students",
            action="store_true",
            help="Ne charge pas les élèves (personnel, classes et horaires uniquement).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        examples_dir = Path(options["examples_dir"])
        if not options["skip_students"]:
            missing = [name for name in WORKBOOKS if not (examples_dir / name).exists()]
            if missing:
                raise CommandError(
                    f"Fichiers introuvables dans {examples_dir} : {', '.join(missing)}"
                )

        owner = self.create_owner()
        school = self.create_school(owner)
        year = self.create_year(school)
        subjects = self.create_subjects(school)
        staff = self.create_staff(school)
        classes = self.create_classes(school, year, staff)
        class_subjects = self.create_class_subjects(classes, subjects)
        self.assign_teachers(school, year, classes, class_subjects, staff)
        if not options["skip_students"]:
            self.create_students(school, year, classes, examples_dir)
        self.report(school, year)

    def create_owner(self):
        owner, created = CustomUser.objects.get_or_create(
            username="amah",
            defaults={
                "last_name": "AMAH",
                "first_name": "Komla",
                "role": CustomUser.Role.OWNER,
                "phone": "90389023",
                "gender": "M",
            },
        )
        if created:
            owner.set_password("amah@")
            owner.save(update_fields=["password"])
            self.stdout.write("Propriétaire créé : amah / amah@")
        return owner

    def create_school(self, owner):
        school, _ = School.objects.get_or_create(
            code=SCHOOL_CODE, defaults={"name": SCHOOL_NAME, "owner": owner},
        )
        SchoolMembership.objects.get_or_create(
            school=school, user=owner, defaults={"role": CustomUser.Role.OWNER},
        )
        return school

    def create_year(self, school):
        year, _ = AcademicYear.objects.get_or_create(
            school=school,
            name=YEAR_NAME,
            defaults={
                "start_date": date(2025, 9, 15),
                "end_date": date(2026, 7, 15),
                "is_active": True,
            },
        )
        return year

    def create_subjects(self, school):
        subjects = {}
        for code, name in SUBJECTS.items():
            subject, _ = Subject.objects.get_or_create(
                school=school, name=name, defaults={"code": slugify(code)},
            )
            subjects[code] = subject
        return subjects

    def create_staff(self, school):
        staff = {}
        for matricule, last_name, first_names, function, _homeroom, contact in STAFF:
            role = NON_TEACHING.get(function, CustomUser.Role.TEACHER)
            user = CustomUser.objects.filter(last_name=last_name, first_name=first_names).first()
            if not user:
                user = CustomUser.objects.create(
                    username=unique_username(f"{last_name}{first_names[:3]}"),
                    last_name=last_name,
                    first_name=first_names,
                    role=role,
                    phone=contact,
                    profession=function,
                    enrollment_number=matricule,
                )
                user.set_password(user.username)
                user.save(update_fields=["password"])
            SchoolMembership.objects.get_or_create(
                school=school, user=user, defaults={"role": role},
            )
            staff[last_name] = user
        return staff

    def create_classes(self, school, year, staff):
        homerooms = {homeroom: last_name for _, last_name, _, _, homeroom, _ in STAFF if homeroom}
        levels = {level.name: level for level in SchoolLevel.objects.filter(school=school)}
        classes = {}
        for group, (level_name, series, _hours_key) in CLASSES.items():
            level = levels.get(level_name)
            if not level:
                raise CommandError(f"Niveau « {level_name} » absent du référentiel de l'école.")
            teacher_name = homerooms.get(group)
            school_class, _ = SchoolClass.objects.get_or_create(
                academic_year=year,
                level=level,
                series=series,
                group=group,
                defaults={
                    "school": school,
                    "homeroom_teacher": staff.get(teacher_name) if teacher_name else None,
                },
            )
            classes[group] = school_class
        return classes

    def create_class_subjects(self, classes, subjects):
        class_subjects = {}
        for group, school_class in classes.items():
            hours_key = CLASSES[group][2]
            class_subjects[group] = {}
            for code, hours in WEEKLY_HOURS[hours_key].items():
                class_subject, _ = ClassSubject.objects.get_or_create(
                    school_class=school_class,
                    subject=subjects[code],
                    defaults={"weekly_hours": hours, "coefficient": 1},
                )
                class_subjects[group][code] = class_subject
        return class_subjects

    def assign_teachers(self, school, year, classes, class_subjects, staff):
        self.unmatched = []
        for group, mapping in ASSIGNMENTS.items():
            school_class = classes[group]
            for code, teacher_name in mapping.items():
                teacher = staff.get(teacher_name)
                class_subject = class_subjects[group].get(code)
                if not teacher or not class_subject:
                    self.unmatched.append(f"{group}/{code} -> {teacher_name}")
                    continue
                assignment, _ = TeacherClassAssignment.objects.get_or_create(
                    school=school, academic_year=year, teacher=teacher, school_class=school_class,
                )
                TeacherAssignmentSubject.objects.get_or_create(
                    assignment=assignment, class_subject=class_subject,
                )

    def create_students(self, school, year, classes, examples_dir):
        self.student_counts = {}
        for filename, sheets in WORKBOOKS.items():
            path = str(examples_dir / filename)
            for sheet_name in sheets:
                school_class = classes[sheet_name]
                rows = read_students(path, sheet_name)
                created = 0
                for index, (last_name, first_names, sex) in enumerate(rows, start=1):
                    number = f"{YEAR_NAME[:4]}{sheet_name}{index:03d}"
                    if StudentEnrollment.objects.filter(
                        school=school, enrollment_number=number,
                    ).exists():
                        continue
                    student = CustomUser.objects.create(
                        username=unique_username(f"{last_name}{first_names[:3]}"),
                        last_name=last_name,
                        first_name=first_names,
                        role=CustomUser.Role.STUDENT,
                        gender=sex,
                        enrollment_number=number,
                    )
                    student.set_password(number)
                    student.save(update_fields=["password"])
                    StudentEnrollment.objects.create(
                        school=school,
                        academic_year=year,
                        student=student,
                        level=school_class.level,
                        school_class=school_class,
                        series=school_class.series,
                        enrollment_number=number,
                    )
                    created += 1
                self.student_counts[sheet_name] = created

    def report(self, school, year):
        self.stdout.write(self.style.SUCCESS(f"\n{school.name} — {year.name}"))
        self.stdout.write(f"  Personnel      : {SchoolMembership.objects.filter(school=school).count()}")
        self.stdout.write(f"  Classes        : {SchoolClass.objects.filter(academic_year=year).count()}")
        self.stdout.write(f"  Matières       : {Subject.objects.filter(school=school).count()}")
        self.stdout.write(
            f"  Config. horaires: {ClassSubject.objects.filter(school_class__academic_year=year).count()}"
        )
        self.stdout.write(
            f"  Affectations   : {TeacherAssignmentSubject.objects.filter(assignment__academic_year=year).count()}"
        )
        enrollments = StudentEnrollment.objects.filter(academic_year=year).count()
        self.stdout.write(f"  Élèves inscrits: {enrollments}")
        if getattr(self, "unmatched", None):
            self.stdout.write(self.style.WARNING(f"  Affectations ignorées : {', '.join(self.unmatched)}"))
