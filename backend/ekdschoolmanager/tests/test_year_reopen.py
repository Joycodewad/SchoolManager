"""Annulation d'une clôture d'année académique.

Une clôture lancée trop tôt doit pouvoir se défaire entièrement : classes
reconduites, barèmes, réinscriptions, dettes reportées et statuts d'élèves.
Mais jamais au prix du travail fait depuis — c'est l'autre moitié des cas
couverts ici.
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    CarriedDebt,
    CarriedDebtPayment,
    ClassFeeItem,
    ClassSubject,
    CustomUser,
    FeeModule,
    FeePayment,
    GradeEntry,
    GradeLine,
    GradeScheme,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
    SubjectCategoryOrder,
    TuitionFeePlan,
    YearClosure,
)
from ekdschoolmanager.yearclosure import close_year
from ekdschoolmanager.yearreopen import YearReopenError, blockers, reopen_year


class YearReopenTests(APITestCase):
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
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        self.next_year = AcademicYear.objects.create(
            school=self.school, name="2026-2027",
            start_date=date(2026, 9, 1), end_date=date(2027, 6, 30),
        )
        self.levels = {
            level.name: level
            for level in SchoolLevel.objects.filter(school=self.school)
        }
        self.session = AcademicSession.objects.create(
            academic_year=self.year, name="Troisième Trimestre", label="T3",
            start_date=date(2026, 4, 1), end_date=date(2026, 6, 30),
            is_active=False, is_closed=True, is_final=True,
        )

    # ── Fabriques ────────────────────────────────────────────────────────────

    def make_class(self, level_name, group, year=None, series=""):
        return SchoolClass.objects.create(
            school=self.school, academic_year=year or self.year,
            level=self.levels[level_name], series=series, group=group,
        )

    def enrol(self, school_class, last_name):
        student = CustomUser.objects.create_user(username=f"e{last_name}", password="x")
        student.last_name, student.first_name = last_name, "Test"
        student.student_status = CustomUser.StudentStatus.NEW
        student.save()
        return StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=school_class, level=school_class.level,
            series=school_class.series,
            enrollment_number=f"2025-{last_name}", status=StudentEnrollment.Status.ACTIVE,
        )

    def decide(self, enrollment, average):
        self.session.classes.add(enrollment.school_class)
        return ReportCard.objects.create(
            session=self.session, enrollment=enrollment,
            school_class=enrollment.school_class,
            general_average=Decimal(average), payload={},
        )

    def make_plan(self, school_class, amount="120000"):
        plan = TuitionFeePlan.objects.create(
            school=self.school, academic_year=school_class.academic_year,
            school_class=school_class,
        )
        module, _ = FeeModule.objects.get_or_create(
            school=self.school, academic_year=school_class.academic_year, name="Écolage",
        )
        return ClassFeeItem.objects.create(
            plan=plan, fee_module=module,
            male_amount=Decimal(amount), female_amount=Decimal(amount),
        )

    def closed_year(self, average="12.50"):
        """Une année clôturée avec un élève admis de 5ème A en 4ème A."""
        cinquieme = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A")
        self.enrollment = self.enrol(cinquieme, "ADJO")
        self.decide(self.enrollment, average)
        return close_year(self.year, user=self.staff)

    # ── Retour en arrière complet ────────────────────────────────────────────

    def test_l_annulation_defait_tout_ce_que_la_cloture_avait_fait(self):
        self.closed_year()
        self.assertEqual(SchoolClass.objects.filter(academic_year=self.next_year).count(), 2)
        self.assertEqual(StudentEnrollment.objects.filter(academic_year=self.next_year).count(), 1)

        report = reopen_year(self.year)

        self.year.refresh_from_db()
        self.assertFalse(self.year.is_closed)
        self.assertTrue(self.year.is_active)
        self.assertEqual(SchoolClass.objects.filter(academic_year=self.next_year).count(), 0)
        self.assertEqual(StudentEnrollment.objects.filter(academic_year=self.next_year).count(), 0)
        self.assertFalse(YearClosure.objects.filter(academic_year=self.year).exists())
        self.assertEqual(report["classes"], 2)
        self.assertEqual(report["enrollments"], 1)

    def test_l_inscription_de_l_annee_close_reste_intacte(self):
        """On rouvre l'année : ce qu'elle contenait n'a jamais été touché."""
        self.closed_year()
        reopen_year(self.year)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.school_class.group, "5A")
        self.assertTrue(ReportCard.objects.filter(enrollment=self.enrollment).exists())

    def test_le_statut_de_l_eleve_redevient_ce_qu_il_etait(self):
        self.closed_year()
        student = self.enrollment.student
        student.refresh_from_db()
        self.assertEqual(student.year_result, CustomUser.YearResult.PASSED)

        report = reopen_year(self.year)

        student.refresh_from_db()
        self.assertEqual(student.student_status, CustomUser.StudentStatus.NEW)
        self.assertIsNone(student.year_result)
        self.assertEqual(report["statuses_restored"], 1)

    def test_un_bachelier_redevient_ce_qu_il_etait_avant(self):
        terminale = self.make_class("Terminale", "TD", series="D")
        enrollment = self.enrol(terminale, "AFATODJI")
        self.decide(enrollment, "12.00")
        ReportCard.objects.filter(enrollment=enrollment).update(exam_average=Decimal("12"))
        close_year(self.year, user=self.staff)
        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.BACHELOR,
        )

        reopen_year(self.year)

        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.NEW,
        )

    def test_la_dette_reportee_disparait(self):
        cinquieme = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A")
        item = self.make_plan(cinquieme)
        enrollment = self.enrol(cinquieme, "DEVANT")
        self.decide(enrollment, "12.00")
        FeePayment.objects.create(
            enrollment=enrollment, class_fee=item, amount=Decimal("85000"),
            paid_on=date(2026, 1, 15), received_by=self.staff,
        )
        close_year(self.year, user=self.staff)
        self.assertTrue(CarriedDebt.objects.filter(origin_year=self.year).exists())

        report = reopen_year(self.year)

        self.assertFalse(CarriedDebt.objects.filter(origin_year=self.year).exists())
        self.assertEqual(report["debts"], 1)
        # Le versement de l'année close, lui, n'a pas bougé.
        self.assertTrue(FeePayment.objects.filter(enrollment=enrollment).exists())

    def test_les_baremes_reconduits_sont_supprimes(self):
        cinquieme = self.make_class("5ème", "5A")
        self.make_plan(cinquieme)
        close_year(self.year, user=self.staff)
        self.assertEqual(TuitionFeePlan.objects.filter(academic_year=self.next_year).count(), 1)

        report = reopen_year(self.year)

        self.assertEqual(TuitionFeePlan.objects.filter(academic_year=self.next_year).count(), 0)
        self.assertEqual(FeeModule.objects.filter(academic_year=self.next_year).count(), 0)
        self.assertEqual(report["fee_plans"], 1)
        self.assertEqual(report["fee_modules"], 1)
        # Le barème de l'année close reste en place.
        self.assertEqual(TuitionFeePlan.objects.filter(academic_year=self.year).count(), 1)

    def test_les_matieres_reconduites_sont_supprimees(self):
        cinquieme = self.make_class("5ème", "5A")
        ClassSubject.objects.create(
            school_class=cinquieme,
            subject=Subject.objects.create(school=self.school, name="Maths", code="maths"),
            weekly_hours=4, coefficient=Decimal("3"),
        )
        close_year(self.year, user=self.staff)

        report = reopen_year(self.year)

        self.assertEqual(
            ClassSubject.objects.filter(school_class__academic_year=self.next_year).count(), 0,
        )
        self.assertEqual(report["class_subjects"], 1)
        self.assertEqual(
            ClassSubject.objects.filter(school_class=cinquieme).count(), 1,
        )

    def test_la_regle_de_bulletin_perd_la_classe_ajoutee(self):
        premiere = self.make_class("Première", "1A4-1", series="A4")
        regle = SubjectCategoryOrder.objects.create(
            school=self.school, name="Littéraires d'abord",
            scope=SubjectCategoryOrder.Scope.CLASSES, categories=["Littéraires"],
        )
        regle.classes.add(premiere)
        close_year(self.year, user=self.staff)
        self.assertEqual(regle.classes.count(), 2)

        report = reopen_year(self.year)

        self.assertEqual(list(regle.classes.all()), [premiere])
        self.assertEqual(report["report_card_rules"], 1)

    def test_une_classe_saisie_a_la_main_n_est_pas_emportee(self):
        """La reconduction n'a pas créé cette classe : elle reste."""
        self.make_class("5ème", "5A")
        gardee = self.make_class("6ème", "6A", year=self.next_year)
        close_year(self.year, user=self.staff)

        reopen_year(self.year)

        self.assertEqual(
            list(SchoolClass.objects.filter(academic_year=self.next_year)), [gardee],
        )

    # ── Année active ─────────────────────────────────────────────────────────

    def test_l_annee_redevient_active_si_aucune_autre_ne_l_est(self):
        self.closed_year()
        report = reopen_year(self.year)
        self.assertTrue(report["is_active"])

    def test_l_annee_reste_en_retrait_si_la_suivante_a_pris_la_main(self):
        self.closed_year()
        AcademicYear.objects.filter(pk=self.next_year.pk).update(is_active=True)

        report = reopen_year(self.year)

        self.year.refresh_from_db()
        self.assertFalse(report["is_active"])
        self.assertFalse(self.year.is_closed)
        self.assertFalse(self.year.is_active)

    # ── Refus ────────────────────────────────────────────────────────────────

    def test_une_annee_non_cloturee_ne_se_rouvre_pas(self):
        with self.assertRaises(YearReopenError) as refus:
            reopen_year(self.year)
        self.assertIn("n'a pas été clôturée", str(refus.exception))

    def test_seule_la_derniere_cloture_s_annule(self):
        """Deux années closes : la plus ancienne attend son tour."""
        self.closed_year()
        third_year = AcademicYear.objects.create(
            school=self.school, name="2027-2028",
            start_date=date(2027, 9, 1), end_date=date(2028, 6, 30),
        )
        AcademicSession.objects.create(
            academic_year=self.next_year, name="Trimestre", label="T1",
            start_date=date(2026, 10, 1), end_date=date(2026, 12, 20),
            is_active=False, is_closed=True, is_final=True,
        )
        close_year(self.next_year, user=self.staff)
        self.assertTrue(third_year.pk)

        with self.assertRaises(YearReopenError) as refus:
            reopen_year(self.year)
        self.assertIn("2026-2027", str(refus.exception))

        # Dans l'ordre, en revanche, les deux se défont.
        reopen_year(self.next_year)
        reopen_year(self.year)
        self.assertEqual(YearClosure.objects.count(), 0)

    def test_une_note_saisie_dans_l_annee_suivante_bloque(self):
        self.closed_year()
        landed = StudentEnrollment.objects.get(academic_year=self.next_year)
        scheme = GradeScheme.objects.create(
            session=AcademicSession.objects.create(
                academic_year=self.next_year, name="Trimestre", label="T1",
                start_date=date(2026, 10, 1), end_date=date(2026, 12, 20),
            ),
            created_by=self.staff,
        )
        line = GradeLine.objects.create(scheme=scheme, name="Devoir", order=1)
        matiere = ClassSubject.objects.create(
            school_class=landed.school_class,
            subject=Subject.objects.create(school=self.school, name="Maths", code="maths"),
            weekly_hours=4, coefficient=Decimal("3"),
        )
        GradeEntry.objects.create(
            line=line, enrollment=landed, class_subject=matiere,
            score=Decimal("14"), entered_by=self.staff,
        )

        with self.assertRaises(YearReopenError) as refus:
            reopen_year(self.year)
        self.assertIn("des notes ont été saisies", str(refus.exception))
        self.year.refresh_from_db()
        self.assertTrue(self.year.is_closed)

    def test_un_ecolage_encaisse_dans_l_annee_suivante_bloque(self):
        cinquieme = self.make_class("5ème", "5A")
        self.make_plan(cinquieme)
        self.make_plan(self.make_class("4ème", "4A"))
        enrollment = self.enrol(cinquieme, "PAYEUR")
        self.decide(enrollment, "12.00")
        close_year(self.year, user=self.staff)

        landed = StudentEnrollment.objects.get(academic_year=self.next_year)
        item = ClassFeeItem.objects.get(plan__school_class=landed.school_class)
        FeePayment.objects.create(
            enrollment=landed, class_fee=item, amount=Decimal("20000"),
            paid_on=date(2026, 10, 5), received_by=self.staff,
        )

        self.assertIn("des écolages ont été encaissés", " ".join(blockers(
            YearClosure.objects.get(academic_year=self.year),
        )))
        with self.assertRaises(YearReopenError):
            reopen_year(self.year)

    def test_un_impaye_deja_regle_bloque(self):
        cinquieme = self.make_class("5ème", "5A")
        item = self.make_plan(cinquieme)
        enrollment = self.enrol(cinquieme, "DEVANT")
        self.decide(enrollment, "12.00")
        FeePayment.objects.create(
            enrollment=enrollment, class_fee=item, amount=Decimal("85000"),
            paid_on=date(2026, 1, 15), received_by=self.staff,
        )
        close_year(self.year, user=self.staff)
        debt = CarriedDebt.objects.get(origin_year=self.year)
        CarriedDebtPayment.objects.create(
            debt=debt, amount=Decimal("10000"), paid_on=date(2026, 10, 5),
            received_by=self.staff,
        )

        with self.assertRaises(YearReopenError) as refus:
            reopen_year(self.year)
        self.assertIn("impayés reportés", str(refus.exception))

    def test_un_eleve_inscrit_a_la_main_dans_une_classe_reconduite_bloque(self):
        self.closed_year()
        nouveau = CustomUser.objects.create_user(username="nouveau", password="x")
        StudentEnrollment.objects.create(
            school=self.school, academic_year=self.next_year, student=nouveau,
            school_class=SchoolClass.objects.get(academic_year=self.next_year, group="5A"),
            enrollment_number="2026-0500", status=StudentEnrollment.Status.ACTIVE,
        )

        with self.assertRaises(YearReopenError) as refus:
            reopen_year(self.year)
        self.assertIn("inscrits à la main", str(refus.exception))

    # ── API ──────────────────────────────────────────────────────────────────

    def test_l_api_annule_la_cloture_et_rend_le_bilan(self):
        self.closed_year()
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}/reopen/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_closed"])
        self.assertEqual(response.data["reopened"]["classes"], 2)
        self.assertEqual(response.data["reopened"]["enrollments"], 1)

    def test_l_api_refuse_avec_un_message_qui_dit_quoi_faire(self):
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}/reopen/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("n'a pas été clôturée", response.data["detail"])

    def test_seule_la_derniere_annee_close_s_annonce_annulable(self):
        self.closed_year()
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(
            f"/api/schools/{self.school.id}/academic-years/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        annulables = {row["name"]: row["can_reopen"] for row in response.data}
        self.assertEqual(annulables, {"2025-2026": True, "2026-2027": False})
