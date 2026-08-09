import re
from decimal import Decimal

from rest_framework import serializers
from django.db import transaction
from django.db.models import Sum
from django.utils.text import slugify

from .models import AcademicSession, AcademicYear, Announcement, AttendanceRecord, AttendanceSession, ClassFeeItem, Conversation, Message, MessageAttachment, ClassSubject, CustomUser, DisciplineRecord, ExpenseCategory, FeeInstallment, FeeModule, FeePayment, GradeGroup, GradeLine, GradeScheme, School, SchoolClass, SchoolExpense, SchoolLevel, SchoolMembership, StudentEnrollment, Subject, SubjectCategory, TeacherClassAssignment, TeacherUnavailability, TuitionFeePlan


def normalize_togolese_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("228"):
        digits = digits[3:]
    if len(digits) != 8:
        raise serializers.ValidationError(
            "Saisissez un numéro togolais de 8 chiffres, par exemple +228 90 12 34 56."
        )
    return f"+228{digits}"


class CustomUserSerializer(serializers.ModelSerializer):
    first_names = serializers.CharField(source="first_name")
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender_label = serializers.CharField(source="get_gender_display", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    student_status_label = serializers.CharField(source="get_student_status_display", read_only=True)
    year_result_label = serializers.CharField(source="get_year_result_display", read_only=True)
    subjects = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    subject_names = serializers.SlugRelatedField(source="subjects", slug_field="name", many=True, read_only=True)
    primary_subject_name = serializers.CharField(source="primary_subject.name", read_only=True)
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
            "id", "username", "last_name", "first_names", "email", "phone", "profession", "gender",
            "gender_label", "role", "role_label", "subjects", "subject_names", "primary_subject", "primary_subject_name", "is_active", "is_archived",
            "date_of_birth", "address", "health_information", "signature", "enrollment_number", "student_status", "student_status_label",
            "year_result", "year_result_label", "is_superuser", "school_ids", "date_joined",
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
        return normalize_togolese_phone(value)

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

        subjects = attrs.get("subjects")
        if subjects is not None and is_teacher_endpoint:
            school = view.get_school()
            invalid_subjects = [subject.name for subject in subjects if subject.school_id != school.id or not subject.is_active]
            if invalid_subjects:
                raise serializers.ValidationError({
                    "subjects": f"Matière indisponible dans cette école : {', '.join(invalid_subjects)}."
                })
        selected_subject_ids = {subject.id for subject in subjects} if subjects is not None else (
            set(self.instance.subjects.values_list("id", flat=True)) if self.instance else set()
        )
        primary_subject = attrs.get("primary_subject", getattr(self.instance, "primary_subject", None))
        if primary_subject and primary_subject.id not in selected_subject_ids:
            raise serializers.ValidationError({"primary_subject": "La matière principale doit être sélectionnée dans les matières enseignées."})
        if is_teacher_endpoint and selected_subject_ids and not primary_subject:
            raise serializers.ValidationError({"primary_subject": "Sélectionnez la matière principale de l’enseignant."})
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
        subjects = validated_data.pop("subjects", [])
        user = CustomUser(**validated_data)
        view = self.context.get("view")
        is_teacher_endpoint = (
            getattr(view, "basename", None) == "teacher"
            or view.__class__.__name__ == "TeacherViewSet"
        )
        initial_password = user.username if is_teacher_endpoint else f"{user.username}@"
        user.set_password(initial_password)
        user.save()
        user.subjects.set(subjects)
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


class SubjectCategorySerializer(serializers.ModelSerializer):
    subject_count = serializers.IntegerField(source="subjects.count", read_only=True)

    class Meta:
        model = SubjectCategory
        fields = ["id", "school", "name", "subject_count", "created_at"]
        read_only_fields = ["id", "school", "created_at"]

    def validate_name(self, value):
        name = " ".join(value.split())
        if len(name) < 2:
            raise serializers.ValidationError("Le nom du type est trop court.")
        school = self.context["view"].get_school()
        queryset = SubjectCategory.objects.filter(school=school, name__iexact=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ce type de matière existe déjà dans cette école.")
        return name


class SubjectSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "school", "name", "code", "category", "category_name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "school", "created_at"]

    def validate_category(self, value):
        if value and value.school_id != self.context["view"].get_school().id:
            raise serializers.ValidationError("Ce type n’appartient pas à cette école.")
        return value

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


class AcademicSessionSerializer(serializers.ModelSerializer):
    classes = serializers.PrimaryKeyRelatedField(queryset=SchoolClass.objects.all(), many=True)
    class_names = serializers.SlugRelatedField(source="classes", slug_field="name", many=True, read_only=True)

    class Meta:
        model = AcademicSession
        fields = ["id", "academic_year", "name", "label", "start_date", "end_date", "classes", "class_names", "is_active", "is_closed", "created_at"]
        read_only_fields = ["id", "academic_year", "is_closed", "created_at"]

    def validate_name(self, value):
        name = " ".join(value.split())
        academic_year = self.context["academic_year"]
        queryset = AcademicSession.objects.filter(academic_year=academic_year, name__iexact=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Une session avec ce nom existe déjà dans cette année académique.")
        return name

    def validate_label(self, value):
        return " ".join(value.split())

    def validate(self, attrs):
        academic_year = self.context["academic_year"]
        if self.instance and self.instance.is_closed and attrs:
            raise serializers.ValidationError("Une session clôturée ne peut plus être modifiée.")
        if attrs.get("is_active") and ((self.instance and self.instance.is_closed) or not academic_year.is_active or academic_year.is_closed):
            raise serializers.ValidationError({"is_active": "Seule une session de l’année académique active peut être activée."})
        classes = attrs.get("classes")
        if classes is not None:
            invalid = [school_class.name for school_class in classes if school_class.academic_year_id != academic_year.id or school_class.school_id != academic_year.school_id]
            if invalid:
                raise serializers.ValidationError({"classes": f"Classes hors de cette année académique : {', '.join(invalid)}."})
            if not classes:
                raise serializers.ValidationError({"classes": "Sélectionnez au moins une classe."})
            will_be_active = attrs.get("is_active", getattr(self.instance, "is_active", True))
            if will_be_active:
                conflicts = AcademicSession.objects.filter(
                    academic_year=academic_year, is_active=True, classes__in=classes,
                )
                if self.instance:
                    conflicts = conflicts.exclude(pk=self.instance.pk)
                conflicting_class_ids = list(conflicts.values_list("classes__id", flat=True).distinct())
                if conflicting_class_ids:
                    conflicting_classes = SchoolClass.objects.filter(
                        id__in=conflicting_class_ids,
                    ).select_related("level").order_by("level__order", "series", "group")
                    conflicting_names = [
                        " ".join(part for part in (school_class.level.name, school_class.series, school_class.group) if part)
                        for school_class in conflicting_classes
                    ]
                    raise serializers.ValidationError({
                        "classes": f"Ces classes appartiennent déjà à une session active : {', '.join(conflicting_names)}."
                    })
        return attrs


class AcademicYearSerializer(serializers.ModelSerializer):
    sessions = AcademicSessionSerializer(many=True, read_only=True)
    class Meta:
        model = AcademicYear
        fields = [
            "id", "school", "name", "start_date", "end_date",
            "is_active", "is_closed", "sessions", "created_at",
        ]
        read_only_fields = ["id", "school", "is_closed", "created_at"]

    def validate_name(self, value):
        return " ".join(value.split())

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "La date de fin doit suivre la date de début."})
        if self.instance and self.instance.is_closed and attrs:
            raise serializers.ValidationError("Une année clôturée ne peut plus être modifiée.")
        return attrs


class FeeInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeInstallment
        fields = ["id", "name", "percentage", "due_date", "order"]
        read_only_fields = ["id"]


class ClassFeeItemSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source="fee_module.name")
    installments = FeeInstallmentSerializer(many=True, required=False)

    class Meta:
        model = ClassFeeItem
        fields = ["id", "module_name", "male_amount", "female_amount", "payable_in_installments", "installments"]
        read_only_fields = ["id"]


class TuitionFeePlanSerializer(serializers.ModelSerializer):
    items = ClassFeeItemSerializer(many=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    level_name = serializers.CharField(source="school_class.level.name", read_only=True)
    series = serializers.CharField(source="school_class.series", read_only=True)

    class Meta:
        model = TuitionFeePlan
        fields = ["id", "school", "academic_year", "school_class", "class_name", "level_name", "series", "items", "created_at", "updated_at"]
        read_only_fields = ["id", "school", "academic_year", "created_at", "updated_at"]

    def validate_school_class(self, school_class):
        if school_class.school_id != self.context["school"].id or school_class.academic_year_id != self.context["academic_year"].id:
            raise serializers.ValidationError("Cette classe ne correspond pas à l’école et à l’année sélectionnées.")
        return school_class

    def validate(self, attrs):
        items = attrs.get("items", [])
        names = [item["fee_module"]["name"].strip().casefold() for item in items]
        if not items:
            raise serializers.ValidationError({"items": "Ajoutez au moins une rubrique de frais."})
        if len(names) != len(set(names)):
            raise serializers.ValidationError({"items": "Chaque rubrique doit avoir un nom différent."})
        for item in items:
            installments = item.get("installments", [])
            if item.get("payable_in_installments"):
                if not installments or sum(row["percentage"] for row in installments) != 100:
                    raise serializers.ValidationError({"items": f"Les tranches de « {item['fee_module']['name']} » doivent totaliser 100 %."})
            elif installments:
                raise serializers.ValidationError({"items": f"La rubrique « {item['fee_module']['name']} » n’est pas marquée payable en tranches."})
        return attrs

    def save_items(self, plan, items):
        for item in items:
            module_data = item.pop("fee_module")
            installments = item.pop("installments", [])
            name = " ".join(module_data["name"].split())
            module = FeeModule.objects.filter(school=plan.school, academic_year=plan.academic_year, name__iexact=name).first()
            if module is None:
                module = FeeModule.objects.create(school=plan.school, academic_year=plan.academic_year, name=name)
            class_fee = ClassFeeItem.objects.create(plan=plan, fee_module=module, **item)
            FeeInstallment.objects.bulk_create([FeeInstallment(class_fee=class_fee, **row) for row in installments])

    def create(self, validated_data):
        items = validated_data.pop("items")
        with transaction.atomic():
            plan = TuitionFeePlan.objects.create(**validated_data)
            self.save_items(plan, items)
        return plan

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            if items is not None:
                if instance.items.filter(payments__isnull=False).exists():
                    raise serializers.ValidationError({"items": "La composition ne peut plus être remplacée après un paiement."})
                instance.items.all().delete()
                self.save_items(instance, items)
        return instance


class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.get_full_name", read_only=True)
    enrollment_number = serializers.CharField(source="enrollment.enrollment_number", read_only=True)
    class_name = serializers.CharField(source="enrollment.school_class.name", read_only=True)
    installment_name = serializers.CharField(source="installment.name", read_only=True)
    module_name = serializers.CharField(source="class_fee.fee_module.name", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = FeePayment
        fields = ["id", "enrollment", "student_name", "enrollment_number", "class_name", "class_fee", "module_name", "installment", "installment_name", "amount", "paid_on", "method", "method_label", "reference", "notes", "received_by_name", "created_at"]
        read_only_fields = ["id", "created_at", "received_by_name"]

    def validate(self, attrs):
        enrollment = attrs["enrollment"]
        school = self.context["school"]
        academic_year = self.context["academic_year"]
        if enrollment.school_id != school.id or enrollment.academic_year_id != academic_year.id:
            raise serializers.ValidationError({"enrollment": "Cette inscription ne correspond pas à l’école et à l’année sélectionnées."})
        if not enrollment.school_class_id:
            raise serializers.ValidationError({"enrollment": "L’élève doit être affecté à une classe."})
        class_fee = attrs["class_fee"]
        if class_fee.plan.school_class_id != enrollment.school_class_id:
            raise serializers.ValidationError({"class_fee": "Cette rubrique ne correspond pas à la classe de l’élève."})
        installment = attrs.get("installment")
        if installment and installment.class_fee_id != class_fee.id:
            raise serializers.ValidationError({"installment": "Cette tranche ne correspond pas à la rubrique sélectionnée."})
        if class_fee.payable_in_installments and not installment:
            raise serializers.ValidationError({"installment": "Sélectionnez une tranche pour cette rubrique."})
        if not class_fee.payable_in_installments and installment:
            raise serializers.ValidationError({"installment": "Cette rubrique n’est pas payable en tranches."})
        base_amount = class_fee.female_amount if enrollment.student.gender == CustomUser.Gender.FEMALE else class_fee.male_amount
        expected = base_amount if installment is None else (
            base_amount * installment.percentage / Decimal("100")
        ).quantize(Decimal("0.01"))
        payments = FeePayment.objects.filter(enrollment=enrollment, class_fee=class_fee)
        if installment is not None:
            payments = payments.filter(installment=installment)
        paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        remaining = max(expected - paid, Decimal("0"))
        if remaining == 0:
            raise serializers.ValidationError({"class_fee": "Cette rubrique ou cette tranche est déjà entièrement payée."})
        if attrs["amount"] > remaining:
            raise serializers.ValidationError({"amount": f"Le montant ne peut pas dépasser le reste à payer de {remaining} FCFA."})
        return attrs


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "is_active"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        name = " ".join(value.split())
        queryset = ExpenseCategory.objects.filter(school=self.context["school"], name__iexact=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Cette catégorie existe déjà.")
        return name


class SchoolExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)

    class Meta:
        model = SchoolExpense
        fields = ["id", "category", "category_name", "label", "description", "beneficiary", "amount", "expense_date", "method", "method_label", "reference", "recorded_by_name", "created_at", "updated_at"]
        read_only_fields = ["id", "recorded_by_name", "created_at", "updated_at"]

    def validate_category(self, category):
        if category.school_id != self.context["school"].id or not category.is_active:
            raise serializers.ValidationError("Cette catégorie n’est pas disponible dans cette école.")
        return category

    def validate_label(self, value):
        return " ".join(value.split())


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.get_full_name", read_only=True)
    enrollment_number = serializers.CharField(source="enrollment.enrollment_number", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "enrollment", "student_name", "enrollment_number",
            "status", "status_label", "minutes_late", "comment",
        ]
        read_only_fields = ["id", "student_name", "enrollment_number", "status_label"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    records = AttendanceRecordSerializer(many=True, read_only=True)
    class_name = serializers.CharField(source="school_class.group", read_only=True)
    subject_name = serializers.CharField(source="class_subject.subject.name", read_only=True)
    taken_by_name = serializers.CharField(source="taken_by.get_full_name", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id", "school_class", "class_name", "class_subject", "subject_name",
            "taken_on", "period", "note", "taken_by_name", "records", "summary",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "taken_by_name", "created_at", "updated_at"]

    def get_summary(self, instance):
        """Compte par statut : ce que l'appel donne à lire d'un coup d'œil."""
        counts = {value: 0 for value, _ in AttendanceRecord.Status.choices}
        for record in instance.records.all():
            counts[record.status] = counts.get(record.status, 0) + 1
        counts["total"] = sum(
            counts[value] for value, _ in AttendanceRecord.Status.choices
        )
        return counts


class DisciplineRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.get_full_name", read_only=True)
    enrollment_number = serializers.CharField(source="enrollment.enrollment_number", read_only=True)
    class_name = serializers.CharField(source="enrollment.school_class.name", read_only=True)
    entry_type_label = serializers.CharField(source="get_entry_type_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)

    class Meta:
        model = DisciplineRecord
        fields = [
            "id", "enrollment", "student_name", "enrollment_number", "class_name",
            "entry_type", "entry_type_label", "occurred_on", "late_hours",
            "incident_type", "severity", "severity_label", "description", "action_taken",
            "recorded_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "recorded_by_name", "created_at", "updated_at"]

    def validate(self, attrs):
        school = self.context["school"]
        academic_year = self.context["academic_year"]
        enrollment = attrs.get("enrollment", getattr(self.instance, "enrollment", None))
        if enrollment.school_id != school.id or enrollment.academic_year_id != academic_year.id:
            raise serializers.ValidationError({"enrollment": "Cette inscription ne correspond pas à l’école et à l’année sélectionnées."})

        entry_type = attrs.get("entry_type", getattr(self.instance, "entry_type", DisciplineRecord.EntryType.INCIDENT))
        if entry_type in {DisciplineRecord.EntryType.LATE, DisciplineRecord.EntryType.ABSENCE}:
            if (attrs.get("late_hours", getattr(self.instance, "late_hours", Decimal("0"))) or Decimal("0")) <= 0:
                raise serializers.ValidationError({"late_hours": "Saisissez un nombre d’heures supérieur à 0."})
            attrs["incident_type"] = ""
            attrs["severity"] = ""
        else:
            incident_type = " ".join(str(attrs.get("incident_type", getattr(self.instance, "incident_type", ""))).split())
            if not incident_type:
                raise serializers.ValidationError({"incident_type": "Précisez le type d’incident."})
            attrs["incident_type"] = incident_type
            attrs["late_hours"] = Decimal("0")
            if not attrs.get("severity", getattr(self.instance, "severity", "")):
                attrs["severity"] = DisciplineRecord.Severity.MEDIUM
        attrs["description"] = str(attrs.get("description", getattr(self.instance, "description", ""))).strip()
        attrs["action_taken"] = str(attrs.get("action_taken", getattr(self.instance, "action_taken", ""))).strip()
        return attrs


class GradeLineConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLine
        fields = ["id", "name", "weight", "max_score", "order"]
        read_only_fields = ["id"]


class GradeGroupConfigSerializer(serializers.ModelSerializer):
    lines = GradeLineConfigSerializer(many=True)

    class Meta:
        model = GradeGroup
        fields = ["id", "name", "weight", "order", "lines"]
        read_only_fields = ["id"]


class GradeSchemeSerializer(serializers.ModelSerializer):
    lines = GradeLineConfigSerializer(many=True, required=False)
    groups = GradeGroupConfigSerializer(many=True, required=False)
    method_label = serializers.CharField(source="get_calculation_method_display", read_only=True)

    class Meta:
        model = GradeScheme
        fields = ["id", "session", "calculation_method", "method_label", "lines", "groups", "created_at", "updated_at"]
        read_only_fields = ["id", "session", "created_at", "updated_at"]

    def validate(self, attrs):
        method = attrs.get("calculation_method", getattr(self.instance, "calculation_method", GradeScheme.CalculationMethod.EQUAL))
        lines = attrs.get("lines", [])
        groups = attrs.get("groups", [])
        all_lines = lines + [line for group in groups for line in group.get("lines", [])]
        if not all_lines:
            raise serializers.ValidationError({"lines": "Ajoutez au moins une ligne de note."})
        names = [line["name"].strip().casefold() for line in all_lines]
        if len(names) != len(set(names)):
            raise serializers.ValidationError({"lines": "Chaque ligne de note doit avoir un nom différent."})
        if method == GradeScheme.CalculationMethod.WEIGHTED:
            if groups:
                raise serializers.ValidationError({"groups": "Le mode par pourcentage n’utilise pas de groupes."})
            total = sum(line.get("weight") or 0 for line in lines)
            if total != 100:
                raise serializers.ValidationError({"lines": "Le total des pourcentages doit être exactement de 100 %."})
        elif method == GradeScheme.CalculationMethod.GROUPS:
            if lines or len(groups) < 2 or any(not group.get("lines") for group in groups):
                raise serializers.ValidationError({"groups": "Créez au moins deux groupes contenant chacun une ligne de note."})
            if sum(group.get("weight") or 0 for group in groups) != 100:
                raise serializers.ValidationError({"groups": "Le total des pourcentages des groupes doit être exactement de 100 %."})
            invalid_groups = [
                group["name"] for group in groups
                if sum(line.get("weight") or 0 for line in group.get("lines", [])) != 100
            ]
            if invalid_groups:
                raise serializers.ValidationError({
                    "groups": f"Le total des lignes doit être de 100 % dans chaque groupe : {', '.join(invalid_groups)}."
                })
        elif groups:
            raise serializers.ValidationError({"groups": "Le mode moyenne simple n’utilise pas de groupes."})
        return attrs

    @staticmethod
    def save_structure(scheme, lines, groups):
        for index, line in enumerate(lines, start=1):
            GradeLine.objects.create(scheme=scheme, order=index, name=" ".join(line["name"].split()), weight=line.get("weight"), max_score=line.get("max_score", 20))
        line_order = 1
        for group_index, group_data in enumerate(groups, start=1):
            group_lines = group_data.pop("lines")
            group = GradeGroup.objects.create(
                scheme=scheme, name=" ".join(group_data["name"].split()),
                weight=group_data.get("weight"), order=group_index,
            )
            for line in group_lines:
                GradeLine.objects.create(scheme=scheme, group=group, order=line_order, name=" ".join(line["name"].split()), weight=line.get("weight"), max_score=line.get("max_score", 20))
                line_order += 1

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        groups = validated_data.pop("groups", [])
        with transaction.atomic():
            scheme = GradeScheme.objects.create(**validated_data)
            self.save_structure(scheme, lines, groups)
        return scheme

    def update(self, instance, validated_data):
        if instance.lines.filter(entries__isnull=False).exists():
            raise serializers.ValidationError("La configuration ne peut plus être modifiée après la saisie de notes.")
        lines = validated_data.pop("lines", [])
        groups = validated_data.pop("groups", [])
        with transaction.atomic():
            instance.calculation_method = validated_data.get("calculation_method", instance.calculation_method)
            instance.save(update_fields=["calculation_method", "updated_at"])
            instance.lines.all().delete()
            instance.groups.all().delete()
            self.save_structure(instance, lines, groups)
        return instance


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    last_name = serializers.CharField(write_only=True)
    first_names = serializers.CharField(write_only=True)
    gender = serializers.ChoiceField(write_only=True, choices=CustomUser.Gender.choices)
    date_of_birth = serializers.DateField(write_only=True)
    health_information = serializers.CharField(write_only=True, required=False, allow_blank=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_last_name = serializers.CharField(source="student.last_name", read_only=True)
    student_first_names = serializers.CharField(source="student.first_name", read_only=True)
    student_gender = serializers.CharField(source="student.gender", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    student_phone = serializers.CharField(source="student.phone", read_only=True)
    student_address = serializers.CharField(source="student.address", read_only=True)
    student_health_information = serializers.CharField(source="student.health_information", read_only=True)
    gender_label = serializers.CharField(source="student.get_gender_display", read_only=True)
    date_of_birth_display = serializers.DateField(source="student.date_of_birth", read_only=True)
    student_year_result = serializers.CharField(source="student.year_result", read_only=True)
    student_year_result_label = serializers.CharField(source="student.get_year_result_display", read_only=True)
    student_date_joined = serializers.DateTimeField(source="student.date_joined", read_only=True)
    level = serializers.PrimaryKeyRelatedField(queryset=SchoolLevel.objects.filter(is_active=True))
    level_name = serializers.CharField(source="level.name", read_only=True)
    level_stage = serializers.CharField(source="level.get_stage_display", read_only=True)
    school_class = serializers.PrimaryKeyRelatedField(queryset=SchoolClass.objects.filter(is_active=True), required=False, allow_null=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    school_class_series = serializers.CharField(source="school_class.series", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    history = serializers.SerializerMethodField()
    student_status = serializers.ChoiceField(choices=CustomUser.StudentStatus.choices, required=False, default=CustomUser.StudentStatus.NEW)
    student_status_label = serializers.CharField(source="student.get_student_status_display", read_only=True)
    previous_average = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True,
        min_value=0, max_value=20,
    )
    guardian_phone = serializers.CharField(write_only=True, required=False)
    guardian_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_first_names = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_profession = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_id = serializers.IntegerField(source="guardian.id", read_only=True)
    guardian_name = serializers.CharField(source="guardian.get_full_name", read_only=True)
    guardian_phone_display = serializers.CharField(source="guardian.phone", read_only=True)
    guardian_profession_display = serializers.CharField(source="guardian.profession", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id", "enrollment_number", "student", "student_name", "student_last_name", "student_first_names", "student_gender",
            "student_username", "student_email", "student_phone", "student_address", "student_health_information", "gender_label", "date_of_birth_display",
            "student_year_result", "student_year_result_label", "student_date_joined", "status", "enrolled_at",
            "level", "level_name", "level_stage", "series", "previous_average", "student_status", "student_status_label", "school_class", "school_class_name", "school_class_series", "academic_year_name", "history",
            "guardian_id", "guardian_name", "guardian_phone_display", "guardian_profession_display",
            "guardian_phone", "guardian_last_name", "guardian_first_names", "guardian_profession",
            "last_name", "first_names", "gender", "date_of_birth", "health_information",
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
        users = CustomUser.objects.filter(username__iexact=number)
        if self.instance:
            users = users.exclude(pk=self.instance.student_id)
        if users.exists():
            raise serializers.ValidationError("Ce matricule est déjà utilisé comme nom d’utilisateur.")
        return number

    def validate(self, attrs):
        academic_year = self.context["academic_year"]
        if not academic_year.is_active or academic_year.is_closed:
            raise serializers.ValidationError({
                "academic_year": "Les inscriptions sont interdites pour une année inactive ou clôturée."
            })
        guardian_phone = attrs.get("guardian_phone")
        if guardian_phone:
            guardian_phone = normalize_togolese_phone(guardian_phone)
            attrs["guardian_phone"] = guardian_phone
            guardian = CustomUser.objects.filter(role=CustomUser.Role.PARENT, phone=guardian_phone).first()
            if guardian is None:
                if CustomUser.objects.filter(username__iexact=guardian_phone).exists():
                    raise serializers.ValidationError({"guardian_phone": "Ce numéro est déjà utilisé par un autre compte."})
                if not attrs.get("guardian_last_name", "").strip():
                    raise serializers.ValidationError({"guardian_last_name": "Le nom du tuteur est obligatoire."})
                if not attrs.get("guardian_first_names", "").strip():
                    raise serializers.ValidationError({"guardian_first_names": "Le prénom du tuteur est obligatoire."})
        elif not self.instance:
            raise serializers.ValidationError({"guardian_phone": "Le numéro de téléphone du tuteur est obligatoire."})
        school_class = attrs.get("school_class", getattr(self.instance, "school_class", None))
        level = attrs.get("level", getattr(self.instance, "level", None))
        series = attrs.get("series", getattr(self.instance, "series", "")).strip()
        allowed_series = {
            "Seconde": {"CD", "A4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
            "Première": {"D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
            "Terminale": {"D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
        }
        normalized_series = series.upper()
        if level and level.stage != SchoolLevel.Stage.HIGH and series:
            raise serializers.ValidationError({"series": "Le Primaire et le Collège n’ont pas de série."})
        if level and level.stage == SchoolLevel.Stage.HIGH:
            if not series:
                raise serializers.ValidationError({"series": "La série est obligatoire au Lycée."})
            if normalized_series not in allowed_series.get(level.name, set()):
                raise serializers.ValidationError({"series": f"Série invalide pour {level.name}."})
            attrs["series"] = "Ti" if normalized_series == "TI" else normalized_series
        else:
            attrs["series"] = ""
        if school_class and (
            school_class.school_id != self.context["school"].id
            or school_class.academic_year_id != academic_year.id
            or school_class.level_id != level.id
            or school_class.series.casefold() != attrs["series"].casefold()
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
            "id": item.id, "academic_year": item.academic_year.name,
            "cycle": item.level.get_stage_display() if item.level else None,
            "level": item.level.name if item.level else None,
            "series": item.series or None, "school_class": item.school_class.name if item.school_class else None,
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
        series = validated_data.pop("series", "")
        student_status = validated_data.pop("student_status", CustomUser.StudentStatus.NEW)
        guardian_phone = validated_data.pop("guardian_phone")
        guardian_last_name = " ".join(validated_data.pop("guardian_last_name", "").split())
        guardian_first_names = " ".join(validated_data.pop("guardian_first_names", "").split())
        guardian_profession = " ".join(validated_data.pop("guardian_profession", "").split())
        enrollment_number = validated_data.pop("enrollment_number")
        username = enrollment_number
        with transaction.atomic():
            guardian = CustomUser.objects.filter(
                role=CustomUser.Role.PARENT, phone=guardian_phone,
            ).first()
            if guardian is None:
                guardian = CustomUser(
                    username=guardian_phone,
                    phone=guardian_phone,
                    last_name=guardian_last_name,
                    first_name=guardian_first_names,
                    profession=guardian_profession,
                    role=CustomUser.Role.PARENT,
                )
                guardian.set_password(guardian_last_name)
                guardian.save()
            SchoolMembership.objects.update_or_create(
                school=school, user=guardian,
                defaults={"role": CustomUser.Role.PARENT, "is_active": True},
            )
            student = CustomUser(
                username=username,
                enrollment_number=enrollment_number,
                student_status=student_status,
                last_name=" ".join(validated_data.pop("last_name").split()),
                first_name=" ".join(validated_data.pop("first_names").split()),
                gender=validated_data.pop("gender"),
                date_of_birth=validated_data.pop("date_of_birth"),
                health_information=validated_data.pop("health_information", "").strip(),
                role=CustomUser.Role.STUDENT,
            )
            student.set_password(enrollment_number)
            student.save()
            SchoolMembership.objects.create(
                school=school, user=student, role=CustomUser.Role.STUDENT
            )
            enrollment = StudentEnrollment.objects.create(
                school=school,
                academic_year=academic_year,
                student=student,
                guardian=guardian,
                level=level,
                school_class=school_class,
                series=series,
                previous_average=validated_data.pop("previous_average", None),
                enrollment_number=enrollment_number,
            )
            return enrollment

    def update(self, instance, validated_data):
        guardian_phone = validated_data.pop("guardian_phone", None)
        guardian_last_name = " ".join(validated_data.pop("guardian_last_name", "").split())
        guardian_first_names = " ".join(validated_data.pop("guardian_first_names", "").split())
        guardian_profession = " ".join(validated_data.pop("guardian_profession", "").split())
        if guardian_phone:
            guardian = CustomUser.objects.filter(role=CustomUser.Role.PARENT, phone=guardian_phone).first()
            if guardian is None:
                guardian = CustomUser(
                    username=guardian_phone, phone=guardian_phone,
                    last_name=guardian_last_name, first_name=guardian_first_names,
                    profession=guardian_profession, role=CustomUser.Role.PARENT,
                )
                guardian.set_password(guardian_last_name)
                guardian.save()
            SchoolMembership.objects.update_or_create(
                school=instance.school, user=guardian,
                defaults={"role": CustomUser.Role.PARENT, "is_active": True},
            )
            instance.guardian = guardian
        student = instance.student
        if "student_status" in validated_data:
            student.student_status = validated_data.pop("student_status")
        field_mapping = {"last_name": "last_name", "first_names": "first_name", "gender": "gender", "date_of_birth": "date_of_birth", "health_information": "health_information"}
        for input_name, model_name in field_mapping.items():
            if input_name in validated_data:
                value = validated_data.pop(input_name)
                setattr(student, model_name, " ".join(value.split()) if isinstance(value, str) else value)
        student.save()
        for field in ("enrollment_number", "level", "series", "school_class", "previous_average"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        if "enrollment_number" in validated_data:
            new_number = validated_data["enrollment_number"]
            student.enrollment_number = new_number
            student.username = new_number
            student.set_password(new_number)
            student.save(update_fields=["enrollment_number", "username", "password"])
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
        fields = ["id", "name", "school", "academic_year", "level", "level_name", "cycle", "cycle_label", "series", "group", "maximum_capacity", "homeroom_teacher", "homeroom_teacher_name", "subjects", "effectif", "is_active", "created_at"]
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

    def validate_maximum_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("La capacité maximale doit être supérieure à zéro.")
        return value

    def validate(self, attrs):
        level = attrs.get("level", getattr(self.instance, "level", None))
        series = attrs.get("series", getattr(self.instance, "series", ""))
        group = attrs.get("group", getattr(self.instance, "group", ""))
        teacher = attrs.get("homeroom_teacher", getattr(self.instance, "homeroom_teacher", None))
        subject_configs = attrs.get("subject_configurations")
        allowed_series = {
            "Seconde": {"CD", "A4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
            "Première": {"D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
            "Terminale": {"D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "TI"},
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


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    author_role = serializers.CharField(source="author.get_role_display", read_only=True)
    audience_label = serializers.CharField(source="get_audience_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    class_names = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "audience", "audience_label", "roles",
            "classes", "class_names", "priority", "priority_label",
            "is_published", "published_at", "expires_on",
            "author_name", "author_role", "is_read", "created_at",
        ]
        read_only_fields = [
            "id", "author_name", "author_role", "audience_label",
            "priority_label", "class_names", "is_read", "created_at",
        ]

    def get_class_names(self, instance):
        return [item.group for item in instance.classes.all()]

    def get_is_read(self, instance):
        # `read_ids` est passé par la vue, qui charge les lectures en une fois
        # plutôt qu'une requête par annonce.
        return instance.id in self.context.get("read_ids", set())

    def validate(self, attrs):
        audience = attrs.get(
            "audience", getattr(self.instance, "audience", Announcement.Audience.EVERYONE)
        )
        roles = attrs.get("roles", getattr(self.instance, "roles", []))
        if audience == Announcement.Audience.ROLES:
            known = dict(CustomUser.Role.choices)
            cleaned = [str(role) for role in roles if str(role) in known]
            if not cleaned:
                raise serializers.ValidationError(
                    {"roles": "Choisissez au moins un rôle valide."}
                )
            attrs["roles"] = cleaned
        else:
            # Hors ciblage par rôle, la liste n'a pas de sens : on la vide pour
            # qu'un changement de destinataires ne laisse pas de reliquat.
            attrs["roles"] = []
        attrs["title"] = " ".join(str(attrs.get("title", "")).split()) or attrs.get("title", "")
        return attrs


class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = MessageAttachment
        fields = [
            "id", "url", "kind", "kind_label", "original_name",
            "content_type", "size", "duration_seconds",
        ]
        read_only_fields = fields

    def get_url(self, instance):
        if not instance.file:
            return None
        request = self.context.get("request")
        # Adresse absolue : le mobile n'a pas de page d'origine d'où résoudre
        # un chemin relatif.
        return (
            request.build_absolute_uri(instance.file.url)
            if request else instance.file.url
        )


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "body", "sent_at", "sender_id", "sender_name", "attachments",
        ]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    participants_detail = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "subject", "participants_detail", "last_message",
            "unread_count", "last_message_at", "created_at",
        ]
        read_only_fields = fields

    def get_participants_detail(self, instance):
        # L'utilisateur courant est retiré : un fil se nomme par ses autres
        # participants, pas par soi-même.
        me = self.context.get("user_id")
        return [
            {
                "id": person.id,
                "name": person.get_full_name(),
                "role": person.get_role_display(),
            }
            for person in instance.participants.all()
            if person.id != me
        ]

    def get_last_message(self, instance):
        message = instance.messages.order_by("-sent_at", "-id").first()
        if message is None:
            return None
        preview = message.body[:160]
        if not preview:
            # Un message sans texte n'est pas vide : il porte une pièce jointe.
            # L'aperçu doit le dire, sinon la liste montrerait une ligne blanche.
            attachment = message.attachments.first()
            preview = {
                MessageAttachment.Kind.IMAGE: "📷 Photo",
                MessageAttachment.Kind.VIDEO: "🎬 Vidéo",
                MessageAttachment.Kind.AUDIO: "🎙 Message vocal",
                MessageAttachment.Kind.DOCUMENT: "📎 Document",
            }.get(attachment.kind, "📎 Pièce jointe") if attachment else ""
        return {
            "body": preview,
            "sent_at": message.sent_at,
            "sender_name": message.sender.get_full_name() if message.sender else "",
        }

    def get_unread_count(self, instance):
        me = self.context.get("user_id")
        if me is None:
            return 0
        # Ses propres messages ne comptent jamais comme non lus.
        return instance.messages.exclude(sender_id=me).exclude(read_by__id=me).count()
