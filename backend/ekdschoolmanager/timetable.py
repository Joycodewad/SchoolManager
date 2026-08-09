"""Génération d'emploi du temps.

Le placement se fait par « séances » et non heure par heure : une matière de 4h
au lycée devient deux séances de 2h, posées chacune sur deux créneaux
consécutifs non séparés par une pause.

Contraintes dures (toujours respectées) :
  - une classe ne suit qu'un cours à la fois ;
  - un enseignant n'est présent que dans une classe à la fois ;
  - les indisponibilités déclarées (TeacherUnavailability) ;
  - les interdictions matière/créneau (SubjectPeriodRestriction) ;
  - les créneaux de pause ne reçoivent aucun cours.

Contraintes pédagogiques, activables une à une sur le modèle Timetable :
  - enforce_paired_hours       : blocs de 2h au lycée (EPS toujours en 1h) ;
  - enforce_single_hour_middle : 1h/jour au collège, sauf au-delà de 4h/sem ;
  - enforce_max_two_hours      : jamais plus de 2h d'une matière le même jour ;
  - enforce_day_spacing        : un jour d'écart minimum entre les deux
                                 premières séances ;
  - skip_primary               : le cycle primaire n'est pas généré.

Si un placement échoue, les contraintes souples sont relâchées progressivement
(espacement, puis blocs) avant d'abandonner une séance.
"""

import random
import time
from datetime import datetime, timedelta

from django.db import transaction

from .models import (
    ClassSubject,
    SchoolLevel,
    SubjectPeriodRestriction,
    ClassGroupSession,
    ExcludedTimetableClass,
    TeacherAssignmentSubject,
    TeacherUnavailability,
    Timetable,
    TimetablePeriod,
    TimetableSlot,
)

# Matières limitées à 1h par jour même au lycée, quel que soit leur volume.
SINGLE_HOUR_SUBJECT_CODES = {"eps"}

# Au collège, au-delà de ce volume la règle « 1h/jour » devient inapplicable
# sur 5 jours : l'excédent est alors posé en bloc de 2h.
MIDDLE_SINGLE_HOUR_LIMIT = 4

# Délogement groupé : retirer deux séances à la fois pour dégager une place
# qu'aucune ne libère seule. Mesuré sur Amou-Oblo et Hiheatro, il n'aboutit
# jamais et allonge la recherche d'environ 60 % — le temps est mieux employé à
# essayer d'autres ordres de placement. Passer à 2 pour le réactiver sur un
# établissement où la grille serait plus contrainte.
DEFAULT_MUTATION_VICTIMS = 1

# Nombre de séances examinées deux à deux quand le délogement groupé est actif.
# L'exploration est quadratique : la borne évite qu'elle ne dévore le budget.
GROUPED_MUTATION_CANDIDATES = 12

DAY_LABELS = dict(TeacherUnavailability.Day.choices)

# Motifs de refus renvoyés par `fits`, du plus structurel au plus circonstanciel.
TEACHER_BUSY = "teacher_busy"
CLASS_BUSY = "class_busy"
TEACHER_UNAVAILABLE = "teacher_unavailable"
DAY_SPACING = "day_spacing"
DAILY_LIMIT = "daily_limit"
NOT_CONTIGUOUS = "not_contiguous"
CLOSED_AFTERNOON = "closed_afternoon"
PERIOD_FORBIDDEN = "period_forbidden"
BLOCK_UNAVAILABLE = "block_unavailable"

REASON_LABELS = {
    TEACHER_BUSY: "l’enseignant est déjà en cours dans une autre classe (augmentez le regroupement de classes ou ajoutez un enseignant)",
    CLASS_BUSY: "la classe occupe déjà tous les créneaux disponibles (ajoutez un créneau ou une journée)",
    TEACHER_UNAVAILABLE: "l’enseignant est déclaré indisponible sur les créneaux restants",
    DAY_SPACING: "l’espacement obligatoire d’un jour ne laisse plus de jour libre",
    DAILY_LIMIT: "le plafond d’heures par jour de cette matière est atteint",
    NOT_CONTIGUOUS: "aucun créneau accolé aux heures déjà posées ce jour-là",
    CLOSED_AFTERNOON: "les après-midi fermés ne laissent plus assez de créneaux",
    PERIOD_FORBIDDEN: "les créneaux restants sont interdits pour cette matière",
    BLOCK_UNAVAILABLE: "aucun bloc de 2h consécutives sans pause n’est disponible",
}

DEFAULT_PERIODS = [
    ("1re heure", "cours", "06:55", "07:55"),
    ("2e heure", "cours", "07:55", "08:50"),
    ("3e heure", "cours", "08:50", "09:45"),
    ("Récréation", "pause", "09:45", "10:15"),
    ("4e heure", "cours", "10:15", "11:10"),
    ("5e heure", "cours", "11:10", "12:05"),
    ("Pause déjeuner", "pause", "12:15", "15:00"),
    ("6e heure", "cours", "15:00", "15:55"),
    ("7e heure", "cours", "15:55", "16:55"),
]


def create_default_periods(timetable):
    """Grille par défaut, utilisée tant que l'utilisateur n'a rien paramétré."""
    periods = []
    for order, (label, kind, start, end) in enumerate(DEFAULT_PERIODS, start=1):
        periods.append(TimetablePeriod(
            timetable=timetable,
            label=label,
            kind=kind,
            start_time=datetime.strptime(start, "%H:%M").time(),
            end_time=datetime.strptime(end, "%H:%M").time(),
            order=order,
        ))
    return TimetablePeriod.objects.bulk_create(periods)


def course_periods(timetable):
    """Créneaux de cours, ordonnés, avec l'indice du créneau suivant s'il est accolé."""
    periods = list(timetable.periods.all())

    # La pause déjeuner est la plus longue interruption de la journée : elle
    # sépare les créneaux du matin de ceux de l'après-midi.
    breaks = [period for period in periods if period.is_break]
    lunch_order = None
    if breaks:
        def duration(period):
            return (
                period.end_time.hour * 60 + period.end_time.minute
                - period.start_time.hour * 60 - period.start_time.minute
            )
        lunch_order = max(breaks, key=duration).order

    rows = []
    for index, period in enumerate(periods):
        if period.is_break:
            continue
        following = periods[index + 1] if index + 1 < len(periods) else None
        # Deux heures forment un bloc si elles se touchent et qu'aucune pause ne
        # les sépare.
        pairs_with_next = (
            following is not None
            and not following.is_break
            and following.start_time == period.end_time
        )
        rows.append({
            "id": period.id,
            "order": period.order,
            "start": period.start_time,
            "end": period.end_time,
            "pairs_with_next": pairs_with_next,
            "before_lunch": lunch_order is None or period.order < lunch_order,
        })
    return rows


def unavailability_map(school, academic_year):
    blocked = {}
    for item in TeacherUnavailability.objects.filter(school=school, academic_year=academic_year):
        blocked.setdefault(item.teacher_id, []).append(
            (item.day, None, None) if item.all_day else (item.day, item.start_time, item.end_time)
        )
    return blocked


def excluded_pairs(timetable):
    """Couples (subject_id, class_id) que l'utilisateur a écartés de la génération."""
    excluded = set()
    for exclusion in ExcludedTimetableClass.objects.filter(timetable=timetable).prefetch_related("classes"):
        for school_class in exclusion.classes.all():
            excluded.add((exclusion.subject_id, school_class.id))
    return excluded


def class_group_map(timetable):
    """(subject_id, class_id) -> identité du regroupement auquel la classe appartient.

    Les classes d'un même regroupement partagent un créneau et un enseignant ;
    l'identité sert à reconnaître qu'elles peuvent coexister sur le même créneau.
    """
    mapping = {}
    for group in ClassGroupSession.objects.filter(timetable=timetable).prefetch_related("classes"):
        members = list(group.classes.all())
        if len(members) < 2:
            continue
        for school_class in members:
            mapping[(group.subject_id, school_class.id)] = group.id
    return mapping


def restriction_map(timetable):
    """(subject_id, period_id) -> set des jours interdits ; None = tous les jours."""
    blocked = {}
    for item in SubjectPeriodRestriction.objects.filter(timetable=timetable):
        blocked.setdefault((item.subject_id, item.period_id), set()).add(item.day)
    return blocked


def is_teacher_available(teacher_id, day, start, end, blocked):
    for blocked_day, blocked_start, blocked_end in blocked.get(teacher_id, []):
        if blocked_day != day:
            continue
        if blocked_start is None:
            return False
        if start < blocked_end and blocked_start < end:
            return False
    return True


def split_into_sessions(configuration, timetable):
    """Découpe un volume hebdomadaire en séances de 1h ou 2h selon le cycle.

    Retourne une liste de durées (1 ou 2), exprimées en nombre de créneaux.
    """
    hours = configuration.weekly_hours
    stage = configuration.school_class.level.stage
    subject_code = (configuration.subject.code or "").lower()

    # L'EPS reste toujours en séances d'1h.
    if subject_code in SINGLE_HOUR_SUBJECT_CODES:
        return [1] * hours

    if stage == SchoolLevel.Stage.MIDDLE:
        if not timetable.enforce_single_hour_middle:
            return [2] * (hours // 2) + [1] * (hours % 2)
        # 1h/jour tant que le volume tient sur la semaine ; au-delà, l'excédent
        # passe en blocs de 2h.
        if hours <= MIDDLE_SINGLE_HOUR_LIMIT:
            return [1] * hours
        extra = hours - MIDDLE_SINGLE_HOUR_LIMIT
        return [1] * MIDDLE_SINGLE_HOUR_LIMIT + [2] * (extra // 2) + [1] * (extra % 2)

    if stage == SchoolLevel.Stage.HIGH:
        if not timetable.enforce_paired_hours:
            return [1] * hours
        return [2] * (hours // 2) + [1] * (hours % 2)

    return [1] * hours


def daily_limit(configuration, timetable):
    """Nombre maximum d'heures de cette matière sur une même journée."""
    stage = configuration.school_class.level.stage
    subject_code = (configuration.subject.code or "").lower()

    # L'EPS ne dépasse jamais 1h par jour, quel que soit le cycle.
    if subject_code in SINGLE_HOUR_SUBJECT_CODES:
        return 1

    if (
        stage == SchoolLevel.Stage.MIDDLE
        and timetable.enforce_single_hour_middle
        and configuration.weekly_hours <= MIDDLE_SINGLE_HOUR_LIMIT
    ):
        return 1

    return 2 if timetable.enforce_max_two_hours else None


def spacing_applies(configuration, timetable):
    """L'espacement d'un jour vise les volumes moyens : 3-4h au lycée, 2h au collège."""
    if (configuration.subject.code or "").lower() in SINGLE_HOUR_SUBJECT_CODES:
        # L'EPS est toujours espacé, y compris si l'option globale est décochée.
        return True
    if not timetable.enforce_day_spacing:
        return False
    stage = configuration.school_class.level.stage
    hours = configuration.weekly_hours
    if stage == SchoolLevel.Stage.HIGH:
        return hours in (3, 4)
    if stage == SchoolLevel.Stage.MIDDLE:
        return hours == 2
    return False


def spacing_is_mandatory(configuration):
    """L'espacement de l'EPS ne peut jamais être relâché pour caser une séance."""
    return (configuration.subject.code or "").lower() in SINGLE_HOUR_SUBJECT_CODES


def collect_sessions(timetable):
    """Une entrée par séance à placer."""
    academic_year = timetable.academic_year
    teacher_by_class_subject = {
        link.class_subject_id: link.assignment.teacher_id
        for link in TeacherAssignmentSubject.objects.filter(
            assignment__academic_year=academic_year,
        ).select_related("assignment")
    }

    configurations = ClassSubject.objects.filter(
        school_class__academic_year=academic_year,
    ).select_related("school_class", "school_class__level", "subject")
    if timetable.skip_primary:
        configurations = configurations.exclude(school_class__level__stage=SchoolLevel.Stage.PRIMARY)

    excluded = excluded_pairs(timetable)
    groups = class_group_map(timetable)
    sessions = []
    for configuration in configurations:
        if (configuration.subject_id, configuration.school_class_id) in excluded:
            continue
        durations = split_into_sessions(configuration, timetable)
        limit = daily_limit(configuration, timetable)
        for index, length in enumerate(durations):
            sessions.append({
                "class_subject": configuration,
                "subject_id": configuration.subject_id,
                "school_class_id": configuration.school_class_id,
                "teacher_id": teacher_by_class_subject.get(configuration.id),
                "length": length,
                "index": index,
                "spacing": spacing_applies(configuration, timetable),
                "spacing_mandatory": spacing_is_mandatory(configuration),
                "daily_limit": limit,
                # Regroupement auquel la classe appartient pour cette matière :
                # les classes d'un même groupe partagent créneau et enseignant.
                "group_id": groups.get((configuration.subject_id, configuration.school_class_id)),
                "afternoon_ok": configuration.can_schedule_afternoon,
                "after_break_ok": configuration.can_schedule_after_break,
            })
    return sessions


def generate_slots(timetable, strategy=0):
    """Retourne (slots, unplaced, relaxed) pour un ordre de placement donné.

    `strategy` fait varier l'ordre dans lequel les séances sont traitées : deux
    ordres différents ne butent pas sur les mêmes impasses. Ne touche pas à la base.
    """
    periods = course_periods(timetable)
    if not periods:
        return [], [], []

    blocked_teachers = unavailability_map(timetable.school, timetable.academic_year)
    restrictions = restriction_map(timetable)
    sessions = collect_sessions(timetable)

    closed_afternoons = set()
    for value in timetable.days_without_afternoon or []:
        try:
            closed_afternoons.add(int(value))
        except (TypeError, ValueError):
            continue

    # Les séances les plus contraintes d'abord : blocs de 2h, enseignants très
    # sollicités, gros volumes horaires.
    teacher_load = {}
    for session in sessions:
        if session["teacher_id"]:
            teacher_load[session["teacher_id"]] = teacher_load.get(session["teacher_id"], 0) + session["length"]
    # Les séances soumises à un espacement obligatoire (EPS) sont les plus dures
    # à caser : elles passent toujours en premier, quelle que soit la stratégie.
    def base_key(item):
        return (
            0 if item["spacing_mandatory"] else 1,
            -item["length"],
            -teacher_load.get(item["teacher_id"], 0),
            -item["class_subject"].weekly_hours,
        )

    sessions.sort(key=base_key)
    if strategy:
        # Les tentatives suivantes rebattent l'ordre entre séances de difficulté
        # équivalente : l'ordre global est préservé, mais les impasses changent.
        shuffler = random.Random(strategy)
        groups = {}
        for session in sessions:
            groups.setdefault(base_key(session), []).append(session)
        sessions = []
        for key in sorted(groups):
            block = groups[key]
            shuffler.shuffle(block)
            sessions.extend(block)

    class_busy = set()    # (class_id, day, period_order)
    # (teacher_id, day, period_order) -> identité du regroupement occupant le
    # créneau (None si l'enseignant y est seul avec une classe). Deux classes ne
    # se partagent un créneau que si elles appartiennent au même regroupement.
    teacher_busy = {}
    # Même clé -> classes effectivement posées, pour libérer le créneau au bon moment.
    teacher_slot_users = {}
    day_hours = {}        # (class_subject_id, day) -> heures déjà posées ce jour
    subject_days = {}     # class_subject_id -> set des jours utilisés
    day_neighbours = {}   # (class_subject_id, day) -> indices accolés aux heures posées
    placed = []
    unplaced = []
    # Contrainte assouplie -> classes concernées, pour expliquer le compromis.
    relaxations = {}

    def note_relaxation(label, session):
        configuration = session["class_subject"]
        entry = relaxations.setdefault(label, {})
        key = configuration.school_class.group
        entry.setdefault(key, set()).add(configuration.subject.name)

    def slot_indices(start_index, length):
        """Indices des créneaux d'un bloc, ou None si le bloc est impossible."""
        if length == 1:
            return [start_index]
        if start_index + 1 >= len(periods):
            return None
        if not periods[start_index]["pairs_with_next"]:
            return None
        return [start_index, start_index + 1]

    def fits(session, day, start_index, ignore_spacing=False, reasons=None):
        """Indices du bloc si le placement est possible, None sinon.

        `reasons` reçoit, quand il est fourni, le motif de chaque refus : c'est
        ce qui permet d'expliquer à l'utilisateur pourquoi une heure a échoué.
        """
        def refuse(motif):
            if reasons is not None:
                reasons[motif] = reasons.get(motif, 0) + 1
            return None

        indices = slot_indices(start_index, session["length"])
        if indices is None:
            return refuse(BLOCK_UNAVAILABLE)
        configuration = session["class_subject"]

        # Jours où l'établissement ne fait pas cours l'après-midi.
        if day in closed_afternoons and any(not periods[index]["before_lunch"] for index in indices):
            return refuse(CLOSED_AFTERNOON)

        # Plafond journalier propre à la séance : 1h pour l'EPS et pour les
        # matières du collège soumises à la règle « 1h par jour », 2h sinon.
        already = day_hours.get((configuration.id, day), 0)
        limit = session["daily_limit"]
        if limit is not None and already + session["length"] > limit:
            return refuse(DAILY_LIMIT)

        # Une deuxième heure le même jour doit prolonger la première sans pause :
        # deux heures isolées dans la journée ne sont jamais acceptables.
        if already and session["length"] == 1:
            neighbours = day_neighbours.get((configuration.id, day), set())
            if start_index not in neighbours:
                return refuse(NOT_CONTIGUOUS)

        # Espacement d'un jour entre séances. Pour l'EPS la règle est absolue et
        # vise toutes les séances ; ailleurs elle ne concerne que la deuxième et
        # peut être relâchée en dernier recours.
        mandatory = session["spacing_mandatory"]
        if session["spacing"] and (mandatory or not ignore_spacing):
            if mandatory or session["index"] == 1:
                for used_day in subject_days.get(configuration.id, set()):
                    if used_day != day and abs(used_day - day) < 2:
                        return refuse(DAY_SPACING)

        for index in indices:
            period = periods[index]
            if (session["school_class_id"], day, period["order"]) in class_busy:
                return refuse(CLASS_BUSY)
            if session["teacher_id"]:
                key = (session["teacher_id"], day, period["order"])
                if key in teacher_busy:
                    # Créneau déjà pris : acceptable uniquement si les deux
                    # classes appartiennent au même regroupement déclaré.
                    if session["group_id"] is None or teacher_busy[key] != session["group_id"]:
                        return refuse(TEACHER_BUSY)
                if not is_teacher_available(session["teacher_id"], day, period["start"], period["end"], blocked_teachers):
                    return refuse(TEACHER_UNAVAILABLE)
            days_blocked = restrictions.get((session["subject_id"], period["id"]))
            if days_blocked is not None and (None in days_blocked or day in days_blocked):
                return refuse(PERIOD_FORBIDDEN)
        return indices

    def place(session, day, indices):
        configuration = session["class_subject"]
        for index in indices:
            period = periods[index]
            class_busy.add((session["school_class_id"], day, period["order"]))
            if session["teacher_id"]:
                key = (session["teacher_id"], day, period["order"])
                teacher_busy[key] = session["group_id"]
                teacher_slot_users.setdefault(key, set()).add(session["school_class_id"])
        day_hours[(configuration.id, day)] = day_hours.get((configuration.id, day), 0) + session["length"]
        subject_days.setdefault(configuration.id, set()).add(day)
        neighbours = day_neighbours.setdefault((configuration.id, day), set())
        for index in indices:
            # Voisin de gauche puis de droite, à condition qu'aucune pause ne coupe.
            if index > 0 and periods[index - 1]["pairs_with_next"]:
                neighbours.add(index - 1)
            if periods[index]["pairs_with_next"]:
                neighbours.add(index + 1)
        placed.append((session, day, indices))

    def unplace(entry):
        session, day, indices = entry
        configuration = session["class_subject"]
        for index in indices:
            period = periods[index]
            class_busy.discard((session["school_class_id"], day, period["order"]))
            if session["teacher_id"]:
                key = (session["teacher_id"], day, period["order"])
                users = teacher_slot_users.get(key)
                if users is not None:
                    users.discard(session["school_class_id"])
                    if not users:
                        teacher_slot_users.pop(key, None)
                        teacher_busy.pop(key, None)
        remaining = day_hours.get((configuration.id, day), 0) - session["length"]
        if remaining > 0:
            day_hours[(configuration.id, day)] = remaining
        else:
            day_hours.pop((configuration.id, day), None)
            day_neighbours.pop((configuration.id, day), None)
            days_used = subject_days.get(configuration.id)
            if days_used:
                days_used.discard(day)
        placed.remove(entry)

    days = list(range(timetable.days_per_week))

    # Les créneaux du matin sont explorés en premier : la matinée se remplit
    # avant qu'on entame l'après-midi.
    search_order = sorted(
        range(len(periods)),
        key=lambda index: (0 if periods[index]["before_lunch"] else 1, index),
    )

    def try_place(session, ignore_spacing, reasons=None):
        # Le créneau prime sur le jour : toute la semaine se remplit au premier
        # créneau du matin avant qu'on descende vers l'après-midi.
        for start_index in search_order:
            for day in days:
                indices = fits(session, day, start_index, ignore_spacing, reasons)
                if indices is not None:
                    place(session, day, indices)
                    return True
        return False

    def try_place_dry_run(session, reasons):
        """Parcourt la grille sans rien placer, pour relever les motifs de refus."""
        for start_index in search_order:
            for day in days:
                fits(session, day, start_index, ignore_spacing=True, reasons=reasons)

    def blocks(candidate, session):
        """Une séance ne peut gêner que si elle partage la classe ou l'enseignant."""
        return (
            candidate["school_class_id"] == session["school_class_id"]
            or (candidate["teacher_id"] is not None
                and candidate["teacher_id"] == session["teacher_id"])
        )

    def try_place_by_mutation(session, depth=2, allow_relax=False,
                              victims=DEFAULT_MUTATION_VICTIMS):
        """Déplace des séances déjà posées pour dégager une place.

        Deux formes de raisonnement se combinent :

        * en chaîne — on déloge une séance gênante, la nouvelle prend sa place,
          et la délogée déloge à son tour si nécessaire (jusqu'à `depth`) ;
        * en faisceau — quand déloger une seule séance ne suffit pas, on en
          retire plusieurs ensemble (jusqu'à `victims`) avant de réinstaller
          tout le monde.

        La seconde répond au cas où la place convoitée est bloquée par deux
        séances distinctes : aucune ne libère seule un créneau utilisable.

        Tout est annulé si la tentative n'aboutit pas.
        """
        if depth <= 0:
            return False

        def place_kept(candidate):
            """Réinstalle une séance délogée, sans sacrifier l'espacement d'office."""
            if try_place(candidate, ignore_spacing=False):
                return True
            if allow_relax and try_place(candidate, ignore_spacing=True):
                if candidate["spacing"]:
                    note_relaxation("espacement d’un jour", candidate)
                return True
            return False

        candidates = [entry for entry in placed if blocks(entry[0], session)]

        # ── Délogement simple, éventuellement en cascade ──
        for entry in candidates:
            if entry not in placed:
                continue
            other = entry[0]
            unplace(entry)
            if place_kept(session):
                moved = placed[-1]
                if place_kept(other):
                    return True
                # La cascade reste en délogement simple : combiner récursion et
                # délogement groupé ferait exploser le temps de calcul.
                if try_place_by_mutation(other, depth - 1, allow_relax, victims=1):
                    return True
                unplace(moved)
            place(*entry)

        # ── Délogement groupé : deux séances retirées d'un coup ──
        # Utile lorsque la place visée est bloquée par deux séances dont aucune
        # ne suffit à elle seule. Le nombre de paires est borné : l'exploration
        # est quadratique, et une recherche exhaustive coûterait plus de temps
        # qu'elle n'en fait gagner sur le nombre de stratégies essayées.
        if victims < 2:
            return False
        shortlist = candidates[:GROUPED_MUTATION_CANDIDATES]
        for first_position, first in enumerate(shortlist):
            if first not in placed:
                continue
            for second in shortlist[first_position + 1:]:
                if second not in placed:
                    continue
                unplace(first)
                unplace(second)
                if place_kept(session):
                    moved = placed[-1]
                    # Les deux délogées doivent retrouver une place, sinon rien
                    # n'est acquis.
                    if place_kept(first[0]):
                        first_moved = placed[-1]
                        if place_kept(second[0]):
                            return True
                        unplace(first_moved)
                    unplace(moved)
                place(*first)
                place(*second)
        return False

    for session in sessions:
        # Passe 1 : toutes les contraintes respectées.
        done = try_place(session, ignore_spacing=False)

        # Passe 2 : déplacer des séances déjà posées. Vient avant le
        # relâchement de l'espacement, qui coûte neuf fois plus cher : mieux
        # vaut déranger une séance que priver un cours de son jour de repos.
        if not done:
            done = try_place_by_mutation(session)
            if done:
                note_relaxation("mutation de séances déjà placées", session)

        # Passe 3 : sacrifier l'espacement d'un jour, d'abord pour la séance
        # elle-même, puis en autorisant les mutations à en faire autant.
        if not done:
            done = try_place(session, ignore_spacing=True)
            if done and session["spacing"]:
                note_relaxation("espacement d’un jour", session)
        if not done:
            done = try_place_by_mutation(session, allow_relax=True)
            if done:
                note_relaxation("mutation de séances déjà placées", session)

        # Passe 4 : en dernier recours, un bloc de 2h est scindé en deux heures
        # posées sur des jours différents.
        if not done and session["length"] == 2:
            used_days = set()
            for _ in range(2):
                half = dict(session, length=1)
                placed_half = False
                for allow_same_day in (False, True):
                    for start_index in search_order:
                        for day in days:
                            if not allow_same_day and day in used_days:
                                continue
                            indices = fits(half, day, start_index, ignore_spacing=True)
                            if indices is not None:
                                place(half, day, indices)
                                used_days.add(day)
                                note_relaxation("blocs de 2h scindés", half)
                                placed_half = True
                                break
                        if placed_half:
                            break
                    if placed_half:
                        break
                if not placed_half and not try_place_by_mutation(half, allow_relax=True):
                    unplaced.append(half)
            done = True

        if not done:
            unplaced.append(session)

    # Rattrapage : la grille est complète, les mutations disposent enfin de tout
    # le contexte. On retente les séances abandonnées.
    for session in list(unplaced):
        if try_place(session, ignore_spacing=False):
            unplaced.remove(session)
        elif try_place_by_mutation(session):
            unplaced.remove(session)
            note_relaxation("mutation de séances déjà placées", session)
        elif try_place(session, ignore_spacing=True):
            unplaced.remove(session)
            if session["spacing"] and not session["spacing_mandatory"]:
                note_relaxation("espacement d’un jour", session)
        # Ultime tentative : mutations autorisées à relâcher l'espacement.
        elif try_place_by_mutation(session, allow_relax=True):
            unplaced.remove(session)
            note_relaxation("mutation de séances déjà placées", session)

    # Diagnostic : pour chaque séance abandonnée, on rejoue la recherche à vide
    # afin de relever le motif qui revient le plus souvent.
    for session in unplaced:
        reasons = {}
        try_place_dry_run(session, reasons)
        session["reason"] = max(reasons, key=reasons.get) if reasons else None

    # Compactage : rapprocher chaque séance du début de journée. On remonte
    # d'abord vers la matinée ; à défaut, on comble les trous laissés dans
    # l'après-midi pour que les heures restantes s'y enchaînent sans interruption.
    rank = {index: position for position, index in enumerate(search_order)}
    for _ in range(4):
        moved_any = False
        for entry in list(placed):
            session, day, indices = entry
            current = rank[indices[0]]
            unplace(entry)
            relocated = False
            for start_index in search_order:
                if rank[start_index] >= current:
                    # Aucun créneau plus précoce : la séance reste où elle est.
                    break
                for candidate_day in days:
                    new_indices = fits(session, candidate_day, start_index, ignore_spacing=False)
                    if new_indices is not None:
                        place(session, candidate_day, new_indices)
                        relocated = moved_any = True
                        break
                if relocated:
                    break
            if not relocated:
                place(*entry)
        if not moved_any:
            break

    slots = []
    for session, day, indices in placed:
        for index in indices:
            period = periods[index]
            slots.append(TimetableSlot(
                timetable=timetable,
                school_class=session["class_subject"].school_class,
                class_subject=session["class_subject"],
                teacher_id=session["teacher_id"],
                day=day,
                start_time=period["start"],
                end_time=period["end"],
            ))
    relaxed = [
        {
            "constraint": label,
            "classes": sorted(
                f"{group} ({', '.join(sorted(subjects))})"
                for group, subjects in scope.items()
            ),
        }
        for label, scope in sorted(relaxations.items())
    ]
    return slots, unplaced, relaxed


def irreducible_deficit(timetable):
    """Heures qu'aucun ordonnancement ne peut placer, faute de créneaux.

    Une classe dont le volume hebdomadaire dépasse la capacité de la grille perd
    forcément la différence : c'est un problème de paramétrage, pas de placement.
    """
    periods = course_periods(timetable)
    if not periods:
        return 0, {}
    afternoon = sum(1 for period in periods if not period["before_lunch"])
    closed = len({int(day) for day in (timetable.days_without_afternoon or [])})
    capacity = len(periods) * timetable.days_per_week - afternoon * closed

    configurations = ClassSubject.objects.filter(
        school_class__academic_year=timetable.academic_year,
    ).select_related("school_class")
    if timetable.skip_primary:
        configurations = configurations.exclude(school_class__level__stage=SchoolLevel.Stage.PRIMARY)

    needed = {}
    for configuration in configurations:
        group = configuration.school_class.group
        needed[group] = needed.get(group, 0) + configuration.weekly_hours

    overflow = {group: hours - capacity for group, hours in needed.items() if hours > capacity}

    return sum(overflow.values()), overflow


# Coût pédagogique de chaque compromis. Une solution qui déplace des séances
# déjà posées est préférable à une qui casse un bloc de 2h, elle-même préférable
# à une qui sacrifie l'espacement d'un jour.
RELAXATION_COST = {
    "mutation de séances déjà placées": 1,
    "blocs de 2h scindés": 4,
    "espacement d’un jour": 9,
}


def relaxation_penalty(relaxed):
    """Somme des coûts, pondérée par le nombre de classes touchées."""
    return sum(
        RELAXATION_COST.get(item["constraint"], 5) * max(1, len(item["classes"]))
        for item in relaxed
    )


def count_spacing_breaches(timetable, slots):
    """Compte les matières dont deux jours de cours se suivent.

    On mesure la grille produite plutôt que les compromis déclarés : une séance
    peut être déplacée plusieurs fois avant de se fixer, et seul l'emploi du
    temps final dit la vérité sur l'espacement réellement obtenu.
    """
    days_by_configuration = {}
    for slot in slots:
        days_by_configuration.setdefault(slot.class_subject_id, set()).add(slot.day)

    if not days_by_configuration:
        return 0

    configurations = ClassSubject.objects.filter(
        id__in=days_by_configuration,
    ).select_related("school_class", "school_class__level", "subject")

    breaches = 0
    for configuration in configurations:
        if not spacing_applies(configuration, timetable):
            continue
        days = sorted(days_by_configuration[configuration.id])
        if any(second - first < 2 for first, second in zip(days, days[1:])):
            breaches += 1
    return breaches


def generate_best(timetable, attempts=200, patience=50, time_budget=120):
    """Cherche le meilleur placement en essayant de nombreux ordres.

    Les tentatives sont comparées d'abord sur les heures perdues, puis sur le
    coût des compromis : à nombre d'heures égal, la solution retenue est celle
    qui assouplit les contraintes les moins pénalisantes, et sur le moins de
    classes possible.

    L'exploration s'arrête quand :
      - une tentative place tout sans aucun compromis (optimum) ;
      - `patience` essais consécutifs n'améliorent plus rien ;
      - `time_budget` secondes se sont écoulées.
    """
    floor, _ = irreducible_deficit(timetable)
    started = time.monotonic()
    best = None
    since_improvement = 0
    strategy = 0

    for strategy in range(max(1, attempts)):
        slots, unplaced, relaxed = generate_slots(timetable, strategy=strategy)
        lost = sum(session["length"] for session in unplaced)
        # L'espacement est mesuré sur la grille obtenue : les compromis déclarés
        # sous-estiment les cours qui finissent sur deux jours consécutifs.
        breaches = count_spacing_breaches(timetable, slots)
        score = (lost, breaches * RELAXATION_COST["espacement d’un jour"]
                 + relaxation_penalty(relaxed))
        if best is None or score < best[0]:
            best = (score, slots, unplaced, relaxed, strategy + 1)
            since_improvement = 0
        else:
            since_improvement += 1

        # Optimum atteint : plus rien à gagner.
        if lost <= floor and not relaxed and not breaches:
            break
        if since_improvement >= patience or time.monotonic() - started > time_budget:
            break

    _, slots, unplaced, relaxed, _ = best
    relaxed = restate_spacing(timetable, slots, relaxed)
    return slots, unplaced, relaxed, strategy + 1, floor


def restate_spacing(timetable, slots, relaxed):
    """Réécrit la ligne « espacement » d'après la grille réellement produite.

    Les compromis sont notés au fil des tentatives ; une séance déplacée
    plusieurs fois peut y figurer à tort, ou en être absente. La grille finale
    est la seule source fiable.
    """
    days_by_configuration = {}
    for slot in slots:
        days_by_configuration.setdefault(slot.class_subject_id, set()).add(slot.day)

    affected = {}
    configurations = ClassSubject.objects.filter(
        id__in=days_by_configuration,
    ).select_related("school_class", "school_class__level", "subject")
    for configuration in configurations:
        if not spacing_applies(configuration, timetable):
            continue
        days = sorted(days_by_configuration[configuration.id])
        if any(second - first < 2 for first, second in zip(days, days[1:])):
            affected.setdefault(configuration.school_class.group, set()).add(
                configuration.subject.name
            )

    label = "espacement d’un jour"
    rewritten = [item for item in relaxed if item["constraint"] != label]
    if affected:
        rewritten.append({
            "constraint": label,
            "classes": sorted(
                f"{group} ({', '.join(sorted(subjects))})"
                for group, subjects in affected.items()
            ),
        })
    return sorted(rewritten, key=lambda item: item["constraint"])


@transaction.atomic
def regenerate(timetable):
    """Remplace les créneaux. Refuse de toucher à un emploi validé."""
    if timetable.is_validated:
        raise ValueError("Cet emploi du temps est validé et ne peut plus être régénéré.")
    if not timetable.periods.exists():
        create_default_periods(timetable)
    slots, unplaced, relaxed, attempts, floor = generate_best(timetable)
    timetable.slots.all().delete()
    TimetableSlot.objects.bulk_create(slots)
    return slots, unplaced, relaxed, attempts, floor


def describe_unplaced(unplaced):
    """Heures non placées, avec la raison dominante de chaque échec."""
    summary = {}
    for session in unplaced:
        configuration = session["class_subject"]
        key = f"{configuration.school_class.group} — {configuration.subject.name}"
        entry = summary.setdefault(key, {"hours": 0, "reasons": set()})
        entry["hours"] += session["length"]
        if session.get("reason"):
            entry["reasons"].add(session["reason"])
    rows = []
    for key, entry in sorted(summary.items()):
        causes = ", ".join(
            REASON_LABELS.get(reason, reason) for reason in sorted(entry["reasons"])
        )
        rows.append(f"{key} ({entry['hours']}h) — {causes}" if causes else f"{key} ({entry['hours']}h)")
    return rows
