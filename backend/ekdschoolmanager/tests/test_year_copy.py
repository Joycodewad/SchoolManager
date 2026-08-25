"""Reconduction des paramètres sur l'année suivante, à la clôture.

Une année qui se clôture prépare la suivante : sans classes dans l'année
neuve, aucun élève admis n'aurait où aller. On vérifie ici que la copie
reprend tout ce qui se reconduit — classes, matières, barèmes, échéances,
règles de bulletin — sans jamais écraser ce que l'établissement a déjà saisi.
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    ClassFeeItem,
    ClassSubject,
    CustomUser,
    FeeInstallment,
    FeeModule,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
    SubjectCategoryOrder,
    TuitionFeePlan,
)
from ekdschoolmanager.yearclosure import close_year
from ekdschoolmanager.yearcopy import copy_year_settings, shift_years


class YearCopyTests(APITestCase):
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

    def make_class(self, level_name, group, year=None, series="", **extra):
        return SchoolClass.objects.create(
            school=self.school, academic_year=year or self.year,
            level=self.levels[level_name], series=series, group=group, **extra,
        )

    def make_subject(self, name, code):
        return Subject.objects.create(school=self.school, name=name, code=code)

    def teach(self, school_class, subject, hours=4, coefficient="3"):
        return ClassSubject.objects.create(
            school_class=school_class, subject=subject,
            weekly_hours=hours, coefficient=Decimal(coefficient),
        )

    def make_plan(self, school_class, amount="120000", installments=()):
        plan = TuitionFeePlan.objects.create(
            school=self.school, academic_year=school_class.academic_year,
            school_class=school_class,
        )
        module, _ = FeeModule.objects.get_or_create(
            school=self.school, academic_year=school_class.academic_year, name="Écolage",
        )
        item = ClassFeeItem.objects.create(
            plan=plan, fee_module=module,
            male_amount=Decimal(amount), female_amount=Decimal(amount),
            payable_in_installments=bool(installments),
        )
        for order, (name, percentage, due) in enumerate(installments, start=1):
            FeeInstallment.objects.create(
                class_fee=item, name=name, percentage=Decimal(percentage),
                due_date=due, order=order,
            )
        return plan

    def enrol(self, school_class, last_name):
        student = CustomUser.objects.create_user(username=f"e{last_name}", password="x")
        student.last_name, student.first_name = last_name, "Test"
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

    # ── Classes ──────────────────────────────────────────────────────────────

    def test_les_classes_sont_reconduites_avec_leur_configuration(self):
        source = self.make_class("5ème", "5A", maximum_capacity=42)
        maths = self.make_subject("Mathématiques", "maths")
        self.teach(source, maths, hours=6, coefficient="4")

        report = copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="5A")
        self.assertEqual(copie.level, self.levels["5ème"])
        self.assertEqual(copie.maximum_capacity, 42)
        configuration = ClassSubject.objects.get(school_class=copie)
        self.assertEqual(configuration.subject, maths)
        self.assertEqual(configuration.weekly_hours, 6)
        self.assertEqual(configuration.coefficient, Decimal("4.00"))
        self.assertEqual(report["classes"], 1)
        self.assertEqual(report["class_subjects"], 1)

    def test_la_serie_du_lycee_suit_la_classe(self):
        self.make_class("Première", "1A4-1", series="A4")
        copy_year_settings(self.year, self.next_year)
        copie = SchoolClass.objects.get(academic_year=self.next_year, group="1A4-1")
        self.assertEqual(copie.series, "A4")

    def test_une_classe_deja_creee_n_est_pas_dupliquee(self):
        self.make_class("5ème", "5A")
        self.make_class("5ème", "5A", year=self.next_year)

        report = copy_year_settings(self.year, self.next_year)

        self.assertEqual(
            SchoolClass.objects.filter(academic_year=self.next_year, group="5A").count(), 1,
        )
        self.assertEqual(report["classes"], 0)
        self.assertEqual(report["classes_kept"], 1)

    def test_une_classe_deja_configuree_garde_ses_matieres(self):
        """L'établissement a retiré une matière : la reconduction ne la remet pas."""
        source = self.make_class("5ème", "5A")
        maths, anglais = self.make_subject("Mathématiques", "maths"), self.make_subject("Anglais", "anglais")
        self.teach(source, maths)
        self.teach(source, anglais)
        deja = self.make_class("5ème", "5A", year=self.next_year)
        self.teach(deja, maths)

        copy_year_settings(self.year, self.next_year)

        self.assertEqual(
            list(ClassSubject.objects.filter(school_class=deja).values_list("subject__name", flat=True)),
            ["Mathématiques"],
        )

    def test_une_classe_inactive_n_est_pas_reconduite(self):
        self.make_class("5ème", "5B", is_active=False)
        copy_year_settings(self.year, self.next_year)
        self.assertFalse(
            SchoolClass.objects.filter(academic_year=self.next_year, group="5B").exists(),
        )

    def test_une_matiere_desactivee_ne_suit_pas(self):
        source = self.make_class("5ème", "5A")
        retiree = self.make_subject("Couture", "couture")
        self.teach(source, retiree)
        retiree.is_active = False
        retiree.save(update_fields=["is_active"])

        copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="5A")
        self.assertEqual(ClassSubject.objects.filter(school_class=copie).count(), 0)

    def test_le_titulaire_n_est_pas_reconduit(self):
        """La répartition des enseignants se refait à chaque rentrée."""
        titulaire = CustomUser.objects.create_user(
            username="kossi", password="x", role=CustomUser.Role.TEACHER,
        )
        SchoolMembership.objects.create(
            school=self.school, user=titulaire,
            role=CustomUser.Role.TEACHER, is_active=True,
        )
        source = self.make_class("5ème", "5A", homeroom_teacher=titulaire)

        copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="5A")
        self.assertIsNone(copie.homeroom_teacher)
        # Celui de l'année close garde le sien.
        source.refresh_from_db()
        self.assertEqual(source.homeroom_teacher, titulaire)

    # ── Barèmes de scolarité ─────────────────────────────────────────────────

    def test_le_bareme_de_scolarite_est_reconduit(self):
        source = self.make_class("5ème", "5A")
        self.make_plan(source, amount="135000")

        report = copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="5A")
        plan = TuitionFeePlan.objects.get(school_class=copie)
        self.assertEqual(plan.academic_year, self.next_year)
        item = plan.items.get()
        self.assertEqual(item.male_amount, Decimal("135000.00"))
        self.assertEqual(item.fee_module.academic_year, self.next_year)
        self.assertEqual(item.fee_module.name, "Écolage")
        self.assertEqual(report["fee_plans"], 1)
        self.assertEqual(report["fee_items"], 1)

    def test_les_echeances_des_tranches_sont_decalees_d_un_an(self):
        source = self.make_class("5ème", "5A")
        self.make_plan(source, installments=(
            ("Première tranche", "50", date(2025, 10, 15)),
            ("Seconde tranche", "50", date(2026, 1, 15)),
        ))

        copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="5A")
        echeances = list(
            FeeInstallment.objects
            .filter(class_fee__plan__school_class=copie)
            .order_by("order")
            .values_list("name", "due_date")
        )
        self.assertEqual(echeances, [
            ("Première tranche", date(2026, 10, 15)),
            ("Seconde tranche", date(2027, 1, 15)),
        ])

    def test_le_module_de_frais_n_est_cree_qu_une_fois_pour_toutes_les_classes(self):
        for group in ("5A", "5B"):
            self.make_plan(self.make_class("5ème", group))

        copy_year_settings(self.year, self.next_year)

        self.assertEqual(
            FeeModule.objects.filter(academic_year=self.next_year, name="Écolage").count(), 1,
        )

    def test_un_bareme_deja_saisi_n_est_pas_ecrase(self):
        source = self.make_class("5ème", "5A")
        self.make_plan(source, amount="135000")
        deja = self.make_class("5ème", "5A", year=self.next_year)
        self.make_plan(deja, amount="150000")

        report = copy_year_settings(self.year, self.next_year)

        self.assertEqual(
            TuitionFeePlan.objects.get(school_class=deja).items.get().male_amount,
            Decimal("150000.00"),
        )
        self.assertEqual(report["fee_plans"], 0)

    def test_une_echeance_du_29_fevrier_recule_au_28(self):
        self.assertEqual(shift_years(date(2024, 2, 29), 1), date(2025, 2, 28))
        self.assertEqual(shift_years(date(2025, 3, 1), 1), date(2026, 3, 1))
        self.assertIsNone(shift_years(None, 1))

    # ── Règles de bulletin ───────────────────────────────────────────────────

    def test_une_regle_de_bulletin_visant_des_classes_suit_les_nouvelles(self):
        source = self.make_class("Première", "1A4-1", series="A4")
        regle = SubjectCategoryOrder.objects.create(
            school=self.school, name="Littéraires d'abord",
            scope=SubjectCategoryOrder.Scope.CLASSES,
            categories=["Littéraires", "Scientifiques"],
        )
        regle.classes.add(source)

        report = copy_year_settings(self.year, self.next_year)

        copie = SchoolClass.objects.get(academic_year=self.next_year, group="1A4-1")
        vises = set(regle.classes.values_list("id", flat=True))
        # L'ancienne classe reste visée : les bulletins déjà édités doivent
        # rester lisibles tels qu'ils ont été imprimés.
        self.assertEqual(vises, {source.id, copie.id})
        self.assertEqual(report["report_card_rules"], 1)

    def test_une_regle_d_etablissement_n_a_rien_a_reconduire(self):
        """Elle vaut par école, donc déjà pour l'année suivante."""
        self.make_class("5ème", "5A")
        SubjectCategoryOrder.objects.create(
            school=self.school, scope=SubjectCategoryOrder.Scope.SCHOOL,
            categories=["Scientifiques", "Littéraires"],
        )

        report = copy_year_settings(self.year, self.next_year)

        self.assertEqual(report["report_card_rules"], 0)

    # ── Rejouabilité ─────────────────────────────────────────────────────────

    def test_reconduire_deux_fois_ne_cree_pas_de_doublon(self):
        source = self.make_class("5ème", "5A")
        self.teach(source, self.make_subject("Mathématiques", "maths"))
        self.make_plan(source)

        copy_year_settings(self.year, self.next_year)
        second = copy_year_settings(self.year, self.next_year)

        self.assertEqual(second["classes"], 0)
        self.assertEqual(second["class_subjects"], 0)
        self.assertEqual(second["fee_plans"], 0)
        self.assertEqual(
            SchoolClass.objects.filter(academic_year=self.next_year).count(), 1,
        )
        self.assertEqual(
            TuitionFeePlan.objects.filter(academic_year=self.next_year).count(), 1,
        )

    # ── Reconduction pendant la clôture ──────────────────────────────────────

    def test_la_cloture_reconduit_avant_de_faire_passer_les_eleves(self):
        """Sans année suivante préparée, l'admis atterrit quand même en classe."""
        cinquieme = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A")
        self.teach(cinquieme, self.make_subject("Mathématiques", "maths"))
        enrollment = self.enrol(cinquieme, "ADJO")
        self.decide(enrollment, "12.50")

        closure = close_year(self.year, user=self.staff)

        landed = StudentEnrollment.objects.get(
            academic_year=self.next_year, student=enrollment.student,
        )
        self.assertEqual(landed.school_class.group, "4A")
        self.assertEqual(closure.copied_class_count, 2)
        self.assertEqual(closure.copied_subject_count, 1)
        self.assertEqual(closure.payload["copied"]["classes"], 2)

    def test_le_bilan_de_cloture_annonce_la_reconduction(self):
        source = self.make_class("5ème", "5A")
        self.make_plan(source)
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}/close/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["closure"]["copied"]["classes"], 1)
        self.assertEqual(response.data["closure"]["copied"]["fee_plans"], 1)

    def test_l_apercu_montre_les_classes_a_venir_sans_rien_ecrire(self):
        """La simulation affecte l'élève, puis se défait : rien n'est créé."""
        cinquieme = self.make_class("5ème", "5A")
        self.make_class("4ème", "4A")
        enrollment = self.enrol(cinquieme, "KODJO")
        self.decide(enrollment, "13.00")
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(
            f"/api/schools/{self.school.id}/academic-years/{self.year.id}/closure-preview/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["copied"]["classes"], 2)
        self.assertEqual(response.data["students"][0]["next_class"], "4A")
        self.assertEqual(response.data["unassigned"], 0)
        self.assertEqual(
            SchoolClass.objects.filter(academic_year=self.next_year).count(), 0,
        )
        self.assertFalse(self.year.is_closed)
