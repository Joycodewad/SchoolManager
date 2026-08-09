"""Coefficients togolais et notes d'exemple pour le Lycée d'Amou-Oblo.

Deux étapes indépendantes, relançables sans créer de doublons :

1. les coefficients de chaque matière, repris du barème officiel togolais —
   ils dépendent du niveau au collège, de la série au lycée ;
2. des notes plausibles pour les élèves inscrits, sur les sessions en cours.

Les notes sont tirées au sort mais de façon reproductible (`--seed`) : deux
exécutions produisent les mêmes bulletins, ce qui rend les écrans et les PDF
comparables d'une fois sur l'autre.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ekdschoolmanager.models import (
    AcademicSession,
    ClassSubject,
    GradeEntry,
    GradeScheme,
    SchoolClass,
    School,
    StudentEnrollment,
)

SCHOOL_CODE = "lycee-amou-oblo"

# ── Coefficients ─────────────────────────────────────────────────────────────
#
# Barème togolais. Au collège le coefficient ne dépend que du niveau ; au
# lycée il dépend de la série, qui fait tout l'écart entre un littéraire (A4)
# et un scientifique (C4, D).

COLLEGE_COEFFICIENTS = {
    "6ème": {"FR": 4, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 2, "MATHS": 4, "PCT": 2, "EPS": 1, "MUS": 1},
    "5ème": {"FR": 4, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 2, "MATHS": 4, "PCT": 2, "EPS": 1, "MUS": 1},
    "4ème": {"FR": 3, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 2, "MATHS": 3, "PCT": 3, "EPS": 1, "MUS": 1},
    "3ème": {"FR": 3, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 2, "MATHS": 3, "PCT": 3, "EPS": 1, "MUS": 1},
}

# Lycée : la série commande le poids des matières.
#   A4 — littéraire : lettres et philosophie dominent.
#   C4 — mathématiques : maths très lourdes, PCT ensuite.
#   D  — sciences expérimentales : SVT et PCT au premier plan.
LYCEE_COEFFICIENTS = {
    "A4": {"FR": 4, "ANG": 3, "HG": 3, "ECM": 1, "SVT": 2, "MATHS": 2, "PCT": 2,
           "PHILO": 4, "ALL": 3, "EPS": 1, "MUS": 1},
    "CD": {"FR": 2, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 3, "MATHS": 5, "PCT": 5,
           "PHILO": 2, "EPS": 1, "MUS": 1},
    "C4": {"FR": 2, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 2, "MATHS": 7, "PCT": 5,
           "PHILO": 2, "EPS": 1, "MUS": 1},
    "D": {"FR": 2, "ANG": 2, "HG": 2, "ECM": 1, "SVT": 6, "MATHS": 5, "PCT": 5,
          "PHILO": 2, "EPS": 1, "MUS": 1},
}

# En terminale la philosophie prend le poids qu'on lui connaît au bac.
TERMINALE_OVERRIDES = {
    "A4": {"PHILO": 6},
    "C4": {"PHILO": 3, "MATHS": 8},
    "D": {"PHILO": 3, "SVT": 7},
}

# Libellé complet de la matière -> code du barème. Le seed d'origine crée les
# matières par leur libellé ; on retrouve le code par ce chemin inverse.
SUBJECT_CODES = {
    "Français": "FR",
    "Anglais": "ANG",
    "Histoire-Géographie": "HG",
    "Éducation Civique et Morale": "ECM",
    "Sciences de la Vie et de la Terre": "SVT",
    "Mathématiques": "MATHS",
    "Physique-Chimie-Technologie": "PCT",
    "Philosophie": "PHILO",
    "Allemand": "ALL",
    "Éducation Physique et Sportive": "EPS",
    "Musique": "MUS",
}

# ── Notes ────────────────────────────────────────────────────────────────────

# Niveau moyen d'une matière : certaines notent traditionnellement plus bas
# (maths, PCT) que d'autres (EPS, musique). Sans cet écart, toutes les
# moyennes se ressembleraient et les bulletins seraient peu réalistes.
SUBJECT_DIFFICULTY = {
    "MATHS": -1.6, "PCT": -1.4, "PHILO": -0.9, "SVT": -0.4, "FR": -0.3,
    "HG": 0.0, "ANG": 0.0, "ALL": 0.2, "ECM": 1.2, "MUS": 2.0, "EPS": 2.6,
}

# Bornes du bulletin : une note reste dans [0, 20].
MIN_SCORE, MAX_SCORE = Decimal("0"), Decimal("20")


class Command(BaseCommand):
    help = (
        "Applique les coefficients togolais aux matières du Lycée d'Amou-Oblo "
        "et remplit les notes des élèves pour les sessions en cours."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed", type=int, default=2026,
            help="Graine du tirage des notes, pour un résultat reproductible.",
        )
        parser.add_argument(
            "--coefficients-only", action="store_true",
            help="N'applique que les coefficients, sans toucher aux notes.",
        )
        parser.add_argument(
            "--notes-only", action="store_true",
            help="Ne saisit que les notes, sans retoucher les coefficients.",
        )
        parser.add_argument(
            "--overwrite", action="store_true",
            help="Réécrit les notes déjà saisies (par défaut elles sont conservées).",
        )
        parser.add_argument(
            "--session", type=int, action="append", dest="sessions",
            help="Limite le remplissage à cette session (répétable).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["coefficients_only"] and options["notes_only"]:
            raise CommandError("--coefficients-only et --notes-only s'excluent.")

        try:
            school = School.objects.get(code=SCHOOL_CODE)
        except School.DoesNotExist:
            raise CommandError(
                f"Établissement « {SCHOOL_CODE} » introuvable. "
                "Lancez d'abord `manage.py seed_amou_oblo`."
            )

        if not options["notes_only"]:
            self.apply_coefficients(school)
        if not options["coefficients_only"]:
            # `GradeEntry.entered_by` est obligatoire : les notes du seed sont
            # portées au compte du propriétaire de l'établissement.
            self.fill_grades(school, school.owner, options)

    # ── Coefficients ────────────────────────────────────────────────────────

    def coefficient_for(self, school_class, code):
        """Coefficient d'une matière pour une classe, ou None si hors barème."""
        level = school_class.level.name
        if level in COLLEGE_COEFFICIENTS:
            return COLLEGE_COEFFICIENTS[level].get(code)

        series = school_class.series or ""
        table = LYCEE_COEFFICIENTS.get(series)
        if table is None:
            return None
        if level == "Terminale":
            table = {**table, **TERMINALE_OVERRIDES.get(series, {})}
        return table.get(code)

    def apply_coefficients(self, school):
        rows = (
            ClassSubject.objects
            .filter(school_class__school=school)
            .select_related("school_class", "school_class__level", "subject")
        )

        updated, unchanged, skipped = 0, 0, []
        for row in rows:
            code = SUBJECT_CODES.get(row.subject.name)
            coefficient = self.coefficient_for(row.school_class, code) if code else None
            if coefficient is None:
                skipped.append(f"{row.school_class.group}/{row.subject.name}")
                continue
            value = Decimal(coefficient)
            if row.coefficient == value:
                unchanged += 1
                continue
            row.coefficient = value
            row.save(update_fields=["coefficient"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Coefficients : {updated} mis à jour, {unchanged} déjà conformes."
        ))
        if skipped:
            # Une matière hors barème garde son coefficient : mieux vaut le
            # signaler que d'imposer une valeur arbitraire.
            self.stdout.write(self.style.WARNING(
                f"  {len(skipped)} matière(s) hors barème, inchangée(s) : "
                + ", ".join(skipped[:8]) + ("…" if len(skipped) > 8 else "")
            ))

    # ── Notes ───────────────────────────────────────────────────────────────

    def student_ability(self, rng):
        """Niveau propre à l'élève, en écart à la moyenne de la classe.

        Une gaussienne resserrée : la plupart des élèves se tiennent autour de
        la moyenne, quelques-uns décrochent ou se détachent nettement.
        """
        return rng.gauss(0, 2.2)

    def draw_score(self, rng, ability, code):
        """Une note sur 20, cohérente avec le niveau de l'élève et la matière."""
        centre = 10.5 + ability + SUBJECT_DIFFICULTY.get(code, 0.0)
        # Le bruit par évaluation évite des notes identiques d'une ligne à
        # l'autre, qui trahiraient immédiatement un jeu de données fabriqué.
        value = Decimal(str(round(rng.gauss(centre, 2.6) * 2) / 2))
        return max(MIN_SCORE, min(MAX_SCORE, value))

    def fill_grades(self, school, author, options):
        sessions = AcademicSession.objects.filter(academic_year__school=school)
        if options["sessions"]:
            sessions = sessions.filter(id__in=options["sessions"])
        sessions = list(sessions.select_related("academic_year"))
        if not sessions:
            raise CommandError("Aucune session à remplir pour cet établissement.")

        created_total, kept_total = 0, 0
        for session in sessions:
            scheme = (
                GradeScheme.objects
                .prefetch_related("lines")
                .filter(session=session)
                .first()
            )
            if scheme is None:
                self.stdout.write(self.style.WARNING(
                    f"  {session.name} : aucun barème de notes, session ignorée."
                ))
                continue

            lines = list(scheme.lines.all())
            classes = SchoolClass.objects.filter(
                school=school, academic_sessions=session,
            ).select_related("level")

            created, kept = self.fill_session(session, lines, classes, author, options)
            created_total += created
            kept_total += kept
            self.stdout.write(
                f"  {session.name} : {created} note(s) saisie(s)"
                + (f", {kept} conservée(s)" if kept else "")
            )

        self.stdout.write(self.style.SUCCESS(
            f"Notes : {created_total} enregistrée(s), {kept_total} conservée(s)."
        ))

    def fill_session(self, session, lines, classes, author, options):
        created, kept = 0, 0
        for school_class in classes:
            subjects = list(
                ClassSubject.objects
                .filter(school_class=school_class)
                .select_related("subject")
            )
            enrollments = list(
                StudentEnrollment.objects
                .filter(school_class=school_class, status=StudentEnrollment.Status.ACTIVE)
                .order_by("id")
            )
            if not subjects or not enrollments:
                continue

            existing = {
                (entry.enrollment_id, entry.class_subject_id, entry.line_id): entry
                for entry in GradeEntry.objects.filter(
                    class_subject__school_class=school_class, line__scheme__session=session,
                )
            }

            batch = []
            for enrollment in enrollments:
                # Graine dérivée de l'inscription : le même élève garde son
                # niveau d'une exécution à l'autre, et d'une session à l'autre.
                rng = random.Random(f"{options['seed']}-{enrollment.id}")
                ability = self.student_ability(rng)
                for item in subjects:
                    code = SUBJECT_CODES.get(item.subject.name)
                    for line in lines:
                        key = (enrollment.id, item.id, line.id)
                        if key in existing:
                            if not options["overwrite"]:
                                kept += 1
                                continue
                            entry = existing[key]
                            entry.score = self.draw_score(rng, ability, code)
                            entry.save(update_fields=["score"])
                            created += 1
                            continue
                        batch.append(GradeEntry(
                            enrollment=enrollment, class_subject=item, line=line,
                            score=self.draw_score(rng, ability, code),
                            entered_by=author,
                        ))

            if batch:
                GradeEntry.objects.bulk_create(batch, batch_size=2000)
                created += len(batch)
        return created, kept
