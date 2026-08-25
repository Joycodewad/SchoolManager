"""Qui peut quoi dans un établissement.

Deux cercles : la **direction** — propriétaire, administrateur, censeur,
proviseur — qui fait tout, et le **secrétariat** — secrétaire, surveillant —
qui tient la vie scolaire : classes, inscriptions, années et sessions. Le
personnel, les matières, les notes, les finances et l'arrêt des comptes
restent à la direction.

Les cas passent par l'API, seule porte que l'utilisateur pousse réellement.
"""

from datetime import date

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import (
    AcademicYear,
    CustomUser,
    ExpenseCategory,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
)

DIRECTION = ["proprietaire", "admin", "censeur", "proviseur"]
SECRETARIAT = ["secretaire", "surveillant"]


class PermissionMatrixTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="fondateur", password="x", role=CustomUser.Role.OWNER,
        )
        self.school = School.objects.create(
            name="Lycée d'Amou-Oblo", code="lycee-amou-oblo", owner=self.owner,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        self.levels = {
            level.name: level
            for level in SchoolLevel.objects.filter(school=self.school)
        }
        self.category = ExpenseCategory.objects.create(
            school=self.school, name="Fournitures",
        )
        self.base = f"/api/schools/{self.school.id}"

    # ── Fabriques ────────────────────────────────────────────────────────────

    def sign_in(self, role):
        """Ouvre une session pour un membre de l'école tenant ce rôle."""
        user = CustomUser.objects.create_user(
            username=f"u{role}", password="x", role=role,
        )
        if role != CustomUser.Role.OWNER or True:
            SchoolMembership.objects.create(
                school=self.school, user=user, role=role, is_active=True,
            )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return user

    @property
    def headers(self):
        return {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}

    def create_class(self, group):
        return self.client.post(f"{self.base}/classes/", {
            "level": self.levels["5ème"].id, "series": "", "group": group,
            "maximum_capacity": 100,
        }, format="json", **self.headers)

    def create_student(self, last_name):
        return self.client.post(f"{self.base}/enrollments/", {
            "enrollment_number": f"2025-{last_name}",
            "last_name": last_name, "first_names": "Kodjo", "gender": "M",
            "date_of_birth": "2012-05-14",
            "level": self.levels["5ème"].id,
            "guardian_phone": "90123456",
            "guardian_last_name": "ABOTSI", "guardian_first_names": "Yao",
        }, format="json", **self.headers)

    def create_year(self, name):
        return self.client.post(f"{self.base}/academic-years/", {
            "name": name, "start_date": "2026-09-01", "end_date": "2027-06-30",
            "is_active": False,
        }, format="json", **self.headers)

    def create_session(self, name, group):
        """Une classe par session : une classe ne suit qu'une session active."""
        school_class, _ = SchoolClass.objects.get_or_create(
            school=self.school, academic_year=self.year,
            level=self.levels["5ème"], series="", group=group,
        )
        return self.client.post(f"{self.base}/academic-years/{self.year.id}/sessions/", {
            "name": name, "label": "T1",
            "start_date": "2025-10-01", "end_date": "2025-12-20",
            "classes": [school_class.id], "is_final": False,
        }, format="json", **self.headers)

    def create_subject(self, name):
        return self.client.post(f"{self.base}/subjects/", {
            "name": name, "code": name.lower(),
        }, format="json", **self.headers)

    def configure_fees(self):
        """Écriture, et non lecture : c'est l'écriture qui est réservée."""
        school_class, _ = SchoolClass.objects.get_or_create(
            school=self.school, academic_year=self.year,
            level=self.levels["5ème"], series="", group="5FEE",
        )
        return self.client.post(f"{self.base}/finance/tuition-plans/", {
            "school_class": school_class.id,
            "items": [{
                "module_name": "Écolage",
                "male_amount": "120000", "female_amount": "115000",
                "payable_in_installments": False, "installments": [],
            }],
        }, format="json", **self.headers)

    def record_expense(self):
        return self.client.post(f"{self.base}/finance/expenses/", {
            "category": self.category.id, "label": "Craie",
            "amount": "5000", "expense_date": "2025-11-02",
        }, format="json", **self.headers)

    def configure_report_cards(self):
        return self.client.put(f"{self.base}/report-cards/settings/", {
            "show_rank": True,
        }, format="json", **self.headers)

    def create_staff(self, username):
        return self.client.post(f"{self.base}/teachers/", {
            "username": username, "last_name": "AGBO", "first_names": "Ama",
            "gender": "F", "role": "enseignant",
        }, format="json", **self.headers)

    def refused(self, response):
        """La réponse est-elle un refus de droits ?"""
        return response.status_code == 400 and "permission" in response.data

    # ── La direction fait tout ───────────────────────────────────────────────

    def test_la_direction_cree_une_classe(self):
        for index, role in enumerate(DIRECTION):
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_class(f"5{chr(65 + index)}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_la_direction_inscrit_un_eleve(self):
        for role in DIRECTION:
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_student(f"ELEVE{role.upper()}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_la_direction_cree_une_annee(self):
        for index, role in enumerate(DIRECTION):
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_year(f"20{30 + index}-20{31 + index}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_la_direction_cree_une_session(self):
        for index, role in enumerate(DIRECTION):
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_session(f"Trimestre {index}", f"5S{index}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_la_direction_parametre_les_matieres_et_le_personnel(self):
        for index, role in enumerate(DIRECTION):
            with self.subTest(role=role):
                self.sign_in(role)
                self.assertEqual(self.create_subject(f"Matiere{index}").status_code, 201)
                self.assertEqual(self.create_staff(f"enseignant{index}").status_code, 201)

    def test_le_censeur_configure_les_bulletins_et_l_ecolage(self):
        self.sign_in(CustomUser.Role.CENSEUR)
        self.assertEqual(self.configure_report_cards().status_code, 200)
        self.assertEqual(self.configure_fees().status_code, 201)

    def test_le_censeur_tient_les_depenses_comme_le_proprietaire(self):
        self.sign_in(CustomUser.Role.CENSEUR)
        response = self.record_expense()
        self.assertEqual(response.status_code, 201, response.data)

    # ── Le secrétariat tient la vie scolaire ─────────────────────────────────

    def test_le_secretariat_cree_une_classe(self):
        for index, role in enumerate(SECRETARIAT):
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_class(f"5{chr(88 + index)}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_le_secretariat_inscrit_un_eleve(self):
        for role in SECRETARIAT:
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.create_student(f"ELEVE{role.upper()}")
                self.assertEqual(response.status_code, 201, response.data)

    def test_le_secretariat_cree_une_annee_et_une_session(self):
        for index, role in enumerate(SECRETARIAT):
            with self.subTest(role=role):
                self.sign_in(role)
                self.assertEqual(
                    self.create_year(f"20{40 + index}-20{41 + index}").status_code, 201,
                )
                self.assertEqual(
                    self.create_session(f"Trimestre {index}", f"5T{index}").status_code, 201,
                )

    # ── Ce que le secrétariat ne fait pas ────────────────────────────────────

    def test_le_secretariat_ne_cree_ni_matiere_ni_personnel(self):
        for role in SECRETARIAT:
            with self.subTest(role=role):
                self.sign_in(role)
                self.assertTrue(self.refused(self.create_subject("Physique")))
                self.assertTrue(self.refused(self.create_staff("nouveau")))

    def test_le_secretariat_ne_configure_ni_bulletins_ni_ecolage_ni_depenses(self):
        for role in SECRETARIAT:
            with self.subTest(role=role):
                self.sign_in(role)
                self.assertTrue(self.refused(self.configure_report_cards()))
                self.assertTrue(self.refused(self.configure_fees()))
                self.assertTrue(self.refused(self.record_expense()))

    def test_le_secretariat_ne_cloture_pas_l_annee(self):
        """Arrêter les comptes reste une décision de direction."""
        for role in SECRETARIAT:
            with self.subTest(role=role):
                self.sign_in(role)
                response = self.client.post(
                    f"{self.base}/academic-years/{self.year.id}/close/", **self.headers,
                )
                self.assertTrue(self.refused(response), response.data)

    # ── Les autres restent dehors ────────────────────────────────────────────

    def test_un_enseignant_ne_cree_pas_de_classe(self):
        self.sign_in(CustomUser.Role.TEACHER)
        self.assertTrue(self.refused(self.create_class("5Z")))

    def test_un_comptable_ne_cree_pas_de_classe_mais_tient_les_depenses(self):
        self.sign_in(CustomUser.Role.ACCOUNTANT)
        self.assertTrue(self.refused(self.create_class("5Y")))
        self.assertEqual(self.record_expense().status_code, 201)

    def test_un_etranger_a_l_ecole_n_a_pas_acces(self):
        outsider = CustomUser.objects.create_user(
            username="ailleurs", password="x", role=CustomUser.Role.PROVISEUR,
        )
        token, _ = Token.objects.get_or_create(user=outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.create_class("5W")
        self.assertEqual(response.status_code, 400)
        self.assertIn("school", response.data)
