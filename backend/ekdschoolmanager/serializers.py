import re
from datetime import timedelta

from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify

from .models import AcademicPeriod, AcademicYear, ClassSubject, CustomUser, School, SchoolClass, SchoolLevel, SchoolMembership, StudentEnrollment, Subject, TeacherClassAssignment, TeacherUnavailability


class CustomUserSerializer(serializers.ModelSerializer):
    first_names = serializers.CharField(source="first_name")
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender_label = serializers.CharField(source="get_gender_display", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    primary_subject_name = serializers.CharField(source="primary_subject.name", read_only=True)
    secondary_subject_name = serializers.CharField(source="secondary_subject.name", read_only=True)
    tertiary_subject_name = serializers.CharField(source="tertiary_subject.name", read_only=True)
    assigned_school_ids = serializers.SerializerMethodField()
    assigned_classes = serializers.SerializerMethodField()
    homeroom_classes = serializers.SerializerMethodField()
    unavailability_schedule = serializers.SerializerMethodField()
    school_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "last_name", "first_names", "email", "phone", "gender",
            "gender_label", "role", "role_label", "primary_subject",
            "primary_subject_name", "secondary_subject", "secondary_subject_name",
            "tertiary_subject", "tertiary_subject_name", "is_active", "is_archived",
            "date_of_birth", "address", "is_superuser", "school_ids", "date_joined",
            "assigned_school_ids", "assigned_classes", "homeroom_classes", "unavailability_schedule",
        ]
        read_only_fields = ["id", "is_superuser", "date_joined"]

    def validate_email(self, value):
        if not value:
            return None

        email = value.lower().strip()
        return email

    def validate_username(self, value):
        username = value.strip()
        if len(username) < 3:
            raise serializers.ValidationError("Le nom d’utilisateur doit contenir au moins 3 caractères.")
        if re.search(r"\s", username):
            raise serializers.ValidationError("Le nom d’utilisateur ne doit contenir aucun espace.")
        users = CustomUser.objects.filter(username__iexact=username)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError("Ce nom d’utilisateur existe déjà.")
        return username

    def validate_phone(self, value):
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        if digits.startswith("228"):
            digits = digits[3:]
        if len(digits) != 8:
            raise serializers.ValidationError(
                "Saisissez un numéro togolais de 8 chiffres, par exemple +228 90 12 34 56."
            )

        phone = f"+228{digits}"
        return phone

    def validate(self, attrs):
        view = self.context.get("view")
        is_teacher_endpoint = (
            getattr(view, "basename", None) == "teacher"
            or view.__class__.__name__ == "TeacherViewSet"
        )
        role = CustomUser.Role.TEACHER if is_teacher_endpoint else attrs.get(
            "role", getattr(self.instance, "role", CustomUser.Role.STAFF)
        )
        gender = attrs.get("gender", getattr(self.instance, "gender", ""))
        if role == CustomUser.Role.TEACHER and not gender:
            raise serializers.ValidationError({"gender": "Le genre est obligatoire pour un enseignant."})

        subjects = [attrs.get(name, getattr(self.instance, name, None)) for name in (
            "primary_subject", "secondary_subject", "tertiary_subject"
        )]
        selected = [subject.pk for subject in subjects if subject]
        if len(selected) != len(set(selected)):
            raise serializers.ValidationError("Les matières sélectionnées doivent être différentes.")
        if selected and is_teacher_endpoint:
            school = view.get_school()
            invalid_subjects = [subject.name for subject in subjects if subject and (subject.school_id != school.id or not subject.is_active)]
            if invalid_subjects:
                raise serializers.ValidationError({
                    "subjects": f"Matière indisponible dans cette école : {', '.join(invalid_subjects)}."
                })
        return attrs

    def get_assigned_school_ids(self, user):
        return list(user.school_memberships.filter(is_active=True).values_list("school_id", flat=True))

    def get_assigned_classes(self, user):
        request = self.context.get("request")
        kwargs = request.parser_context.get("kwargs", {}) if request and request.parser_context else {}
        school_id = kwargs.get("school_pk")
        year_id = request.headers.get("X-Academic-Year-ID") if request else None
        if not school_id or not year_id:
            return []
        assignments = TeacherClassAssignment.objects.filter(
            teacher=user, school_id=school_id, academic_year_id=year_id,
        ).select_related("school_class__level").prefetch_related("subject_links__class_subject__subject")
        return [{
            "id": assignment.school_class_id,
            "name": assignment.school_class.name,
            "subjects": [link.class_subject.subject.name for link in assignment.subject_links.all()],
            "weekly_hours": sum(link.class_subject.weekly_hours for link in assignment.subject_links.all()),
        } for assignment in assignments]

    def get_homeroom_classes(self, user):
        school_id, year_id = self._school_year_context()
        if not school_id or not year_id:
            return []
        return [{"id": school_class.id, "name": school_class.name} for school_class in SchoolClass.objects.filter(
            homeroom_teacher=user, school_id=school_id, academic_year_id=year_id, is_active=True,
        ).select_related("level")]

    def get_unavailability_schedule(self, user):
        school_id, year_id = self._school_year_context()
        if not school_id or not year_id:
            return []
        return [{
            "day": item.day, "day_label": item.get_day_display(), "all_day": item.all_day,
            "start_time": item.start_time.strftime("%H:%M") if item.start_time else None,
            "end_time": item.end_time.strftime("%H:%M") if item.end_time else None,
        } for item in TeacherUnavailability.objects.filter(
            teacher=user, school_id=school_id, academic_year_id=year_id,
        )]

    def _school_year_context(self):
        request = self.context.get("request")
        kwargs = request.parser_context.get("kwargs", {}) if request and request.parser_context else {}
        return kwargs.get("school_pk"), request.headers.get("X-Academic-Year-ID") if request else None

    def create(self, validated_data):
        validated_data.pop("school_ids", None)
        user = CustomUser(**validated_data)
        view = self.context.get("view")
        is_teacher_endpoint = (
            getattr(view, "basename", None) == "teacher"
            or view.__class__.__name__ == "TeacherViewSet"
        )
        initial_password = user.username if is_teacher_endpoint else f"{user.username}@"
        user.set_password(initial_password)
        user.save()
        return user


class SchoolSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role=CustomUser.Role.OWNER),
        required=False,
    )
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ["id", "name", "code", "logo", "owner", "owner_name", "user_role", "is_active", "created_at"]
        read_only_fields = ["id", "owner_name", "user_role", "created_at"]

    def validate_owner(self, owner):
        if not self.context["request"].user.is_superuser:
            raise serializers.ValidationError("Seul un superutilisateur peut choisir le propriétaire.")
        if owner.role != CustomUser.Role.OWNER:
            raise serializers.ValidationError("L’utilisateur sélectionné n’est pas un propriétaire.")
        return owner

    def validate_name(self, value):
        name = " ".join(value.split())
        if len(name) < 2:
            raise serializers.ValidationError("Le nom de l’école est trop court.")
        return name

    def validate_code(self, value):
        code = slugify(value.strip())
        if not code:
            raise serializers.ValidationError("Saisissez un code valide.")
        queryset = School.objects.filter(code=code)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ce code est déjà utilisé.")
        return code

    def validate_logo(self, value):
        if value and value.size > 3 * 1024 * 1024:
            raise serializers.ValidationError("Le logo ne doit pas dépasser 3 Mo.")
        return value

    def get_user_role(self, school):
        user = self.context.get("authenticated_user") or self.context["request"].user
        if not user.is_authenticated:
            return None
        if user.is_superuser:
            return "superutilisateur"
        if school.owner_id == user.id:
            return CustomUser.Role.OWNER
        membership = school.memberships.filter(user=user, is_active=True).first()
        return membership.role if membership else None


class SchoolMembershipSerializer(serializers.ModelSerializer):
    user_details = CustomUserSerializer(source="user", read_only=True)

    class Meta:
        model = SchoolMembership
        fields = ["id", "school", "user", "user_details", "role", "is_active", "joined_at"]
        read_only_fields = ["id", "school", "joined_at"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "school", "name", "code", "description", "is_active", "created_at"]
        read_only_fields = ["id", "school", "created_at"]

    def validate_name(self, value):
        name = " ".join(value.split())
        if len(name) < 2:
            raise serializers.ValidationError("Le nom de la matière est trop court.")
        return name

    def validate_code(self, value):
        code = slugify(value.strip())
        if not code:
            raise serializers.ValidationError("Saisissez un code valide.")
        return code

    def validate(self, attrs):
        school = self.context["view"].get_school()
        name = attrs.get("name", getattr(self.instance, "name", ""))
        code = attrs.get("code", getattr(self.instance, "code", ""))
        queryset = Subject.objects.filter(school=school)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        errors = {}
        if queryset.filter(name__iexact=name).exists():
            errors["name"] = "Cette matière existe déjà dans cette école."
        if queryset.filter(code=code).exists():
            errors["code"] = "Ce code est déjà utilisé dans cette école."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class AcademicPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicPeriod
        fields = ["id", "number", "name", "start_date", "end_date", "is_active", "is_closed"]
        read_only_fields = ["id", "number", "is_active", "is_closed"]


class AcademicYearSerializer(serializers.ModelSerializer):
    periods = AcademicPeriodSerializer(many=True, required=False)
    division_label = serializers.CharField(source="get_division_system_display", read_only=True)

    class Meta:
        model = AcademicYear
        fields = [
            "id", "school", "name", "start_date", "end_date", "division_system",
            "division_label", "is_active", "is_closed", "periods", "created_at",
        ]
        read_only_fields = ["id", "school", "is_closed", "created_at"]

    def validate_name(self, value):
        return " ".join(value.split())

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "La date de fin doit suivre la date de début."})
        if self.instance and "division_system" in attrs and attrs["division_system"] != self.instance.division_system:
            raise serializers.ValidationError({"division_system": "Le découpage ne peut plus être changé après création."})
        if self.instance and self.instance.is_closed and attrs:
            raise serializers.ValidationError("Une année clôturée ne peut plus être modifiée.")
        periods = attrs.get("periods")
        division = attrs.get("division_system", getattr(self.instance, "division_system", None))
        if self.instance and periods is not None and self.instance.periods.filter(is_closed=True).exists():
            raise serializers.ValidationError({"periods": "Les périodes ne peuvent plus être modifiées après une clôture."})
        if periods is not None:
            expected = 3 if division == AcademicYear.DivisionSystem.TRIMESTER else 2
            if len(periods) != expected:
                raise serializers.ValidationError({"periods": f"Ce découpage exige exactement {expected} périodes."})
            ordered = sorted(periods, key=lambda period: period["start_date"])
            for index, period in enumerate(ordered):
                if period["end_date"] < period["start_date"]:
                    raise serializers.ValidationError({"periods": f"Les dates de la période {index + 1} sont invalides."})
                if start and end and (period["start_date"] < start or period["end_date"] > end):
                    raise serializers.ValidationError({"periods": f"La période {index + 1} doit être comprise dans l’année académique."})
                if index and ordered[index - 1]["end_date"] >= period["start_date"]:
                    raise serializers.ValidationError({"periods": "Les périodes ne doivent pas se chevaucher."})
        return attrs

    @staticmethod
    def build_automatic_periods(academic_year):
        count = 3 if academic_year.division_system == AcademicYear.DivisionSystem.TRIMESTER else 2
        label = "trimestre" if count == 3 else "semestre"
        total_days = (academic_year.end_date - academic_year.start_date).days + 1
        periods = []
        for index in range(count):
            start = academic_year.start_date + timedelta(days=(total_days * index) // count)
            next_start = academic_year.start_date + timedelta(days=(total_days * (index + 1)) // count)
            periods.append({
                "name": f"{index + 1}{'er' if index == 0 else 'e'} {label}",
                "start_date": start,
                "end_date": academic_year.end_date if index == count - 1 else next_start - timedelta(days=1),
            })
        return periods

    def create(self, validated_data):
        periods = validated_data.pop("periods", None)
        academic_year = AcademicYear.objects.create(**validated_data)
        periods = periods or self.build_automatic_periods(academic_year)
        periods = sorted(periods, key=lambda period: period["start_date"])
        AcademicPeriod.objects.bulk_create([
            AcademicPeriod(academic_year=academic_year, number=index, is_active=index == 1 and academic_year.is_active, **period)
            for index, period in enumerate(periods, start=1)
        ])
        return academic_year

    def update(self, instance, validated_data):
        periods = validated_data.pop("periods", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if periods is not None:
            periods = sorted(periods, key=lambda period: period["start_date"])
            instance.periods.all().delete()
            AcademicPeriod.objects.bulk_create([
                AcademicPeriod(academic_year=instance, number=index, is_active=index == 1 and instance.is_active, **period)
                for index, period in enumerate(periods, start=1)
            ])
        return instance


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    last_name = serializers.CharField(write_only=True)
    first_names = serializers.CharField(write_only=True)
    gender = serializers.ChoiceField(write_only=True, choices=CustomUser.Gender.choices)
    date_of_birth = serializers.DateField(write_only=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_last_name = serializers.CharField(source="student.last_name", read_only=True)
    student_first_names = serializers.CharField(source="student.first_name", read_only=True)
    student_gender = serializers.CharField(source="student.gender", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_address = serializers.CharField(source="student.address", read_only=True)
    gender_label = serializers.CharField(source="student.get_gender_display", read_only=True)
    date_of_birth_display = serializers.DateField(source="student.date_of_birth", read_only=True)
    level = serializers.PrimaryKeyRelatedField(queryset=SchoolLevel.objects.filter(is_active=True))
    level_name = serializers.CharField(source="level.name", read_only=True)
    level_stage = serializers.CharField(source="level.get_stage_display", read_only=True)
    school_class = serializers.PrimaryKeyRelatedField(queryset=SchoolClass.objects.filter(is_active=True), required=False, allow_null=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    school_class_series = serializers.CharField(source="school_class.series", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    history = serializers.SerializerMethodField()

    class Meta:
        model = StudentEnrollment
        fields = [
            "id", "enrollment_number", "student", "student_name", "student_last_name", "student_first_names", "student_gender",
            "student_username", "student_address", "gender_label", "date_of_birth_display", "status", "enrolled_at",
            "level", "level_name", "level_stage", "school_class", "school_class_name", "school_class_series", "academic_year_name", "history", "last_name", "first_names", "gender", "date_of_birth", "address",
        ]
        read_only_fields = ["id", "student", "status", "enrolled_at"]

    def validate_enrollment_number(self, value):
        number = value.strip().upper()
        if not number:
            raise serializers.ValidationError("Le numéro matricule est obligatoire.")
        school = self.context["school"]
        queryset = StudentEnrollment.objects.filter(school=school, enrollment_number__iexact=number)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ce numéro matricule existe déjà dans cette école.")
        return number

    def validate(self, attrs):
        academic_year = self.context["academic_year"]
        if not academic_year.is_active or academic_year.is_closed:
            raise serializers.ValidationError({
                "academic_year": "Les inscriptions sont interdites pour une année inactive ou clôturée."
            })
        school_class = attrs.get("school_class", getattr(self.instance, "school_class", None))
        level = attrs.get("level", getattr(self.instance, "level", None))
        if school_class and (
            school_class.school_id != self.context["school"].id
            or school_class.academic_year_id != academic_year.id
            or school_class.level_id != level.id
        ):
            raise serializers.ValidationError({"school_class": "Cette classe ne correspond pas au niveau sélectionné."})
        return attrs

    def get_history(self, enrollment):
        view = self.context.get("view")
        if getattr(view, "action", None) != "retrieve":
            return []
        history = StudentEnrollment.objects.filter(
            school=enrollment.school, student=enrollment.student,
        ).select_related("academic_year", "level", "school_class").order_by("-academic_year__start_date")
        return [{
            "id": item.id, "academic_year": item.academic_year.name, "level": item.level.name if item.level else None,
            "school_class": item.school_class.name if item.school_class else None,
            "status": item.get_status_display(), "enrolled_at": item.enrolled_at,
        } for item in history]

    def validate_level(self, level):
        if level.school_id != self.context["school"].id:
            raise serializers.ValidationError("Ce niveau n’appartient pas à l’école sélectionnée.")
        return level

    def create(self, validated_data):
        school = self.context["school"]
        academic_year = self.context["academic_year"]
        level = validated_data.pop("level")
        school_class = validated_data.pop("school_class", None)
        enrollment_number = validated_data.pop("enrollment_number")
        username_base = slugify(f"{school.code}-{enrollment_number}").replace("-", "")
        username = username_base
        suffix = 1
        while CustomUser.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{username_base}{suffix}"
        with transaction.atomic():
            student = CustomUser(
                username=username,
                last_name=" ".join(validated_data.pop("last_name").split()),
                first_name=" ".join(validated_data.pop("first_names").split()),
                gender=validated_data.pop("gender"),
                date_of_birth=validated_data.pop("date_of_birth"),
                address=validated_data.pop("address", "").strip(),
                role=CustomUser.Role.STUDENT,
            )
            student.set_password(f"{student.username}@")
            student.save()
            SchoolMembership.objects.create(
                school=school, user=student, role=CustomUser.Role.STUDENT
            )
            enrollment = StudentEnrollment.objects.create(
                school=school,
                academic_year=academic_year,
                student=student,
                level=level,
                school_class=school_class,
                enrollment_number=enrollment_number,
            )
            return enrollment

    def update(self, instance, validated_data):
        student = instance.student
        field_mapping = {"last_name": "last_name", "first_names": "first_name", "gender": "gender", "date_of_birth": "date_of_birth", "address": "address"}
        for input_name, model_name in field_mapping.items():
            if input_name in validated_data:
                value = validated_data.pop(input_name)
                setattr(student, model_name, " ".join(value.split()) if isinstance(value, str) else value)
        student.save()
        for field in ("enrollment_number", "level", "school_class"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class SchoolLevelSerializer(serializers.ModelSerializer):
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = SchoolLevel
        fields = ["id", "name", "stage", "stage_label", "order", "is_active"]


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = ClassSubject
        fields = ["id", "subject", "subject_name", "weekly_hours", "coefficient", "can_schedule_after_break", "can_schedule_afternoon"]
        read_only_fields = ["id", "subject_name"]


class SchoolClassSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    level_name = serializers.CharField(source="level.name", read_only=True)
    cycle = serializers.CharField(source="level.stage", read_only=True)
    cycle_label = serializers.CharField(source="level.get_stage_display", read_only=True)
    homeroom_teacher_name = serializers.CharField(source="homeroom_teacher.get_full_name", read_only=True)
    subjects = ClassSubjectSerializer(source="subject_configurations", many=True, required=False)
    effectif = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = ["id", "name", "school", "academic_year", "level", "level_name", "cycle", "cycle_label", "series", "group", "homeroom_teacher", "homeroom_teacher_name", "subjects", "effectif", "is_active", "created_at"]
        read_only_fields = ["id", "name", "school", "academic_year", "level_name", "cycle", "cycle_label", "homeroom_teacher_name", "created_at"]

    def validate_level(self, level):
        if level.school_id != self.context["school"].id or not level.is_active:
            raise serializers.ValidationError("Ce niveau n’appartient pas à cette école.")
        return level

    def validate_series(self, value):
        return value.strip().upper()

    def validate_group(self, value):
        group = value.strip().upper()
        if not group:
            raise serializers.ValidationError("Le groupe est obligatoire.")
        return group

    def validate(self, attrs):
        level = attrs.get("level", getattr(self.instance, "level", None))
        series = attrs.get("series", getattr(self.instance, "series", ""))
        group = attrs.get("group", getattr(self.instance, "group", ""))
        teacher = attrs.get("homeroom_teacher", getattr(self.instance, "homeroom_teacher", None))
        subject_configs = attrs.get("subject_configurations")
        allowed_series = {
            "Seconde": {"CD", "A4"},
            "Première": {"D", "A4", "C4"},
            "Terminale": {"D", "A4", "C4"},
        }
        if level and level.stage != SchoolLevel.Stage.HIGH and series:
            raise serializers.ValidationError({"series": "Le Primaire et le Collège n’ont pas de série."})
        if level and series and series not in allowed_series.get(level.name, set()):
            choices = ", ".join(sorted(allowed_series.get(level.name, set())))
            raise serializers.ValidationError({"series": f"Série invalide pour {level.name}. Choix autorisés : {choices}."})
        school = self.context["school"]
        if teacher and (
            teacher.role != CustomUser.Role.TEACHER
            or not SchoolMembership.objects.filter(school=school, user=teacher, is_active=True).exists()
        ):
            raise serializers.ValidationError({"homeroom_teacher": "Le titulaire doit être un enseignant actif de cette école."})
        if subject_configs is not None:
            subject_ids = [config["subject"].id for config in subject_configs]
            if len(subject_ids) != len(set(subject_ids)):
                raise serializers.ValidationError({"subjects": "Une matière ne peut apparaître qu’une seule fois."})
            invalid = [config["subject"].name for config in subject_configs if config["subject"].school_id != school.id or not config["subject"].is_active]
            if invalid:
                raise serializers.ValidationError({"subjects": f"Matières indisponibles dans cette école : {', '.join(invalid)}."})
        queryset = SchoolClass.objects.filter(academic_year=self.context["academic_year"], level=level, series__iexact=series, group__iexact=group)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Cette classe existe déjà pour cette année académique.")
        return attrs

    def create(self, validated_data):
        subject_configs = validated_data.pop("subject_configurations", [])
        with transaction.atomic():
            school_class = super().create(validated_data)
            ClassSubject.objects.bulk_create([
                ClassSubject(school_class=school_class, **config) for config in subject_configs
            ])
        return school_class

    def update(self, instance, validated_data):
        subject_configs = validated_data.pop("subject_configurations", None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if subject_configs is not None:
                matching_classes = list(SchoolClass.objects.filter(
                    school=instance.school,
                    academic_year=instance.academic_year,
                    level=instance.level,
                    series__iexact=instance.series,
                    is_active=True,
                ))
                ClassSubject.objects.filter(school_class__in=matching_classes).delete()
                ClassSubject.objects.bulk_create([
                    ClassSubject(school_class=school_class, **config)
                    for school_class in matching_classes
                    for config in subject_configs
                ])
        return instance
