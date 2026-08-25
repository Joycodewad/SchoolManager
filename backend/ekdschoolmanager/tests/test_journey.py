"""Parcours d'un élève : recherche puis dossier complet.

Le dossier doit rester lisible après le départ de l'élève — c'est même son
premier usage : retrouver un ancien, avec ses classes, ses moyennes et sa vie
scolaire, des années plus tard.
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    AttendanceRecord,
    AttendanceSession,
    CustomUser,
    DisciplineRecord,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
)


class StudentJourneyTests(APITestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="proviseur", password="x", role=CustomUser.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Lycée d'Amou-Oblo", code="lycee-amou-oblo", owner=self.staff,
        )
        SchoolMembership.objects.create(
            school=self.school, user=self.staff, role=CustomUser.Role.ADMIN, is_active=True,
        )
        self.student = CustomUser.objects.create_user(username="kodjo", password="x")
        self.student.last_name, self.student.first_name = "ABOTSI", "Kodjo Norbert"
        self.student.save()

        self.years, self.enrollments = {}, {}
        for name, start, level_name, group in (
            ("2024-2025", date(2024, 9, 1), "6ème", "6A"),
            ("2025-2026", date(2025, 9, 1), "5ème", "5A"),
        ):
            year = AcademicYear.objects.create(
                school=self.school, name=name, start_date=start,
                end_date=start.replace(year=start.year + 1, month=6, day=30),
            )
            level = SchoolLevel.objects.get(school=self.school, name=level_name)
            school_class = SchoolClass.objects.create(
                school=self.school, academic_year=year, level=level, group=group,
            )
            self.years[name] = year
            self.enrollments[name] = StudentEnrollment.objects.create(
                school=self.school, academic_year=year, student=self.student,
                school_class=school_class, level=level,
                enrollment_number=f"{start.year}-0001",
                status=StudentEnrollment.Status.ACTIVE,
            )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = f"/api/schools/{self.school.id}/students/journey/"

    def add_report_card(self, year_name, session_name, average, rank):
        enrollment = self.enrollments[year_name]
        session = AcademicSession.objects.create(
            academic_year=self.years[year_name], name=session_name, label=session_name,
            start_date=self.years[year_name].start_date,
            end_date=self.years[year_name].end_date, is_active=False, is_closed=True,
        )
        session.classes.add(enrollment.school_class)
        ReportCard.objects.create(
            session=session, enrollment=enrollment, school_class=enrollment.school_class,
            general_average=Decimal(average), rank=rank, payload={},
        )

    # ── Recherche ────────────────────────────────────────────────────────────

    def test_la_recherche_par_nom_trouve_l_eleve(self):
        response = self.client.get(f"{self.url}?q=ABOTSI")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["name"], "Kodjo Norbert ABOTSI")

    def test_la_recherche_par_matricule_trouve_l_eleve(self):
        response = self.client.get(f"{self.url}?q=2025-0001")
        self.assertEqual(len(response.data["results"]), 1)

    def test_un_eleve_inscrit_plusieurs_annees_n_apparait_qu_une_fois(self):
        """Et c'est sa dernière classe qui s'affiche, pas la première."""
        response = self.client.get(f"{self.url}?q=ABOTSI")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["last_class"], "5A")
        self.assertEqual(response.data["results"][0]["last_year"], "2025-2026")

    def test_une_recherche_trop_courte_ne_ratisse_pas_tout(self):
        self.assertEqual(self.client.get(f"{self.url}?q=A").data["results"], [])

    def test_un_eleve_d_une_autre_ecole_n_est_pas_trouve(self):
        other = School.objects.create(
            name="Collège voisin", code="college-voisin", owner=self.staff,
        )
        response = self.client.get(f"/api/schools/{other.id}/students/journey/?q=ABOTSI")
        self.assertEqual(response.data["results"], [])

    # ── Dossier ──────────────────────────────────────────────────────────────

    def test_le_dossier_reprend_toutes_les_annees(self):
        response = self.client.get(f"{self.url}?student={self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [year["academic_year"] for year in response.data["years"]],
            ["2024-2025", "2025-2026"],
        )
        self.assertEqual(
            [year["class"] for year in response.data["years"]], ["6A", "5A"],
        )

    def test_les_moyennes_de_session_et_l_annuelle_sont_reprises(self):
        self.add_report_card("2025-2026", "Premier Trimestre", "12.00", 5)
        self.add_report_card("2025-2026", "Deuxième Trimestre", "14.00", 3)

        response = self.client.get(f"{self.url}?student={self.student.id}")
        year = next(row for row in response.data["years"] if row["academic_year"] == "2025-2026")
        self.assertEqual([row["average"] for row in year["sessions"]], ["12.00", "14.00"])
        self.assertEqual(year["annual_average"], "13.00")

    def test_la_discipline_et_les_appels_sont_compt_s_par_annee(self):
        enrollment = self.enrollments["2025-2026"]
        DisciplineRecord.objects.create(
            school=self.school, academic_year=self.years["2025-2026"], enrollment=enrollment,
            entry_type=DisciplineRecord.EntryType.LATE, occurred_on=date(2026, 2, 10),
            late_hours=Decimal("2"), recorded_by=self.staff,
        )
        session = AttendanceSession.objects.create(
            school=self.school, academic_year=self.years["2025-2026"],
            school_class=enrollment.school_class, taken_on=date(2026, 2, 10),
            taken_by=self.staff,
        )
        AttendanceRecord.objects.create(
            session=session, enrollment=enrollment, status=AttendanceRecord.Status.ABSENT,
        )

        response = self.client.get(f"{self.url}?student={self.student.id}")
        current = next(row for row in response.data["years"] if row["academic_year"] == "2025-2026")
        past = next(row for row in response.data["years"] if row["academic_year"] == "2024-2025")
        self.assertEqual(current["discipline"]["late"]["count"], 1)
        self.assertEqual(current["discipline"]["late"]["hours"], "2.00")
        self.assertEqual(current["attendance"]["absent"], 1)
        # L'année précédente reste vierge : chaque année porte la sienne.
        self.assertEqual(past["discipline"]["late"]["count"], 0)
        self.assertEqual(past["attendance"]["sessions"], 0)

    def test_les_totaux_couvrent_tout_le_parcours(self):
        self.add_report_card("2024-2025", "Premier Trimestre", "11.00", 8)
        self.add_report_card("2025-2026", "Premier Trimestre", "12.00", 5)

        totals = self.client.get(f"{self.url}?student={self.student.id}").data["totals"]
        self.assertEqual(totals["years"], 2)
        self.assertEqual(totals["classes"], ["6A", "5A"])
        self.assertEqual(totals["report_cards"], 2)

    def test_un_eleve_parti_garde_son_dossier(self):
        """Aucune inscription courante, mais le passé reste consultable."""
        self.student.student_status = CustomUser.StudentStatus.BEPC_HOLDER
        self.student.save(update_fields=["student_status"])

        response = self.client.get(f"{self.url}?student={self.student.id}")
        self.assertEqual(response.data["student"]["status_label"], "Titulaire du BEPC")
        self.assertEqual(len(response.data["years"]), 2)

    def test_un_eleve_hors_ecole_est_refuse(self):
        outsider = CustomUser.objects.create_user(username="ailleurs", password="x")
        response = self.client.get(f"{self.url}?student={outsider.id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("student", response.data)
