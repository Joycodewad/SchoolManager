"""Copie de la configuration des notes d'une session vers une autre.

Le barème reste propre à chaque session : la copie évite de le ressaisir à
chaque trimestre, sans lier les sessions entre elles. Seule la structure est
copiée — les notes, elles, ne suivent jamais.

La source peut appartenir à une autre année académique : un établissement
garde ses habitudes de notation d'une année sur l'autre, et le barème de l'an
dernier est souvent le meilleur point de départ.
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.closures import close_session
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    ClassSubject,
    CustomUser,
    GradeEntry,
    GradeGroup,
    GradeLine,
    GradeScheme,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
    Subject,
)


class SchemeCopyTests(APITestCase):
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
        subject = Subject.objects.create(school=self.school, name="Mathématiques")
        self.class_subject = ClassSubject.objects.create(
            school_class=self.school_class, subject=subject,
            coefficient=Decimal("4"), weekly_hours=4,
        )

        self.t1 = self.make_session("Trimestre 1", date(2025, 10, 1), date(2025, 12, 20))
        self.t2 = self.make_session("Trimestre 2", date(2026, 1, 5), date(2026, 3, 20))

        # Source : deux groupes pondérés, trois lignes.
        self.source = GradeScheme.objects.create(
            session=self.t1,
            calculation_method=GradeScheme.CalculationMethod.GROUPS,
            created_by=self.staff,
        )
        continu = GradeGroup.objects.create(
            scheme=self.source, name="Contrôle continu",
            weight=Decimal("40.00"), order=1,
        )
        examen = GradeGroup.objects.create(
            scheme=self.source, name="Examen", weight=Decimal("60.00"), order=2,
        )
        GradeLine.objects.create(
            scheme=self.source, group=continu, name="Interrogation",
            weight=Decimal("50.00"), max_score=Decimal("20"), order=1,
        )
        GradeLine.objects.create(
            scheme=self.source, group=continu, name="Devoir",
            weight=Decimal("50.00"), max_score=Decimal("20"), order=2,
        )
        GradeLine.objects.create(
            scheme=self.source, group=examen, name="Composition",
            weight=Decimal("100.00"), max_score=Decimal("20"), order=3,
        )

        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}

    def make_session(self, name, start, end):
        session = AcademicSession.objects.create(
            academic_year=self.year, name=name, label=name[:2],
            start_date=start, end_date=end, is_active=True,
        )
        session.classes.add(self.school_class)
        return session

    def copy_url(self, target):
        return (
            f"/api/schools/{self.school.id}/grades/sessions/{target.id}/scheme/"
        )

    def copy(self, target, source):
        return self.client.post(
            self.copy_url(target), {"source": source.id},
            format="json", **self.headers,
        )

    def enrol(self):
        student = CustomUser.objects.create_user(username="eleve1", password="x")
        return StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            school_class=self.school_class, level=self.level,
            enrollment_number="2025TC4003", status=StudentEnrollment.Status.ACTIVE,
        )

    # ── Cas nominal ──

    def test_copie_reproduit_groupes_et_lignes(self):
        response = self.copy(self.t2, self.t1)
        self.assertEqual(response.status_code, 201)

        copy = GradeScheme.objects.get(session=self.t2)
        self.assertEqual(copy.calculation_method, GradeScheme.CalculationMethod.GROUPS)
        self.assertEqual(
            [(g.name, str(g.weight), g.order) for g in copy.groups.order_by("order")],
            [("Contrôle continu", "40.00", 1), ("Examen", "60.00", 2)],
        )
        self.assertEqual(
            [(l.name, str(l.weight), str(l.max_score), l.order)
             for l in copy.lines.order_by("order")],
            [("Interrogation", "50.00", "20.00", 1),
             ("Devoir", "50.00", "20.00", 2),
             ("Composition", "100.00", "20.00", 3)],
        )

    def test_les_lignes_restent_dans_leur_groupe(self):
        self.copy(self.t2, self.t1)
        copy = GradeScheme.objects.get(session=self.t2)
        par_groupe = {
            group.name: sorted(line.name for line in group.lines.all())
            for group in copy.groups.all()
        }
        self.assertEqual(par_groupe, {
            "Contrôle continu": ["Devoir", "Interrogation"],
            "Examen": ["Composition"],
        })

    def test_la_copie_est_independante_de_la_source(self):
        """Deux barèmes distincts : modifier l'un ne touche pas l'autre."""
        self.copy(self.t2, self.t1)
        copy = GradeScheme.objects.get(session=self.t2)
        self.assertNotEqual(copy.pk, self.source.pk)
        self.assertFalse(
            set(copy.lines.values_list("pk", flat=True))
            & set(self.source.lines.values_list("pk", flat=True))
        )

    def test_les_notes_ne_sont_pas_copiees(self):
        enrollment = self.enrol()
        GradeEntry.objects.create(
            line=self.source.lines.first(), enrollment=enrollment,
            class_subject=self.class_subject, score=Decimal("14"),
            entered_by=self.staff,
        )
        self.copy(self.t2, self.t1)
        copy = GradeScheme.objects.get(session=self.t2)
        self.assertFalse(GradeEntry.objects.filter(line__scheme=copy).exists())
        # La source garde la sienne.
        self.assertEqual(GradeEntry.objects.filter(line__scheme=self.source).count(), 1)

    def test_copie_remplace_une_configuration_vierge(self):
        vierge = GradeScheme.objects.create(
            session=self.t2,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        GradeLine.objects.create(
            scheme=vierge, name="À jeter", max_score=Decimal("20"), order=1,
        )
        response = self.copy(self.t2, self.t1)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(GradeScheme.objects.filter(session=self.t2).count(), 1)
        self.assertFalse(
            GradeLine.objects.filter(scheme__session=self.t2, name="À jeter").exists()
        )

    # ── Refus ──

    def test_copie_refusee_si_la_destination_porte_des_notes(self):
        """Remplacer un barème déjà noté détruirait les notes en cascade."""
        cible = GradeScheme.objects.create(
            session=self.t2,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        line = GradeLine.objects.create(
            scheme=cible, name="Devoir", max_score=Decimal("20"), order=1,
        )
        GradeEntry.objects.create(
            line=line, enrollment=self.enrol(), class_subject=self.class_subject,
            score=Decimal("11"), entered_by=self.staff,
        )
        response = self.copy(self.t2, self.t1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("notes", str(response.data))
        self.assertTrue(GradeEntry.objects.filter(line=line).exists())

    def test_copie_refusee_vers_une_session_cloturee(self):
        GradeScheme.objects.create(
            session=self.t2,
            calculation_method=GradeScheme.CalculationMethod.EQUAL,
            created_by=self.staff,
        )
        close_session(self.t2, user=self.staff)
        self.t2.refresh_from_db()
        response = self.copy(self.t2, self.t1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("clôturée", str(response.data))

    def test_copie_refusee_si_la_source_n_a_pas_de_configuration(self):
        t3 = self.make_session("Trimestre 3", date(2026, 4, 1), date(2026, 6, 20))
        response = self.copy(self.t2, t3)
        self.assertEqual(response.status_code, 400)
        self.assertIn("pas de configuration", str(response.data))

    def test_copie_sur_elle_meme_refusee(self):
        response = self.copy(self.t1, self.t1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("identiques", str(response.data))

    def test_source_absente_refusee(self):
        response = self.client.post(
            self.copy_url(self.t2), {}, format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    # ── D'une année à l'autre ──

    def previous_year(self):
        """Une année passée avec son trimestre configuré."""
        year = AcademicYear.objects.create(
            school=self.school, name="2024-2025",
            start_date=date(2024, 9, 1), end_date=date(2025, 6, 30), is_closed=True,
        )
        session = AcademicSession.objects.create(
            academic_year=year, name="Trimestre 3 (2024-2025)", label="T3",
            start_date=date(2025, 4, 1), end_date=date(2025, 6, 20),
            is_active=False, is_closed=True,
        )
        scheme = GradeScheme.objects.create(
            session=session,
            calculation_method=GradeScheme.CalculationMethod.WEIGHTED,
            created_by=self.staff,
        )
        GradeLine.objects.create(
            scheme=scheme, name="Composition unique",
            weight=Decimal("100.00"), max_score=Decimal("20"), order=1,
        )
        return year, session

    def test_la_configuration_de_l_an_dernier_se_reprend(self):
        _, ancienne = self.previous_year()

        response = self.copy(self.t2, ancienne)

        self.assertEqual(response.status_code, 201, response.data)
        copie = GradeScheme.objects.get(session=self.t2)
        self.assertEqual(
            copie.calculation_method, GradeScheme.CalculationMethod.WEIGHTED,
        )
        self.assertEqual(
            list(copie.lines.values_list("name", flat=True)), ["Composition unique"],
        )

    def test_une_session_close_reste_une_source_valable(self):
        """On reprend son barème sans la rouvrir : rien n'y est écrit."""
        _, ancienne = self.previous_year()
        self.copy(self.t2, ancienne)
        ancienne.refresh_from_db()
        self.assertTrue(ancienne.is_closed)
        self.assertEqual(ancienne.grade_scheme.lines.count(), 1)

    def test_une_session_d_une_autre_ecole_est_refusee(self):
        autre = School.objects.create(
            name="Lycée de Kara", code="lycee-kara", owner=self.staff,
        )
        annee = AcademicYear.objects.create(
            school=autre, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30),
        )
        session = AcademicSession.objects.create(
            academic_year=annee, name="Trimestre 1", label="T1",
            start_date=date(2025, 10, 1), end_date=date(2025, 12, 20),
        )

        response = self.copy(self.t2, session)

        self.assertEqual(response.status_code, 400)
        self.assertIn("invalide", str(response.data))

    # ── Sources proposées ──

    def test_les_sources_sont_groupees_par_annee_la_plus_recente_d_abord(self):
        annee, ancienne = self.previous_year()

        response = self.client.get(
            f"/api/schools/{self.school.id}/grades/scheme-sources/", **self.headers,
        )

        self.assertEqual(response.status_code, 200, response.data)
        annees = response.data["years"]
        self.assertEqual([row["name"] for row in annees], ["2025-2026", "2024-2025"])
        self.assertTrue(annees[0]["is_active"])
        # Seules les sessions déjà configurées sont proposées.
        self.assertEqual([row["id"] for row in annees[0]["sessions"]], [self.t1.id])
        self.assertEqual([row["id"] for row in annees[1]["sessions"]], [ancienne.id])
        self.assertTrue(annees[1]["sessions"][0]["is_closed"])
        self.assertEqual(annee.name, "2024-2025")

    # ── Contexte ──

    def test_les_contextes_signalent_les_sessions_configurees(self):
        response = self.client.get(
            f"/api/schools/{self.school.id}/grades/contexts/", **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        par_id = {row["id"]: row for row in response.data["sessions"]}
        self.assertTrue(par_id[self.t1.id]["has_scheme"])
        self.assertFalse(par_id[self.t2.id]["has_scheme"])
