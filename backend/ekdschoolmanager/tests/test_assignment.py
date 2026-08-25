"""Répartition des élèves sans classe, et ses règles.

Chaque règle de l'établissement est vérifiée sur un cas où elle se voit : des
effectifs de départ inégaux, des filles mal réparties, des moyennes étagées,
des classes pleines. Les scénarios reprennent la forme d'un vrai niveau —
quatre classes de 4ème, une centaine d'élèves à placer.
"""

from datetime import date
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.assignment import (
    attach_fallback_averages, band_counts, band_of, distribute_group,
    effective_average, natural_class_key, rules_for, stream_key,
    unassigned_students,
)
from ekdschoolmanager.models import (
    AcademicSession,
    AcademicYear,
    ClassAssignmentSettings,
    CustomUser,
    ReportCard,
    School,
    SchoolClass,
    SchoolLevel,
    SchoolMembership,
    StudentEnrollment,
)


class AssignmentBase(APITestCase):
    """Un niveau de 4ème, ses classes et ses élèves : décor commun."""

    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="proviseur", password="x", role=CustomUser.Role.PROVISEUR,
        )
        self.school = School.objects.create(
            name="Lycée d'Amou-Oblo", code="lycee-amou-oblo", owner=self.staff,
        )
        SchoolMembership.objects.create(
            school=self.school, user=self.staff,
            role=CustomUser.Role.PROVISEUR, is_active=True,
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2026-2027",
            start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_active=True,
        )
        self.level = SchoolLevel.objects.get(school=self.school, name="4ème")
        self.rules = rules_for(self.school)
        self.counter = 0

    # ── Fabriques ────────────────────────────────────────────────────────────

    def make_class(self, group, capacity=50, effectif=0, series="", level=None):
        school_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.year, level=level or self.level,
            series=series, group=group, maximum_capacity=capacity,
        )
        # `effectif` est annoté par la vue : on le pose comme elle le ferait.
        school_class.effectif = effectif
        return school_class

    def make_student(self, average=None, born=2012, gender="M", series="", level=None):
        self.counter += 1
        student = CustomUser.objects.create_user(
            username=f"eleve{self.counter}", password="x",
            role=CustomUser.Role.STUDENT,
        )
        student.gender, student.date_of_birth = gender, date(born, 6, 1)
        student.save()
        return StudentEnrollment.objects.create(
            school=self.school, academic_year=self.year, student=student,
            level=level or self.level, series=series,
            enrollment_number=f"2026-{self.counter:04d}",
            previous_average=Decimal(average) if average is not None else None,
            status=StudentEnrollment.Status.ACTIVE,
        )

    def spread(self, classes, students, girls_before=None):
        allocations = distribute_group(
            classes, students, girls_before or {}, self.rules,
        )
        ordered = sorted(classes, key=natural_class_key)
        return ordered, allocations

    def counts(self, classes, allocations, girls_before=None):
        girls_before = girls_before or {}
        return [
            (
                school_class.group,
                school_class.effectif + len(allocations[school_class.pk]),
                girls_before.get(school_class.pk, 0) + sum(
                    1 for row in allocations[school_class.pk]
                    if row.student.gender == "F"
                ),
            )
            for school_class in sorted(classes, key=natural_class_key)
        ]


class AssignmentRulesTests(AssignmentBase):
    # ── Effectifs ────────────────────────────────────────────────────────────

    def test_les_effectifs_du_niveau_finissent_dans_le_meme_ordre_de_grandeur(self):
        classes = [
            self.make_class("4A", effectif=25), self.make_class("4B", effectif=40),
            self.make_class("4C", effectif=35), self.make_class("4D", effectif=40),
        ]
        students = [self.make_student(average="10") for _ in range(20)]

        ordered, allocations = self.spread(classes, students)

        totals = [total for _, total, _ in self.counts(ordered, allocations)]
        self.assertEqual(sum(totals), 25 + 40 + 35 + 40 + 20)
        self.assertLessEqual(max(totals) - min(totals), 1, totals)

    def test_la_classe_la_moins_remplie_se_remplit_la_premiere(self):
        classes = [self.make_class("4A", effectif=10), self.make_class("4B", effectif=30)]
        students = [self.make_student(average="10") for _ in range(4)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual([len(allocations[c.pk]) for c in ordered], [4, 0])

    def test_sans_equilibrage_les_classes_se_remplissent_l_une_apres_l_autre(self):
        self.rules.balance_headcount = False
        classes = [self.make_class("4A", capacity=3), self.make_class("4B", capacity=3)]
        students = [self.make_student(average="10") for _ in range(4)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual([len(allocations[c.pk]) for c in ordered], [3, 1])

    # ── Filles ───────────────────────────────────────────────────────────────

    def test_les_filles_sont_reparties_comme_les_effectifs(self):
        classes = [self.make_class("4A"), self.make_class("4B"), self.make_class("4C")]
        students = (
            [self.make_student(average="10", gender="F") for _ in range(12)]
            + [self.make_student(average="10", gender="M") for _ in range(12)]
        )

        ordered, allocations = self.spread(classes, students)

        girls = [girls for _, _, girls in self.counts(ordered, allocations)]
        self.assertEqual(girls, [4, 4, 4])

    def test_les_filles_deja_inscrites_comptent_dans_l_equilibre(self):
        """Une classe qui compte déjà beaucoup de filles en reçoit moins."""
        classes = [self.make_class("4A", effectif=10), self.make_class("4B", effectif=10)]
        girls_before = {classes[0].pk: 8, classes[1].pk: 2}
        students = (
            [self.make_student(average="10", gender="F") for _ in range(6)]
            + [self.make_student(average="10", gender="M") for _ in range(6)]
        )

        ordered, allocations = self.spread(classes, students, girls_before)

        girls = [girls for _, _, girls in self.counts(ordered, allocations, girls_before)]
        self.assertEqual(girls, [8, 8])

    def test_sans_equilibrage_des_filles_le_rang_seul_decide(self):
        self.rules.balance_girls = False
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = (
            [self.make_student(average="18", gender="F") for _ in range(2)]
            + [self.make_student(average="8", gender="M") for _ in range(2)]
        )

        ordered, allocations = self.spread(classes, students)

        # Les deux meilleures — deux filles — ouvrent la première classe.
        self.assertEqual(
            [row.student.gender for row in allocations[ordered[0].pk]], ["F", "F"],
        )

    # ── Rang, âge et réserve ─────────────────────────────────────────────────

    def test_les_meilleures_moyennes_ouvrent_les_premieres_classes(self):
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (7, 15, 9, 13)]

        ordered, allocations = self.spread(classes, students)

        moyennes = [
            [float(row.previous_average) for row in allocations[c.pk]] for c in ordered
        ]
        self.assertEqual(moyennes, [[15.0, 13.0], [9.0, 7.0]])

    def test_a_moyenne_egale_le_plus_jeune_passe_devant(self):
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        aine = self.make_student(average="12", born=2010)
        cadet = self.make_student(average="12", born=2013)

        ordered, allocations = self.spread(classes, [aine, cadet])

        self.assertEqual(allocations[ordered[0].pk], [cadet])
        self.assertEqual(allocations[ordered[1].pk], [aine])

    def test_la_reserve_place_les_tout_meilleurs_dans_les_dernieres_classes(self):
        """Sans elle, la dernière classe n'aurait aucun bon élève."""
        self.rules.reserved_excellent = 1
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 18, 8, 7)]

        ordered, allocations = self.spread(classes, students)

        derniere = [float(row.previous_average) for row in allocations[ordered[1].pk]]
        self.assertIn(19.0, derniere)

    def test_une_reserve_a_zero_laisse_les_meilleurs_devant(self):
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 18, 8, 7)]

        ordered, allocations = self.spread(classes, students)

        premiere = [float(row.previous_average) for row in allocations[ordered[0].pk]]
        self.assertEqual(premiere, [19.0, 18.0])

    def test_le_seuil_d_excellence_est_reglable(self):
        """À 14, un élève de 15 entre dans la réserve ; à 16, non."""
        self.rules.reserved_excellent = 1
        self.rules.excellent_minimum = Decimal("14")
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (15, 14, 8, 7)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(
            [float(row.previous_average) for row in allocations[ordered[1].pk]], [15.0, 7.0],
        )

    def test_un_eleve_sans_moyenne_passe_en_dernier(self):
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        connu = self.make_student(average="5")
        inconnu = self.make_student(average=None)

        ordered, allocations = self.spread(classes, [inconnu, connu])

        self.assertEqual(allocations[ordered[0].pk], [connu])
        self.assertEqual(allocations[ordered[1].pk], [inconnu])

    # ── Capacité ─────────────────────────────────────────────────────────────

    def test_le_maximum_est_legerement_depasse_quand_tout_est_plein(self):
        self.rules.overflow_margin = 5
        classes = [self.make_class("4A", capacity=10, effectif=10),
                   self.make_class("4B", capacity=10, effectif=10)]
        students = [self.make_student(average="10") for _ in range(6)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual([len(allocations[c.pk]) for c in ordered], [3, 3])

    def test_le_depassement_reste_borne(self):
        self.rules.overflow_margin = 2
        classes = [self.make_class("4A", capacity=10, effectif=10)]
        students = [self.make_student(average="10") for _ in range(6)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(len(allocations[ordered[0].pk]), 2)

    def test_sans_depassement_les_eleves_restent_sans_classe(self):
        self.rules.allow_overflow = False
        classes = [self.make_class("4A", capacity=10, effectif=10)]
        students = [self.make_student(average="10") for _ in range(3)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(len(allocations[ordered[0].pk]), 0)

    def test_le_maximum_est_respecte_tant_qu_il_reste_de_la_place(self):
        classes = [self.make_class("4A", capacity=10, effectif=10),
                   self.make_class("4B", capacity=10, effectif=2)]
        students = [self.make_student(average="10") for _ in range(5)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual([len(allocations[c.pk]) for c in ordered], [0, 5])

    # ── Ordre des classes ────────────────────────────────────────────────────

    def test_les_classes_numerotees_suivent_l_ordre_des_nombres(self):
        classes = [self.make_class("TD-10"), self.make_class("TD-2"), self.make_class("TD-1")]
        self.assertEqual(
            [c.group for c in sorted(classes, key=natural_class_key)],
            ["TD-1", "TD-2", "TD-10"],
        )


class BandLimitTests(AssignmentBase):
    """Plafonner le nombre d'élèves d'une tranche de moyenne par classe.

    Équilibrer les effectifs ne suffit pas : trois classes de 35 dont l'une
    concentre tous les élèves à plus de 16 restent déséquilibrées. Le plafond
    étale les tranches — sans jamais laisser un élève sans classe.
    """

    def limit(self, level=None, series="", **caps):
        """Plafonne des tranches sur un cursus — la 4ème sans série par défaut."""
        target = level or self.level
        self.rules.band_limits = {
            stream_key(target.id, series): {
                str(key): value for key, value in caps.items()
            },
        }

    def averages_in(self, allocations, school_class):
        return sorted(
            float(effective_average(row)) for row in allocations[school_class.pk]
        )

    def test_la_tranche_haute_s_etale_au_lieu_de_se_concentrer(self):
        self.rules.reserved_excellent = 0
        self.limit(**{"18": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(self.averages_in(allocations, ordered[0]), [8.0, 19.0])
        self.assertEqual(self.averages_in(allocations, ordered[1]), [8.0, 19.0])

    def test_sans_plafond_la_tranche_se_concentre_devant(self):
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(self.averages_in(allocations, ordered[0]), [19.0, 19.0])

    def test_chaque_tranche_a_son_propre_plafond(self):
        self.rules.reserved_excellent = 0
        self.limit(**{"18": 1, "14": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 19, 15, 15)]

        ordered, allocations = self.spread(classes, students)

        for school_class in ordered:
            self.assertEqual(self.averages_in(allocations, school_class), [15.0, 19.0])

    def test_le_plafond_cede_plutot_que_de_laisser_un_eleve_sans_classe(self):
        """Cinq élèves à 19, deux classes, plafond à 1 : personne n'est laissé."""
        self.rules.reserved_excellent = 0
        self.limit(**{"18": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average="19") for _ in range(5)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(
            sum(len(allocations[c.pk]) for c in ordered), 5,
        )

    def test_un_plafond_a_zero_ne_limite_rien(self):
        self.rules.reserved_excellent = 0
        self.limit(**{"18": 0})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(self.averages_in(allocations, ordered[0]), [19.0, 19.0])

    def test_les_eleves_sous_douze_ne_sont_jamais_plafonnes(self):
        self.rules.reserved_excellent = 0
        self.limit(**{"18": 1, "16": 1, "14": 1, "12": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average="8") for _ in range(4)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual([len(allocations[c.pk]) for c in ordered], [2, 2])

    def test_la_reserve_respecte_le_plafond(self):
        """Elle ne peut pas entasser trois élèves de 18+ dans une classe."""
        self.rules.reserved_excellent = 3
        self.rules.excellent_minimum = Decimal("16")
        self.limit(**{"18": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average="19") for _ in range(6)]

        ordered, allocations = self.spread(classes, students)

        # Le plafond a cédé au second passage, mais l'étalement a eu lieu :
        # trois de chaque côté au lieu de tout dans la même classe.
        self.assertEqual([len(allocations[c.pk]) for c in ordered], [3, 3])

    def test_le_plafond_d_un_autre_niveau_ne_s_applique_pas(self):
        """Dix-sept élèves en 12-14 ne se traitent pas pareil selon le niveau."""
        self.rules.reserved_excellent = 0
        self.limit(level=SchoolLevel.objects.get(school=self.school, name="3ème"),
                   **{"18": 1})
        classes = [self.make_class("4A"), self.make_class("4B")]
        students = [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        ordered, allocations = self.spread(classes, students)

        # Le plafond vise la 3ème : la 4ème répartit sans contrainte.
        self.assertEqual(self.averages_in(allocations, ordered[0]), [19.0, 19.0])

    def test_une_serie_a_son_propre_plafond(self):
        """Une 1ère D ne se règle pas comme une 1ère A4."""
        self.rules.reserved_excellent = 0
        premiere = SchoolLevel.objects.get(school=self.school, name="Première")
        self.limit(level=premiere, series="A4", **{"18": 1})

        def quatre_eleves():
            return [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        litteraires, alloc_a4 = self.spread([
            self.make_class("1A4-1", series="A4", level=premiere),
            self.make_class("1A4-2", series="A4", level=premiere),
        ], quatre_eleves())
        scientifiques, alloc_d = self.spread([
            self.make_class("1D-1", series="D", level=premiere),
            self.make_class("1D-2", series="D", level=premiere),
        ], quatre_eleves())

        # A4 plafonnée : les deux 19 se séparent. D non réglée : ils restent
        # ensemble dans la première classe.
        self.assertEqual(self.averages_in(alloc_a4, litteraires[0]), [8.0, 19.0])
        self.assertEqual(self.averages_in(alloc_d, scientifiques[0]), [19.0, 19.0])

    def test_le_plafond_du_niveau_sans_serie_sert_de_repli(self):
        """Un réglage posé sans série vaut pour les séries non réglées."""
        self.rules.reserved_excellent = 0
        premiere = SchoolLevel.objects.get(school=self.school, name="Première")
        self.limit(level=premiere, **{"18": 1})
        classes = [
            self.make_class("1D-1", series="D", level=premiere),
            self.make_class("1D-2", series="D", level=premiere),
        ]
        students = [self.make_student(average=str(note)) for note in (19, 19, 8, 8)]

        ordered, allocations = self.spread(classes, students)

        self.assertEqual(self.averages_in(allocations, ordered[0]), [8.0, 19.0])

    def test_la_tranche_d_un_eleve_se_lit_sur_la_moyenne_retenue(self):
        self.assertEqual(band_of(self.make_student(average="20")), "18")
        self.assertEqual(band_of(self.make_student(average="18")), "18")
        self.assertEqual(band_of(self.make_student(average="17.99")), "16")
        self.assertEqual(band_of(self.make_student(average="12")), "12")
        self.assertIsNone(band_of(self.make_student(average="11.99")))
        self.assertIsNone(band_of(self.make_student(average=None)))


class FallbackAverageTests(AssignmentBase):
    """Retrouver la moyenne d'un élève qui n'en a pas de saisie.

    Un élève réinscrit par la clôture arrive sans moyenne sur sa fiche :
    personne ne la recopie. Elle est pourtant dans ses bulletins de l'an
    dernier — note d'examen s'il en a passé un, moyenne annuelle sinon.
    """

    def setUp(self):
        super().setUp()
        self.last_year = AcademicYear.objects.create(
            school=self.school, name="2025-2026",
            start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_closed=True,
        )
        self.last_class = SchoolClass.objects.create(
            school=self.school, academic_year=self.last_year,
            level=SchoolLevel.objects.get(school=self.school, name="3ème"), group="3A",
        )

    def with_history(self, averages, exam=None):
        """Un élève sans moyenne saisie, mais avec les bulletins de l'an dernier."""
        enrollment = self.make_student(average=None)
        previous = StudentEnrollment.objects.create(
            school=self.school, academic_year=self.last_year,
            student=enrollment.student, school_class=self.last_class,
            level=self.last_class.level, enrollment_number=f"2025-{enrollment.pk}",
            status=StudentEnrollment.Status.ACTIVE,
        )
        for index, average in enumerate(averages, start=1):
            session = AcademicSession.objects.create(
                academic_year=self.last_year, name=f"Trimestre {index}", label=f"T{index}",
                start_date=date(2025, 9, 1 + index), end_date=date(2025, 10, 1 + index),
                is_active=False, is_closed=True, is_final=index == len(averages),
            )
            ReportCard.objects.create(
                session=session, enrollment=previous, school_class=self.last_class,
                general_average=Decimal(average), payload={},
                exam_average=Decimal(exam) if exam and index == len(averages) else None,
            )
        return enrollment

    def resolve(self, *students):
        attach_fallback_averages(self.school, self.year, list(students))
        return students

    def test_la_moyenne_annuelle_de_l_an_dernier_prend_le_relais(self):
        enrollment, = self.resolve(self.with_history(["10", "12", "14"]))
        self.assertEqual(effective_average(enrollment), Decimal("12.00"))
        self.assertEqual(enrollment.average_source, "annuelle")

    def test_la_note_d_examen_prime_sur_la_moyenne_annuelle(self):
        enrollment, = self.resolve(self.with_history(["10", "12", "14"], exam="16"))
        self.assertEqual(effective_average(enrollment), Decimal("16"))
        self.assertEqual(enrollment.average_source, "examen")

    def test_sans_note_d_examen_on_retombe_sur_la_moyenne_annuelle(self):
        enrollment, = self.resolve(self.with_history(["8", "10"], exam=None))
        self.assertEqual(effective_average(enrollment), Decimal("9.00"))
        self.assertEqual(enrollment.average_source, "annuelle")

    def test_la_moyenne_saisie_reste_prioritaire(self):
        enrollment = self.with_history(["18", "18"], exam="19")
        enrollment.previous_average = Decimal("11")
        enrollment.save(update_fields=["previous_average"])
        enrollment, = self.resolve(enrollment)
        self.assertEqual(effective_average(enrollment), Decimal("11"))
        self.assertEqual(enrollment.average_source, "saisie")

    def test_un_eleve_sans_passe_dans_l_ecole_reste_sans_moyenne(self):
        enrollment, = self.resolve(self.make_student(average=None))
        self.assertIsNone(effective_average(enrollment))
        self.assertEqual(enrollment.average_source, "")

    def test_la_moyenne_retrouvee_classe_l_eleve(self):
        """Elle vaut la moyenne saisie : c'est elle qui décide du rang."""
        self.rules.reserved_excellent = 0
        classes = [self.make_class("4A"), self.make_class("4B")]
        fort = self.with_history(["17", "17"])
        faible = self.make_student(average="6")
        self.resolve(fort, faible)

        ordered, allocations = self.spread(classes, [faible, fort])

        self.assertEqual(allocations[ordered[0].pk], [fort])

    def test_les_tranches_comptent_les_moyennes_retenues(self):
        students = [
            self.make_student(average="19"), self.make_student(average="18"),
            self.make_student(average="17"), self.make_student(average="15"),
            self.make_student(average="13"), self.make_student(average="9"),
            self.with_history(["16", "16"]), self.make_student(average=None),
        ]
        self.resolve(*students)

        counts = band_counts(students)

        self.assertEqual(counts["total"], 8)
        self.assertEqual(counts["without_average"], 1)
        self.assertEqual(
            [(row["label"], row["count"]) for row in counts["bands"]],
            [("18 à 20", 2), ("16 à 18", 2), ("14 à 16", 1), ("12 à 14", 1)],
        )

    def test_la_liste_des_eleves_sans_classe_annonce_la_moyenne_retrouvee(self):
        enrollment = self.with_history(["10", "12", "14"], exam="15")
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(
            f"/api/schools/{self.school.id}/enrollments/unassigned/",
            **{"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)},
        )

        self.assertEqual(response.status_code, 200, response.data)
        row = next(r for r in response.data if r["id"] == enrollment.pk)
        self.assertIsNone(row["previous_average"])
        # Deux décimales, comme la moyenne saisie : même colonne, même forme.
        self.assertEqual(row["effective_average"], "15.00")
        self.assertEqual(row["average_source"], "examen")

    def test_un_eleve_parti_ne_compte_pas_dans_les_tranches(self):
        reste = self.make_student(average="19")
        parti = self.make_student(average="19")
        parti.student.student_status = CustomUser.StudentStatus.DROPPED_OUT
        parti.student.save(update_fields=["student_status"])

        students = list(unassigned_students(self.school, self.year))

        self.assertEqual([row.pk for row in students], [reste.pk])


class AssignmentSettingsApiTests(AssignmentBase):
    """Le paramétrage : qui le lit, qui le modifie."""

    def setUp(self):
        super().setUp()
        self.url = f"/api/schools/{self.school.id}/enrollments/assignment-settings/"
        self.headers = {"HTTP_X_ACADEMIC_YEAR_ID": str(self.year.id)}

    def sign_in(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def member(self, role):
        user = CustomUser.objects.create_user(
            username=f"u{role}", password="x", role=role,
        )
        SchoolMembership.objects.create(
            school=self.school, user=user, role=role, is_active=True,
        )
        return user

    def test_les_tranches_sont_detaillees_niveau_par_niveau(self):
        """Deux élèves à 18 répartis sur deux niveaux ne posent pas le même
        problème que les deux mêmes dans un seul."""
        self.sign_in(self.staff)
        troisieme = SchoolLevel.objects.get(school=self.school, name="3ème")
        for note in ("19", "13"):
            self.make_student(average=note)
        for note in ("19", "15"):
            enrollment = self.make_student(average=note)
            enrollment.level = troisieme
            enrollment.save(update_fields=["level"])

        response = self.client.get(self.url, **self.headers)

        niveaux = {row["label"]: row for row in response.data["levels"]}
        self.assertEqual(set(niveaux), {"4ème", "3ème"})
        self.assertEqual(niveaux["4ème"]["total"], 2)
        # La clé du cursus accompagne la ligne : c'est elle qui porte les
        # plafonds.
        self.assertEqual(niveaux["3ème"]["level"], troisieme.id)
        self.assertEqual(niveaux["3ème"]["key"], stream_key(troisieme.id, ""))

    def test_deux_series_d_un_meme_niveau_font_deux_lignes(self):
        """Une 1ère D et une 1ère A4 se comptent et se règlent séparément."""
        self.sign_in(self.staff)
        premiere = SchoolLevel.objects.get(school=self.school, name="Première")
        self.make_student(average="19", series="A4", level=premiere)
        self.make_student(average="13", series="D", level=premiere)
        self.make_student(average="13", series="D", level=premiere)

        response = self.client.get(self.url, **self.headers)

        lignes = {row["label"]: row for row in response.data["levels"]}
        self.assertEqual(set(lignes), {"Première A4", "Première D"})
        self.assertEqual(lignes["Première A4"]["total"], 1)
        self.assertEqual(lignes["Première D"]["total"], 2)
        self.assertEqual(lignes["Première A4"]["key"], stream_key(premiere.id, "A4"))
        self.assertEqual(lignes["Première D"]["key"], stream_key(premiere.id, "D"))
        self.assertEqual(
            [(row["label"], row["count"]) for row in niveaux["3ème"]["bands"]],
            [("18 à 20", 1), ("16 à 18", 0), ("14 à 16", 1), ("12 à 14", 0)],
        )

    def test_le_plafond_s_enregistre_cursus_par_cursus(self):
        self.sign_in(self.staff)
        premiere = SchoolLevel.objects.get(school=self.school, name="Première")

        response = self.client.put(self.url, {"band_limits": {
            stream_key(self.level.id, ""): {"18": 2, "16": 4},
            stream_key(premiere.id, "A4"): {"12": 6},
            stream_key(premiere.id, "D"): {"12": 3},
        }}, format="json", **self.headers)

        self.assertEqual(response.status_code, 200, response.data)
        rules = ClassAssignmentSettings.objects.get(school=self.school)
        self.assertEqual(rules.band_limits, {
            f"{self.level.id}|": {"18": 2, "16": 4},
            f"{premiere.id}|A4": {"12": 6},
            f"{premiere.id}|D": {"12": 3},
        })

    def test_un_cursus_absent_de_la_liste_garde_son_plafond(self):
        """Sinon l'enregistrement suivant effacerait un réglage invisible."""
        self.sign_in(self.staff)
        premiere = SchoolLevel.objects.get(school=self.school, name="Première")
        self.client.put(self.url, {"band_limits": {
            stream_key(premiere.id, "D"): {"18": 2},
        }}, format="json", **self.headers)

        # Aucun élève de Première à répartir : la ligne ne s'affiche pas.
        response = self.client.get(self.url, **self.headers)

        self.assertEqual(
            response.data["band_limits"][stream_key(premiere.id, "D")], {"18": 2},
        )

    def test_les_plafonds_a_zero_ne_sont_pas_conserves(self):
        self.sign_in(self.staff)
        self.client.put(self.url, {"band_limits": {
            stream_key(self.level.id, ""): {"18": 0, "16": 0, "14": 0, "12": 0},
        }}, format="json", **self.headers)

        rules = ClassAssignmentSettings.objects.get(school=self.school)
        self.assertEqual(rules.band_limits, {})

    def test_une_tranche_inconnue_est_refusee(self):
        self.sign_in(self.staff)
        response = self.client.put(
            self.url, {"band_limits": {stream_key(self.level.id, ""): {"10": 2}}},
            format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("band_limits", response.data)

    def test_un_niveau_d_une_autre_ecole_est_refuse(self):
        self.sign_in(self.staff)
        ailleurs = School.objects.create(
            name="Lycée de Kara", code="lycee-kara", owner=self.staff,
        )
        etranger = SchoolLevel.objects.filter(school=ailleurs).first()

        response = self.client.put(
            self.url, {"band_limits": {stream_key(etranger.id, ""): {"18": 2}}},
            format="json", **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Niveau inconnu", str(response.data["band_limits"]))

    def test_le_parametrage_annonce_les_tranches_de_moyennes(self):
        self.sign_in(self.staff)
        for note in ("19", "17", "15", "13", "8"):
            self.make_student(average=note)

        response = self.client.get(self.url, **self.headers)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total"], 5)
        self.assertEqual(
            [(row["label"], row["count"]) for row in response.data["bands"]],
            [("18 à 20", 1), ("16 à 18", 1), ("14 à 16", 1), ("12 à 14", 1)],
        )

    def test_les_reglages_par_defaut_sont_ceux_de_l_usage(self):
        self.sign_in(self.staff)
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["balance_headcount"])
        self.assertTrue(response.data["balance_girls"])
        self.assertEqual(response.data["reserved_excellent"], 3)
        self.assertEqual(response.data["excellent_minimum"], "16.00")
        self.assertTrue(response.data["can_configure"])

    def test_la_direction_modifie_les_regles(self):
        self.sign_in(self.staff)
        response = self.client.put(self.url, {
            "balance_girls": False, "reserved_excellent": 5,
            "excellent_minimum": "14.5", "overflow_margin": 8,
        }, format="json", **self.headers)

        self.assertEqual(response.status_code, 200, response.data)
        rules = ClassAssignmentSettings.objects.get(school=self.school)
        self.assertFalse(rules.balance_girls)
        self.assertEqual(rules.reserved_excellent, 5)
        self.assertEqual(rules.excellent_minimum, Decimal("14.50"))
        self.assertEqual(rules.overflow_margin, 8)

    def test_le_secretariat_lit_les_regles_sans_les_changer(self):
        self.sign_in(self.member(CustomUser.Role.SECRETARY))
        lecture = self.client.get(self.url, **self.headers)
        self.assertEqual(lecture.status_code, 200, lecture.data)
        self.assertFalse(lecture.data["can_configure"])

        ecriture = self.client.put(
            self.url, {"balance_girls": False}, format="json", **self.headers,
        )
        self.assertEqual(ecriture.status_code, 400)
        self.assertIn("permission", ecriture.data)

    def test_une_moyenne_hors_bareme_est_refusee(self):
        self.sign_in(self.staff)
        response = self.client.put(
            self.url, {"excellent_minimum": "25"}, format="json", **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("excellent_minimum", response.data)

    def test_la_repartition_suit_les_regles_enregistrees(self):
        """Réserve à zéro : les meilleurs remontent dans la première classe."""
        self.sign_in(self.staff)
        self.client.put(
            self.url, {"reserved_excellent": 0}, format="json", **self.headers,
        )
        self.make_class("4A")
        self.make_class("4B")
        for note in (19, 18, 8, 7):
            self.make_student(average=str(note))

        response = self.client.post(
            f"/api/schools/{self.school.id}/enrollments/auto-assign/",
            format="json", **self.headers,
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["assigned"], 4)
        premiere = SchoolClass.objects.get(academic_year=self.year, group="4A")
        moyennes = sorted(
            float(row.previous_average) for row in
            StudentEnrollment.objects.filter(school_class=premiere)
        )
        self.assertEqual(moyennes, [18.0, 19.0])

    def test_le_bilan_annonce_les_filles_et_les_depassements(self):
        self.sign_in(self.staff)
        self.client.put(
            self.url, {"overflow_margin": 5}, format="json", **self.headers,
        )
        school_class = self.make_class("4A", capacity=2)
        for _ in range(4):
            self.make_student(average="10", gender="F")

        response = self.client.post(
            f"/api/schools/{self.school.id}/enrollments/auto-assign/",
            format="json", **self.headers,
        )

        classe = response.data["summary"][0]["classes"][0]
        self.assertEqual(classe["id"], school_class.pk)
        self.assertEqual(classe["girls"], 4)
        self.assertTrue(classe["over_capacity"])
