"""Charge les données du Lycée de Hiheatro (année scolaire 2025-2026).

Le seed est idempotent : il peut être relancé sans créer de doublons.
L'établissement ne comporte que du second cycle (Seconde, Première, Terminale).
"""

from datetime import date

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
    Subject,
    TeacherAssignmentSubject,
    TeacherClassAssignment,
)

SCHOOL_NAME = "Lycée de Hiheatro"
SCHOOL_CODE = "lycee-hiheatro"
YEAR_NAME = "2025-2026"

SUBJECTS = {
    "FR": "Français",
    "ANG": "Anglais",
    "ALL": "Allemand",
    "PHILO": "Philosophie",
    "HG": "Histoire-Géographie",
    "ECM": "Éducation Civique et Morale",
    "MATHS": "Mathématiques",
    "PC": "Physique-Chimie",
    "SVT": "Sciences de la Vie et de la Terre",
    "EPS": "Éducation Physique et Sportive",
    "DESSIN": "Dessin",
    "MUSIQUE": "Musique",
}

# Classe réelle -> (niveau du référentiel, série, colonne du barème horaire).
# Hiheatro dédouble certaines séries (2A41, 2A42…) : toutes suivent le volume
# horaire de leur série d'origine.
CLASSES = {
    "2A41": ("Seconde", "A4", "2A4"), "2A42": ("Seconde", "A4", "2A4"),
    "2A43": ("Seconde", "A4", "2A4"), "2CD": ("Seconde", "CD", "2CD"),
    "1A41": ("Première", "A4", "1A4"), "1A42": ("Première", "A4", "1A4"),
    "1A43": ("Première", "A4", "1A4"), "1A44": ("Première", "A4", "1A4"),
    "1D": ("Première", "D", "1D"),
    "TA41": ("Terminale", "A4", "TA4"), "TA42": ("Terminale", "A4", "TA4"),
    "TA43": ("Terminale", "A4", "TA4"), "TD": ("Terminale", "D", "TD"),
}

# Heures hebdomadaires par série, reprises du barème du second cycle.
# DESSIN et MUSIQUE sont à 1h partout (13 h pour 13 classes chez ABELIA et IDAYE).
WEEKLY_HOURS = {
    "2A4": {"FR": 5, "ANG": 4, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 3, "PC": 3, "PHILO": 2, "ALL": 4, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
    "2CD": {"FR": 4, "ANG": 3, "HG": 3, "ECM": 1, "SVT": 3, "MATHS": 5, "PC": 5, "PHILO": 2, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
    "1A4": {"FR": 5, "ANG": 4, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 2, "PC": 2, "PHILO": 2, "ALL": 4, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
    "1D": {"FR": 4, "ANG": 3, "HG": 4, "ECM": 1, "SVT": 5, "MATHS": 5, "PC": 5, "PHILO": 2, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
    "TA4": {"FR": 4, "ANG": 3, "HG": 4, "ECM": 1, "SVT": 2, "MATHS": 2, "PC": 2, "PHILO": 6, "ALL": 3, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
    "TD": {"FR": 2, "ANG": 2, "HG": 4, "ECM": 1, "SVT": 6, "MATHS": 6, "PC": 5, "PHILO": 3, "EPS": 2, "DESSIN": 1, "MUSIQUE": 1},
}

# Enseignant -> {matière: classes}. Les volumes annoncés dans la répartition
# servent de contrôle, ils ne sont pas stockés tels quels.
STAFF = [
    ("ARREIS", {"FR": "2A41 1A42 1A44 TA43"}),
    ("YENA", {"FR": "2CD 2A43 1A43 TA41 TD"}),
    ("ESSEDOH", {"FR": "2A42 1A41 1D TA42"}),
    ("KPELI", {"ANG": "2A42 2A43 1A43 1A44 1D TA42 TD"}),
    ("TORA", {"ANG": "2A41 2CD 1A41 1A42 TA41 TA43"}),
    ("ADJIGBLI", {"ALL": "2A41 2A43 1A42 1A44 TA42"}),
    ("ALLAHARE", {"ALL": "2A42 1A41 1A43 TA41 TA43"}),
    ("TCHANTCHA", {"PHILO": "2A41 2A43 1A41 1A42 1A43 TA41 TD"}),
    ("KOFFI", {"PHILO": "2A42 2CD 1A44 1D TA42 TA43"}),
    ("AMADOU", {"HG": "2A41 1A41 1A44 TA43", "ECM": "2A42 1A42 1A43 1D"}),
    ("MEGNAOSSAN", {"HG": "2A42 1A42 TA41 TD", "ECM": "2A43 2CD 1A44"}),
    ("NSOUKPOE", {"HG": "2A43 2CD 1A43 1D TA42", "ECM": "2A41 1A41"}),
    ("AMAH", {"MATHS": "2A41 2CD 1A43 1D TA41 TA43"}),
    ("DOUMALO", {"MATHS": "2A42 2A43 1A41 1A42 1A44 TA42 TD"}),
    ("BATAKO", {"PC": "2A42 2A43 1A41 1A44 TA41 TA43 TD"}),
    ("SIZING", {"PC": "2A41 2CD 1A42 1A43 1D TA42"}),
    ("KPOGLI", {"SVT": "2CD 2A43 1A41 1A44 TA43 TD"}),
    ("KADAGMA", {"SVT": "2A41 2A42 1A42 1A43 1D TA41 TA42"}),
    ("ABDOU", {"EPS": "2A41 2A42 2A43 2CD 1A41 1A42 1A43 1A44 1D TA41 TA42 TA43 TD"}),
    ("ABELIA", {"DESSIN": "2A41 2A42 2A43 2CD 1A41 1A42 1A43 1A44 1D TA41 TA42 TA43 TD"}),
    ("IDAYE", {"MUSIQUE": "2A41 2A42 2A43 2CD 1A41 1A42 1A43 1A44 1D TA41 TA42 TA43 TD"}),
]


def unique_username(base):
    base = slugify(base).replace("-", "") or "user"
    candidate = base
    suffix = 1
    while CustomUser.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


class Command(BaseCommand):
    help = "Charge les données du Lycée de Hiheatro (2025-2026) : classes, matières, horaires et enseignants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner", default="amah",
            help="Identifiant du propriétaire à rattacher (créé s’il n’existe pas).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        owner = self.get_owner(options["owner"])
        school = self.create_school(owner)
        year = self.create_year(school)
        subjects = self.create_subjects(school)
        classes = self.create_classes(school, year)
        class_subjects = self.create_class_subjects(classes, subjects)
        self.create_staff(school, year, classes, class_subjects)
        self.report(school, year)

    def get_owner(self, username):
        owner = CustomUser.objects.filter(username=username).first()
        if not owner:
            owner = CustomUser.objects.create(
                username=username, last_name=username.upper(),
                role=CustomUser.Role.OWNER,
            )
            owner.set_password(f"{username}@")
            owner.save(update_fields=["password"])
            self.stdout.write(f"Propriétaire créé : {username} / {username}@")
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
            school=school, name=YEAR_NAME,
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

    def create_classes(self, school, year):
        levels = {level.name: level for level in SchoolLevel.objects.filter(school=school)}
        classes = {}
        for group, (level_name, series, _hours_key) in CLASSES.items():
            level = levels.get(level_name)
            if not level:
                raise CommandError(f"Niveau « {level_name} » absent du référentiel de l’école.")
            school_class, _ = SchoolClass.objects.get_or_create(
                academic_year=year, level=level, series=series, group=group,
                defaults={"school": school},
            )
            classes[group] = school_class
        return classes

    def create_class_subjects(self, classes, subjects):
        class_subjects = {}
        for group, school_class in classes.items():
            hours_key = CLASSES[group][2]
            class_subjects[group] = {}
            for code, hours in WEEKLY_HOURS[hours_key].items():
                configuration, _ = ClassSubject.objects.get_or_create(
                    school_class=school_class, subject=subjects[code],
                    defaults={"weekly_hours": hours, "coefficient": 1},
                )
                class_subjects[group][code] = configuration
        return class_subjects

    def create_staff(self, school, year, classes, class_subjects):
        self.unmatched = []
        self.workload = {}
        for last_name, teaching in STAFF:
            teacher = CustomUser.objects.filter(last_name=last_name, role=CustomUser.Role.TEACHER).first()
            if not teacher:
                teacher = CustomUser.objects.create(
                    username=unique_username(last_name),
                    last_name=last_name,
                    role=CustomUser.Role.TEACHER,
                    profession="/".join(teaching),
                )
                teacher.set_password(teacher.username)
                teacher.save(update_fields=["password"])
            SchoolMembership.objects.get_or_create(
                school=school, user=teacher, defaults={"role": CustomUser.Role.TEACHER},
            )

            hours = 0
            for code, groups in teaching.items():
                for group in groups.split():
                    configuration = class_subjects.get(group, {}).get(code)
                    if not configuration:
                        # Matière non prévue pour cette série (allemand en D/CD,
                        # ECM en terminale) : l'affectation est signalée.
                        self.unmatched.append(f"{group}/{code} → {last_name}")
                        continue
                    assignment, _ = TeacherClassAssignment.objects.get_or_create(
                        school=school, academic_year=year,
                        teacher=teacher, school_class=classes[group],
                    )
                    TeacherAssignmentSubject.objects.get_or_create(
                        assignment=assignment, class_subject=configuration,
                    )
                    hours += configuration.weekly_hours
            self.workload[last_name] = hours

    def report(self, school, year):
        self.stdout.write(self.style.SUCCESS(f"\n{school.name} — {year.name}"))
        self.stdout.write(f"  Classes         : {SchoolClass.objects.filter(academic_year=year).count()}")
        self.stdout.write(f"  Matières        : {Subject.objects.filter(school=school).count()}")
        self.stdout.write(f"  Enseignants     : {SchoolMembership.objects.filter(school=school, role=CustomUser.Role.TEACHER).count()}")
        self.stdout.write(
            f"  Config. horaires: {ClassSubject.objects.filter(school_class__academic_year=year).count()}"
        )
        self.stdout.write(
            f"  Affectations    : {TeacherAssignmentSubject.objects.filter(assignment__academic_year=year).count()}"
        )
        self.stdout.write("\n  Charge hebdomadaire par enseignant :")
        for name, hours in sorted(self.workload.items()):
            self.stdout.write(f"    {name:12} {hours:2} h")
        if self.unmatched:
            self.stdout.write(self.style.WARNING(
                f"\n  Affectations ignorées (matière non prévue pour la série) :\n    "
                + "\n    ".join(self.unmatched)
            ))
