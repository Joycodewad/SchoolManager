from datetime import time

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPERUSER = "superuser", "Superutilisateur"
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

    class StudentStatus(models.TextChoices):
        NEW = "nouveau", "Nouveau"
        REPEATING = "redoublant", "Redoublant"
        DROPPED_OUT = "abandon", "Abandon"
        # Diplômes de fin de cursus. Un élève les reçoit à la clôture de
        # l'année quand il a réussi l'examen de son niveau et que l'école ne
        # va pas plus loin : il quitte l'établissement avec son titre.
        CEPD_HOLDER = "titulaire_cepd", "Titulaire du CEPD"
        BEPC_HOLDER = "titulaire_bepc", "Titulaire du BEPC"
        BACHELOR = "bachelier", "Bachelier"
        # Filet pour une école dont l'examen ne porte aucun de ces noms.
        GRADUATED = "diplome", "Diplômé"

    class YearResult(models.TextChoices):
        PASSED = "reussi", "Réussi"
        FAILED = "echoue", "Échoué"

    username = models.CharField("nom d’utilisateur", max_length=150, unique=True)
    email = models.EmailField("adresse courriel", null=True, blank=True)
    phone = models.CharField("numéro de téléphone", max_length=30, null=True, blank=True)
    profession = models.CharField("profession", max_length=150, blank=True)
    gender = models.CharField("genre", max_length=1, choices=Gender.choices, blank=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.STAFF)
    is_archived = models.BooleanField("archivé", default=False)
    subjects = models.ManyToManyField("Subject", blank=True, related_name="personnel", verbose_name="matières enseignées")
    primary_subject = models.ForeignKey(
        "Subject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="primary_personnel", verbose_name="matière principale",
    )
    date_of_birth = models.DateField("date de naissance", null=True, blank=True)
    address = models.TextField("adresse", blank=True)
    health_information = models.TextField("allergies et soucis de santé", blank=True)
    signature = models.ImageField("signature", upload_to="personnel/signatures/", null=True, blank=True)
    enrollment_number = models.CharField("numéro matricule", max_length=50, null=True, blank=True)
    student_status = models.CharField(
        "statut de l’élève", max_length=20, choices=StudentStatus.choices,
        default=StudentStatus.NEW,
    )
    year_result = models.CharField(
        "résultat de fin d’année", max_length=8, choices=YearResult.choices,
        null=True, blank=True, default=None,
    )

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
    # Coordonnées imprimées en tête des bulletins.
    country = models.CharField("pays", max_length=120, blank=True, default="RÉPUBLIQUE TOGOLAISE")
    country_motto = models.CharField(
        "devise nationale", max_length=160, blank=True, default="Travail — Liberté — Patrie",
    )
    ministry = models.CharField(
        "ministère", max_length=200, blank=True,
        default="MINISTÈRE DE L’ÉDUCATION NATIONALE",
    )
    motto = models.CharField("devise", max_length=120, blank=True)
    phone = models.CharField("téléphone", max_length=80, blank=True)
    postal_box = models.CharField("boîte postale", max_length=80, blank=True)
    city = models.CharField("ville", max_length=80, blank=True)
    cabinet = models.CharField("cabinet", max_length=160, blank=True)
    general_secretariat = models.CharField("secrétariat général", max_length=160, blank=True)
    education_direction = models.CharField("direction régionale", max_length=160, blank=True)
    # Ville de la direction régionale : « Atakpamé » sous « Plateaux-Est ».
    direction_city = models.CharField("ville de la direction", max_length=80, blank=True)
    inspection = models.CharField("inspection", max_length=160, blank=True)
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


class SubjectCategory(models.Model):
    """Type de matière défini par l'établissement (facultative, littéraire, scientifique…)."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subject_categories")
    name = models.CharField("nom", max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_subject_category_per_school"),
        ]
        verbose_name = "type de matière"
        verbose_name_plural = "types de matières"

    def __str__(self):
        return f"{self.name} — {self.school.name}"


class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField("nom", max_length=120)
    code = models.SlugField("code", max_length=40)
    category = models.ForeignKey(
        SubjectCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subjects", verbose_name="type de matière",
    )
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
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField("nom", max_length=30)
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")
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


class AcademicSession(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="sessions")
    classes = models.ManyToManyField("SchoolClass", related_name="academic_sessions", verbose_name="classes concernées")
    name = models.CharField("nom", max_length=80)
    label = models.CharField("label", max_length=80)
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")
    is_active = models.BooleanField("active", default=True)
    is_final = models.BooleanField(
        "dernière session de l'année", default=False,
        help_text="Les bulletins de cette session portent la moyenne annuelle.",
    )
    is_closed = models.BooleanField("clôturée", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "name"], name="unique_session_name_per_year"),
            models.CheckConstraint(condition=~Q(is_closed=True, is_active=True), name="closed_session_cannot_be_active"),
        ]
        verbose_name = "session académique"
        verbose_name_plural = "sessions académiques"

    def __str__(self):
        return f"{self.name} — {self.academic_year.name}"


class SessionClosure(models.Model):
    """Archive figée d'une session au moment de sa clôture.

    Les bulletins portent déjà leur propre instantané (`ReportCard.payload`)
    et restent la source d'affichage. Cette table conserve ce qui n'y figure
    pas — le détail brut des notes, la discipline et les appels — pour que la
    session reste relisible telle quelle même si une classe est regroupée, une
    matière renommée ou une inscription supprimée par la suite.
    """

    session = models.OneToOneField(
        AcademicSession, on_delete=models.CASCADE, related_name="closure",
        verbose_name="session",
    )
    closed_at = models.DateTimeField("clôturée le", auto_now_add=True)
    closed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="closed_sessions", verbose_name="clôturée par",
    )
    report_card_count = models.PositiveIntegerField("bulletins", default=0)
    grade_entry_count = models.PositiveIntegerField("notes", default=0)
    discipline_count = models.PositiveIntegerField("entrées de discipline", default=0)
    attendance_session_count = models.PositiveIntegerField("appels", default=0)
    attendance_record_count = models.PositiveIntegerField("présences", default=0)
    payload = models.JSONField("archive", default=dict)

    class Meta:
        ordering = ["-closed_at"]
        verbose_name = "clôture de session"
        verbose_name_plural = "clôtures de session"

    def __str__(self):
        return f"Clôture — {self.session}"


class YearClosure(models.Model):
    """Archive figée d'une année académique au moment de sa clôture.

    Clôturer une année, c'est arrêter ses comptes et faire passer les élèves.
    L'état d'avant — les classes, qui était inscrit où, ce que chacun devait —
    ne doit pas dépendre de ce qui sera modifié ensuite : il est recopié ici,
    et le détail du sort de chaque élève avec lui.
    """

    academic_year = models.OneToOneField(
        AcademicYear, on_delete=models.CASCADE, related_name="closure",
        verbose_name="année académique",
    )
    next_year = models.ForeignKey(
        AcademicYear, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incoming_closures", verbose_name="année suivante",
    )
    closed_at = models.DateTimeField("clôturée le", auto_now_add=True)
    closed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="closed_years", verbose_name="clôturée par",
    )
    class_count = models.PositiveIntegerField("classes", default=0)
    enrollment_count = models.PositiveIntegerField("inscriptions", default=0)
    promoted_count = models.PositiveIntegerField("passages", default=0)
    repeated_count = models.PositiveIntegerField("redoublements", default=0)
    graduated_count = models.PositiveIntegerField("sorties diplômées", default=0)
    unassigned_count = models.PositiveIntegerField("sans classe", default=0)
    undecided_count = models.PositiveIntegerField("sans décision", default=0)
    # Volume de vie scolaire arrêté avec l'année. Ces écritures restent
    # rattachées à leur année et ne suivent pas les élèves : l'année suivante
    # repart vierge, sans que rien n'ait été effacé.
    discipline_count = models.PositiveIntegerField("entrées de discipline", default=0)
    attendance_session_count = models.PositiveIntegerField("appels", default=0)
    attendance_record_count = models.PositiveIntegerField("présences", default=0)
    carried_debt_total = models.DecimalField(
        "impayés reportés", max_digits=14, decimal_places=2, default=0,
    )
    # Ce que la clôture a reconduit sur l'année suivante. Sans classes dans
    # l'année neuve, aucun élève admis n'aurait où être affecté : la
    # reconduction fait partie de la clôture, et son bilan avec.
    copied_class_count = models.PositiveIntegerField("classes reconduites", default=0)
    copied_subject_count = models.PositiveIntegerField("matières reconduites", default=0)
    copied_fee_plan_count = models.PositiveIntegerField("barèmes reconduits", default=0)
    payload = models.JSONField("archive", default=dict)

    class Meta:
        ordering = ["-closed_at"]
        verbose_name = "clôture d’année"
        verbose_name_plural = "clôtures d’année"

    def __str__(self):
        return f"Clôture — {self.academic_year.name}"


class CarriedDebt(models.Model):
    """Écolage resté impayé à la clôture d'une année.

    L'inscription de l'année close ne bouge plus ; la dette, elle, suit
    l'élève. Elle se règle plus tard, pendant n'importe quelle année, en une
    fois ou par versements.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="carried_debts")
    student = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="carried_debts",
        verbose_name="élève",
    )
    origin_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="carried_debts",
        verbose_name="année d’origine",
    )
    origin_enrollment = models.OneToOneField(
        "StudentEnrollment", on_delete=models.PROTECT, related_name="carried_debt",
        verbose_name="inscription d’origine",
    )
    amount = models.DecimalField("montant dû", max_digits=12, decimal_places=2)
    settled_amount = models.DecimalField(
        "montant réglé", max_digits=12, decimal_places=2, default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["origin_year__start_date", "student__last_name"]
        verbose_name = "impayé reporté"
        verbose_name_plural = "impayés reportés"

    @property
    def outstanding(self):
        """Ce qu'il reste à régler sur cette dette."""
        return self.amount - self.settled_amount

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.origin_year.name} : {self.outstanding}"


class CarriedDebtPayment(models.Model):
    """Versement sur un impayé reporté, tracé comme un encaissement d'écolage."""

    debt = models.ForeignKey(CarriedDebt, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("montant", max_digits=12, decimal_places=2)
    paid_on = models.DateField("date de paiement")
    method = models.CharField("mode de paiement", max_length=20, default="espece")
    reference = models.CharField("référence", max_length=100, blank=True)
    notes = models.TextField("notes", blank=True)
    received_by = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="received_debt_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        verbose_name = "versement sur impayé"
        verbose_name_plural = "versements sur impayés"

    def __str__(self):
        return f"{self.amount} — {self.debt.student.get_full_name()}"


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
    # Moyenne exigée en fin d'année. Sur un niveau d'examen, elle porte sur la
    # note de l'examen officiel plutôt que sur la moyenne annuelle : c'est
    # l'examen qui décide du passage, pas le conseil de classe.
    passing_average = models.DecimalField(
        "moyenne de passage", max_digits=4, decimal_places=2, default=10,
    )
    is_exam_level = models.BooleanField(
        "classe d'examen", default=False,
        help_text="Niveau sanctionné par un examen officiel : la décision de "
                  "fin d'année suit le résultat de l'examen.",
    )
    exam_name = models.CharField(
        "examen", max_length=30, blank=True, default="",
        help_text="Nom de l'examen, écrit tel quel sur le bulletin (CEPD, BEPC, BAC 1…).",
    )

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


# Cursus togolais. Le troisième terme nomme l'examen qui sanctionne le niveau,
# quand il y en a un : CM2, 3ème, Première et Terminale sont les quatre paliers
# où c'est l'examen officiel, et non le conseil de classe, qui fait passer.
DEFAULT_SCHOOL_LEVELS = [
    ("CEI", SchoolLevel.Stage.PRIMARY, ""),
    ("CP1", SchoolLevel.Stage.PRIMARY, ""),
    ("CP2", SchoolLevel.Stage.PRIMARY, ""),
    ("CE1", SchoolLevel.Stage.PRIMARY, ""),
    ("CE2", SchoolLevel.Stage.PRIMARY, ""),
    ("CM1", SchoolLevel.Stage.PRIMARY, ""),
    ("CM2", SchoolLevel.Stage.PRIMARY, "CEPD"),
    ("6ème", SchoolLevel.Stage.MIDDLE, ""),
    ("5ème", SchoolLevel.Stage.MIDDLE, ""),
    ("4ème", SchoolLevel.Stage.MIDDLE, ""),
    ("3ème", SchoolLevel.Stage.MIDDLE, "BEPC"),
    ("Seconde", SchoolLevel.Stage.HIGH, ""),
    ("Première", SchoolLevel.Stage.HIGH, "Baccalauréat Première partie"),
    ("Terminale", SchoolLevel.Stage.HIGH, "Baccalauréat Deuxième partie"),
]


@receiver(post_save, sender=School)
def create_default_school_levels(sender, instance, created, **kwargs):
    if created:
        SchoolLevel.objects.bulk_create([
            SchoolLevel(
                school=instance, name=name, stage=stage, order=index,
                is_exam_level=bool(exam), exam_name=exam,
            )
            for index, (name, stage, exam) in enumerate(DEFAULT_SCHOOL_LEVELS, start=1)
        ])


class SchoolClass(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classes")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")
    level = models.ForeignKey(SchoolLevel, on_delete=models.PROTECT, related_name="classes")
    homeroom_teacher = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="homeroom_classes", verbose_name="enseignant titulaire",
    )
    series = models.CharField("série", max_length=20, blank=True, default="")
    group = models.CharField("groupe", max_length=20)
    maximum_capacity = models.PositiveSmallIntegerField("capacité maximale", default=100)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level__order", "series", "group"]
        constraints = [models.UniqueConstraint(fields=["academic_year", "level", "series", "group"], name="unique_class_per_academic_year")]
        verbose_name = "classe"
        verbose_name_plural = "classes"

    @property
    def name(self):
        return self.group

    def __str__(self):
        return f"{self.name} — {self.academic_year.name}"

    def clean(self):
        super().clean()
        if self.school_id and self.academic_year_id and self.academic_year.school_id != self.school_id:
            raise ValidationError({"academic_year": "Cette année n’appartient pas à l’école sélectionnée."})
        if self.school_id and self.level_id and self.level.school_id != self.school_id:
            raise ValidationError({"level": "Ce niveau n’appartient pas à l’école sélectionnée."})


class ClassSubject(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="subject_configurations")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_configurations")
    weekly_hours = models.PositiveSmallIntegerField("heures par semaine")
    coefficient = models.DecimalField("coefficient", max_digits=5, decimal_places=2)
    can_schedule_after_break = models.BooleanField("programmable après la récréation", default=True)
    can_schedule_afternoon = models.BooleanField("programmable l’après-midi", default=True)

    class Meta:
        ordering = ["subject__name"]
        constraints = [
            models.UniqueConstraint(fields=["school_class", "subject"], name="unique_subject_per_class"),
            models.CheckConstraint(condition=Q(weekly_hours__gt=0), name="class_subject_weekly_hours_positive"),
            models.CheckConstraint(condition=Q(coefficient__gt=0), name="class_subject_coefficient_positive"),
        ]
        verbose_name = "matière de classe"
        verbose_name_plural = "matières de classe"

    def __str__(self):
        return f"{self.subject.name} — {self.school_class.name}"


class TeacherClassAssignment(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="teacher_class_assignments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="teacher_class_assignments")
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="class_assignments")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="teacher_assignments")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["teacher", "school_class"], name="unique_teacher_class_assignment")]
        verbose_name = "affectation d’enseignant"
        verbose_name_plural = "affectations d’enseignants"


class TeacherAssignmentSubject(models.Model):
    assignment = models.ForeignKey(TeacherClassAssignment, on_delete=models.CASCADE, related_name="subject_links")
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name="teacher_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assignment", "class_subject"], name="unique_subject_per_teacher_assignment"),
            models.UniqueConstraint(fields=["class_subject"], name="one_teacher_per_class_subject"),
        ]
        verbose_name = "matière affectée à un enseignant"
        verbose_name_plural = "matières affectées aux enseignants"


class TeacherUnavailability(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, "Lundi"
        TUESDAY = 1, "Mardi"
        WEDNESDAY = 2, "Mercredi"
        THURSDAY = 3, "Jeudi"
        FRIDAY = 4, "Vendredi"
        SATURDAY = 5, "Samedi"
        SUNDAY = 6, "Dimanche"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="teacher_unavailabilities")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="teacher_unavailabilities")
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="unavailabilities")
    day = models.PositiveSmallIntegerField("jour", choices=Day.choices)
    all_day = models.BooleanField("toute la journée", default=False)
    start_time = models.TimeField("heure de début", null=True, blank=True)
    end_time = models.TimeField("heure de fin", null=True, blank=True)

    class Meta:
        ordering = ["day", "start_time"]
        constraints = [models.CheckConstraint(
            condition=(Q(all_day=True, start_time__isnull=True, end_time__isnull=True) | Q(all_day=False, start_time__isnull=False, end_time__isnull=False)),
            name="teacher_unavailability_valid_times",
        )]
        verbose_name = "indisponibilité d’enseignant"
        verbose_name_plural = "indisponibilités d’enseignants"


class StudentEnrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "annulee", "Annulée"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="student_enrollments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="student_enrollments")
    student = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="student_enrollments")
    guardian = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="guarded_student_enrollments",
        null=True, blank=True, verbose_name="tuteur",
    )
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
        null=True,
        blank=True,
        verbose_name="niveau",
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="student_enrollments",
        null=True, blank=True, verbose_name="classe",
    )
    series = models.CharField("série", max_length=20, blank=True, default="")
    previous_average = models.DecimalField(
        "moyenne scolaire de l’année écoulée", max_digits=5, decimal_places=2,
        null=True, blank=True,
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

    @property
    def student_status(self):
        return self.student.student_status

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
        if self.school_class_id and (
            self.school_class.school_id != self.school_id
            or self.school_class.academic_year_id != self.academic_year_id
            or self.school_class.level_id != self.level_id
        ):
            raise ValidationError({"school_class": "Cette classe ne correspond pas à l’école, l’année et au niveau sélectionnés."})


class AttendanceSession(models.Model):
    """Un appel : une classe, un jour, éventuellement une matière.

    L'appel est le relevé, la ligne `AttendanceRecord` en est le détail élève.
    Séparer les deux permet de savoir qu'un appel a bien été fait même si
    personne n'était absent — une classe sans ligne d'absence et une classe
    dont l'appel n'a jamais été fait ne se confondent pas.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="attendance_sessions")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="attendance_sessions",
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="attendance_sessions",
    )
    # Matière facultative : au primaire l'appel est journalier, au secondaire
    # il se fait souvent cours par cours.
    class_subject = models.ForeignKey(
        ClassSubject, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="attendance_sessions", verbose_name="matière",
    )
    taken_on = models.DateField("date de l’appel")
    period = models.CharField(
        "créneau", max_length=40, blank=True,
        help_text="Créneau horaire ou moment de la journée, libre.",
    )
    taken_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="taken_attendance_sessions", verbose_name="fait par",
    )
    note = models.TextField("observation", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-taken_on", "school_class__group"]
        constraints = [
            # Un seul appel par classe, par jour et par créneau : refaire
            # l'appel corrige le relevé existant au lieu de le dédoubler.
            models.UniqueConstraint(
                fields=["school_class", "taken_on", "class_subject", "period"],
                name="unique_attendance_session_per_slot",
            ),
        ]
        verbose_name = "appel"
        verbose_name_plural = "appels"

    def __str__(self):
        return f"Appel {self.school_class.group} — {self.taken_on:%d/%m/%Y}"

    def clean(self):
        super().clean()
        if self.school_class_id and (
            self.school_class.school_id != self.school_id
            or self.school_class.academic_year_id != self.academic_year_id
        ):
            raise ValidationError(
                {"school_class": "Cette classe ne correspond pas à l’école et à l’année sélectionnées."}
            )
        if self.class_subject_id and self.class_subject.school_class_id != self.school_class_id:
            raise ValidationError({"class_subject": "Cette matière n’est pas enseignée dans cette classe."})


class AttendanceRecord(models.Model):
    """Présence d'un élève à un appel."""

    class Status(models.TextChoices):
        PRESENT = "present", "Présent"
        ABSENT = "absent", "Absent"
        LATE = "retard", "En retard"
        EXCUSED = "excuse", "Absence justifiée"

    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="records",
    )
    enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.CASCADE, related_name="attendance_records",
    )
    status = models.CharField(
        "statut", max_length=10, choices=Status.choices, default=Status.PRESENT,
    )
    minutes_late = models.PositiveSmallIntegerField("minutes de retard", default=0)
    comment = models.CharField("motif", max_length=200, blank=True)

    class Meta:
        ordering = ["enrollment__student__last_name", "enrollment__student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrollment"], name="unique_attendance_per_student",
            ),
        ]
        verbose_name = "présence"
        verbose_name_plural = "présences"

    def __str__(self):
        return f"{self.enrollment} — {self.get_status_display()}"


class DisciplineRecord(models.Model):
    class EntryType(models.TextChoices):
        LATE = "retard", "Retard"
        ABSENCE = "absence", "Absence"
        INCIDENT = "incident", "Incident"

    class Severity(models.TextChoices):
        LOW = "leger", "Léger"
        MEDIUM = "moyen", "Moyen"
        HIGH = "grave", "Grave"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="discipline_records")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="discipline_records")
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name="discipline_records")
    entry_type = models.CharField("type", max_length=12, choices=EntryType.choices)
    occurred_on = models.DateField("date")
    late_hours = models.DecimalField("heures de retard", max_digits=5, decimal_places=2, default=0)
    incident_type = models.CharField("type d’incident", max_length=120, blank=True)
    severity = models.CharField("gravité", max_length=12, choices=Severity.choices, blank=True)
    description = models.TextField("description", blank=True)
    action_taken = models.TextField("mesure prise", blank=True)
    recorded_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recorded_discipline_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(late_hours__gte=0),
                name="discipline_record_late_hours_positive",
            ),
        ]
        verbose_name = "entrée de discipline"
        verbose_name_plural = "entrées de discipline"

    def __str__(self):
        return f"{self.get_entry_type_display()} — {self.enrollment}"

    def clean(self):
        super().clean()
        if self.enrollment_id and (
            self.enrollment.school_id != self.school_id
            or self.enrollment.academic_year_id != self.academic_year_id
        ):
            raise ValidationError({"enrollment": "Cette inscription ne correspond pas à l’école et à l’année sélectionnées."})
        if self.entry_type in {self.EntryType.LATE, self.EntryType.ABSENCE} and self.late_hours <= 0:
            raise ValidationError({"late_hours": "Saisissez un nombre d’heures supérieur à 0."})
        if self.entry_type == self.EntryType.INCIDENT and not self.incident_type.strip():
            raise ValidationError({"incident_type": "Précisez le type d’incident."})


class TuitionFeePlan(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="tuition_fee_plans")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="tuition_fee_plans")
    school_class = models.OneToOneField(SchoolClass, on_delete=models.CASCADE, related_name="tuition_fee_plan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["school_class__level__order", "school_class__group"]
        verbose_name = "barème de scolarité"
        verbose_name_plural = "barèmes de scolarité"


class FeeModule(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="fee_modules")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="fee_modules")
    name = models.CharField("nom", max_length=100)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["school", "academic_year", "name"], name="unique_fee_module_per_year")]


class ClassFeeItem(models.Model):
    plan = models.ForeignKey(TuitionFeePlan, on_delete=models.CASCADE, related_name="items")
    fee_module = models.ForeignKey(FeeModule, on_delete=models.PROTECT, related_name="class_fee_items")
    male_amount = models.DecimalField("montant masculin", max_digits=12, decimal_places=2)
    female_amount = models.DecimalField("montant féminin", max_digits=12, decimal_places=2)
    payable_in_installments = models.BooleanField("payable en tranches", default=False)

    class Meta:
        ordering = ["fee_module__name"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "fee_module"], name="unique_fee_module_per_class_plan"),
            models.CheckConstraint(condition=Q(male_amount__gte=0), name="class_fee_male_non_negative"),
            models.CheckConstraint(condition=Q(female_amount__gte=0), name="class_fee_female_non_negative"),
        ]


class FeeInstallment(models.Model):
    class_fee = models.ForeignKey(ClassFeeItem, on_delete=models.CASCADE, related_name="installments")
    name = models.CharField("nom", max_length=80)
    percentage = models.DecimalField("pourcentage", max_digits=5, decimal_places=2)
    due_date = models.DateField("échéance", null=True, blank=True)
    order = models.PositiveSmallIntegerField("ordre")

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["class_fee", "order"], name="unique_installment_order_per_class_fee"),
            models.CheckConstraint(condition=Q(percentage__gt=0, percentage__lte=100), name="fee_installment_percentage_range"),
        ]


class FeePayment(models.Model):
    class Method(models.TextChoices):
        CASH = "especes", "Espèces"
        MOBILE = "mobile_money", "Mobile Money"
        BANK = "banque", "Banque"
        OTHER = "autre", "Autre"

    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.PROTECT, related_name="fee_payments")
    class_fee = models.ForeignKey(ClassFeeItem, on_delete=models.PROTECT, related_name="payments")
    installment = models.ForeignKey(FeeInstallment, on_delete=models.PROTECT, related_name="payments", null=True, blank=True)
    amount = models.DecimalField("montant", max_digits=12, decimal_places=2)
    paid_on = models.DateField("date de paiement")
    method = models.CharField("mode de paiement", max_length=20, choices=Method.choices, default=Method.CASH)
    reference = models.CharField("référence", max_length=100, blank=True)
    notes = models.TextField("notes", blank=True)
    received_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="received_fee_payments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="fee_payment_amount_positive"),
        ]


class ExpenseCategory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="expense_categories")
    name = models.CharField("nom", max_length=100)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["school", "name"], name="unique_expense_category_per_school")]
        verbose_name = "catégorie de dépense"
        verbose_name_plural = "catégories de dépenses"


class SchoolExpense(models.Model):
    class Method(models.TextChoices):
        CASH = "especes", "Espèces"
        MOBILE = "mobile_money", "Mobile Money"
        BANK = "banque", "Banque"
        CHEQUE = "cheque", "Chèque"
        OTHER = "autre", "Autre"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="expenses")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    label = models.CharField("libellé", max_length=180)
    description = models.TextField("description", blank=True)
    beneficiary = models.CharField("bénéficiaire ou fournisseur", max_length=180, blank=True)
    amount = models.DecimalField("montant", max_digits=12, decimal_places=2)
    expense_date = models.DateField("date de dépense")
    method = models.CharField("mode de paiement", max_length=20, choices=Method.choices, default=Method.CASH)
    reference = models.CharField("référence", max_length=100, blank=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="recorded_school_expenses")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="school_expense_amount_positive")]
        verbose_name = "dépense scolaire"
        verbose_name_plural = "dépenses scolaires"


class GradeScheme(models.Model):
    class CalculationMethod(models.TextChoices):
        EQUAL = "equal", "Même poids pour chaque ligne"
        WEIGHTED = "weighted", "Pourcentage par ligne"
        GROUPS = "groups", "Moyenne des groupes"

    session = models.OneToOneField(AcademicSession, on_delete=models.CASCADE, related_name="grade_scheme")
    calculation_method = models.CharField("mode de calcul", max_length=12, choices=CalculationMethod.choices, default=CalculationMethod.EQUAL)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="created_grade_schemes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GradeGroup(models.Model):
    scheme = models.ForeignKey(GradeScheme, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField("nom", max_length=100)
    weight = models.DecimalField("pourcentage", max_digits=5, decimal_places=2, null=True, blank=True)
    order = models.PositiveSmallIntegerField("ordre")

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["scheme", "name"], name="unique_grade_group_name"),
            models.UniqueConstraint(fields=["scheme", "order"], name="unique_grade_group_order"),
            models.CheckConstraint(condition=Q(weight__isnull=True) | Q(weight__gt=0, weight__lte=100), name="grade_group_weight_range"),
        ]


class GradeLine(models.Model):
    scheme = models.ForeignKey(GradeScheme, on_delete=models.CASCADE, related_name="lines")
    group = models.ForeignKey(GradeGroup, on_delete=models.CASCADE, related_name="lines", null=True, blank=True)
    name = models.CharField("nom", max_length=100)
    weight = models.DecimalField("pourcentage", max_digits=5, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField("note maximale", max_digits=5, decimal_places=2, default=20)
    order = models.PositiveSmallIntegerField("ordre")

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["scheme", "name"], name="unique_grade_line_name"),
            models.UniqueConstraint(fields=["scheme", "order"], name="unique_grade_line_order"),
            models.CheckConstraint(condition=Q(max_score__gt=0), name="grade_line_max_score_positive"),
            models.CheckConstraint(condition=Q(weight__isnull=True) | Q(weight__gt=0, weight__lte=100), name="grade_line_weight_range"),
        ]


class GradeEntry(models.Model):
    line = models.ForeignKey(GradeLine, on_delete=models.CASCADE, related_name="entries")
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name="grade_entries")
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name="grade_entries")
    score = models.DecimalField("note", max_digits=6, decimal_places=2)
    entered_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="entered_grades")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["line", "enrollment", "class_subject"], name="unique_grade_entry"),
            models.CheckConstraint(condition=Q(score__gte=0), name="grade_entry_score_non_negative"),
        ]


class Timetable(models.Model):
    class Status(models.TextChoices):
        DRAFT = "brouillon", "Brouillon"
        VALIDATED = "valide", "Validé"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="timetables")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="timetables")
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.DRAFT)
    days_per_week = models.PositiveSmallIntegerField("jours par semaine", default=5)
    period_duration = models.PositiveSmallIntegerField("durée d’un créneau (minutes)", default=60)
    morning_start = models.TimeField("début de la matinée", default=time(7, 0))
    morning_end = models.TimeField("fin de la matinée", default=time(12, 0))
    afternoon_start = models.TimeField("début de l’après-midi", default=time(15, 0))
    afternoon_end = models.TimeField("fin de l’après-midi", default=time(18, 0))

    # Contraintes pédagogiques activables individuellement par l'utilisateur.
    enforce_paired_hours = models.BooleanField(
        "regrouper les heures par blocs de 2h (lycée)", default=True,
    )
    enforce_single_hour_middle = models.BooleanField(
        "1h par jour au collège", default=True,
    )
    enforce_day_spacing = models.BooleanField(
        "espacer d’au moins un jour les deux premières séances", default=True,
    )
    enforce_max_two_hours = models.BooleanField(
        "jamais plus de 2h d’une matière le même jour", default=True,
    )
    skip_primary = models.BooleanField(
        "ne pas générer pour le cycle primaire", default=True,
    )
    days_without_afternoon = models.JSONField(
        "jours sans cours l’après-midi", default=list, blank=True,
        help_text="Indices des jours (0 = lundi) où les créneaux d’après-midi restent vides.",
    )

    generated_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="generated_timetables")
    generated_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField("validé le", null=True, blank=True)

    class Meta:
        ordering = ["-generated_at"]
        constraints = [
            # Un seul emploi du temps par école et par année académique.
            models.UniqueConstraint(fields=["school", "academic_year"], name="unique_timetable_per_school_year"),
        ]
        verbose_name = "emploi du temps"
        verbose_name_plural = "emplois du temps"

    def __str__(self):
        return f"Emploi du temps {self.academic_year.name} — {self.school.name}"

    @property
    def is_validated(self):
        return self.status == self.Status.VALIDATED


class TimetablePeriod(models.Model):
    """Créneau horaire de la grille hebdomadaire.

    Les créneaux de pause ne reçoivent aucun cours et coupent la continuité :
    deux heures séparées par une pause ne forment jamais un bloc de 2h.
    """

    class Kind(models.TextChoices):
        COURSE = "cours", "Cours"
        BREAK = "pause", "Pause"

    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="periods")
    label = models.CharField("libellé", max_length=60, blank=True)
    kind = models.CharField("type", max_length=8, choices=Kind.choices, default=Kind.COURSE)
    start_time = models.TimeField("heure de début")
    end_time = models.TimeField("heure de fin")
    order = models.PositiveSmallIntegerField("ordre")

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["timetable", "order"], name="unique_period_order_per_timetable"),
            models.UniqueConstraint(fields=["timetable", "start_time"], name="unique_period_start_per_timetable"),
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="timetable_period_end_after_start"),
        ]
        verbose_name = "créneau horaire"
        verbose_name_plural = "créneaux horaires"

    def __str__(self):
        return f"{self.start_time:%H:%M}-{self.end_time:%H:%M} ({self.get_kind_display()})"

    @property
    def is_break(self):
        return self.kind == self.Kind.BREAK


class ExcludedTimetableClass(models.Model):
    """Classes écartées de la génération, matière par matière.

    L'exclusion porte sur un couple (matière, classe) : les autres matières de
    la classe restent programmées normalement.
    """

    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="excluded_classes")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="timetable_exclusions")
    classes = models.ManyToManyField(
        SchoolClass, related_name="timetable_exclusions", verbose_name="classes exclues",
    )

    class Meta:
        ordering = ["subject__name"]
        constraints = [
            models.UniqueConstraint(fields=["timetable", "subject"], name="unique_excluded_subject_per_timetable"),
        ]
        verbose_name = "exclusion de matière"
        verbose_name_plural = "exclusions de matière"

    def __str__(self):
        return f"{self.subject.name} exclue pour {self.classes.count()} classe(s)"


class ClassGroupSession(models.Model):
    """Classes réunies pour suivre une matière ensemble, au même créneau.

    Le regroupement n'est possible que si toutes les classes ont le même
    enseignant pour cette matière — sinon deux professeurs devraient assurer
    le même cours au même moment.
    """

    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="class_groups")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_groups")
    classes = models.ManyToManyField(
        SchoolClass, related_name="timetable_groups", verbose_name="classes réunies",
    )

    class Meta:
        ordering = ["subject__name"]
        verbose_name = "regroupement de classes"
        verbose_name_plural = "regroupements de classes"

    def __str__(self):
        groups = ", ".join(item.group for item in self.classes.all())
        return f"{self.subject.name} — {groups}"


class SubjectPeriodRestriction(models.Model):
    """Interdit de programmer une matière sur un créneau (et éventuellement un jour) donné."""

    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="restrictions")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="period_restrictions")
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE, related_name="restrictions")
    day = models.PositiveSmallIntegerField(
        "jour", choices=TeacherUnavailability.Day.choices, null=True, blank=True,
        help_text="Laisser vide pour interdire ce créneau tous les jours.",
    )

    class Meta:
        ordering = ["subject__name", "period__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "subject", "period", "day"],
                name="unique_subject_period_restriction",
            ),
        ]
        verbose_name = "interdiction de créneau"
        verbose_name_plural = "interdictions de créneaux"

    def __str__(self):
        scope = self.get_day_display() if self.day is not None else "tous les jours"
        return f"{self.subject.name} — {self.period} ({scope})"


class TimetableSlot(models.Model):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="slots")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="timetable_slots")
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name="timetable_slots")
    teacher = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="timetable_slots", verbose_name="enseignant",
    )
    day = models.PositiveSmallIntegerField("jour", choices=TeacherUnavailability.Day.choices)
    start_time = models.TimeField("heure de début")
    end_time = models.TimeField("heure de fin")

    class Meta:
        ordering = ["day", "start_time", "school_class__group"]
        constraints = [
            # Une classe ne peut avoir qu'un cours à un créneau donné.
            models.UniqueConstraint(
                fields=["timetable", "school_class", "day", "start_time"],
                name="unique_class_slot_per_time",
            ),
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="timetable_slot_end_after_start"),
        ]
        verbose_name = "créneau d’emploi du temps"
        verbose_name_plural = "créneaux d’emploi du temps"

    def __str__(self):
        return f"{self.school_class.group} — {self.class_subject.subject.name} ({self.get_day_display()} {self.start_time:%H:%M})"


def default_band_limits():
    """Aucune limite au départ : seule la capacité des classes borne alors la
    répartition."""
    return {}


class ClassAssignmentSettings(models.Model):
    """Règles de répartition des élèves sans classe, réglées par école.

    Répartir, c'est arbitrer entre plusieurs équilibres qui se contredisent :
    des effectifs égaux, autant de filles partout, les meilleurs devant, et des
    classes qui ne soient pas vidées de leurs bons élèves. Chaque établissement
    tranche à sa façon — ces réglages disent comment.

    Ils valent pour l'établissement, pas pour une année : ce sont des habitudes
    de maison, qui survivent au changement d'année.
    """

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="class_assignment_settings",
    )
    youngest_first = models.BooleanField(
        "les moins âgés dans les premières classes", default=True,
        help_text="À moyenne égale, l'élève le plus jeune passe devant. Les "
                  "plus âgés se retrouvent donc dans les dernières classes.",
    )
    best_first = models.BooleanField(
        "les meilleures moyennes dans les premières classes", default=True,
        help_text="Les élèves sont rangés par moyenne décroissante avant d'être "
                  "distribués, la première classe servie en premier.",
    )
    balance_headcount = models.BooleanField(
        "équilibrer les effectifs", default=True,
        help_text="Chaque élève rejoint la classe la moins remplie de son "
                  "niveau : les effectifs restent dans le même ordre de "
                  "grandeur au lieu de remplir une classe avant la suivante.",
    )
    balance_girls = models.BooleanField(
        "équilibrer le nombre de filles", default=True,
        help_text="Les filles sont réparties comme les effectifs, en tenant "
                  "compte de celles déjà inscrites dans chaque classe.",
    )
    reserved_excellent = models.PositiveSmallIntegerField(
        "excellents élèves réservés par classe", default=3,
        help_text="Nombre d'excellents élèves mis de côté pour chaque classe "
                  "avant la distribution, en commençant par les dernières : "
                  "sans cela, les meilleurs se concentrent tous devant. Zéro "
                  "désactive la réserve.",
    )
    excellent_minimum = models.DecimalField(
        "moyenne d'un excellent élève", max_digits=4, decimal_places=2, default=16,
        help_text="Moyenne à partir de laquelle un élève entre dans la réserve.",
    )
    band_limits = models.JSONField(
        "maximum par tranche de moyenne", default=default_band_limits, blank=True,
        help_text="Nombre maximal d'élèves d'une tranche de moyenne à placer "
                  "dans une même classe, niveau par niveau : "
                  "{\"7\": {\"18\": 2}} limite à deux les élèves de 18 à 20 "
                  "par classe du niveau 7. Une tranche absente ou à zéro n'est "
                  "pas limitée, et la limite cède plutôt que de laisser un "
                  "élève sans classe.",
    )
    allow_overflow = models.BooleanField(
        "dépasser légèrement la capacité", default=True,
        help_text="Quand toutes les classes d'un niveau sont pleines et qu'il "
                  "reste des élèves, la capacité maximale est dépassée plutôt "
                  "que de les laisser sans classe.",
    )
    overflow_margin = models.PositiveSmallIntegerField(
        "dépassement toléré par classe", default=5,
        help_text="Nombre de places ouvertes au-delà de la capacité maximale, "
                  "et seulement quand il n'y a plus de place ailleurs.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "règles de répartition"
        verbose_name_plural = "règles de répartition"

    def __str__(self):
        return f"Répartition — {self.school.name}"


class ReportCardSettings(models.Model):
    """Mise en forme des bulletins, réglée par école.

    Le calcul reste toujours une moyenne pondérée par les coefficients ; ce
    sont l'affichage et les seuils d'appréciation qui varient d'un
    établissement à l'autre.
    """

    class Template(models.TextChoices):
        STANDARD = "standard", "Standard"
        OFFICIEL = "officiel", "Officiel (compact)"

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="report_card_settings",
    )
    template = models.CharField(
        "modèle de bulletin", max_length=12,
        choices=Template.choices, default=Template.STANDARD,
        help_text="Disposition imprimée. Le modèle officiel reprend la maquette "
                  "administrative : une seule grille de notes et un pied de page "
                  "récapitulatif (trimestres, absences, décision du conseil).",
    )
    class Watermark(models.TextChoices):
        NONE = "aucun", "Aucun"
        TILED = "mosaique", "Mosaïque (texte répété)"
        DIAGONAL = "diagonale", "Bandeau en diagonale"
        LOGO = "logo", "Logo en fond"

    class WatermarkDensity(models.TextChoices):
        """Serrage du motif en mosaïque, du plus aéré au plus couvrant."""

        NORMAL = "normale", "Normale (lignes espacées)"
        FULL = "pleine", "Pleine (motif serré)"
        MAX = "max", "Maximale (page saturée)"

    class WatermarkSource(models.TextChoices):
        NAME = "nom", "Nom de l’établissement"
        CODE = "code", "Code de l’établissement"

    watermark = models.CharField(
        "filigrane", max_length=12,
        choices=Watermark.choices, default=Watermark.NONE,
        help_text="Ancien réglage à choix unique, conservé pour les établissements "
                  "paramétrés avant les filigranes combinés. C'est « watermarks » "
                  "qui fait foi à l'impression.",
    )
    watermarks = models.JSONField(
        "filigranes", default=list, blank=True,
        help_text="Marques de fond imprimées derrière le bulletin, contre la "
                  "photocopie. Elles se cumulent : mosaïque + diagonale + logo "
                  "peuvent être imprimées ensemble.",
    )
    watermark_density = models.CharField(
        "densité de la mosaïque", max_length=8,
        choices=WatermarkDensity.choices, default=WatermarkDensity.NORMAL,
        help_text="Serrage du texte répété, sans effet sur les autres filigranes.",
    )
    watermark_source = models.CharField(
        "texte du filigrane", max_length=8,
        choices=WatermarkSource.choices, default=WatermarkSource.NAME,
        help_text="Texte repris par le filigrane, sans effet sur le filigrane « logo ».",
    )
    show_score_detail = models.BooleanField(
        "afficher le détail des notes", default=True,
        help_text="Affiche chaque ligne de note (interrogation, devoir…) en plus de la moyenne.",
    )
    group_by_category = models.BooleanField(
        "regrouper par type de matière", default=True,
        help_text="Regroupe les matières par type, avec un sous-total par groupe.",
    )
    show_rank = models.BooleanField("afficher le rang", default=True)
    show_teacher = models.BooleanField("afficher le professeur", default=True)
    show_appreciation = models.BooleanField("afficher l’appréciation", default=True)
    show_class_statistics = models.BooleanField(
        "afficher les statistiques de classe", default=True,
        help_text="Plus forte moyenne, plus faible moyenne et moyenne générale de la classe.",
    )
    # Signataires imprimés au pied du bulletin. Le titre — « Le Proviseur » —
    # figure toujours sur la maquette ; ces réglages décident si le nom de la
    # personne s'inscrit dessous. Les noms viennent des rôles de l'école, il
    # n'y a rien à ressaisir ici.
    show_principal_name = models.BooleanField(
        "nom du proviseur", default=True,
        help_text="Inscrit le nom du proviseur sous sa signature.",
    )
    show_censor_name = models.BooleanField(
        "nom du censeur", default=False,
        help_text="Ajoute la signature du censeur au pied du bulletin.",
    )
    show_founder_name = models.BooleanField(
        "nom du fondateur", default=False,
        help_text="Ajoute la signature du fondateur — le propriétaire de "
                  "l'établissement — au pied du bulletin.",
    )
    council_note = models.TextField("mention du conseil", blank=True)
    configured_at = models.DateTimeField(
        "enregistré le", null=True, blank=True,
        help_text="Date du premier enregistrement manuel. Tant qu'elle est vide, "
                  "l'établissement n'a jamais réglé ses bulletins et reçoit les "
                  "valeurs d'usage ; une fois posée, plus rien ne modifie le "
                  "paramétrage en dehors d'une saisie explicite.",
    )

    class Meta:
        verbose_name = "paramétrage des bulletins"
        verbose_name_plural = "paramétrages des bulletins"

    def __str__(self):
        return f"Bulletins — {self.school.name}"

    @property
    def active_watermarks(self):
        """Filigranes réellement imprimés, sans « aucun » ni doublon.

        Les écoles paramétrées avant les filigranes combinés n'ont que
        l'ancien champ à choix unique : on le reprend tant que la liste est
        vide, sinon leur bulletin perdrait sa marque de fond.
        """
        chosen = self.watermarks if isinstance(self.watermarks, list) else []
        valid = dict(self.Watermark.choices)
        kinds = [
            kind for kind in chosen
            if kind in valid and kind != self.Watermark.NONE
        ]
        if not kinds and self.watermark != self.Watermark.NONE:
            kinds = [self.watermark]
        # `dict.fromkeys` dédoublonne sans perdre l'ordre de superposition.
        return list(dict.fromkeys(kinds))


class SubjectCategoryOrder(models.Model):
    """Rang d'un type de matière sur le bulletin, pour un périmètre donné.

    L'ordre des blocs varie d'une filière à l'autre : un littéraire attend ses
    matières littéraires en tête, un scientifique l'inverse. Une règle vise
    donc soit un cycle, soit une série, soit des classes précises.

    La règle la plus spécifique gagne : classes, puis série, puis cycle, puis
    la règle générale de l'établissement.
    """

    class Scope(models.TextChoices):
        SCHOOL = "ecole", "Tout l’établissement"
        STAGE = "cycle", "Un cycle"
        SERIES = "serie", "Une série"
        CLASSES = "classes", "Des classes choisies"

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="category_orders",
    )
    name = models.CharField("nom de la règle", max_length=80, blank=True)
    scope = models.CharField(
        "portée", max_length=10, choices=Scope.choices, default=Scope.SCHOOL,
    )
    stage = models.CharField(
        "cycle", max_length=12, choices=SchoolLevel.Stage.choices, blank=True,
    )
    series = models.CharField("série", max_length=20, blank=True)
    classes = models.ManyToManyField(
        SchoolClass, blank=True, related_name="category_orders",
        verbose_name="classes visées",
    )
    # Types de matières dans l'ordre voulu : le premier ouvre le bulletin.
    categories = models.JSONField("ordre des types", default=list)

    class Meta:
        ordering = ["scope", "name"]
        verbose_name = "ordre des types de matières"
        verbose_name_plural = "ordres des types de matières"

    def __str__(self):
        return self.name or self.get_scope_display()

    def matches(self, school_class):
        """La règle s'applique-t-elle à cette classe ?"""
        if self.scope == self.Scope.SCHOOL:
            return True
        if self.scope == self.Scope.STAGE:
            return school_class.level.stage == self.stage
        if self.scope == self.Scope.SERIES:
            return (school_class.series or "").casefold() == self.series.casefold()
        return self.classes.filter(pk=school_class.pk).exists()

    @property
    def precision(self):
        """Plus le nombre est élevé, plus la règle est spécifique."""
        return {
            self.Scope.SCHOOL: 0,
            self.Scope.STAGE: 1,
            self.Scope.SERIES: 2,
            self.Scope.CLASSES: 3,
        }[self.scope]


class ReportCardAppreciation(models.Model):
    """Seuil d'appréciation : « à partir de 16, Très Bien »."""

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="report_card_appreciations",
    )
    label = models.CharField("libellé", max_length=60)
    minimum = models.DecimalField("note minimale", max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["-minimum"]
        constraints = [
            models.UniqueConstraint(fields=["school", "label"], name="unique_appreciation_per_school"),
            models.CheckConstraint(
                condition=Q(minimum__gte=0) & Q(minimum__lte=20),
                name="appreciation_minimum_within_scale",
            ),
        ]
        verbose_name = "appréciation de bulletin"
        verbose_name_plural = "appréciations de bulletin"

    def __str__(self):
        return f"{self.label} (≥ {self.minimum})"


class ReportCard(models.Model):
    """Bulletin figé d'un élève pour une session.

    Les moyennes et le rang sont enregistrés au moment de la génération : un
    bulletin remis ne doit pas changer parce qu'une note a été saisie ailleurs
    depuis. Corriger passe par une régénération explicite.
    """

    session = models.ForeignKey(
        AcademicSession, on_delete=models.CASCADE, related_name="report_cards",
    )
    enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.CASCADE, related_name="report_cards",
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="report_cards",
    )
    # Instantané du bulletin : matières, notes, sous-totaux, statistiques.
    payload = models.JSONField("contenu", default=dict)
    general_average = models.DecimalField(
        "moyenne générale", max_digits=5, decimal_places=2, null=True, blank=True,
    )
    rank = models.PositiveIntegerField("rang", null=True, blank=True)
    # Date imprimée au pied du bulletin — « fait à …, le … ». Elle est choisie
    # à la génération : c'est la date d'établissement que porte le document
    # remis à la famille, pas l'horodatage technique du calcul.
    issued_on = models.DateField("établi le", null=True, blank=True)
    # Note obtenue à l'examen officiel, saisie par la direction quand les
    # résultats tombent. Elle ne concerne que les niveaux d'examen, et c'est
    # elle qui commande alors la décision de fin d'année.
    exam_average = models.DecimalField(
        "moyenne à l'examen", max_digits=5, decimal_places=2, null=True, blank=True,
    )
    generated_at = models.DateTimeField("généré le", auto_now=True)
    generated_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="generated_report_cards",
    )

    class Meta:
        ordering = ["school_class__group", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrollment"], name="unique_report_card_per_session",
            ),
        ]
        verbose_name = "bulletin"
        verbose_name_plural = "bulletins"

    def __str__(self):
        return f"Bulletin {self.enrollment.student.get_full_name()} — {self.session.name}"


class Announcement(models.Model):
    """Annonce diffusée par la direction.

    Une annonce vise soit toute l'école, soit des rôles précis, soit des
    classes précises — ce dernier cas touchant les enseignants de ces classes
    et, plus tard, les parents de leurs élèves.
    """

    class Audience(models.TextChoices):
        EVERYONE = "tous", "Tout l’établissement"
        STAFF = "personnel", "Le personnel"
        ROLES = "roles", "Certains rôles"
        CLASSES = "classes", "Certaines classes"

    class Priority(models.TextChoices):
        NORMAL = "normale", "Normale"
        IMPORTANT = "importante", "Importante"
        URGENT = "urgente", "Urgente"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="announcements")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="announcements",
    )
    title = models.CharField("titre", max_length=180)
    body = models.TextField("contenu")
    audience = models.CharField(
        "destinataires", max_length=12,
        choices=Audience.choices, default=Audience.EVERYONE,
    )
    # Rempli seulement quand `audience` vaut « roles » : liste de valeurs de
    # CustomUser.Role.
    roles = models.JSONField("rôles visés", default=list, blank=True)
    classes = models.ManyToManyField(
        SchoolClass, blank=True, related_name="announcements",
        verbose_name="classes visées",
    )
    priority = models.CharField(
        "priorité", max_length=12,
        choices=Priority.choices, default=Priority.NORMAL,
    )
    is_published = models.BooleanField(
        "publiée", default=True,
        help_text="Une annonce non publiée reste un brouillon, visible de son "
                  "seul auteur.",
    )
    published_at = models.DateTimeField("publiée le", default=timezone.now)
    # Au-delà de cette date l'annonce sort des listes : une information
    # périmée qui traîne vaut moins que pas d'information du tout.
    expires_on = models.DateField("expire le", null=True, blank=True)
    author = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="announcements", verbose_name="auteur",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "annonce"
        verbose_name_plural = "annonces"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.audience == self.Audience.ROLES and not self.roles:
            raise ValidationError({"roles": "Choisissez au moins un rôle."})


class AnnouncementRead(models.Model):
    """Accusé de lecture, pour distinguer le lu du non-lu."""

    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="reads",
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="announcement_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["announcement", "user"], name="unique_announcement_read",
            ),
        ]
        verbose_name = "lecture d’annonce"
        verbose_name_plural = "lectures d’annonces"

    def __str__(self):
        return f"{self.user} a lu « {self.announcement} »"


class Conversation(models.Model):
    """Fil de discussion entre membres d'une même école.

    Le fil porte ses participants ; il n'y a pas de notion d'expéditeur au
    niveau du fil, seulement au niveau de chaque message.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="conversations")
    subject = models.CharField("objet", max_length=180, blank=True)
    participants = models.ManyToManyField(
        CustomUser, related_name="conversations", verbose_name="participants",
    )
    started_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="started_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Recopié à chaque message pour trier les fils sans agrégat coûteux.
    last_message_at = models.DateTimeField("dernier message", default=timezone.now)

    class Meta:
        ordering = ["-last_message_at"]
        verbose_name = "conversation"
        verbose_name_plural = "conversations"

    def __str__(self):
        return self.subject or f"Conversation {self.pk}"


class Message(models.Model):
    """Message d'un fil."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages",
    )
    sender = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_messages", verbose_name="expéditeur",
    )
    # Vide autorisé : un message peut n'être qu'une photo ou un vocal. La vue
    # refuse en revanche un message sans texte *et* sans pièce jointe.
    body = models.TextField("message", blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(
        CustomUser, blank=True, related_name="read_messages",
        verbose_name="lu par",
    )

    class Meta:
        ordering = ["sent_at", "id"]
        verbose_name = "message"
        verbose_name_plural = "messages"

    def __str__(self):
        return f"{self.sender} — {self.body[:40]}"


def message_attachment_path(instance, filename):
    """Range les pièces jointes par école et par mois.

    Un dossier unique finirait par contenir des dizaines de milliers de
    fichiers, ce qu'aucun système de fichiers n'aime.
    """
    school_id = instance.message.conversation.school_id
    stamp = timezone.now()
    return f"messages/{school_id}/{stamp:%Y-%m}/{filename}"


class MessageAttachment(models.Model):
    """Fichier joint à un message.

    Le `kind` est déduit du type MIME à l'enregistrement : le mobile s'en sert
    pour choisir l'affichage (vignette, lecteur audio, icône de document) sans
    avoir à réinterpréter le MIME lui-même.
    """

    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Vidéo"
        AUDIO = "audio", "Message vocal"
        DOCUMENT = "document", "Document"

    # Types acceptés, par famille. Tout le reste est refusé : une messagerie
    # scolaire n'a pas à véhiculer d'exécutables.
    ALLOWED_TYPES = {
        Kind.IMAGE: {
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/heic",
        },
        Kind.VIDEO: {
            "video/mp4", "video/quicktime", "video/3gpp", "video/webm",
            "video/x-matroska",
        },
        Kind.AUDIO: {
            "audio/mpeg", "audio/mp4", "audio/aac", "audio/ogg", "audio/opus",
            "audio/wav", "audio/x-wav", "audio/webm", "audio/3gpp", "audio/m4a",
            "audio/x-m4a",
        },
        Kind.DOCUMENT: {
            "application/pdf",
            # Word, Excel — anciens formats et OpenXML.
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            # Certains clients envoient les .docx/.xlsx en flux binaire brut ;
            # l'extension tranche alors, cf. `resolve_kind`.
            "application/octet-stream",
        },
    }

    # Extensions retenues quand le type MIME est trop vague pour décider.
    DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"}

    # 25 Mio : de quoi passer une vidéo courte ou un PDF scanné, sans saturer
    # un forfait mobile ni le disque du serveur.
    MAX_SIZE = 25 * 1024 * 1024

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments",
    )
    file = models.FileField("fichier", upload_to=message_attachment_path)
    kind = models.CharField(
        "type", max_length=10, choices=Kind.choices, default=Kind.DOCUMENT,
    )
    original_name = models.CharField("nom d’origine", max_length=255, blank=True)
    content_type = models.CharField("type MIME", max_length=120, blank=True)
    size = models.PositiveIntegerField("taille", default=0)
    # Renseignée pour les vocaux et les vidéos : le mobile affiche la durée
    # sans avoir à télécharger le fichier pour la mesurer.
    duration_seconds = models.PositiveIntegerField(
        "durée", null=True, blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "pièce jointe"
        verbose_name_plural = "pièces jointes"

    def __str__(self):
        return self.original_name or f"Pièce jointe {self.pk}"

    @classmethod
    def resolve_kind(cls, content_type, filename=""):
        """Famille du fichier, à partir du type MIME et, à défaut, du nom.

        Retourne `None` quand le fichier n'est pas d'un type accepté.
        """
        mime = (content_type or "").split(";")[0].strip().lower()
        extension = ""
        if "." in filename:
            extension = filename[filename.rfind("."):].lower()

        # Un binaire générique ne dit rien du contenu : l'extension décide.
        if mime in ("", "application/octet-stream"):
            if extension in cls.DOCUMENT_EXTENSIONS:
                return cls.Kind.DOCUMENT
            return None

        for kind, allowed in cls.ALLOWED_TYPES.items():
            if mime in allowed:
                # « octet-stream » n'est accepté que pour un document, jamais
                # comme image ou vidéo dont le rendu dépend du vrai format.
                if mime == "application/octet-stream" and kind != cls.Kind.DOCUMENT:
                    continue
                return kind

        # Les familles génériques couvrent les variantes exotiques (image/avif,
        # audio/flac…) que l'énumération ci-dessus ne liste pas.
        for prefix, kind in (
            ("image/", cls.Kind.IMAGE),
            ("video/", cls.Kind.VIDEO),
            ("audio/", cls.Kind.AUDIO),
        ):
            if mime.startswith(prefix):
                return kind
        return None
