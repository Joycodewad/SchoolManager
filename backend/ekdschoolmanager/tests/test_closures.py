"""Clôture d'une session : archive puis verrou."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from ekdschoolmanager.closures import (
    ClosureError,
    close_session,
    closed_session_for_date,
)
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    AttendanceRecord,
    AttendanceSession,
    ClassSubject,
    CustomUser,
    DisciplineRecord,
    GradeEntry,
    GradeLine,
    GradeScheme,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    StudentEnrollment,
    Subject,
)


class SessionClosureTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(username="censeur", password="x")
        self.school = School.objects.create(
            name="Lycée de Lomé", code="lycee-lome", owner=self.staff,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        # Créer une école sème ses niveaux par défaut (signal post_save) :
        # on reprend l'un d'eux plutôt que d'en ajouter un en doublon.
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

        GradeEntry.objects.create(
            line=self.line, enrollment=self.enrollment,
            class_subject=self.class_subject, score=Decimal("14.50"),
            entered_by=self.staff,
        )
        DisciplineRecord.objects.create(
            school=self.school, academic_year=self.year, enrollment=self.enrollment,
            entry_type=DisciplineRecord.EntryType.LATE,
            occurred_on=date(2025, 11, 12), late_hours=Decimal("2"),
        )
        call = AttendanceSession.objects.create(
            school=self.school, academic_year=self.year,
            school_class=self.school_class, taken_on=date(2025, 11, 13),
        )
        AttendanceRecord.objects.create(
            session=call, enrollment=self.enrollment,
            status=AttendanceRecord.Status.ABSENT,
        )

    # ── Archive ──

    def test_cloture_archive_notes_discipline_et_appels(self):
        closure = close_session(self.session, user=self.staff)

        self.assertEqual(closure.grade_entry_count, 1)
        self.assertEqual(closure.discipline_count, 1)
        self.assertEqual(closure.attendance_session_count, 1)
        self.assertEqual(closure.attendance_record_count, 1)

        grade = closure.payload["grades"][0]
        self.assertEqual(grade["score"], "14.50")
        self.assertEqual(grade["subject"], "Mathématiques")
        self.assertEqual(grade["matricule"], "2025TC4003")

        self.assertEqual(closure.payload["discipline"][0]["late_hours"], "2.00")
        self.assertEqual(
            closure.payload["attendance"][0]["records"][0]["status"], "absent",
        )

    def test_cloture_genere_les_bulletins_manquants(self):
        self.assertFalse(ReportCard.objects.filter(session=self.session).exists())
        closure = close_session(self.session, user=self.staff)
        self.assertEqual(closure.report_card_count, 1)
        self.assertTrue(ReportCard.objects.filter(session=self.session).exists())

    def test_cloture_ne_regenere_pas_un_bulletin_existant(self):
        """Une correction faite avant la clôture ne doit pas être écrasée."""
        ReportCard.objects.create(
            session=self.session, enrollment=self.enrollment,
            school_class=self.school_class, payload={"corrige": True},
            general_average=Decimal("18.00"), rank=1,
        )
        close_session(self.session, user=self.staff)
        card = ReportCard.objects.get(session=self.session, enrollment=self.enrollment)
        self.assertEqual(card.payload, {"corrige": True})
        self.assertEqual(card.general_average, Decimal("18.00"))

    # ── Verrou ──

    def test_cloture_bascule_les_drapeaux(self):
        close_session(self.session, user=self.staff)
        self.session.refresh_from_db()
        self.assertTrue(self.session.is_closed)
        self.assertFalse(self.session.is_active)

    def test_deuxieme_cloture_refusee(self):
        close_session(self.session, user=self.staff)
        self.session.refresh_from_db()
        with self.assertRaises(ClosureError):
            close_session(self.session, user=self.staff)

    def test_cloture_refusee_sans_bareme(self):
        self.scheme.delete()
        with self.assertRaises(ClosureError):
            close_session(self.session, user=self.staff)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_closed)

    def test_echec_ne_laisse_pas_de_cloture_partielle(self):
        self.scheme.delete()
        with self.assertRaises(ClosureError):
            close_session(self.session, user=self.staff)
        self.assertFalse(hasattr(self.session, "closure"))
        self.assertFalse(ReportCard.objects.filter(session=self.session).exists())

    # ── Rattachement par date ──

    def test_date_dans_la_periode_close_est_verrouillee(self):
        close_session(self.session, user=self.staff)
        found = closed_session_for_date(self.year, self.school_class, date(2025, 11, 12))
        self.assertEqual(found, self.session)

    def test_date_hors_periode_reste_ouverte(self):
        close_session(self.session, user=self.staff)
        self.assertIsNone(
            closed_session_for_date(self.year, self.school_class, date(2026, 1, 15)),
        )

    def test_date_en_chaine_acceptee(self):
        close_session(self.session, user=self.staff)
        self.assertEqual(
            closed_session_for_date(self.year, self.school_class, "2025-11-12"),
            self.session,
        )

    def test_classe_hors_session_reste_ouverte(self):
        autre = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=self.level, group="TD1",
        )
        close_session(self.session, user=self.staff)
        self.assertIsNone(
            closed_session_for_date(self.year, autre, date(2025, 11, 12)),
        )
