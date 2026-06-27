from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        OWNER = "proprietaire", "Propriétaire"
        TEACHER = "enseignant", "Enseignant"
        STUDENT = "eleve", "Élève"
        PARENT = "parent", "Parent"
        ACCOUNTANT = "comptable", "Comptable"
        SECRETARY = "secretaire", "Secrétaire"
        CENSEUR = "censeur", "Censeur"
        PROVISEUR = "proviseur", "Proviseur"
        SURVEILLANT = "surveillant", "Surveillant"
        STAFF = "personnel", "Personnel"

    class Gender(models.TextChoices):
        MALE = "M", "Masculin"
        FEMALE = "F", "Féminin"

    username = models.CharField("nom d’utilisateur", max_length=150, unique=True)
    email = models.EmailField("adresse courriel", null=True, blank=True)
    phone = models.CharField("numéro de téléphone", max_length=30, null=True, blank=True)
    gender = models.CharField("genre", max_length=1, choices=Gender.choices, blank=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.STAFF)
    is_archived = models.BooleanField("archivé", default=False)
    primary_subject = models.CharField("matière principale", max_length=100, blank=True)
    secondary_subject = models.CharField("matière secondaire", max_length=100, blank=True)
    tertiary_subject = models.CharField("matière tertiaire", max_length=100, blank=True)
    date_of_birth = models.DateField("date de naissance", null=True, blank=True)
    address = models.TextField("adresse", blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        full_name = self.get_full_name().strip() or self.phone
        return f"{full_name} ({self.get_role_display()})"


class School(models.Model):
    name = models.CharField("nom", max_length=180)
    code = models.SlugField("code", max_length=60, unique=True)
    logo = models.ImageField("logo", upload_to="schools/logos/", null=True, blank=True)
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="owned_schools",
        verbose_name="propriétaire",
    )
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "école"
        verbose_name_plural = "écoles"

    def __str__(self):
        return self.name


class SchoolMembership(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="school_memberships")
    role = models.CharField("rôle", max_length=20, choices=CustomUser.Role.choices)
    is_active = models.BooleanField("active", default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "user"], name="unique_school_user"),
        ]
        ordering = ["school", "user__last_name"]
        verbose_name = "adhésion à une école"
        verbose_name_plural = "adhésions aux écoles"

    def __str__(self):
        return f"{self.user} — {self.school}"


class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField("nom", max_length=120)
    code = models.SlugField("code", max_length=40)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_subject_name_per_school"),
            models.UniqueConstraint(fields=["school", "code"], name="unique_subject_code_per_school"),
        ]
        verbose_name = "matière"
        verbose_name_plural = "matières"

    def __str__(self):
        return f"{self.name} — {self.school.name}"


class AcademicYear(models.Model):
    class DivisionSystem(models.TextChoices):
        TRIMESTER = "trimestre", "Trimestres"
        SEMESTER = "semestre", "Semestres"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField("nom", max_length=30)
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")
    division_system = models.CharField(
        "découpage",
        max_length=12,
        choices=DivisionSystem.choices,
        default=DivisionSystem.TRIMESTER,
    )
    is_active = models.BooleanField("active", default=False)
    is_closed = models.BooleanField("clôturée", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_year_name_per_school"),
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_active=True),
                name="one_active_academic_year_per_school",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="academic_year_end_after_start",
            ),
            models.CheckConstraint(
                condition=~Q(is_closed=True, is_active=True),
                name="closed_academic_year_cannot_be_active",
            ),
        ]
        verbose_name = "année académique"
        verbose_name_plural = "années académiques"

    def __str__(self):
        return f"{self.name} — {self.school.name}"


class AcademicPeriod(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="periods")
    number = models.PositiveSmallIntegerField("numéro")
    name = models.CharField("nom", max_length=40)
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")
    is_active = models.BooleanField("active", default=False)
    is_closed = models.BooleanField("clôturée", default=False)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "number"], name="unique_period_number_per_year"),
            models.UniqueConstraint(
                fields=["academic_year"],
                condition=Q(is_active=True),
                name="one_active_period_per_academic_year",
            ),
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")), name="period_end_after_start"),
        ]
        verbose_name = "période académique"
        verbose_name_plural = "périodes académiques"

    def __str__(self):
        return f"{self.name} — {self.academic_year.name}"


class SchoolLevel(models.Model):
    class Stage(models.TextChoices):
        PRIMARY = "primaire", "Primaire"
        MIDDLE = "college", "Collège"
        HIGH = "lycee", "Lycée"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="levels")
    name = models.CharField("nom", max_length=30)
    stage = models.CharField("cycle", max_length=12, choices=Stage.choices)
    order = models.PositiveSmallIntegerField("ordre")
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_level_name_per_school"),
            models.UniqueConstraint(fields=["school", "order"], name="unique_level_order_per_school"),
        ]
        verbose_name = "niveau scolaire"
        verbose_name_plural = "niveaux scolaires"

    def __str__(self):
        return f"{self.name} — {self.school.name}"


DEFAULT_SCHOOL_LEVELS = [
    ("CEI", SchoolLevel.Stage.PRIMARY),
    ("CP1", SchoolLevel.Stage.PRIMARY),
    ("CP2", SchoolLevel.Stage.PRIMARY),
    ("CE1", SchoolLevel.Stage.PRIMARY),
    ("CE2", SchoolLevel.Stage.PRIMARY),
    ("CM1", SchoolLevel.Stage.PRIMARY),
    ("CM2", SchoolLevel.Stage.PRIMARY),
    ("6ème", SchoolLevel.Stage.MIDDLE),
    ("5ème", SchoolLevel.Stage.MIDDLE),
    ("4ème", SchoolLevel.Stage.MIDDLE),
    ("3ème", SchoolLevel.Stage.MIDDLE),
    ("Seconde", SchoolLevel.Stage.HIGH),
    ("Première", SchoolLevel.Stage.HIGH),
    ("Terminale", SchoolLevel.Stage.HIGH),
]


@receiver(post_save, sender=School)
def create_default_school_levels(sender, instance, created, **kwargs):
    if created:
        SchoolLevel.objects.bulk_create([
            SchoolLevel(school=instance, name=name, stage=stage, order=index)
            for index, (name, stage) in enumerate(DEFAULT_SCHOOL_LEVELS, start=1)
        ])


class StudentEnrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "annulee", "Annulée"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="student_enrollments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="student_enrollments")
    student = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="student_enrollments")
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
        null=True,
        blank=True,
        verbose_name="niveau",
    )
    enrollment_number = models.CharField("matricule", max_length=50)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField("date d’inscription", auto_now_add=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "student"],
                name="unique_student_enrollment_per_year",
            ),
            models.UniqueConstraint(
                fields=["school", "enrollment_number"],
                name="unique_enrollment_number_per_school",
            ),
        ]
        verbose_name = "inscription d’élève"
        verbose_name_plural = "inscriptions d’élèves"

    def __str__(self):
        return f"{self.enrollment_number} — {self.student.get_full_name()}"

    def clean(self):
        super().clean()
        if self.academic_year_id and (
            not self.academic_year.is_active or self.academic_year.is_closed
        ):
            raise ValidationError({
                "academic_year": "Les inscriptions sont interdites pour une année inactive ou clôturée."
            })
        if self.school_id and self.academic_year_id and self.academic_year.school_id != self.school_id:
            raise ValidationError({"academic_year": "Cette année n’appartient pas à l’école sélectionnée."})
        if self.level_id and self.school_id and self.level.school_id != self.school_id:
            raise ValidationError({"level": "Ce niveau n’appartient pas à l’école sélectionnée."})
