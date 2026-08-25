"""Clôture d'une année académique : arrêt des comptes et passage des élèves.

Les cas couverts sont ceux de la vraie vie togolaise : une cinquième qui monte
en quatrième, une classe sans équivalent au niveau supérieur, un examen réussi
qui rend l'orientation libre, et une fin de cursus qui délivre un diplôme.
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
    CarriedDebt,
    ClassFeeItem,
    CustomUser,
    DisciplineRecord,
    FeeModule,
    FeePayment,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    TuitionFeePlan,
    YearClosure,
)
from ekdschoolmanager.yearclosure import YearClosureError, close_year, student_outcome


class YearClosureTests(APITestCase):
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

    def enrol(self, school_class, last_name, gender="M"):
        student = CustomUser.objects.create_user(username=f"e{last_name}", password="x")
        student.last_name, student.first_name, student.gender = last_name, "Test", gender
        student.save()
        return StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=school_class, level=school_class.level,
            series=school_class.series,
            enrollment_number=f"2025-{last_name}", status=StudentEnrollment.Status.ACTIVE,
        )

    def decide(self, enrollment, average=None, exam=None):
        """Fige un bulletin de dernière session, seul porteur de la décision."""
        self.session.classes.add(enrollment.school_class)
        return ReportCard.objects.create(
            session=self.session, enrollment=enrollment,
            school_class=enrollment.school_class,
            general_average=Decimal(average) if average else None,
            exam_average=Decimal(exam) if exam else None,
            payload={},
        )

    # ── Conditions préalables ────────────────────────────────────────────────

    def test_une_session_ouverte_bloque_la_cloture(self):
        AcademicSession.objects.create(
            academic_year=self.year, name="Rattrapage", label="R",
            start_date=date(2026, 5, 1), end_date=date(2026, 6, 20), is_active=True,
        )
        with self.assertRaises(YearClosureError) as refus:
            close_year(self.year, user=self.staff)
        self.assertIn("Rattrapage", str(refus.exception))
        self.year.refresh_from_db()
        self.assertFalse(self.year.is_closed)

    def test_sans_annee_suivante_la_cloture_est_refusee(self):
        self.next_year.delete()
        with self.assertRaises(YearClosureError) as refus:
            close_year(self.year, user=self.staff)
        self.assertIn("année suivante", str(refus.exception))

    # ── Passage de classe ────────────────────────────────────────────────────

    def test_une_cinquieme_a_monte_en_quatrieme_a(self):
        self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(SchoolClass.objects.get(group="5A"), "ADJO")
        self.decide(enrollment, average="12.50")

        close_year(self.year, user=self.staff)
        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertEqual(landed.school_class.group, "4A")
        self.assertEqual(landed.level.name, "4ème")

    def test_sans_classe_correspondante_l_eleve_passe_sans_classe(self):
        """Une 5ème D dont la 4ème n'a que trois classes : niveau, pas de classe."""
        for group in ("5A", "5B", "5C", "5D"):
            self.make_class("5ème", group)
        for group in ("4A", "4B", "4C"):
            self.make_class("4ème", group, year=self.next_year)
        enrollment = self.enrol(SchoolClass.objects.get(group="5D"), "KOSSI")
        self.decide(enrollment, average="11.00")

        close_year(self.year, user=self.staff)
        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertIsNone(landed.school_class)
        self.assertEqual(landed.level.name, "4ème")

    def test_le_rang_suit_la_serie_au_lycee(self):
        """2nde A4 rang 1 va en 1ère A4 rang 1, sans confondre les séries."""
        self.make_class("Seconde", "2A4-1", series="A4")
        self.make_class("Seconde", "2A4-2", series="A4")
        self.make_class("Première", "1A4-1", year=self.next_year, series="A4")
        self.make_class("Première", "1A4-2", year=self.next_year, series="A4")
        enrollment = self.enrol(SchoolClass.objects.get(group="2A4-2"), "AMEGAN")
        self.decide(enrollment, average="13.00")

        close_year(self.year, user=self.staff)
        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertEqual(landed.school_class.group, "1A4-2")

    def test_un_eleve_qui_echoue_redouble_son_niveau(self):
        self.make_class("5ème", "5A")
        self.make_class("5ème", "5A", year=self.next_year)
        enrollment = self.enrol(SchoolClass.objects.get(group="5A", academic_year=self.year), "BODJONA")
        self.decide(enrollment, average="7.00")

        close_year(self.year, user=self.staff)
        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertEqual(landed.level.name, "5ème")
        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.REPEATING,
        )

    # ── Classes d'examen ─────────────────────────────────────────────────────

    def test_un_examen_reussi_mene_au_niveau_suivant_sans_classe(self):
        """Après le BEPC l'orientation change : la classe se décide à l'inscription."""
        self.make_class("3ème", "3A")
        self.make_class("Seconde", "2A4", year=self.next_year, series="A4")
        enrollment = self.enrol(SchoolClass.objects.get(group="3A"), "ABLIMI")
        self.decide(enrollment, average="9.00", exam="12.00")

        close_year(self.year, user=self.staff)
        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertIsNone(landed.school_class)
        self.assertEqual(landed.level.name, "Seconde")

    def test_sans_niveau_suivant_l_eleve_sort_avec_son_diplome(self):
        """Un collège sans lycée : le BEPC clôt le cursus dans cette école."""
        SchoolLevel.objects.filter(
            school=self.school, order__gt=self.levels["3ème"].order,
        ).delete()
        self.make_class("3ème", "3A")
        enrollment = self.enrol(SchoolClass.objects.get(group="3A"), "ADAM")
        self.decide(enrollment, average="9.00", exam="11.50")

        close_year(self.year, user=self.staff)
        self.assertFalse(StudentEnrollment.objects.filter(
            academic_year=self.next_year, student=enrollment.student,
        ).exists())
        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.BEPC_HOLDER,
        )

    def test_la_terminale_reussie_donne_bachelier(self):
        self.make_class("Terminale", "TD", series="D")
        enrollment = self.enrol(SchoolClass.objects.get(group="TD"), "AFATODJI")
        self.decide(enrollment, average="10.50", exam="12.00")

        close_year(self.year, user=self.staff)
        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.BACHELOR,
        )
        self.assertFalse(StudentEnrollment.objects.filter(
            academic_year=self.next_year, student=enrollment.student,
        ).exists())

    def test_le_cm2_reussi_sans_sixieme_donne_titulaire_du_cepd(self):
        SchoolLevel.objects.filter(
            school=self.school, order__gt=self.levels["CM2"].order,
        ).delete()
        self.make_class("CM2", "CM2A")
        enrollment = self.enrol(SchoolClass.objects.get(group="CM2A"), "AGBA", gender="F")
        self.decide(enrollment, average="12.00", exam="13.00")

        close_year(self.year, user=self.staff)
        enrollment.student.refresh_from_db()
        self.assertEqual(
            enrollment.student.student_status, CustomUser.StudentStatus.CEPD_HOLDER,
        )

    # ── Sans décision ────────────────────────────────────────────────────────

    def test_un_eleve_sans_bulletin_reste_a_son_niveau(self):
        """On ne fait passer personne sur une absence de résultat."""
        self.make_class("5ème", "5A")
        enrollment = self.enrol(SchoolClass.objects.get(group="5A"), "SANSNOTE")

        closure = close_year(self.year, user=self.staff)
        self.assertEqual(closure.undecided_count, 1)
        self.assertFalse(StudentEnrollment.objects.filter(
            academic_year=self.next_year, student=enrollment.student,
        ).exists())

    # ── Écolage impayé ───────────────────────────────────────────────────────

    def test_le_reste_du_devient_une_dette_reportee(self):
        school_class = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(school_class, "DEVANT")
        self.decide(enrollment, average="12.00")

        plan = TuitionFeePlan.objects.create(
            school=self.school, academic_year=self.year, school_class=school_class,
        )
        module = FeeModule.objects.create(
            school=self.school, academic_year=self.year, name="Écolage",
        )
        item = ClassFeeItem.objects.create(
            plan=plan, fee_module=module,
            male_amount=Decimal("120000"), female_amount=Decimal("120000"),
        )
        FeePayment.objects.create(
            enrollment=enrollment, class_fee=item, amount=Decimal("85000"),
            paid_on=date(2026, 1, 15), received_by=self.staff,
        )

        closure = close_year(self.year, user=self.staff)
        debt = CarriedDebt.objects.get(origin_enrollment=enrollment)
        self.assertEqual(debt.amount, Decimal("35000.00"))
        self.assertEqual(debt.outstanding, Decimal("35000.00"))
        self.assertEqual(closure.carried_debt_total, Decimal("35000.00"))

    def test_un_eleve_a_jour_ne_laisse_pas_de_dette(self):
        school_class = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(school_class, "AJOUR")
        self.decide(enrollment, average="12.00")

        plan = TuitionFeePlan.objects.create(
            school=self.school, academic_year=self.year, school_class=school_class,
        )
        module = FeeModule.objects.create(
            school=self.school, academic_year=self.year, name="Écolage",
        )
        item = ClassFeeItem.objects.create(
            plan=plan, fee_module=module,
            male_amount=Decimal("120000"), female_amount=Decimal("120000"),
        )
        FeePayment.objects.create(
            enrollment=enrollment, class_fee=item, amount=Decimal("120000"),
            paid_on=date(2026, 1, 15), received_by=self.staff,
        )

        close_year(self.year, user=self.staff)
        self.assertFalse(CarriedDebt.objects.filter(origin_enrollment=enrollment).exists())

    # ── Archive ──────────────────────────────────────────────────────────────

    def test_la_cloture_archive_l_etat_de_l_annee(self):
        self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(SchoolClass.objects.get(group="5A"), "ARCHIVE")
        self.decide(enrollment, average="12.00")

        closure = close_year(self.year, user=self.staff)
        self.assertEqual(closure.enrollment_count, 1)
        self.assertEqual(closure.promoted_count, 1)
        self.assertEqual(closure.next_year, self.next_year)
        self.assertEqual(len(closure.payload["students"]), 1)
        self.assertEqual(closure.payload["students"][0]["next_class"], "4A")
        self.assertEqual(closure.payload["classes"][0]["group"], "5A")

        self.year.refresh_from_db()
        self.assertTrue(self.year.is_closed)
        self.assertFalse(self.year.is_active)

    def test_une_annee_deja_close_ne_se_reclot_pas(self):
        self.make_class("5ème", "5A")
        close_year(self.year, user=self.staff)
        with self.assertRaises(YearClosureError):
            close_year(self.year, user=self.staff)
        self.assertEqual(YearClosure.objects.count(), 1)

    def test_une_inscription_deja_saisie_est_respectee(self):
        """La clôture ne remplace pas ce que l'établissement a déjà fait."""
        self.make_class("5ème", "5A")
        target = self.make_class("4ème", "4B", year=self.next_year)
        enrollment = self.enrol(SchoolClass.objects.get(group="5A"), "DEJALA")
        self.decide(enrollment, average="12.00")
        StudentEnrollment.objects.create(
            school=self.school, academic_year=self.next_year, student=enrollment.student,
            school_class=target, level=target.level, enrollment_number="2026-9999",
            status=StudentEnrollment.Status.ACTIVE,
        )

        close_year(self.year, user=self.staff)
        self.assertEqual(
            StudentEnrollment.objects.filter(
                academic_year=self.next_year, student=enrollment.student,
            ).count(), 1,
        )


class CarriedDebtApiTests(YearClosureTests):
    """Une dette reportée se consulte et se règle depuis une autre année."""

    def setUp(self):
        super().setUp()
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = f"/api/schools/{self.school.id}/finance/carried-debts/"
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.next_year.id)}

    def indebted_student(self, paid="85000"):
        school_class = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(school_class, "DEVANT")
        self.decide(enrollment, average="12.00")
        plan = TuitionFeePlan.objects.create(
            school=self.school, academic_year=self.year, school_class=school_class,
        )
        module = FeeModule.objects.create(
            school=self.school, academic_year=self.year, name="Écolage",
        )
        item = ClassFeeItem.objects.create(
            plan=plan, fee_module=module,
            male_amount=Decimal("120000"), female_amount=Decimal("120000"),
        )
        FeePayment.objects.create(
            enrollment=enrollment, class_fee=item, amount=Decimal(paid),
            paid_on=date(2026, 1, 15), received_by=self.staff,
        )
        close_year(self.year, user=self.staff)
        return CarriedDebt.objects.get(origin_enrollment=enrollment)

    def test_la_dette_se_lit_depuis_l_annee_suivante(self):
        self.indebted_student()
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["outstanding_total"], "35000.00")
        self.assertEqual(response.data["debts"][0]["origin_year"], "2025-2026")

    def test_un_versement_reduit_le_reste_du(self):
        debt = self.indebted_student()
        response = self.client.post(
            self.url, {"debt": debt.id, "amount": "20000", "paid_on": "2026-10-05"},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["outstanding"], "15000.00")
        debt.refresh_from_db()
        self.assertEqual(debt.settled_amount, Decimal("20000"))
        self.assertEqual(debt.payments.count(), 1)

    def test_on_ne_verse_pas_plus_que_le_reste_du(self):
        debt = self.indebted_student()
        response = self.client.post(
            self.url, {"debt": debt.id, "amount": "50000"}, format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("35000", str(response.data))

    def test_une_dette_soldee_quitte_la_liste_de_recouvrement(self):
        debt = self.indebted_student()
        self.client.post(
            self.url, {"debt": debt.id, "amount": "35000"}, format="json", **self.headers,
        )
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.data["debts"], [])
        self.assertEqual(
            len(self.client.get(f"{self.url}?settled=1", **self.headers).data["debts"]), 1,
        )


class SchoolLifeIsolationTests(YearClosureTests):
    """Discipline et appels repartent à zéro sans que rien ne soit effacé.

    Ces écritures portent leur année : la nouvelle n'en hérite pas, et la
    clôturée les garde. C'est ce que ces tests vérifient — la remise à zéro
    n'est pas un effacement, c'est un cloisonnement.
    """

    def with_school_life(self):
        school_class = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A", year=self.next_year)
        enrollment = self.enrol(school_class, "VIESCOLAIRE")
        self.decide(enrollment, average="12.00")

        DisciplineRecord.objects.create(
            school=self.school, academic_year=self.year, enrollment=enrollment,
            entry_type=DisciplineRecord.EntryType.LATE, occurred_on=date(2026, 2, 10),
            late_hours=Decimal("2"), recorded_by=self.staff,
        )
        session = AttendanceSession.objects.create(
            school=self.school, academic_year=self.year, school_class=school_class,
            taken_on=date(2026, 2, 10), taken_by=self.staff,
        )
        AttendanceRecord.objects.create(
            session=session, enrollment=enrollment,
            status=AttendanceRecord.Status.ABSENT,
        )
        return enrollment

    def test_la_cloture_compte_la_vie_scolaire_sans_l_effacer(self):
        self.with_school_life()
        closure = close_year(self.year, user=self.staff)

        self.assertEqual(closure.discipline_count, 1)
        self.assertEqual(closure.attendance_session_count, 1)
        self.assertEqual(closure.attendance_record_count, 1)
        # Rien n'a disparu : l'année close reste consultable telle quelle.
        self.assertEqual(
            DisciplineRecord.objects.filter(academic_year=self.year).count(), 1,
        )
        self.assertEqual(
            AttendanceSession.objects.filter(academic_year=self.year).count(), 1,
        )

    def test_l_annee_suivante_repart_vierge(self):
        """Aucune écriture de vie scolaire ne suit l'élève réinscrit."""
        self.with_school_life()
        close_year(self.year, user=self.staff)

        self.assertEqual(
            DisciplineRecord.objects.filter(academic_year=self.next_year).count(), 0,
        )
        self.assertEqual(
            AttendanceSession.objects.filter(academic_year=self.next_year).count(), 0,
        )

    def test_la_discipline_ne_suit_pas_la_nouvelle_inscription(self):
        """Elle vise l'inscription de l'année close, pas celle qui la remplace."""
        enrollment = self.with_school_life()
        close_year(self.year, user=self.staff)

        new_enrollment = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertEqual(new_enrollment.discipline_records.count(), 0)
        self.assertEqual(enrollment.discipline_records.count(), 1)
