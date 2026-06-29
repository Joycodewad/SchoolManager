import csv
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils.text import slugify
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AcademicSession, AcademicYear, ClassFeeItem, ClassSubject, CustomUser, ExpenseCategory, FeeInstallment, FeePayment, GradeEntry, GradeScheme, School, SchoolClass, SchoolExpense, SchoolLevel, SchoolMembership, StudentEnrollment, Subject, TeacherAssignmentSubject, TeacherClassAssignment, TeacherUnavailability, TuitionFeePlan
from .serializers import AcademicSessionSerializer, AcademicYearSerializer, CustomUserSerializer, ExpenseCategorySerializer, FeePaymentSerializer, GradeSchemeSerializer, SchoolClassSerializer, SchoolExpenseSerializer, SchoolLevelSerializer, SchoolMembershipSerializer, SchoolSerializer, StudentEnrollmentSerializer, SubjectSerializer, TuitionFeePlanSerializer, normalize_togolese_phone


XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def read_xlsx_without_dependency(uploaded_file):
    """Lit la première feuille d'un XLSX quand openpyxl n'est pas installé."""
    with zipfile.ZipFile(uploaded_file) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(node.text or "" for node in item.iter(f"{XLSX_NS}t")) for item in root]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        first_sheet = workbook.find(f".//{XLSX_NS}sheet")
        if first_sheet is None:
            return []
        relation_id = first_sheet.attrib.get(f"{OFFICE_REL_NS}id")
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            (relation.attrib["Target"] for relation in relationships.findall(f"{REL_NS}Relationship") if relation.attrib.get("Id") == relation_id),
            "worksheets/sheet1.xml",
        )
        sheet_path = posixpath.normpath(posixpath.join("xl", target))

        date_styles = set()
        if "xl/styles.xml" in archive.namelist():
            styles = ET.fromstring(archive.read("xl/styles.xml"))
            custom_formats = {
                int(item.attrib["numFmtId"]): item.attrib.get("formatCode", "").lower()
                for item in styles.findall(f".//{XLSX_NS}numFmt")
            }
            cell_formats = styles.find(f"{XLSX_NS}cellXfs")
            if cell_formats is not None:
                for index, style in enumerate(cell_formats):
                    format_id = int(style.attrib.get("numFmtId", 0))
                    format_code = custom_formats.get(format_id, "")
                    if format_id in range(14, 23) or all(marker in format_code for marker in ("y", "d")):
                        date_styles.add(index)

        sheet = ET.fromstring(archive.read(sheet_path))
        parsed_rows = []
        for row in sheet.findall(f".//{XLSX_NS}row"):
            values = {}
            for cell in row.findall(f"{XLSX_NS}c"):
                reference = cell.attrib.get("r", "A1")
                letters = re.match(r"[A-Z]+", reference)
                column = 0
                for letter in letters.group(0) if letters else "A":
                    column = column * 26 + ord(letter) - 64
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{XLSX_NS}v")
                raw_value = value_node.text if value_node is not None else ""
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{XLSX_NS}t"))
                elif cell_type == "s" and raw_value:
                    value = shared_strings[int(raw_value)]
                elif cell_type == "b":
                    value = raw_value == "1"
                elif raw_value and int(cell.attrib.get("s", 0)) in date_styles:
                    value = date(1899, 12, 30) + timedelta(days=float(raw_value))
                else:
                    value = raw_value
                values[column] = value
            parsed_rows.append([values.get(index, "") for index in range(1, max(values, default=0) + 1)])

    if not parsed_rows:
        return []
    headers = [str(value or "").strip() for value in parsed_rows[0]]
    return [dict(zip(headers, row)) for row in parsed_rows[1:] if any(value not in (None, "") for value in row)]


def accessible_schools(user):
    if user.is_superuser:
        return School.objects.filter(is_active=True)
    return School.objects.filter(
        Q(owner=user) | Q(memberships__user=user, memberships__is_active=True),
        is_active=True,
    ).distinct()


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        user = authenticate(request, username=username, password=request.data.get("password", ""))
        if not user or user.is_archived:
            return Response({"message": "Nom d’utilisateur ou mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        schools = accessible_schools(user)
        return Response({
            "token": token.key,
            "user": CustomUserSerializer(user, context={"request": request}).data,
            "schools": SchoolSerializer(
                schools,
                many=True,
                context={"request": request, "authenticated_user": user},
            ).data,
        })


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsernameSuggestionView(APIView):
    def get(self, request):
        last_name = str(request.query_params.get("last_name", "")).strip()
        first_names = str(request.query_params.get("first_names", "")).strip()
        first_name = first_names.split()[0] if first_names else ""
        clean_last = slugify(last_name).replace("-", "")
        clean_first = slugify(first_name).replace("-", "")
        candidates = [
            clean_last,
            clean_first,
            f"{clean_last[:3]}{clean_first[:3]}",
            f"{clean_first[:3]}{clean_last[:3]}",
        ]
        candidates = list(dict.fromkeys(candidate for candidate in candidates if len(candidate) >= 3))
        if not candidates:
            return Response({"username": ""})
        username = next(
            (candidate for candidate in candidates if not CustomUser.objects.filter(username__iexact=candidate).exists()),
            None,
        )
        if username is None:
            base = candidates[2] if len(candidates) > 2 else candidates[0]
            suffix = 2
            username = f"{base}{suffix}"
            while CustomUser.objects.filter(username__iexact=username).exists():
                suffix += 1
                username = f"{base}{suffix}"
        return Response({"username": username})


class RoleChoicesView(APIView):
    def get(self, request):
        personnel_roles = {
            CustomUser.Role.ADMIN,
            CustomUser.Role.TEACHER,
            CustomUser.Role.ACCOUNTANT,
            CustomUser.Role.SECRETARY,
            CustomUser.Role.CENSEUR,
            CustomUser.Role.PROVISEUR,
            CustomUser.Role.SURVEILLANT,
            CustomUser.Role.STAFF,
        }
        roles = [
            {"value": value, "label": label}
            for value, label in CustomUser.Role.choices
            if value in personnel_roles
        ]
        return Response(roles)


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer

    def get_queryset(self):
        return accessible_schools(self.request.user)

    def perform_create(self, serializer):
        if not (self.request.user.is_superuser or self.request.user.role == CustomUser.Role.OWNER):
            raise serializers.ValidationError({"permission": "Seuls un propriétaire ou un superutilisateur peuvent créer une école."})
        if self.request.user.is_superuser:
            owner = serializer.validated_data.get("owner")
            if not owner:
                raise serializers.ValidationError({"owner": "Sélectionnez le propriétaire de l’école."})
        else:
            owner = self.request.user
        school = serializer.save(owner=owner)
        if owner.role != CustomUser.Role.OWNER:
            owner.role = CustomUser.Role.OWNER
            owner.save(update_fields=["role"])
        SchoolMembership.objects.get_or_create(
            school=school,
            user=owner,
            defaults={"role": CustomUser.Role.OWNER},
        )

    def perform_update(self, serializer):
        if not self.request.user.is_superuser and serializer.instance.owner_id != self.request.user.id:
            raise serializers.ValidationError({"permission": "Seul le propriétaire peut modifier cette école."})
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser and instance.owner_id != self.request.user.id:
            raise serializers.ValidationError({"permission": "Seul le propriétaire peut supprimer cette école."})
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        school = self.get_object()
        if request.method == "GET":
            memberships = school.memberships.select_related("user")
            return Response(SchoolMembershipSerializer(memberships, many=True).data)
        if not request.user.is_superuser and school.owner_id != request.user.id:
            return Response({"detail": "Seul le propriétaire peut ajouter un membre."}, status=403)
        serializer = SchoolMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(school=school)
        return Response(serializer.data, status=201)


class SchoolScopedMixin:
    school = None

    def get_school(self):
        if self.school is not None:
            return self.school
        school_id = self.kwargs.get("school_pk") or self.request.headers.get("X-School-ID")
        if not school_id:
            raise serializers.ValidationError({"school": "Sélectionnez une école."})
        try:
            self.school = accessible_schools(self.request.user).get(pk=school_id)
        except (School.DoesNotExist, ValueError):
            raise serializers.ValidationError({"school": "Vous n’avez pas accès à cette école."})
        return self.school

    def ensure_manager(self):
        school = self.get_school()
        self.ensure_manager_for_school(school)

    def ensure_manager_for_school(self, school):
        allowed_roles = [CustomUser.Role.ADMIN, CustomUser.Role.OWNER, CustomUser.Role.PROVISEUR]
        is_manager = self.request.user.is_superuser or school.owner_id == self.request.user.id or school.memberships.filter(
            user=self.request.user, role__in=allowed_roles, is_active=True
        ).exists()
        if not is_manager:
            raise serializers.ValidationError({"permission": "Vous ne pouvez pas gérer le personnel de cette école."})


class FinanceMixin(SchoolScopedMixin):
    def ensure_fee_configurator(self):
        school = self.get_school()
        allowed_roles = [CustomUser.Role.OWNER, CustomUser.Role.CENSEUR, CustomUser.Role.PROVISEUR]
        if not (
            self.request.user.is_superuser
            or school.owner_id == self.request.user.id
            or school.memberships.filter(user=self.request.user, role__in=allowed_roles, is_active=True).exists()
        ):
            raise serializers.ValidationError({"permission": "Seuls le propriétaire, le censeur ou le proviseur peuvent configurer l’écolage."})

    def ensure_finance_manager(self):
        school = self.get_school()
        allowed_roles = [CustomUser.Role.ADMIN, CustomUser.Role.OWNER, CustomUser.Role.PROVISEUR, CustomUser.Role.ACCOUNTANT]
        if not (
            self.request.user.is_superuser
            or school.owner_id == self.request.user.id
            or school.memberships.filter(user=self.request.user, role__in=allowed_roles, is_active=True).exists()
        ):
            raise serializers.ValidationError({"permission": "Vous ne pouvez pas gérer les finances de cette école."})

    def get_academic_year(self):
        year_id = self.request.headers.get("X-Academic-Year-ID")
        if not year_id:
            raise serializers.ValidationError({"academic_year": "Sélectionnez une année académique."})
        try:
            return AcademicYear.objects.get(pk=year_id, school=self.get_school())
        except (AcademicYear.DoesNotExist, ValueError):
            raise serializers.ValidationError({"academic_year": "Année académique invalide."})


class TuitionFeePlanListView(FinanceMixin, APIView):
    def get(self, request, school_pk):
        year = self.get_academic_year()
        plans = TuitionFeePlan.objects.filter(school=self.get_school(), academic_year=year).select_related(
            "school_class", "school_class__level"
        ).prefetch_related("items__fee_module", "items__installments")
        return Response(TuitionFeePlanSerializer(plans, many=True).data)

    def post(self, request, school_pk):
        self.ensure_fee_configurator()
        year = self.get_academic_year()
        serializer = TuitionFeePlanSerializer(data=request.data, context={"school": self.get_school(), "academic_year": year})
        serializer.is_valid(raise_exception=True)
        serializer.save(school=self.get_school(), academic_year=year)
        return Response(serializer.data, status=201)


class TuitionFeePlanDetailView(FinanceMixin, APIView):
    def get_object(self, pk):
        try:
            return TuitionFeePlan.objects.prefetch_related("items__fee_module", "items__installments").get(
                pk=pk, school=self.get_school(), academic_year=self.get_academic_year()
            )
        except TuitionFeePlan.DoesNotExist:
            raise serializers.ValidationError({"plan": "Barème introuvable."})

    def patch(self, request, school_pk, pk):
        self.ensure_fee_configurator()
        plan = self.get_object(pk)
        serializer = TuitionFeePlanSerializer(plan, data=request.data, partial=True, context={"school": self.get_school(), "academic_year": self.get_academic_year()})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, school_pk, pk):
        self.ensure_fee_configurator()
        plan = self.get_object(pk)
        if plan.items.filter(payments__isnull=False).exists():
            return Response({"detail": "Ce barème possède des paiements et ne peut pas être supprimé."}, status=400)
        plan.delete()
        return Response(status=204)

    def post(self, request, school_pk, pk):
        self.ensure_fee_configurator()
        source = self.get_object(pk)
        target_ids = request.data.get("target_classes", [])
        if not isinstance(target_ids, list) or not target_ids:
            raise serializers.ValidationError({"target_classes": "Sélectionnez au moins une classe cible."})
        try:
            normalized_ids = {int(value) for value in target_ids}
        except (TypeError, ValueError):
            raise serializers.ValidationError({"target_classes": "Une ou plusieurs classes cibles sont invalides."})
        if source.school_class_id in normalized_ids:
            raise serializers.ValidationError({"target_classes": "La classe source ne peut pas être une cible."})
        target_classes = list(SchoolClass.objects.filter(
            pk__in=normalized_ids, school=self.get_school(), academic_year=self.get_academic_year(),
        ))
        if len(target_classes) != len(normalized_ids):
            raise serializers.ValidationError({"target_classes": "Une ou plusieurs classes cibles sont invalides."})
        existing_plans = {
            plan.school_class_id: plan for plan in TuitionFeePlan.objects.filter(
                school_class_id__in=normalized_ids,
            ).prefetch_related("items__payments")
        }
        blocked = [school_class.name for school_class in target_classes if (
            existing_plans.get(school_class.id)
            and existing_plans[school_class.id].items.filter(payments__isnull=False).exists()
        )]
        if blocked:
            return Response({"detail": f"Copie impossible : des paiements existent déjà pour {', '.join(blocked)}."}, status=400)
        source_items = list(source.items.select_related("fee_module").prefetch_related("installments"))
        created_plans = []
        with transaction.atomic():
            for target_class in target_classes:
                existing = existing_plans.get(target_class.id)
                if existing:
                    existing.delete()
                target = TuitionFeePlan.objects.create(
                    school=self.get_school(), academic_year=self.get_academic_year(), school_class=target_class,
                )
                for source_item in source_items:
                    target_item = ClassFeeItem.objects.create(
                        plan=target, fee_module=source_item.fee_module,
                        male_amount=source_item.male_amount, female_amount=source_item.female_amount,
                        payable_in_installments=source_item.payable_in_installments,
                    )
                    FeeInstallment.objects.bulk_create([
                        FeeInstallment(
                            class_fee=target_item, name=row.name, percentage=row.percentage,
                            due_date=row.due_date, order=row.order,
                        ) for row in source_item.installments.all()
                    ])
                created_plans.append(target.id)
        targets = TuitionFeePlan.objects.filter(pk__in=created_plans).prefetch_related("items__fee_module", "items__installments")
        return Response(TuitionFeePlanSerializer(targets, many=True).data, status=201)


class TuitionPaymentListView(FinanceMixin, APIView):
    def get(self, request, school_pk):
        year = self.get_academic_year()
        queryset = FeePayment.objects.filter(
            enrollment__school=self.get_school(), enrollment__academic_year=year,
        ).select_related("enrollment__student", "enrollment__school_class", "class_fee__fee_module", "installment", "received_by")
        if request.query_params.get("class_id"):
            queryset = queryset.filter(enrollment__school_class_id=request.query_params["class_id"])
        return Response(FeePaymentSerializer(queryset, many=True).data)

    def post(self, request, school_pk):
        self.ensure_finance_manager()
        serializer = FeePaymentSerializer(data=request.data, context={"school": self.get_school(), "academic_year": self.get_academic_year()})
        serializer.is_valid(raise_exception=True)
        serializer.save(received_by=request.user)
        return Response(serializer.data, status=201)


class TuitionComplianceView(FinanceMixin, APIView):
    def get(self, request, school_pk):
        year = self.get_academic_year()
        class_id = request.query_params.get("class_id")
        target = request.query_params.get("target")
        if not class_id:
            raise serializers.ValidationError({"class_id": "Sélectionnez une classe."})
        try:
            plan = TuitionFeePlan.objects.prefetch_related("items__fee_module", "items__installments").get(
                school=self.get_school(), academic_year=year, school_class_id=class_id,
            )
        except TuitionFeePlan.DoesNotExist:
            raise serializers.ValidationError({"plan": "Définissez d’abord le barème de cette classe."})
        if not target:
            raise serializers.ValidationError({"target": "Sélectionnez une rubrique de frais."})
        installment = None
        try:
            if target.startswith("installment:"):
                installment = FeeInstallment.objects.select_related("class_fee__fee_module").get(pk=target.split(":", 1)[1], class_fee__plan=plan)
                class_fee = installment.class_fee
            else:
                class_fee_id = target.split(":", 1)[1] if target.startswith("item:") else target
                class_fee = ClassFeeItem.objects.select_related("fee_module").get(pk=class_fee_id, plan=plan)
        except (ValueError, IndexError, FeeInstallment.DoesNotExist, ClassFeeItem.DoesNotExist):
            raise serializers.ValidationError({"target": "Rubrique ou tranche invalide."})
        enrollments = StudentEnrollment.objects.filter(
            school=self.get_school(), academic_year=year, school_class_id=class_id, status=StudentEnrollment.Status.ACTIVE,
        ).select_related("student", "school_class")
        rows = []
        for enrollment in enrollments:
            base_amount = class_fee.female_amount if enrollment.student.gender == CustomUser.Gender.FEMALE else class_fee.male_amount
            expected = base_amount if installment is None else (base_amount * installment.percentage / Decimal("100")).quantize(Decimal("0.01"))
            payments = enrollment.fee_payments.filter(class_fee=class_fee)
            if installment is not None:
                payments = payments.filter(installment=installment)
            paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
            rows.append({
                "enrollment": enrollment.id, "enrollment_number": enrollment.enrollment_number,
                "student_name": enrollment.student.get_full_name(), "gender": enrollment.student.get_gender_display(),
                "student_status": enrollment.student.get_student_status_display(), "expected": expected,
                "paid": paid, "balance": max(expected - paid, Decimal("0")), "is_compliant": paid >= expected,
            })
        return Response({
            "plan": TuitionFeePlanSerializer(plan).data,
            "target": class_fee.fee_module.name if installment is None else f"{class_fee.fee_module.name} — {installment.name}",
            "compliant_count": sum(row["is_compliant"] for row in rows),
            "non_compliant_count": sum(not row["is_compliant"] for row in rows),
            "students": rows,
        })


class ExpenseCategoryListView(FinanceMixin, APIView):
    def get(self, request, school_pk):
        categories = ExpenseCategory.objects.filter(school=self.get_school(), is_active=True)
        return Response(ExpenseCategorySerializer(categories, many=True).data)

    def post(self, request, school_pk):
        self.ensure_finance_manager()
        serializer = ExpenseCategorySerializer(data=request.data, context={"school": self.get_school()})
        serializer.is_valid(raise_exception=True)
        serializer.save(school=self.get_school())
        return Response(serializer.data, status=201)


class SchoolExpenseListView(FinanceMixin, APIView):
    def get(self, request, school_pk):
        year = self.get_academic_year()
        queryset = SchoolExpense.objects.filter(
            school=self.get_school(), academic_year=year,
        ).select_related("category", "recorded_by")
        category_id = request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if request.query_params.get("date_from"):
            queryset = queryset.filter(expense_date__gte=request.query_params["date_from"])
        if request.query_params.get("date_to"):
            queryset = queryset.filter(expense_date__lte=request.query_params["date_to"])
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(label__icontains=search) | Q(beneficiary__icontains=search) | Q(reference__icontains=search))
        return Response(SchoolExpenseSerializer(queryset, many=True).data)

    def post(self, request, school_pk):
        self.ensure_finance_manager()
        serializer = SchoolExpenseSerializer(data=request.data, context={"school": self.get_school()})
        serializer.is_valid(raise_exception=True)
        serializer.save(school=self.get_school(), academic_year=self.get_academic_year(), recorded_by=request.user)
        return Response(serializer.data, status=201)


class SchoolExpenseDetailView(FinanceMixin, APIView):
    def get_object(self, pk):
        try:
            return SchoolExpense.objects.select_related("category", "recorded_by").get(
                pk=pk, school=self.get_school(), academic_year=self.get_academic_year(),
            )
        except SchoolExpense.DoesNotExist:
            raise serializers.ValidationError({"expense": "Dépense introuvable."})

    def patch(self, request, school_pk, pk):
        self.ensure_finance_manager()
        serializer = SchoolExpenseSerializer(
            self.get_object(pk), data=request.data, partial=True, context={"school": self.get_school()},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, school_pk, pk):
        self.ensure_finance_manager()
        self.get_object(pk).delete()
        return Response(status=204)


class GradeMixin(SchoolScopedMixin):
    def get_academic_year(self):
        try:
            return AcademicYear.objects.get(pk=self.request.headers.get("X-Academic-Year-ID"), school=self.get_school())
        except (AcademicYear.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"academic_year": "Sélectionnez une année académique valide."})

    def can_configure_grades(self):
        school = self.get_school()
        roles = [CustomUser.Role.OWNER, CustomUser.Role.ADMIN, CustomUser.Role.CENSEUR, CustomUser.Role.PROVISEUR]
        return self.request.user.is_superuser or school.owner_id == self.request.user.id or school.memberships.filter(user=self.request.user, role__in=roles, is_active=True).exists()

    def ensure_grade_access(self):
        if self.can_configure_grades():
            return
        if self.request.user.role == CustomUser.Role.TEACHER or self.get_school().memberships.filter(user=self.request.user, role=CustomUser.Role.TEACHER, is_active=True).exists():
            return
        raise serializers.ValidationError({"permission": "Vous n’avez pas accès aux notes."})

    def ensure_grade_configurator(self):
        if not self.can_configure_grades():
            raise serializers.ValidationError({"permission": "Seuls le propriétaire, l’administrateur, le censeur ou le proviseur peuvent configurer les notes."})

    def can_access_class_subject(self, class_subject):
        if self.can_configure_grades():
            return True
        return TeacherAssignmentSubject.objects.filter(
            assignment__teacher=self.request.user,
            assignment__school=self.get_school(),
            assignment__academic_year=class_subject.school_class.academic_year,
            assignment__school_class=class_subject.school_class,
            class_subject=class_subject,
        ).exists()


class GradeContextView(GradeMixin, APIView):
    def get(self, request, school_pk):
        self.ensure_grade_access()
        year = self.get_academic_year()
        sessions = AcademicSession.objects.filter(academic_year=year, is_active=True, is_closed=False).prefetch_related("classes__level", "classes__subject_configurations__subject")
        result = []
        for session in sessions:
            classes = []
            for school_class in session.classes.all():
                subjects = [config for config in school_class.subject_configurations.all() if self.can_access_class_subject(config)]
                if subjects or self.can_configure_grades():
                    classes.append({
                        "id": school_class.id,
                        "name": " ".join(part for part in (school_class.level.name, school_class.series, school_class.group) if part),
                        "subjects": [{"id": config.id, "name": config.subject.name} for config in subjects],
                    })
            if classes:
                result.append({"id": session.id, "name": session.name, "label": session.label, "classes": classes})
        return Response({"can_configure": self.can_configure_grades(), "sessions": result})


class GradeSchemeView(GradeMixin, APIView):
    def get_session(self, session_pk):
        try:
            return AcademicSession.objects.get(pk=session_pk, academic_year=self.get_academic_year())
        except AcademicSession.DoesNotExist:
            raise serializers.ValidationError({"session": "Session académique invalide."})

    def get(self, request, school_pk, session_pk):
        self.ensure_grade_access()
        session = self.get_session(session_pk)
        try:
            scheme = GradeScheme.objects.prefetch_related("lines", "groups__lines").get(session=session)
        except GradeScheme.DoesNotExist:
            return Response(None)
        return Response(GradeSchemeSerializer(scheme).data)

    def put(self, request, school_pk, session_pk):
        self.ensure_grade_configurator()
        session = self.get_session(session_pk)
        scheme = GradeScheme.objects.filter(session=session).first()
        serializer = GradeSchemeSerializer(scheme, data=request.data) if scheme else GradeSchemeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session, created_by=request.user) if scheme is None else serializer.save()
        return Response(serializer.data, status=201 if scheme is None else 200)


class GradeSheetView(GradeMixin, APIView):
    def get_context(self, session_pk, class_subject_pk):
        year = self.get_academic_year()
        try:
            session = AcademicSession.objects.get(pk=session_pk, academic_year=year, is_active=True, is_closed=False)
            class_subject = ClassSubject.objects.select_related("school_class", "subject").get(pk=class_subject_pk, school_class__academic_year=year, school_class__school=self.get_school())
        except (AcademicSession.DoesNotExist, ClassSubject.DoesNotExist):
            raise serializers.ValidationError({"context": "Session, classe ou matière invalide."})
        if not session.classes.filter(pk=class_subject.school_class_id).exists():
            raise serializers.ValidationError({"session": "Cette classe n’appartient pas à la session."})
        if not self.can_access_class_subject(class_subject):
            raise serializers.ValidationError({"permission": "Cette matière ne vous est pas affectée dans cette classe."})
        try:
            scheme = GradeScheme.objects.prefetch_related("lines", "groups__lines").get(session=session)
        except GradeScheme.DoesNotExist:
            raise serializers.ValidationError({"configuration": "Les lignes de notes ne sont pas encore configurées pour cette session."})
        return session, class_subject, scheme

    @staticmethod
    def calculate_average(scheme, scores):
        lines = list(scheme.lines.all())
        if not lines or any(line.id not in scores for line in lines):
            return None
        normalized = {line.id: scores[line.id] * Decimal("20") / line.max_score for line in lines}
        if scheme.calculation_method == GradeScheme.CalculationMethod.WEIGHTED:
            return sum(normalized[line.id] * line.weight / Decimal("100") for line in lines)
        if scheme.calculation_method == GradeScheme.CalculationMethod.GROUPS:
            group_averages = []
            groups = list(scheme.groups.all())
            legacy_group_weight = Decimal("100") / len(groups)
            for group in groups:
                group_lines = list(group.lines.all())
                legacy_line_weight = Decimal("100") / len(group_lines)
                group_average = sum(
                    normalized[line.id] * (line.weight or legacy_line_weight) / Decimal("100")
                    for line in group_lines
                )
                group_averages.append(group_average * (group.weight or legacy_group_weight) / Decimal("100"))
            return sum(group_averages)
        return sum(normalized.values()) / len(normalized)

    def get(self, request, school_pk, session_pk, class_subject_pk):
        self.ensure_grade_access()
        _, class_subject, scheme = self.get_context(session_pk, class_subject_pk)
        enrollments = StudentEnrollment.objects.filter(school_class=class_subject.school_class, status=StudentEnrollment.Status.ACTIVE).select_related("student").order_by("student__last_name", "student__first_name")
        entries = GradeEntry.objects.filter(class_subject=class_subject, line__scheme=scheme)
        entry_map = {(entry.enrollment_id, entry.line_id): entry.score for entry in entries}
        rows = []
        for enrollment in enrollments:
            scores = {line.id: entry_map[(enrollment.id, line.id)] for line in scheme.lines.all() if (enrollment.id, line.id) in entry_map}
            average = self.calculate_average(scheme, scores)
            rows.append({"enrollment": enrollment.id, "matricule": enrollment.enrollment_number, "student_name": enrollment.student.get_full_name(), "scores": {str(key): value for key, value in scores.items()}, "average": average.quantize(Decimal("0.01")) if average is not None else None})
        return Response({"scheme": GradeSchemeSerializer(scheme).data, "class_subject": {"id": class_subject.id, "subject": class_subject.subject.name}, "students": rows})

    def post(self, request, school_pk, session_pk, class_subject_pk):
        self.ensure_grade_access()
        _, class_subject, scheme = self.get_context(session_pk, class_subject_pk)
        lines = {line.id: line for line in scheme.lines.all()}
        enrollment_ids = set(StudentEnrollment.objects.filter(school_class=class_subject.school_class, status=StudentEnrollment.Status.ACTIVE).values_list("id", flat=True))
        grades = request.data.get("grades", [])
        errors = []
        prepared = []
        for index, item in enumerate(grades, start=1):
            try:
                enrollment_id, line_id = int(item["enrollment"]), int(item["line"])
                score = Decimal(str(item["score"]))
                if enrollment_id not in enrollment_ids or line_id not in lines or score < 0 or score > lines[line_id].max_score:
                    raise ValueError
                prepared.append((enrollment_id, line_id, score))
            except (KeyError, TypeError, ValueError, ArithmeticError):
                errors.append(f"Note invalide à la ligne {index}.")
        if errors:
            return Response({"grades": errors}, status=400)
        with transaction.atomic():
            for enrollment_id, line_id, score in prepared:
                GradeEntry.objects.update_or_create(
                    enrollment_id=enrollment_id, line_id=line_id, class_subject=class_subject,
                    defaults={"score": score, "entered_by": request.user},
                )
        return self.get(request, school_pk, session_pk, class_subject_pk)


class CustomUserViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        school = self.get_school()
        return CustomUser.objects.filter(
            school_memberships__school=school,
            school_memberships__is_active=True,
            is_archived=False,
        ).distinct()

    def perform_create(self, serializer):
        self.ensure_manager()
        with transaction.atomic():
            user = serializer.save()
            SchoolMembership.objects.create(school=self.get_school(), user=user, role=user.role)

    def perform_update(self, serializer):
        self.ensure_manager()
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_manager()
        SchoolMembership.objects.filter(school=self.get_school(), user=instance).update(is_active=False)


class TeacherViewSet(CustomUserViewSet):
    def get_selected_academic_year(self):
        try:
            return AcademicYear.objects.get(pk=self.request.headers.get("X-Academic-Year-ID"), school=self.get_school())
        except (AcademicYear.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"academic_year": "Sélectionnez une année académique valide."})

    def get_queryset(self):
        school = self.get_school()
        return CustomUser.objects.filter(
            school_memberships__school=school,
            school_memberships__role__in=[
                CustomUser.Role.ADMIN,
                CustomUser.Role.TEACHER,
                CustomUser.Role.ACCOUNTANT,
                CustomUser.Role.SECRETARY,
                CustomUser.Role.CENSEUR,
                CustomUser.Role.PROVISEUR,
                CustomUser.Role.SURVEILLANT,
                CustomUser.Role.STAFF,
            ],
            school_memberships__is_active=True,
            is_archived=False,
        ).select_related("primary_subject").prefetch_related("subjects").distinct()

    def perform_create(self, serializer):
        role = serializer.validated_data.get("role", CustomUser.Role.TEACHER)
        if role == CustomUser.Role.OWNER and not self.request.user.is_superuser:
            raise serializers.ValidationError({"role": "Seul un superutilisateur peut créer un propriétaire."})
        selected_ids = serializer.validated_data.pop("school_ids", [])
        if not selected_ids:
            selected_ids = [self.get_school().id]
        schools = list(accessible_schools(self.request.user).filter(id__in=set(selected_ids)))
        if len(schools) != len(set(selected_ids)):
            raise serializers.ValidationError({"school_ids": "Une ou plusieurs écoles sont inaccessibles."})
        for school in schools:
            self.ensure_manager_for_school(school)
        with transaction.atomic():
            user = serializer.save(role=role)
            SchoolMembership.objects.bulk_create([
                SchoolMembership(school=school, user=user, role=role)
                for school in schools
            ])

    def perform_update(self, serializer):
        self.ensure_manager()
        selected_ids = serializer.validated_data.pop("school_ids", None)
        role = serializer.validated_data.get("role", serializer.instance.role)
        if role == CustomUser.Role.OWNER and not self.request.user.is_superuser:
            raise serializers.ValidationError({"role": "Seul un superutilisateur peut attribuer le rôle propriétaire."})
        schools = None
        if selected_ids is not None:
            if not selected_ids:
                raise serializers.ValidationError({"school_ids": "Sélectionnez au moins une école."})
            schools = list(accessible_schools(self.request.user).filter(id__in=set(selected_ids)))
            if len(schools) != len(set(selected_ids)):
                raise serializers.ValidationError({"school_ids": "Une ou plusieurs écoles sont inaccessibles."})
            for school in schools:
                self.ensure_manager_for_school(school)
        with transaction.atomic():
            user = serializer.save(role=role)
            if schools is not None:
                SchoolMembership.objects.filter(user=user).exclude(school__in=schools).update(is_active=False)
                for school in schools:
                    SchoolMembership.objects.update_or_create(
                        school=school,
                        user=user,
                        defaults={"role": role, "is_active": True},
                    )

    @action(detail=True, methods=["get", "post"], url_path="classes")
    def class_assignments(self, request, pk=None, school_pk=None):
        teacher = self.get_object()
        year = self.get_selected_academic_year()
        if teacher.role != CustomUser.Role.TEACHER:
            return Response({"teacher": "Les classes peuvent être assignées uniquement à un enseignant."}, status=400)
        if request.method == "GET":
            assignments = TeacherClassAssignment.objects.filter(
                school=self.get_school(), academic_year=year, teacher=teacher,
            ).prefetch_related("subject_links__class_subject")
            conflicts = TeacherAssignmentSubject.objects.filter(
                assignment__school=self.get_school(), assignment__academic_year=year,
            ).exclude(assignment__teacher=teacher).select_related("assignment__teacher", "class_subject")
            return Response({
                "assignments": [{
                    "class_id": assignment.school_class_id,
                    "subject_ids": [link.class_subject.subject_id for link in assignment.subject_links.all()],
                } for assignment in assignments],
                "unavailable_subjects": [{
                    "class_id": link.assignment.school_class_id,
                    "subject_id": link.class_subject.subject_id,
                    "teacher_name": link.assignment.teacher.get_full_name(),
                } for link in conflicts],
            })
        self.ensure_manager()
        requested = request.data.get("assignments", [])
        class_ids = [item.get("class_id") for item in requested]
        if len(class_ids) != len(set(class_ids)):
            return Response({"assignments": "Une classe ne peut apparaître qu’une seule fois."}, status=400)
        classes = list(SchoolClass.objects.filter(
            id__in=class_ids, school=self.get_school(), academic_year=year, is_active=True,
        ))
        if len(classes) != len(class_ids):
            return Response({"assignments": "Une ou plusieurs classes sont invalides."}, status=400)
        class_map = {school_class.id: school_class for school_class in classes}
        prepared = []
        selected_config_ids = []
        teacher_subject_ids = set(teacher.subjects.values_list("id", flat=True))
        for item in requested:
            subject_ids = list(dict.fromkeys(item.get("subject_ids", [])))
            if not subject_ids:
                return Response({"assignments": f"Sélectionnez au moins une matière pour {class_map[item['class_id']].name}."}, status=400)
            configs = list(ClassSubject.objects.filter(school_class_id=item["class_id"], subject_id__in=subject_ids))
            if len(configs) != len(subject_ids):
                return Response({"assignments": "Une matière sélectionnée n’est pas configurée dans cette classe."}, status=400)
            invalid_subjects = [config.subject.name for config in configs if config.subject_id not in teacher_subject_ids]
            if invalid_subjects:
                return Response({"assignments": f"Cet enseignant n’enseigne pas : {', '.join(invalid_subjects)}."}, status=400)
            prepared.append((class_map[item["class_id"]], configs))
            selected_config_ids.extend(config.id for config in configs)
        conflicts = TeacherAssignmentSubject.objects.filter(
            class_subject_id__in=selected_config_ids,
        ).exclude(assignment__teacher=teacher).select_related("assignment__teacher", "class_subject__subject").first()
        if conflicts:
            return Response({"assignments": f"{conflicts.class_subject.subject.name} est déjà enseignée par {conflicts.assignment.teacher.get_full_name()} dans cette classe."}, status=400)
        with transaction.atomic():
            TeacherClassAssignment.objects.filter(school=self.get_school(), academic_year=year, teacher=teacher).delete()
            links = []
            for school_class, configs in prepared:
                assignment = TeacherClassAssignment.objects.create(school=self.get_school(), academic_year=year, teacher=teacher, school_class=school_class)
                links.extend(TeacherAssignmentSubject(assignment=assignment, class_subject=config) for config in configs)
            TeacherAssignmentSubject.objects.bulk_create(links)
        return Response({"assignments": len(prepared)})

    @action(detail=True, methods=["get", "post"], url_path="unavailability")
    def unavailability(self, request, pk=None, school_pk=None):
        teacher = self.get_object()
        year = self.get_selected_academic_year()
        if teacher.role != CustomUser.Role.TEACHER:
            return Response({"teacher": "Les indisponibilités concernent uniquement les enseignants."}, status=400)
        queryset = TeacherUnavailability.objects.filter(school=self.get_school(), academic_year=year, teacher=teacher)
        if request.method == "GET":
            return Response([{
                "id": item.id, "day": item.day, "day_label": item.get_day_display(), "all_day": item.all_day,
                "start_time": item.start_time.strftime("%H:%M") if item.start_time else None,
                "end_time": item.end_time.strftime("%H:%M") if item.end_time else None,
            } for item in queryset])
        self.ensure_manager()
        slots = request.data.get("slots", [])
        normalized = []
        by_day = {}
        for index, slot in enumerate(slots, start=1):
            try:
                day = int(slot.get("day"))
                if day not in range(7): raise ValueError
                all_day = bool(slot.get("all_day"))
                start = end = None
                if not all_day:
                    start = datetime.strptime(str(slot.get("start_time")), "%H:%M").time()
                    end = datetime.strptime(str(slot.get("end_time")), "%H:%M").time()
                    if start >= end: raise ValueError
            except (TypeError, ValueError):
                return Response({"slots": f"Plage invalide à la ligne {index}."}, status=400)
            existing = by_day.setdefault(day, [])
            if existing and (all_day or any(item[0] for item in existing)):
                return Response({"slots": f"Les indisponibilités du jour {day + 1} se chevauchent."}, status=400)
            if not all_day and any(not (end <= item[1] or start >= item[2]) for item in existing):
                return Response({"slots": f"Les indisponibilités du jour {day + 1} se chevauchent."}, status=400)
            existing.append((all_day, start, end))
            normalized.append((day, all_day, start, end))
        with transaction.atomic():
            queryset.delete()
            TeacherUnavailability.objects.bulk_create([
                TeacherUnavailability(school=self.get_school(), academic_year=year, teacher=teacher, day=day, all_day=all_day, start_time=start, end_time=end)
                for day, all_day, start, end in normalized
            ])
        return Response({"slots": len(normalized)})


class SubjectViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = SubjectSerializer

    def get_queryset(self):
        return Subject.objects.filter(school=self.get_school(), is_active=True)

    def perform_create(self, serializer):
        self.ensure_manager()
        serializer.save(school=self.get_school())

    def perform_update(self, serializer):
        self.ensure_manager()
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_manager()
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class AcademicYearViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = AcademicYearSerializer

    def get_queryset(self):
        return AcademicYear.objects.filter(school=self.get_school()).prefetch_related("sessions__classes")

    def perform_create(self, serializer):
        self.ensure_manager()
        with transaction.atomic():
            if serializer.validated_data.get("is_active"):
                current = AcademicYear.objects.filter(
                    school=self.get_school(), is_active=True
                ).first()
                if current:
                    raise serializers.ValidationError({
                        "is_active": f"Clôturez d’abord l’année académique active « {current.name} ».",
                    })
            serializer.save(school=self.get_school())

    def perform_update(self, serializer):
        self.ensure_manager()
        with transaction.atomic():
            if (
                serializer.instance.is_active
                and "is_active" in serializer.validated_data
                and not serializer.validated_data["is_active"]
            ):
                raise serializers.ValidationError({
                    "is_active": "Une année active doit être clôturée pour devenir inactive.",
                })
            if serializer.validated_data.get("is_active") and not serializer.instance.is_active:
                current = AcademicYear.objects.filter(
                    school=self.get_school(), is_active=True
                ).exclude(pk=serializer.instance.pk).first()
                if current:
                    raise serializers.ValidationError({
                        "is_active": f"Clôturez d’abord l’année académique active « {current.name} ».",
                    })
            serializer.save()

    def perform_destroy(self, instance):
        self.ensure_manager()
        if instance.is_active:
            raise serializers.ValidationError({"year": "Une année active ne peut pas être supprimée."})
        instance.delete()

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None, school_pk=None):
        self.ensure_manager()
        academic_year = self.get_object()
        if academic_year.is_closed:
            return Response({"detail": "Cette année est déjà clôturée."}, status=400)
        with transaction.atomic():
            academic_year.is_closed = True
            academic_year.is_active = False
            academic_year.save(update_fields=["is_closed", "is_active"])
            academic_year.sessions.update(is_active=False)
        return Response(self.get_serializer(academic_year).data)


class AcademicSessionListView(SchoolScopedMixin, APIView):
    def get_academic_year(self, year_pk):
        try:
            return AcademicYear.objects.get(pk=year_pk, school=self.get_school())
        except AcademicYear.DoesNotExist:
            raise serializers.ValidationError({"academic_year": "Année académique introuvable."})

    def get(self, request, school_pk, year_pk):
        year = self.get_academic_year(year_pk)
        return Response(AcademicSessionSerializer(year.sessions.all(), many=True).data)

    def post(self, request, school_pk, year_pk):
        self.ensure_manager()
        year = self.get_academic_year(year_pk)
        if not year.is_active or year.is_closed:
            raise serializers.ValidationError({"academic_year": "Les sessions ne peuvent être créées que dans l’année académique active."})
        serializer = AcademicSessionSerializer(data={**request.data, "is_active": True}, context={"academic_year": year})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(academic_year=year)
        return Response(serializer.data, status=201)


class AcademicSessionDetailView(AcademicSessionListView):
    def get_object(self, year_pk, pk):
        year = self.get_academic_year(year_pk)
        try:
            return year.sessions.get(pk=pk), year
        except AcademicSession.DoesNotExist:
            raise serializers.ValidationError({"session": "Session académique introuvable."})

    def patch(self, request, school_pk, year_pk, pk):
        self.ensure_manager()
        session, year = self.get_object(year_pk, pk)
        serializer = AcademicSessionSerializer(session, data=request.data, partial=True, context={"academic_year": year})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data)

    def delete(self, request, school_pk, year_pk, pk):
        return Response({"detail": "Une session doit être clôturée et non supprimée."}, status=405)

    def post(self, request, school_pk, year_pk, pk):
        self.ensure_manager()
        session, _ = self.get_object(year_pk, pk)
        if session.is_closed:
            return Response({"detail": "Cette session est déjà clôturée."}, status=400)
        session.is_closed = True
        session.is_active = False
        session.save(update_fields=["is_closed", "is_active"])
        return Response(AcademicSessionSerializer(session).data)


class StudentEnrollmentViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = StudentEnrollmentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_academic_year(self):
        year_id = self.request.headers.get("X-Academic-Year-ID")
        if not year_id:
            raise serializers.ValidationError({"academic_year": "Sélectionnez une année académique."})
        try:
            academic_year = AcademicYear.objects.get(pk=year_id, school=self.get_school())
        except (AcademicYear.DoesNotExist, ValueError):
            raise serializers.ValidationError({"academic_year": "Année académique invalide."})
        return academic_year

    def get_queryset(self):
        return StudentEnrollment.objects.filter(
            school=self.get_school(),
            academic_year=self.get_academic_year(),
            status=StudentEnrollment.Status.ACTIVE,
        ).select_related("student", "guardian", "academic_year", "level", "school_class")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(school=self.get_school(), academic_year=self.get_academic_year())
        return context

    def perform_create(self, serializer):
        self.ensure_manager()
        academic_year = self.get_academic_year()
        if not academic_year.is_active or academic_year.is_closed:
            raise serializers.ValidationError({
                "academic_year": "Les inscriptions sont autorisées uniquement pour l’année active non clôturée."
            })
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_manager()
        instance.status = StudentEnrollment.Status.CANCELLED
        instance.save(update_fields=["status"])

    def perform_update(self, serializer):
        self.ensure_manager()
        serializer.save()

    def eligible_unassigned_queryset(self):
        return self.get_queryset().filter(
            school_class__isnull=True,
        ).exclude(
            student__student_status__in=[
                CustomUser.StudentStatus.DROPPED_OUT,
                CustomUser.StudentStatus.BACHELOR,
            ]
        )

    @action(detail=False, methods=["get"], url_path="guardian-lookup")
    def guardian_lookup(self, request, school_pk=None):
        try:
            phone = normalize_togolese_phone(request.query_params.get("phone"))
        except serializers.ValidationError as exc:
            return Response({"phone": exc.detail}, status=400)
        guardian = CustomUser.objects.filter(role=CustomUser.Role.PARENT, phone=phone).first()
        if guardian is None:
            return Response({"found": False, "phone": phone})
        return Response({
            "found": True,
            "id": guardian.pk,
            "phone": guardian.phone,
            "last_name": guardian.last_name,
            "first_names": guardian.first_name,
            "profession": guardian.profession,
        })

    @action(detail=False, methods=["get"], url_path="unassigned")
    def unassigned(self, request, school_pk=None):
        queryset = self.eligible_unassigned_queryset().order_by(
            "level__order", "series", "student__last_name", "student__first_name",
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["post"], url_path="auto-assign")
    def auto_assign(self, request, school_pk=None):
        self.ensure_manager()
        school = self.get_school()
        academic_year = self.get_academic_year()
        if not academic_year.is_active or academic_year.is_closed:
            return Response({"academic_year": "L’année académique doit être active."}, status=400)

        students = list(self.eligible_unassigned_queryset())
        if not students:
            return Response({"message": "Aucun élève éligible sans classe.", "assigned": 0, "warnings": []})

        classes = list(SchoolClass.objects.filter(
            school=school, academic_year=academic_year, is_active=True,
        ).annotate(
            effectif=Count(
                "student_enrollments",
                filter=Q(student_enrollments__status=StudentEnrollment.Status.ACTIVE),
                distinct=True,
            ),
        ).select_related("level"))

        def group_key(level_id, series):
            return level_id, (series or "").strip().casefold()

        def natural_class_key(school_class):
            return tuple(
                (token.isdigit(), int(token) if token.isdigit() else token.casefold())
                for token in re.split(r"(\d+)", school_class.group)
                if token
            )

        classes_by_group = {}
        for school_class in classes:
            classes_by_group.setdefault(group_key(school_class.level_id, school_class.series), []).append(school_class)
        for grouped_classes in classes_by_group.values():
            grouped_classes.sort(key=natural_class_key)

        students_by_group = {}
        for enrollment in students:
            students_by_group.setdefault(group_key(enrollment.level_id, enrollment.series), []).append(enrollment)

        warnings = []
        assignments = []
        summary = []

        def student_rank(enrollment):
            average = float(enrollment.previous_average) if enrollment.previous_average is not None else -1.0
            birth_ordinal = enrollment.student.date_of_birth.toordinal() if enrollment.student.date_of_birth else 0
            return -average, -birth_ordinal, enrollment.pk

        for key, grouped_students in students_by_group.items():
            grouped_classes = classes_by_group.get(key, [])
            level_name = grouped_students[0].level.name if grouped_students[0].level else "Niveau inconnu"
            series_label = grouped_students[0].series or "sans série"
            group_label = f"{level_name} — {series_label}"
            if not grouped_classes:
                warnings.append(f"{group_label} : aucune classe active correspondante pour {len(grouped_students)} élève(s).")
                continue

            additions = {school_class.pk: 0 for school_class in grouped_classes}
            capacity = {
                school_class.pk: max(0, school_class.maximum_capacity - school_class.effectif)
                for school_class in grouped_classes
            }
            assignable_count = min(len(grouped_students), sum(capacity.values()))
            for _ in range(assignable_count):
                candidates = [
                    school_class for school_class in grouped_classes
                    if additions[school_class.pk] < capacity[school_class.pk]
                ]
                selected = min(candidates, key=lambda school_class: (
                    school_class.effectif + additions[school_class.pk],
                    (school_class.effectif + additions[school_class.pk]) / school_class.maximum_capacity,
                    natural_class_key(school_class),
                ))
                additions[selected.pk] += 1

            ranked_students = sorted(grouped_students, key=student_rank)
            excellent_students = [
                enrollment for enrollment in ranked_students
                if enrollment.previous_average is not None and enrollment.previous_average >= 16
            ]
            allocated_ids = set()
            class_allocations = {school_class.pk: [] for school_class in grouped_classes}
            reserve_rounds = min(3, len(excellent_students) // len(grouped_classes))
            excellent_index = 0
            for _ in range(reserve_rounds):
                for school_class in grouped_classes:
                    if excellent_index >= len(excellent_students):
                        break
                    if len(class_allocations[school_class.pk]) >= additions[school_class.pk]:
                        continue
                    enrollment = excellent_students[excellent_index]
                    excellent_index += 1
                    class_allocations[school_class.pk].append(enrollment)
                    allocated_ids.add(enrollment.pk)

            remaining_students = [enrollment for enrollment in ranked_students if enrollment.pk not in allocated_ids]
            remaining_index = 0
            for school_class in grouped_classes:
                remaining_places = additions[school_class.pk] - len(class_allocations[school_class.pk])
                selected_students = remaining_students[remaining_index:remaining_index + remaining_places]
                class_allocations[school_class.pk].extend(selected_students)
                remaining_index += len(selected_students)

            assigned_in_group = 0
            for school_class in grouped_classes:
                for enrollment in class_allocations[school_class.pk]:
                    enrollment.school_class = school_class
                    assignments.append(enrollment)
                    assigned_in_group += 1
            summary.append({
                "group": group_label,
                "assigned": assigned_in_group,
                "classes": [
                    {
                        "id": school_class.pk,
                        "name": school_class.name,
                        "added": len(class_allocations[school_class.pk]),
                        "total": school_class.effectif + len(class_allocations[school_class.pk]),
                        "capacity": school_class.maximum_capacity,
                    }
                    for school_class in grouped_classes
                ],
            })
            if assigned_in_group < len(grouped_students):
                warnings.append(
                    f"{group_label} : capacité insuffisante, {len(grouped_students) - assigned_in_group} élève(s) restent sans classe."
                )

        with transaction.atomic():
            StudentEnrollment.objects.bulk_update(assignments, ["school_class"])

        return Response({
            "message": f"{len(assignments)} élève(s) réparti(s) automatiquement.",
            "assigned": len(assignments),
            "remaining": len(students) - len(assignments),
            "warnings": warnings,
            "summary": summary,
        })

    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser, FormParser])
    def import_file(self, request, school_pk=None):
        self.ensure_manager()
        school = self.get_school()
        academic_year = self.get_academic_year()
        if not academic_year.is_active or academic_year.is_closed:
            return Response({"academic_year": "L’année académique doit être active."}, status=400)
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"file": "Sélectionnez un fichier Excel ou CSV."}, status=400)

        try:
            if uploaded_file.name.lower().endswith(".csv"):
                content = uploaded_file.read().decode("utf-8-sig")
                rows = list(csv.DictReader(io.StringIO(content), delimiter=";" if ";" in content.splitlines()[0] else ","))
            elif uploaded_file.name.lower().endswith(".xlsx"):
                try:
                    from openpyxl import load_workbook
                except ImportError:
                    rows = read_xlsx_without_dependency(uploaded_file)
                else:
                    sheet = load_workbook(uploaded_file, read_only=True, data_only=True).active
                    values = list(sheet.iter_rows(values_only=True))
                    if not values:
                        rows = []
                    else:
                        headers = [str(value or "").strip() for value in values[0]]
                        rows = [dict(zip(headers, values_row)) for values_row in values[1:] if any(value not in (None, "") for value in values_row)]
            else:
                return Response({"file": "Formats acceptés : .xlsx et .csv."}, status=400)
        except (UnicodeDecodeError, ValueError, OSError, zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
            return Response({"file": f"Impossible de lire le fichier : {exc}"}, status=400)

        aliases = {
            "matricule": "enrollment_number", "numero_matricule": "enrollment_number",
            "nom": "last_name", "prenoms": "first_names", "prénoms": "first_names",
            "genre": "gender", "date_naissance": "date_of_birth", "date_de_naissance": "date_of_birth",
            "cycle": "cycle", "niveau": "level", "serie": "series", "série": "series", "statut": "student_status", "status": "student_status", "classe": "school_class", "nom_classe": "school_class", "nom_de_la_classe": "school_class",
            "allergie": "health_information", "allergies": "health_information",
            "souci_de_sante": "health_information", "soucis_de_sante": "health_information", "probleme_de_sante": "health_information",
            "informations_de_sante": "health_information", "allergies_et_soucis_de_sante": "health_information",
            "moyenne": "previous_average", "moyenne_precedente": "previous_average",
            "moyenne_annee_ecoulee": "previous_average", "moyenne_scolaire": "previous_average",
            "moyenne_scolaire_de_l_annee_ecoulee": "previous_average",
            "telephone_tuteur": "guardian_phone", "numero_tuteur": "guardian_phone",
            "nom_tuteur": "guardian_last_name", "prenom_tuteur": "guardian_first_names",
            "prenoms_tuteur": "guardian_first_names", "profession_tuteur": "guardian_profession",
        }
        normalized_rows = []
        errors = []
        seen_numbers = set()
        next_sequence = StudentEnrollment.objects.filter(school=school).count() + 1

        for index, source_row in enumerate(rows, start=2):
            row = {aliases.get(slugify(str(key)).replace("-", "_"), slugify(str(key)).replace("-", "_")): value for key, value in source_row.items()}
            level_name = str(row.get("level") or "").strip()
            level = SchoolLevel.objects.filter(school=school, name__iexact=level_name, is_active=True).first()
            cycle_value = slugify(str(row.get("cycle") or "").strip())
            cycle_map = {"primaire": SchoolLevel.Stage.PRIMARY, "college": SchoolLevel.Stage.MIDDLE, "lycee": SchoolLevel.Stage.HIGH}
            selected_cycle = cycle_map.get(cycle_value)
            class_name = str(row.get("school_class") or "").strip()
            school_class = SchoolClass.objects.filter(
                school=school, academic_year=academic_year, group__iexact=class_name, is_active=True,
            ).first() if class_name else None
            series = str(row.get("series") or "").strip()
            student_status = slugify(str(row.get("student_status") or "nouveau").strip()) or "nouveau"
            if not series and school_class:
                series = school_class.series
            number = str(row.get("enrollment_number") or "").strip().upper().replace(" ", "")
            if not number:
                while True:
                    number = f"{academic_year.start_date.year}-{next_sequence:04d}"
                    next_sequence += 1
                    if number not in seen_numbers and not StudentEnrollment.objects.filter(school=school, enrollment_number__iexact=number).exists():
                        break
            gender_value = str(row.get("gender") or "").strip().lower()
            gender = {"m": "M", "masculin": "M", "f": "F", "feminin": "F", "féminin": "F"}.get(gender_value, "")
            birth_date = row.get("date_of_birth")
            if isinstance(birth_date, (datetime, date)):
                birth_date = birth_date.strftime("%Y-%m-%d")
            payload = {
                "enrollment_number": number,
                "last_name": str(row.get("last_name") or "").strip(),
                "first_names": str(row.get("first_names") or "").strip(),
                "gender": gender,
                "date_of_birth": str(birth_date or "").strip(),
                "health_information": str(row.get("health_information") or "").strip(),
                "level": level.pk if level else None,
                "series": series,
                "student_status": student_status,
                "previous_average": str(row.get("previous_average") or "").strip().replace(",", ".") or None,
                "guardian_phone": str(row.get("guardian_phone") or "").strip(),
                "guardian_last_name": str(row.get("guardian_last_name") or "").strip(),
                "guardian_first_names": str(row.get("guardian_first_names") or "").strip(),
                "guardian_profession": str(row.get("guardian_profession") or "").strip(),
                "school_class": school_class.pk if school_class else None,
            }
            import_rule_errors = {}
            if not selected_cycle:
                import_rule_errors["cycle"] = ["Cycle obligatoire ou invalide. Choix : Primaire, Collège ou Lycée."]
            elif level and level.stage != selected_cycle:
                import_rule_errors["cycle"] = [f"Le niveau « {level_name} » appartient au cycle {level.get_stage_display()}, pas au cycle indiqué."]
            if selected_cycle in (SchoolLevel.Stage.PRIMARY, SchoolLevel.Stage.MIDDLE) and series:
                import_rule_errors["serie"] = [f"Le cycle {'Primaire' if selected_cycle == SchoolLevel.Stage.PRIMARY else 'Collège'} ne doit pas avoir de série."]
            if number.casefold() in seen_numbers:
                errors.append({"ligne": index, "erreurs": {"matricule": ["Matricule répété dans le fichier."]}})
                continue
            seen_numbers.add(number.casefold())
            serializer = self.get_serializer(data=payload)
            if serializer.is_valid():
                row_errors = dict(import_rule_errors)
                if class_name and not school_class:
                    row_errors["classe"] = [f"La classe « {class_name} » n’existe pas dans cette école pour l’année {academic_year.name}. Vérifiez son nom exact."]
                elif school_class and level and school_class.level_id != level.id:
                    row_errors["classe"] = [f"La classe « {class_name} » appartient au niveau {school_class.level.name}, pas au niveau {level_name}."]
                if row_errors:
                    errors.append({"ligne": index, "erreurs": row_errors})
                else:
                    normalized_rows.append(serializer)
            else:
                row_errors = {**dict(serializer.errors), **import_rule_errors}
                if not level:
                    row_errors["niveau"] = [f"Niveau « {level_name} » introuvable dans cette école."]
                if class_name and not school_class:
                    row_errors["classe"] = [f"La classe « {class_name} » n’existe pas dans cette école pour l’année {academic_year.name}. Vérifiez son nom exact."]
                elif school_class and level and school_class.level_id != level.id:
                    row_errors["classe"] = [f"La classe « {class_name} » appartient au niveau {school_class.level.name}, pas au niveau {level_name}."]
                errors.append({"ligne": index, "erreurs": row_errors})

        if not rows:
            return Response({"file": "Le fichier ne contient aucun élève."}, status=400)
        if errors:
            return Response({
                "message": "Import annulé : aucune donnée du fichier n’a été enregistrée. Corrigez les lignes indiquées puis réessayez.",
                "errors": errors,
            }, status=400)

        with transaction.atomic():
            enrollments = [serializer.save() for serializer in normalized_rows]
        return Response({
            "message": f"{len(enrollments)} élève(s) importé(s) avec succès.",
            "count": len(enrollments),
            "enrollments": self.get_serializer(enrollments, many=True).data,
        }, status=201)


class EnrollmentNumberSuggestionView(SchoolScopedMixin, APIView):
    def get(self, request, school_pk):
        school = self.get_school()
        year_id = request.headers.get("X-Academic-Year-ID")
        try:
            academic_year = AcademicYear.objects.get(pk=year_id, school=school)
        except (AcademicYear.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Sélectionnez une année académique valide."}, status=400)
        sequence = StudentEnrollment.objects.filter(school=school).count() + 1
        while True:
            number = f"{academic_year.start_date.year}-{sequence:04d}"
            if not StudentEnrollment.objects.filter(
                school=school, enrollment_number__iexact=number
            ).exists():
                return Response({"enrollment_number": number})
            sequence += 1


class SchoolLevelViewSet(SchoolScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolLevelSerializer

    def get_queryset(self):
        return SchoolLevel.objects.filter(school=self.get_school(), is_active=True)


class SchoolClassViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = SchoolClassSerializer

    def get_academic_year(self):
        year_id = self.request.headers.get("X-Academic-Year-ID")
        try:
            return AcademicYear.objects.get(pk=year_id, school=self.get_school())
        except (AcademicYear.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"academic_year": "Sélectionnez une année académique valide."})

    def get_queryset(self):
        queryset = SchoolClass.objects.filter(school=self.get_school(), academic_year=self.get_academic_year())
        if self.request.query_params.get("include_inactive", "").lower() not in {"1", "true", "yes"}:
            queryset = queryset.filter(is_active=True)
        return queryset.annotate(
            effectif=Count("student_enrollments", filter=Q(student_enrollments__status=StudentEnrollment.Status.ACTIVE), distinct=True),
        ).select_related("level", "academic_year", "homeroom_teacher").prefetch_related("subject_configurations__subject")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(school=self.get_school(), academic_year=self.get_academic_year())
        return context

    def perform_create(self, serializer):
        self.ensure_manager()
        year = self.get_academic_year()
        if not year.is_active or year.is_closed:
            raise serializers.ValidationError({"academic_year": "Les classes peuvent être créées uniquement dans l’année active."})
        serializer.save(school=self.get_school(), academic_year=year)

    def perform_update(self, serializer):
        self.ensure_manager()
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_manager()
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class OwnerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [IsSuperUser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.Role.OWNER, is_archived=False)

    def perform_create(self, serializer):
        serializer.save(role=CustomUser.Role.OWNER)
