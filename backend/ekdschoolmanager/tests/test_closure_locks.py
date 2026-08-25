"""Verrous d'écriture posés par la clôture, vus depuis l'API.

Une session close reste lisible : ce sont les écritures qui sont refusées.
Discipline et appels ne connaissent pas la session — c'est leur date qui les
rattache à la période, d'où les cas « dans la période » / « hors période ».
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.closures import close_session
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    AttendanceSession,
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


class ClosureLockTests(APITestCase):
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
        self.level = SchoolLevel.objects.filter(
            school=self.school, stage=SchoolLevel.Stage.HIGH,
        ).first()
        self.school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=self.level, group="TC4",
        )
        self.session = AcademicSession.objects.create(
            academic_year=self.year, name="Trimestre 1", label="T1",
            start_date=date(2025, 10, 1), end_date=date(2025, 12, 20), is_active=True,
        )
        self.session.classes.add(self.school_class)

        subject = Subject.objects.create(school=self.school, name="Mathématiques")
        self.class_subject = ClassSubject.objects.create(
            school_class=self.school_class, subject=subject,
            coefficient=Decimal("4"), weekly_hours=4,
        )
        self.scheme = GradeScheme.objects.create(
            session=self.session,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        self.line = GradeLine.objects.create(
            scheme=self.scheme, name="Devoir 1", max_score=Decimal("20"), order=1,
        )
        student = CustomUser.objects.create_user(username="eleve1", password="x")
        student.first_name, student.last_name = "Kokou", "ODOH"
        student.save()
        self.enrollment = StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=self.school_class, level=self.level,
            enrollment_number="2025TC4003", status=StudentEnrollment.Status.ACTIVE,
        )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}

    # ── URL helpers ──

    def grade_sheet_url(self):
        return (
            f"/api/schools/{self.school.id}/grades/sessions/{self.session.id}"
            f"/subjects/{self.class_subject.id}/"
        )

    def close(self):
        close_session(self.session, user=self.staff)
        self.session.refresh_from_db()

    # ── Notes ──

    def test_saisie_de_notes_refusee_apres_cloture(self):
        self.close()
        response = self.client.post(
            self.grade_sheet_url(),
            {"grades": [{
                "enrollment": self.enrollment.id,
                "line": self.line.id,
                "score": "15",
            }]},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    def test_lecture_des_notes_reste_ouverte_apres_cloture(self):
        """Le point de la clôture : figer, pas masquer."""
        self.close()
        response = self.client.get(self.grade_sheet_url(), **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["students"]), 1)

    def test_session_close_reste_listee_dans_les_contextes(self):
        self.close()
        response = self.client.get(
            f"/api/schools/{self.school.id}/grades/contexts/", **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        sessions = {row["id"]: row for row in response.data["sessions"]}
        self.assertIn(self.session.id, sessions)
        self.assertTrue(sessions[self.session.id]["is_closed"])

    def test_bareme_verrouille_apres_cloture(self):
        self.close()
        response = self.client.put(
            f"/api/schools/{self.school.id}/grades/sessions/{self.session.id}/scheme/",
            {"calculation_method": "equal", "lines": [
                {"name": "Devoir 1", "max_score": "20", "order": 1},
            ]},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    # ── Discipline ──

    def test_discipline_refusee_dans_la_periode_close(self):
        self.close()
        response = self.client.post(
            f"/api/schools/{self.school.id}/discipline/records/",
            {
                "enrollment": self.enrollment.id,
                "entry_type": "retard",
                "occurred_on": "2025-11-12",
                "late_hours": "2",
            },
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    def test_discipline_acceptee_hors_periode_close(self):
        self.close()
        response = self.client.post(
            f"/api/schools/{self.school.id}/discipline/records/",
            {
                "enrollment": self.enrollment.id,
                "entry_type": "retard",
                "occurred_on": "2026-02-10",
                "late_hours": "2",
            },
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 201)

    # ── Appels ──

    def test_appel_refuse_dans_la_periode_close(self):
        self.close()
        response = self.client.post(
            f"/api/schools/{self.school.id}/attendance/sessions/",
            {
                "school_class": self.school_class.id,
                "taken_on": "2025-11-13",
                "records": [{
                    "enrollment": self.enrollment.id, "status": "absent",
                }],
            },
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    def test_appel_accepte_hors_periode_close(self):
        self.close()
        response = self.client.post(
            f"/api/schools/{self.school.id}/attendance/sessions/",
            {
                "school_class": self.school_class.id,
                "taken_on": "2026-02-10",
                "records": [{
                    "enrollment": self.enrollment.id, "status": "absent",
                }],
            },
            format="json", **self.headers,
        )
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(
            AttendanceSession.objects.filter(taken_on=date(2026, 2, 10)).exists(),
        )

    # ── Bulletins ──

    def test_regeneration_globale_permise_tant_que_la_session_est_ouverte(self):
        """Une session ouverte se régénère autant de fois qu'il le faut."""
        url = f"/api/schools/{self.school.id}/report-cards/sessions/{self.session.id}/generate/"
        first = self.client.post(url, {"scope": "school"}, format="json", **self.headers)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertIn("générés", first.data["detail"])

        second = self.client.post(url, {"scope": "school"}, format="json", **self.headers)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertIn("régénérés", second.data["detail"])
        self.assertEqual(second.data["written"], first.data["written"])

    def test_regeneration_de_bulletins_refusee_apres_cloture(self):
        self.close()
        response = self.client.post(
            f"/api/schools/{self.school.id}/report-cards/sessions/{self.session.id}/generate/",
            {"scope": "school"}, format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    # ── Endpoint de clôture ──

    def test_endpoint_de_cloture_renvoie_les_compteurs(self):
        response = self.client.post(
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}"
            f"/sessions/{self.session.id}/close/",
            {}, format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_closed"])
        self.assertEqual(response.data["closure"]["report_cards"], 1)

    def test_deuxieme_cloture_refusee_par_l_api(self):
        url = (
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}"
            f"/sessions/{self.session.id}/close/"
        )
        self.client.post(url, {}, format="json", **self.headers)
        response = self.client.post(url, {}, format="json", **self.headers)
        self.assertEqual(response.status_code, 400)
