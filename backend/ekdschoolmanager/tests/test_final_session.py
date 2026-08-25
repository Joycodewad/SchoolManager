"""Désignation de la dernière session de l'année.

La moyenne annuelle ne s'imprime que sur le bulletin de la dernière session.
Une école peut désigner cette session elle-même — un trimestre de rattrapage
ne clôt pas forcément l'année — et, à défaut, la dernière du calendrier fait
foi comme avant l'arrivée du champ.
"""

from datetime import date

from django.test import TestCase

from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    CustomUser,
    School,
    SchoolClass,
    SchoolLevel,
)
from ekdschoolmanager.reportcards import annual_average, term_history
from ekdschoolmanager.serializers import AcademicSessionSerializer


class FinalSessionTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="censeur", password="x", role=CustomUser.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Lycée de Lomé", code="lycee-lome", owner=self.staff,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_active=True,
        )
        level = SchoolLevel.objects.filter(
            school=self.school, stage=SchoolLevel.Stage.HIGH,
        ).first()
        self.school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=level, group="TC4",
        )
        self.sessions = []
        for index, (name, start, end) in enumerate((
            ("Premier Trimestre", date(2025, 9, 1), date(2025, 12, 20)),
            ("Deuxième Trimestre", date(2026, 1, 5), date(2026, 3, 28)),
            ("Rattrapage", date(2026, 4, 6), date(2026, 6, 30)),
        )):
            session = AcademicSession.objects.create(
                academic_year=self.year, name=name, label=name,
                start_date=start, end_date=end, is_active=index == 0,
            )
            session.classes.add(self.school_class)
            self.sessions.append(session)

    def history(self, session):
        return term_history(session, self.school_class, [])

    def test_no_annual_average_until_a_session_is_designated(self):
        """Sans désignation, aucune session ne porte la moyenne annuelle.

        Être dernière au calendrier ne suffit pas : le bulletin se contente
        alors du rappel des sessions déjà éditées.
        """
        self.assertEqual(
            [self.history(session)["is_final"] for session in self.sessions],
            [False, False, False],
        )

    def test_past_sessions_are_recalled_even_without_designation(self):
        """Le rappel des sessions passées, lui, ne dépend d'aucun réglage."""
        history = self.history(self.sessions[1])
        self.assertEqual(
            [term["name"] for term in history["terms"]],
            ["Premier Trimestre", "Deuxième Trimestre"],
        )
        self.assertFalse(history["is_final"])

    def test_designated_session_carries_the_annual_average(self):
        """Le deuxième trimestre désigné clôt l'année, pas le rattrapage."""
        self.sessions[1].is_final = True
        self.sessions[1].save(update_fields=["is_final"])
        self.assertEqual(
            [self.history(session)["is_final"] for session in self.sessions],
            [False, True, False],
        )

    def test_single_designated_session_carries_annual_average(self):
        """Une classe à session unique désignée porte quand même la moyenne."""
        for session in self.sessions[1:]:
            session.classes.clear()
        only = self.sessions[0]
        self.assertFalse(self.history(only)["is_final"])
        only.is_final = True
        only.save(update_fields=["is_final"])
        self.assertTrue(self.history(only)["is_final"])

    def test_annual_average_covers_the_edited_sessions(self):
        """La moyenne annuelle est la moyenne des bulletins déjà édités."""
        self.assertEqual(
            annual_average([{"average": "12.50"}, {"average": "13.50"}]), "13.00",
        )
        self.assertIsNone(annual_average([{"average": None}]))

    def test_two_final_sessions_for_the_same_class_are_refused(self):
        """Deux dernières sessions pour une même classe se contrediraient."""
        self.sessions[1].is_final = True
        self.sessions[1].save(update_fields=["is_final"])
        serializer = AcademicSessionSerializer(
            self.sessions[2], data={"is_final": True}, partial=True,
            context={"academic_year": self.year},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("is_final", serializer.errors)

    def test_session_stays_editable_when_it_is_the_designated_one(self):
        """Rééditer la session finale ne la met pas en conflit avec elle-même."""
        self.sessions[1].is_final = True
        self.sessions[1].save(update_fields=["is_final"])
        serializer = AcademicSessionSerializer(
            self.sessions[1], data={"label": "Deuxième Trimestre "}, partial=True,
            context={"academic_year": self.year},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
