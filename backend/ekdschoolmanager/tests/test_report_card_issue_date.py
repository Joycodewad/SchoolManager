"""Date d'établissement portée par les bulletins.

Le pied du bulletin annonce « fait à …, le … ». Cette date est choisie par la
direction au moment de générer — la remise aux familles ne tombe pas forcément
le jour du calcul — puis figée sur chaque bulletin écrit.
"""

from datetime import date

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.reportcard_pdf import footer_block, official_footer
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    ClassSubject,
    CustomUser,
    GradeLine,
    GradeScheme,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
)


class ReportCardIssueDateTests(APITestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="censeur", password="x", role=CustomUser.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Lycée de Lomé", code="lycee-lome", owner=self.staff, city="Lomé",
        )
        SchoolMembership.objects.create(
            school=self.school, user=self.staff,
            role=CustomUser.Role.ADMIN, is_active=True,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        level = SchoolLevel.objects.filter(
            school=self.school, stage=SchoolLevel.Stage.HIGH,
        ).first()
        self.school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=level, group="TC4",
        )
        self.session = AcademicSession.objects.create(
            academic_year=self.year, name="Trimestre 1", label="T1",
            start_date=date(2025, 10, 1), end_date=date(2025, 12, 20), is_active=True,
        )
        self.session.classes.add(self.school_class)

        subject = Subject.objects.create(school=self.school, name="Mathématiques")
        ClassSubject.objects.create(
            school_class=self.school_class, subject=subject,
            coefficient=4, weekly_hours=4,
        )
        scheme = GradeScheme.objects.create(
            session=self.session,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        GradeLine.objects.create(scheme=scheme, name="Devoir 1", max_score=20, order=1)

        student = CustomUser.objects.create_user(username="eleve1", password="x")
        student.first_name, student.last_name = "Kokou", "ODOH"
        student.save()
        StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=self.school_class, level=level,
            enrollment_number="2025TC4003", status=StudentEnrollment.Status.ACTIVE,
        )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}
        self.url = (
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/generate/"
        )

    def generate(self, **payload):
        return self.client.post(
            self.url, {"scope": "school", **payload}, format="json", **self.headers,
        )

    def test_la_date_choisie_est_figee_sur_les_bulletins(self):
        response = self.generate(issued_on="2026-01-15")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            set(ReportCard.objects.values_list("issued_on", flat=True)),
            {date(2026, 1, 15)},
        )

    def test_une_regeneration_remplace_la_date(self):
        self.generate(issued_on="2026-01-15")
        self.generate(issued_on="2026-02-03")
        self.assertEqual(
            set(ReportCard.objects.values_list("issued_on", flat=True)),
            {date(2026, 2, 3)},
        )

    def test_sans_date_choisie_le_jour_de_generation_fait_foi(self):
        self.generate()
        self.assertEqual(
            set(ReportCard.objects.values_list("issued_on", flat=True)),
            {date.today()},
        )

    def test_une_date_illisible_est_refusee(self):
        response = self.generate(issued_on="15/01/2026")
        self.assertEqual(response.status_code, 400)
        self.assertIn("issued_on", response.data)
        self.assertFalse(ReportCard.objects.exists())

    def test_la_date_est_imprimee_au_pied_du_bulletin(self):
        """Le PDF remplace la ligne de pointillés par la date retenue."""
        self.generate(issued_on="2026-01-15")
        export = self.client.get(
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/export/?scope=school",
            **self.headers,
        )
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "application/pdf")

    def test_le_pied_officiel_porte_la_date_retenue(self):
        """La maquette officielle remplace ses pointillés par la date."""
        _, _, signatures = official_footer(
            {"city": "Amou-Oblo"}, "", issued_on="15 janvier 2026",
        )
        printed = self.cell_text(signatures)
        self.assertIn("AMOU-OBLO, le 15 janvier 2026", printed)
        self.assertNotIn("……", printed)

    def test_le_pied_officiel_garde_ses_pointilles_sans_date(self):
        """Un bulletin d'avant le champ se remplit encore à la main."""
        _, _, signatures = official_footer({"city": "Amou-Oblo"}, "")
        self.assertIn("AMOU-OBLO, le ……", self.cell_text(signatures))

    def test_le_pied_standard_porte_aussi_la_date(self):
        table = footer_block({"city": "Lomé"}, "", issued_on="15 janvier 2026")
        self.assertIn("Fait à Lomé, le 15 janvier 2026", self.cell_text(table))

    @staticmethod
    def cell_text(table):
        """Texte des paragraphes d'un tableau ReportLab, mis bout à bout.

        Une cellule peut empiler plusieurs flowables — titre, signature, nom —
        d'où la descente dans les listes.
        """
        def walk(node):
            if isinstance(node, (list, tuple)):
                return " ".join(walk(item) for item in node)
            return getattr(node, "text", "")

        return walk(table._cellvalues)
