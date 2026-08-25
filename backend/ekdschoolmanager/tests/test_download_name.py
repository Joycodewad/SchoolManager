"""Nom des bulletins téléchargés.

Un fichier qui arrive dans le dossier « Téléchargements » doit se lire sans
l'ouvrir : la session, l'année, et ce qu'il contient — un élève, une classe ou
tout l'établissement.
"""

from datetime import date
from urllib.parse import quote

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    ClassSubject,
    CustomUser,
    GradeLine,
    GradeScheme,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
)
from ekdschoolmanager.views import ReportCardExportView


class DownloadNameTests(APITestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="proviseur", password="x", role=CustomUser.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Lycée d'Amou-Oblo", code="lycee-amou-oblo", owner=self.staff, city="Amou-Oblo",
        )
        SchoolMembership.objects.create(
            school=self.school, user=self.staff, role=CustomUser.Role.ADMIN, is_active=True,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        level = SchoolLevel.objects.get(school=self.school, name="6ème")
        self.school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=level, group="6A",
        )
        self.session = AcademicSession.objects.create(
            academic_year=self.year, name="Troisième Trimestre", label="T3",
            start_date=date(2026, 4, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        self.session.classes.add(self.school_class)

        subject = Subject.objects.create(school=self.school, name="Mathématiques")
        ClassSubject.objects.create(
            school_class=self.school_class, subject=subject, coefficient=4, weekly_hours=4,
        )
        scheme = GradeScheme.objects.create(
            session=self.session,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        GradeLine.objects.create(scheme=scheme, name="Devoir 1", max_score=20, order=1)

        student = CustomUser.objects.create_user(username="eleve1", password="x")
        student.first_name, student.last_name = "Kodjo Norbert", "ABOTSI"
        student.save()
        self.enrollment = StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=self.school_class, level=level,
            enrollment_number="20256A001", status=StudentEnrollment.Status.ACTIVE,
        )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}
        self.client.post(
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/generate/",
            {"scope": "school", "issued_on": "2026-06-28"}, format="json", **self.headers,
        )

    def export(self, query):
        return self.client.get(
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/export/?{query}", **self.headers,
        )

    def test_un_eleve_donne_un_bulletin_a_son_nom(self):
        response = self.export(f"scope=student&enrollment={self.enrollment.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            quote("Bulletin du Troisième Trimestre 2025-2026 de Kodjo Norbert ABOTSI.pdf"),
            response["Content-Disposition"],
        )

    def test_une_classe_donne_des_bulletins_au_nom_de_la_classe(self):
        response = self.export(f"scope=class&school_class={self.school_class.id}")
        self.assertIn(
            quote("Bulletins du Troisième Trimestre 2025-2026 de 6ème 6A.pdf"),
            response["Content-Disposition"],
        )

    def test_l_etablissement_donne_des_bulletins_a_son_nom(self):
        response = self.export("scope=school")
        self.assertIn(
            quote("Bulletins du Troisième Trimestre 2025-2026 de Lycée d'Amou-Oblo.pdf"),
            response["Content-Disposition"],
        )

    def test_l_en_tete_porte_aussi_une_version_ascii(self):
        """Les clients qui ignorent `filename*` téléchargent quand même."""
        disposition = self.export("scope=school")["Content-Disposition"]
        self.assertIn(
            'filename="Bulletins du Troisieme Trimestre 2025-2026 de Lycee d\'Amou-Oblo.pdf"',
            disposition,
        )

    def test_les_caracteres_interdits_sont_ecartes(self):
        """Une barre oblique dans un nom de classe casserait l'écriture du fichier."""
        response = ReportCardExportView.as_attachment(b"", 'Bulletins 6A/6B "T3".pdf')
        self.assertNotIn("/", response["Content-Disposition"].split("filename=")[1])
        self.assertIn(quote("Bulletins 6A 6B T3 .pdf"), response["Content-Disposition"])
