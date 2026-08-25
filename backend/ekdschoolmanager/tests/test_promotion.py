"""Décision de fin d'année : passage en classe supérieure ou examen.

Deux régimes cohabitent. Sur un niveau ordinaire, la moyenne annuelle décide,
comparée au seuil du niveau. Sur un niveau d'examen — CM2, 3ème, Première,
Terminale au Togo — la moyenne annuelle ne décide de rien : seul le résultat
de l'examen officiel fait passer.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

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
from ekdschoolmanager.reportcard_pdf import (
    average_in_words, decision_line, number_in_words, official_footer,
)
from ekdschoolmanager.reportcards import promotion_decision


class PromotionRuleTests(TestCase):
    """La règle seule, sans passer par l'API."""

    def setUp(self):
        self.school = School.objects.create(
            name="Lycée de Lomé", code="lycee-lome",
            owner=CustomUser.objects.create_user(username="chef", password="x"),
        )
        self.ordinary = SchoolLevel.objects.get(school=self.school, name="Seconde")
        self.exam = SchoolLevel.objects.get(school=self.school, name="Terminale")

    def test_les_niveaux_d_examen_sont_reconnus_a_la_creation(self):
        """Une école neuve part avec ses quatre paliers d'examen togolais."""
        self.assertEqual(
            {level.name: level.exam_name for level in
             SchoolLevel.objects.filter(school=self.school, is_exam_level=True)},
            {"CM2": "CEPD", "3ème": "BEPC",
             "Première": "Baccalauréat Première partie",
             "Terminale": "Baccalauréat Deuxième partie"},
        )
        self.assertFalse(self.ordinary.is_exam_level)
        self.assertEqual(self.ordinary.passing_average, Decimal("10.00"))

    def test_niveau_ordinaire_la_moyenne_annuelle_decide(self):
        admitted = promotion_decision(self.ordinary, "12.78", None)
        self.assertTrue(admitted["passed"])
        self.assertEqual(admitted["label"], "Admis en classe supérieure")

        held_back = promotion_decision(self.ordinary, "9.99", None)
        self.assertFalse(held_back["passed"])
        self.assertEqual(held_back["label"], "Redouble")

    def test_le_seuil_du_niveau_fait_foi(self):
        """Un niveau plus exigeant recale une moyenne qui passerait ailleurs."""
        self.ordinary.passing_average = Decimal("12")
        self.assertFalse(promotion_decision(self.ordinary, "11.50", None)["passed"])

    def test_niveau_d_examen_seul_l_examen_decide(self):
        """Une moyenne annuelle faible n'empêche pas d'être reçu au BAC."""
        passed = promotion_decision(self.exam, "8.20", Decimal("12.50"))
        self.assertTrue(passed["passed"])
        self.assertEqual(passed["label"], "Admis au Baccalauréat Deuxième partie")
        self.assertEqual(passed["basis"], "examen")

        failed = promotion_decision(self.exam, "15.00", Decimal("8.75"))
        self.assertFalse(failed["passed"])
        self.assertEqual(failed["label"], "Échoué à l'examen")

    def test_pas_de_decision_tant_que_le_resultat_manque(self):
        """Sans note d'examen, on n'annonce pas un échec par défaut."""
        self.assertIsNone(promotion_decision(self.exam, "15.00", None))
        self.assertIsNone(promotion_decision(self.ordinary, None, None))

    def test_la_mention_s_accorde_avec_l_eleve(self):
        """« Admise » pour une fille, y compris à l'examen."""
        self.assertEqual(
            promotion_decision(self.ordinary, "12.53", None, gender="F")["label"],
            "Admise en classe supérieure",
        )
        self.assertEqual(
            promotion_decision(self.ordinary, "12.53", None, gender="M")["label"],
            "Admis en classe supérieure",
        )
        self.assertEqual(
            promotion_decision(self.exam, None, Decimal("12.50"), gender="F")["label"],
            "Admise au Baccalauréat Deuxième partie",
        )
        self.assertEqual(
            promotion_decision(self.exam, None, Decimal("8.00"), gender="F")["label"],
            "Échouée à l'examen",
        )

    def test_le_libelle_enregistre_du_genre_est_accepte(self):
        """Les bulletins figés portent « Féminin », pas le code « F »."""
        self.assertEqual(
            promotion_decision(self.ordinary, "12.53", None, gender="Féminin")["label"],
            "Admise en classe supérieure",
        )

    def test_redouble_ne_s_accorde_pas(self):
        """C'est un verbe : il s'écrit pareil pour tout le monde."""
        for gender in ("F", "M"):
            self.assertEqual(
                promotion_decision(self.ordinary, "8.10", None, gender=gender)["label"],
                "Redouble",
            )

    def test_la_decision_s_ecrit_dans_la_case_du_conseil(self):
        """Le bulletin annonce la décision, et la moyenne qui la fonde."""
        card = {"decision": promotion_decision(self.ordinary, "12.78", None)}
        line = decision_line(card)
        self.assertIn("ADMIS EN CLASSE SUPÉRIEURE", line)
        self.assertIn("moyenne annuelle 12.78 sur 20", line)
        self.assertNotIn("seuil", line)

        cells = official_footer({"city": "Lomé"}, "", decision=line)[0]._cellvalues
        printed = " ".join(
            cell.text for row in cells for cell in row if hasattr(cell, "text")
        )
        self.assertIn("ADMIS EN CLASSE SUPÉRIEURE", printed)

    def test_la_case_du_conseil_reste_libre_sans_decision(self):
        """Un bulletin de milieu d'année n'écrit rien dans la case."""
        self.assertEqual(decision_line({"decision": None}), "")


class YearEndApiTests(APITestCase):
    """Le parcours complet : seuils, saisie des notes d'examen, décisions."""

    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="proviseur", password="x", role=CustomUser.Role.ADMIN,
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
        self.level = SchoolLevel.objects.get(school=self.school, name="Terminale")
        self.school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=self.level, group="TD1",
        )
        self.session = AcademicSession.objects.create(
            academic_year=self.year, name="Troisième Trimestre", label="T3",
            start_date=date(2026, 4, 1), end_date=date(2026, 6, 30),
            is_active=True, is_final=True,
        )
        self.session.classes.add(self.school_class)

        subject = Subject.objects.create(school=self.school, name="Mathématiques")
        ClassSubject.objects.create(
            school_class=self.school_class, subject=subject, coefficient=5, weekly_hours=5,
        )
        scheme = GradeScheme.objects.create(
            session=self.session,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        GradeLine.objects.create(scheme=scheme, name="Devoir 1", max_score=20, order=1)

        student = CustomUser.objects.create_user(username="eleve1", password="x")
        student.first_name, student.last_name = "Kodjo", "ABOTSI"
        student.save()
        self.enrollment = StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=self.school_class, level=self.level,
            enrollment_number="2025TD1001", status=StudentEnrollment.Status.ACTIVE,
        )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}
        self.year_end_url = (
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/year-end/"
        )
        self.client.post(
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/generate/",
            {"scope": "school", "issued_on": "2026-06-28"}, format="json", **self.headers,
        )

    def test_les_seuils_se_reglent_niveau_par_niveau(self):
        url = f"/api/schools/{self.school.id}/report-cards/promotion/"
        levels = self.client.get(url, **self.headers).data["levels"]
        seconde = next(row for row in levels if row["name"] == "Seconde")
        seconde["passing_average"] = "11.50"

        response = self.client.put(url, {"levels": [seconde]}, format="json", **self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            SchoolLevel.objects.get(pk=seconde["id"]).passing_average, Decimal("11.50"),
        )

    def test_un_seuil_hors_bornes_est_refuse(self):
        url = f"/api/schools/{self.school.id}/report-cards/promotion/"
        levels = self.client.get(url, **self.headers).data["levels"]
        levels[0]["passing_average"] = "21"
        response = self.client.put(url, {"levels": [levels[0]]}, format="json", **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("passing_average", response.data)

    def test_la_note_d_examen_saisie_produit_la_decision(self):
        response = self.client.post(
            self.year_end_url,
            {"school_class": self.school_class.id,
             "results": [{"enrollment": self.enrollment.id, "exam_average": "12.50"}]},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            ReportCard.objects.get(enrollment=self.enrollment).exam_average, Decimal("12.50"),
        )
        decision = response.data["students"][0]["decision"]
        self.assertTrue(decision["passed"])
        self.assertEqual(decision["label"], "Admis au Baccalauréat Deuxième partie")

    def test_une_note_d_examen_hors_bornes_est_refusee(self):
        response = self.client.post(
            self.year_end_url,
            {"school_class": self.school_class.id,
             "results": [{"enrollment": self.enrollment.id, "exam_average": "25"}]},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("exam_average", response.data)

    def test_les_decisions_sont_refusees_hors_derniere_session(self):
        """Une session de milieu d'année n'a pas de décision à prendre."""
        self.session.is_final = False
        self.session.save(update_fields=["is_final"])
        response = self.client.get(
            f"{self.year_end_url}?school_class={self.school_class.id}", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dernière session", str(response.data))

    def test_la_decision_s_imprime_sur_le_bulletin(self):
        self.client.post(
            self.year_end_url,
            {"school_class": self.school_class.id,
             "results": [{"enrollment": self.enrollment.id, "exam_average": "12.50"}]},
            format="json", **self.headers,
        )
        export = self.client.get(
            f"/api/schools/{self.school.id}/report-cards"
            f"/sessions/{self.session.id}/export/?scope=school", **self.headers,
        )
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "application/pdf")


class NumberInWordsTests(TestCase):
    """Moyenne en toutes lettres, pour la case de la maquette officielle."""

    def test_les_irregularites_du_francais_sont_respectees(self):
        for number, expected in (
            (0, "zéro"), (16, "seize"), (17, "dix-sept"), (20, "vingt"),
            (21, "vingt et un"), (53, "cinquante-trois"), (70, "soixante-dix"),
            (71, "soixante et onze"), (80, "quatre-vingts"), (81, "quatre-vingt-un"),
            (91, "quatre-vingt-onze"), (99, "quatre-vingt-dix-neuf"),
        ):
            self.assertEqual(number_in_words(number), expected, number)

    def test_une_moyenne_s_ecrit_avec_ses_centiemes(self):
        self.assertEqual(average_in_words("12.53"), "Douze virgule cinquante-trois")
        self.assertEqual(average_in_words("9.75"), "Neuf virgule soixante-quinze")

    def test_une_moyenne_ronde_s_en_tient_a_son_entier(self):
        self.assertEqual(average_in_words("14.00"), "Quatorze")
        self.assertEqual(average_in_words("20.00"), "Vingt")

    def test_les_centiemes_sous_dix_gardent_leur_zero(self):
        """Sans lui, « 12,05 » se lirait « douze virgule cinq »."""
        self.assertEqual(average_in_words("12.05"), "Douze virgule zéro cinq")

    def test_une_valeur_absente_ou_illisible_n_ecrit_rien(self):
        for value in (None, "", "abc"):
            self.assertEqual(average_in_words(value), "")
