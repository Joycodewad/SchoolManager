"""Coût en requêtes de l'exposition de la clôture.

`closure` est une OneToOne inverse : lue sans prefetch, elle coûte une requête
par session — et une de plus par `closed_by`. C'est ce qui a fait exploser
`/academic-years/`. Ces tests figent le nombre de requêtes pour que la
régression ne revienne pas silencieusement.
"""

from datetime import date

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.closures import close_session
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    CustomUser,
    GradeLine,
    GradeScheme,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
)
from decimal import Decimal


class ClosureQueryCountTests(APITestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="censeur", password="x", role=CustomUser.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Lycée de Lomé", code="lycee-lome", owner=self.staff,
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

        # Trois trimestres : un clôturé, deux ouverts. Le mélange est ce qui
        # révèle une lecture non mise en cache côté « pas de clôture ».
        self.sessions = []
        for index, (name, start, end) in enumerate([
            ("Trimestre 1", date(2025, 10, 1), date(2025, 12, 20)),
            ("Trimestre 2", date(2026, 1, 5), date(2026, 3, 20)),
            ("Trimestre 3", date(2026, 4, 1), date(2026, 6, 20)),
        ]):
            school_class = SchoolClass.objects.create(
                school=self.school, academic_year=self.year,
                level=level, group=f"TC{index + 1}",
            )
            session = AcademicSession.objects.create(
                academic_year=self.year, name=name, label=name[:2],
                start_date=start, end_date=end, is_active=(index == 0),
            )
            session.classes.add(school_class)
            scheme = GradeScheme.objects.create(
                session=session,
                calculation_method=GradeScheme.CalculationMethod.EQUAL,
                created_by=self.staff,
            )
            GradeLine.objects.create(
                scheme=scheme, name="Devoir 1", max_score=Decimal("20"), order=1,
            )
            self.sessions.append(session)

        close_session(self.sessions[0], user=self.staff)

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_liste_des_annees_ne_fait_pas_de_requete_par_session(self):
        url = f"/api/schools/{self.school.id}/academic-years/"
        with self.assertNumQueries(6):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        sessions = {s["name"]: s for s in response.data[0]["sessions"]}
        self.assertIsNotNone(sessions["Trimestre 1"]["closure"])
        self.assertIsNone(sessions["Trimestre 2"]["closure"])
        self.assertIsNone(sessions["Trimestre 3"]["closure"])

    def test_liste_des_sessions_ne_fait_pas_de_requete_par_session(self):
        url = (
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}/sessions/"
        )
        with self.assertNumQueries(6):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_le_payload_ne_descend_pas_dans_la_liste(self):
        """L'archive peut peser plusieurs Mo : elle reste hors des listes."""
        url = f"/api/schools/{self.school.id}/academic-years/"
        response = self.client.get(url)
        closure = response.data[0]["sessions"][0]["closure"]
        self.assertNotIn("payload", closure)
        self.assertIn("report_cards", closure)
