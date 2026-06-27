import csv
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AcademicPeriod, AcademicYear, CustomUser, School, SchoolLevel, SchoolMembership, StudentEnrollment, Subject
from .serializers import AcademicPeriodSerializer, AcademicYearSerializer, CustomUserSerializer, SchoolLevelSerializer, SchoolMembershipSerializer, SchoolSerializer, StudentEnrollmentSerializer, SubjectSerializer


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
        ).distinct()

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
        return AcademicYear.objects.filter(school=self.get_school()).prefetch_related("periods")

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
            academic_year.periods.update(is_active=False, is_closed=True)
        return Response(self.get_serializer(academic_year).data)


class AcademicPeriodCloseView(SchoolScopedMixin, APIView):
    def post(self, request, school_pk, year_pk, period_pk):
        self.ensure_manager()
        try:
            period = AcademicPeriod.objects.select_related("academic_year").get(
                pk=period_pk,
                academic_year_id=year_pk,
                academic_year__school=self.get_school(),
            )
        except AcademicPeriod.DoesNotExist:
            return Response({"detail": "Période introuvable."}, status=404)
        if period.is_closed:
            return Response({"detail": "Cette période est déjà clôturée."}, status=400)
        if not period.is_active:
            return Response({"detail": "Seule la période active peut être clôturée."}, status=400)
        with transaction.atomic():
            period.is_closed = True
            period.is_active = False
            period.save(update_fields=["is_closed", "is_active"])
            if period.academic_year.is_active:
                next_period = period.academic_year.periods.filter(
                    number__gt=period.number, is_closed=False
                ).order_by("number").first()
                if next_period:
                    next_period.is_active = True
                    next_period.save(update_fields=["is_active"])
        return Response(AcademicPeriodSerializer(period).data)


class StudentEnrollmentViewSet(SchoolScopedMixin, viewsets.ModelViewSet):
    serializer_class = StudentEnrollmentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

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
        ).select_related("student", "academic_year")

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
            "niveau": "level", "adresse": "address",
        }
        normalized_rows = []
        errors = []
        seen_numbers = set()
        next_sequence = StudentEnrollment.objects.filter(school=school).count() + 1

        for index, source_row in enumerate(rows, start=2):
            row = {aliases.get(slugify(str(key)).replace("-", "_"), slugify(str(key)).replace("-", "_")): value for key, value in source_row.items()}
            level_name = str(row.get("level") or "").strip()
            level = SchoolLevel.objects.filter(school=school, name__iexact=level_name, is_active=True).first()
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
                "address": str(row.get("address") or "").strip(),
                "level": level.pk if level else None,
            }
            if number.casefold() in seen_numbers:
                errors.append({"ligne": index, "erreurs": {"matricule": ["Matricule répété dans le fichier."]}})
                continue
            seen_numbers.add(number.casefold())
            serializer = self.get_serializer(data=payload)
            if serializer.is_valid():
                normalized_rows.append(serializer)
            else:
                row_errors = dict(serializer.errors)
                if not level:
                    row_errors["niveau"] = [f"Niveau « {level_name} » introuvable dans cette école."]
                errors.append({"ligne": index, "erreurs": row_errors})

        if not rows:
            return Response({"file": "Le fichier ne contient aucun élève."}, status=400)
        if errors:
            return Response({"message": "Certaines lignes sont invalides.", "errors": errors}, status=400)

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
