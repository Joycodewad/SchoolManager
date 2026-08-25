"""Répartition des élèves sans classe dans les classes de leur niveau.

Un élève inscrit sans classe — nouveau venu, admis d'un niveau inférieur,
arrivé d'un autre établissement — doit rejoindre une classe de son niveau et
de sa série. Le faire à la main sur deux cents élèves est long et donne des
classes déséquilibrées ; le faire au hasard donne pire.

La répartition poursuit quatre équilibres qui se contredisent partiellement,
et que les réglages de l'établissement (`ClassAssignmentSettings`) arbitrent :

* **les effectifs** — chaque élève rejoint la classe la moins remplie de son
  niveau, de sorte qu'aucune classe ne se remplisse pendant qu'une autre reste
  vide ;
* **les filles** — réparties de la même façon, en tenant compte de celles déjà
  inscrites ;
* **le rang** — les meilleures moyennes et les plus jeunes dans les premières
  classes (6ème A avant 6ème B, Tle D-1 avant Tle D-2) ;
* **la réserve** — quelques excellents élèves mis de côté pour les dernières
  classes, sans quoi elles n'auraient que des élèves faibles et les plus âgés.

Quand toutes les classes d'un niveau sont pleines, le maximum peut être
légèrement dépassé : mieux vaut une classe à 52 que deux élèves sans classe.
"""

import re
from decimal import Decimal

from .models import ClassAssignmentSettings, CustomUser, ReportCard, StudentEnrollment
from .reportcards import annual_average

# Un élève sans moyenne connue est rangé après ceux qui en ont une : on ne lui
# prête ni un bon ni un mauvais niveau, il passe simplement en dernier.
UNKNOWN_AVERAGE = Decimal("-1")

# Tranches de moyennes affichées avant de régler la réserve : elles disent
# combien d'élèves un seuil donné retiendrait. Bornes basses incluses, hautes
# exclues, sauf la dernière qui va jusqu'à 20.
AVERAGE_BANDS = [
    ("18 à 20", Decimal("18"), Decimal("20.01")),
    ("16 à 18", Decimal("16"), Decimal("18")),
    ("14 à 16", Decimal("14"), Decimal("16")),
    ("12 à 14", Decimal("12"), Decimal("14")),
]


def rules_for(school):
    """Réglages de l'établissement, créés à la volée à la première demande."""
    rules, _ = ClassAssignmentSettings.objects.get_or_create(school=school)
    return rules


def unassigned_students(school, year):
    """Élèves inscrits sans classe qu'il y a lieu de répartir.

    Un élève en abandon ou sorti avec son baccalauréat n'attend pas de classe :
    il ne compte ni dans la répartition, ni dans les tranches de moyennes.
    """
    return (
        StudentEnrollment.objects
        .filter(
            school=school, academic_year=year,
            status=StudentEnrollment.Status.ACTIVE, school_class__isnull=True,
        )
        .exclude(student__student_status__in=[
            CustomUser.StudentStatus.DROPPED_OUT,
            CustomUser.StudentStatus.BACHELOR,
        ])
        .select_related("student", "level", "academic_year")
    )


def previous_records(school, year, student_ids):
    """Dernière inscription de chaque élève avant cette année, dans cette école."""
    previous = {}
    rows = (
        StudentEnrollment.objects
        .filter(
            school=school, student_id__in=student_ids,
            academic_year__start_date__lt=year.start_date,
        )
        .order_by("student_id", "-academic_year__start_date")
    )
    for enrollment in rows:
        previous.setdefault(enrollment.student_id, enrollment)
    return previous


def attach_fallback_averages(school, year, students):
    """Complète la moyenne des élèves dont la fiche n'en porte aucune.

    Le matricule d'un élève réinscrit par la clôture n'a pas de moyenne saisie
    à la main — personne ne la recopie. Elle se retrouve pourtant dans ses
    bulletins de l'an dernier, et deux valeurs s'y disputent la préséance :

    * **la note d'examen**, pour qui sortait d'une classe d'examen — c'est
      elle qui l'a fait passer, donc elle qui dit son niveau ;
    * **la moyenne annuelle** sinon, ou quand la note d'examen n'a pas été
      saisie.

    La valeur trouvée est posée sur l'inscription (`fallback_average`,
    `average_source`) sans être enregistrée : elle sert au classement et à
    l'affichage, la fiche de l'élève reste celle que l'établissement a saisie.
    """
    for enrollment in students:
        enrollment.fallback_average = None
        enrollment.average_source = "saisie" if enrollment.previous_average is not None else ""

    missing = [row for row in students if row.previous_average is None]
    if not missing:
        return students

    previous = previous_records(school, year, {row.student_id for row in missing})
    cards = {}
    for card in ReportCard.objects.filter(enrollment_id__in=[e.id for e in previous.values()]):
        cards.setdefault(card.enrollment_id, []).append(card)

    for enrollment in missing:
        source = previous.get(enrollment.student_id)
        if source is None:
            continue
        rows = cards.get(source.id, [])
        exam = next(
            (card.exam_average for card in rows if card.exam_average is not None), None,
        )
        if exam is not None:
            enrollment.fallback_average = Decimal(exam)
            enrollment.average_source = "examen"
            continue
        yearly = annual_average(
            [{"average": card.general_average} for card in rows]
        )
        if yearly is not None:
            enrollment.fallback_average = Decimal(yearly)
            enrollment.average_source = "annuelle"
    return students


def effective_average(enrollment):
    """Moyenne réellement utilisée : celle saisie, sinon celle retrouvée."""
    if enrollment.previous_average is not None:
        return enrollment.previous_average
    return getattr(enrollment, "fallback_average", None)


def tally(students):
    """Nombre d'élèves par tranche de moyenne, plus ceux qui n'en ont aucune."""
    averages = [effective_average(row) for row in students]
    known = [value for value in averages if value is not None]
    return {
        "total": len(averages),
        "without_average": len(averages) - len(known),
        "bands": [
            {
                "label": label,
                "minimum": str(low),
                "count": sum(1 for value in known if low <= value < high),
            }
            for label, low, high in AVERAGE_BANDS
        ],
    }


def band_counts(students):
    """Les tranches de moyennes, pour tout l'effectif puis niveau par niveau.

    Le total ne suffit pas à régler quoi que ce soit : deux élèves à plus de 18
    répartis sur trois niveaux ne posent aucun problème, les mêmes deux dans un
    seul cursus à trois classes, si. Le détail va donc jusqu'à la série — une
    1ère D et une 1ère A4 se répartissent séparément — et c'est aussi la maille
    des plafonds.
    """
    groups = {}
    for enrollment in students:
        level = enrollment.level
        key = (
            level.order if level else 999,
            level.id if level else None,
            level.name if level else "Niveau inconnu",
            (enrollment.series or "").strip().upper(),
        )
        groups.setdefault(key, []).append(enrollment)

    return {
        **tally(students),
        "levels": [
            {
                "level": level_id,
                "series": series,
                "key": stream_key(level_id, series) if level_id else "",
                "label": f"{name} {series}".strip(),
                **tally(grouped),
            }
            for (_, level_id, name, series), grouped in sorted(
                groups.items(), key=lambda item: (item[0][0], item[0][2], item[0][3]),
            )
        ],
    }


def band_of(enrollment):
    """Borne basse de la tranche où tombe la moyenne retenue, ou `None`.

    Un élève sous 12, ou sans moyenne, n'appartient à aucune tranche : les
    limites ne portent que sur le haut du classement, là où la concentration
    pose problème.
    """
    average = effective_average(enrollment)
    if average is None:
        return None
    for _, low, high in AVERAGE_BANDS:
        if low <= average < high:
            return str(low)
    return None


def stream_key(level_id, series):
    """Clé d'un cursus : le niveau et, s'il y en a une, la série.

    Une 1ère D et une 1ère A4 portent le même niveau et n'ont pourtant rien à
    voir — filières, effectifs et profils diffèrent. Les plafonds se règlent
    donc sur le couple, pas sur le seul niveau.
    """
    return f"{level_id}|{(series or '').strip().upper()}"


def band_limits(rules, level_id=None, series=""):
    """Plafonds par tranche de moyenne pour un cursus, nettoyés.

    Dix-sept élèves entre 12 et 14 ne se traitent pas pareil en 5ème, où trois
    classes se les partagent, et en Terminale D, où il n'y en a qu'une. À
    défaut de réglage propre à la série, celui du niveau sans série sert de
    repli : un collège n'a pas de série à distinguer.
    """
    stored = rules.band_limits if isinstance(rules.band_limits, dict) else {}
    bands = stored.get(stream_key(level_id, series))
    if not isinstance(bands, dict) and (series or "").strip():
        bands = stored.get(stream_key(level_id, ""))
    if not isinstance(bands, dict):
        return {}

    limits = {}
    for key, value in bands.items():
        try:
            limit = int(value)
        except (TypeError, ValueError):
            continue
        if limit > 0:
            limits[str(key)] = limit
    return limits


def group_key(level_id, series):
    """Niveau et série : deux élèves ne se répartissent ensemble que là-dedans."""
    return level_id, (series or "").strip().casefold()


def natural_class_key(school_class):
    """Ordre naturel des classes : 6A, 6B… et Tle D-1 avant Tle D-10.

    Un tri alphabétique placerait « D-10 » avant « D-2 » ; découper les
    nombres et les comparer comme des nombres rétablit l'ordre attendu.
    """
    return tuple(
        (token.isdigit(), int(token) if token.isdigit() else token.casefold())
        for token in re.split(r"(\d+)", school_class.group)
        if token
    )


def is_girl(enrollment):
    return (getattr(enrollment.student, "gender", "") or "").strip().upper().startswith("F")


def student_order(rules):
    """Clé de tri des élèves, selon les règles de l'établissement.

    Le premier de la liste va dans la première classe. Selon les réglages, il
    est le meilleur, le plus jeune, les deux, ou ni l'un ni l'autre — auquel
    cas seul le matricule départage, ce qui reste stable et reproductible.
    """
    def key(enrollment):
        average = effective_average(enrollment)
        rank = -(average if average is not None else UNKNOWN_AVERAGE) if rules.best_first else Decimal("0")
        birth = enrollment.student.date_of_birth
        # Une date de naissance élevée = élève plus jeune : la nier le fait
        # remonter, donc le place dans les premières classes.
        youth = -(birth.toordinal() if birth else 0) if rules.youngest_first else 0
        return rank, youth, enrollment.pk
    return key


# ── Combien d'élèves chaque classe reçoit ────────────────────────────────────

def free_places(school_class, rules, overflowing=False):
    """Places restantes dans une classe, marge de dépassement comprise."""
    ceiling = school_class.maximum_capacity
    if overflowing and rules.allow_overflow:
        ceiling += rules.overflow_margin
    return max(0, ceiling - school_class.effectif)


def headcount_quotas(classes, count, rules, overflowing=False):
    """Nombre d'élèves attribué à chaque classe, sans encore dire lesquels.

    Équilibrer, c'est donner le prochain élève à la classe la moins remplie —
    une classe à 25 se remplit avant une classe à 40. Sans équilibrage, les
    classes se remplissent l'une après l'autre jusqu'à leur maximum.
    """
    capacity = {school_class.pk: free_places(school_class, rules, overflowing) for school_class in classes}
    quotas = {school_class.pk: 0 for school_class in classes}
    placeable = min(count, sum(capacity.values()))

    if not rules.balance_headcount:
        left = placeable
        for school_class in classes:
            taken = min(left, capacity[school_class.pk])
            quotas[school_class.pk] = taken
            left -= taken
        return quotas, placeable

    for _ in range(placeable):
        candidates = [c for c in classes if quotas[c.pk] < capacity[c.pk]]
        chosen = min(candidates, key=lambda c: (
            c.effectif + quotas[c.pk],
            (c.effectif + quotas[c.pk]) / max(1, c.maximum_capacity),
            natural_class_key(c),
        ))
        quotas[chosen.pk] += 1
    return quotas, placeable


def girl_quotas(classes, quotas, girls_before, girl_count, rules):
    """Combien de filles chaque classe reçoit, à quota d'effectif donné.

    Même principe que pour les effectifs, mais sur le nombre de filles déjà
    présentes : la classe qui en compte le moins reçoit la suivante. Une classe
    ne peut évidemment pas recevoir plus de filles que de places attribuées.
    """
    added = {school_class.pk: 0 for school_class in classes}
    if not rules.balance_girls:
        return added, False

    for _ in range(girl_count):
        candidates = [c for c in classes if added[c.pk] < quotas[c.pk]]
        if not candidates:
            break
        chosen = min(candidates, key=lambda c: (
            girls_before.get(c.pk, 0) + added[c.pk], natural_class_key(c),
        ))
        added[chosen.pk] += 1
    return added, True


# ── Qui va où ────────────────────────────────────────────────────────────────

def reserve_excellent(classes, quotas, students, rules, limits):
    """Met de côté quelques excellents élèves pour les dernières classes.

    Sans cette réserve, les meilleurs remplissent les premières classes et les
    dernières n'ont plus que des élèves en difficulté. On sert donc les classes
    à l'envers — la dernière d'abord — pour que les tout meilleurs y aillent,
    et l'on s'arrête à ce que chaque classe peut recevoir.

    Retourne aussi le compte par tranche déjà consommé dans chaque classe, que
    la distribution poursuit.
    """
    allocations = {school_class.pk: [] for school_class in classes}
    used = {school_class.pk: {} for school_class in classes}
    if not rules.reserved_excellent or not classes:
        return allocations, set(), used

    excellent = [
        enrollment for enrollment in students
        if (effective_average(enrollment) or UNKNOWN_AVERAGE) >= rules.excellent_minimum
    ]
    rounds = min(rules.reserved_excellent, len(excellent) // len(classes))
    reserved, index = set(), 0
    for _ in range(rounds):
        for school_class in reversed(classes):
            if index >= len(excellent):
                break
            if len(allocations[school_class.pk]) >= quotas[school_class.pk]:
                continue
            enrollment = excellent[index]
            band = band_of(enrollment)
            counters = used[school_class.pk]
            if band and band in limits and counters.get(band, 0) >= limits[band]:
                # La tranche est pleine ici : cet excellent ira ailleurs.
                continue
            allocations[school_class.pk].append(enrollment)
            if band:
                counters[band] = counters.get(band, 0) + 1
            reserved.add(enrollment.pk)
            index += 1
    return allocations, reserved, used


def serve(pool, taken, school_class, used, limits, wanted, allocations, strict=True):
    """Sert `wanted` élèves d'une file à une classe, dans l'ordre du rang.

    Un élève dont la tranche de moyenne est déjà pleine dans cette classe est
    sauté : il reste dans la file et ira dans une classe suivante. Au second
    passage (`strict` à faux) la limite ne s'applique plus — mieux vaut une
    classe un peu trop bien dotée qu'un élève laissé sans classe.
    """
    served = 0
    counters = used[school_class.pk]
    for enrollment in pool:
        if served >= wanted:
            break
        if enrollment.pk in taken:
            continue
        band = band_of(enrollment)
        if strict and band in limits and counters.get(band, 0) >= limits[band]:
            continue
        taken.add(enrollment.pk)
        if band:
            counters[band] = counters.get(band, 0) + 1
        allocations[school_class.pk].append(enrollment)
        served += 1
    return served


def fill(classes, quotas, allocations, students, girls_added, gendered, used, limits):
    """Distribue les élèves restants, classe par classe, dans l'ordre du rang.

    Les élèves arrivent déjà triés : la première classe prend les premiers.
    Quand l'équilibre des filles est demandé, on puise dans deux files — filles
    et garçons — pour respecter le quota de chacune sans casser l'ordre du rang
    à l'intérieur de chaque file.

    Deux passages : le premier respecte les limites par tranche de moyenne, le
    second comble ce qu'elles ont empêché de remplir.
    """
    girls = [row for row in students if is_girl(row)] if gendered else []
    others = [row for row in students if not is_girl(row)] if gendered else []
    taken = set()

    for strict in (True, False):
        for school_class in classes:
            missing = quotas[school_class.pk] - len(allocations[school_class.pk])
            if missing <= 0:
                continue
            if gendered:
                wanted = min(girls_added.get(school_class.pk, 0), missing)
                # Au second passage, les quotas de filles sont déjà servis :
                # on ne cherche qu'à combler ce qui manque.
                wanted = wanted if strict else 0
                served = serve(girls, taken, school_class, used, limits, wanted, allocations, strict)
                missing -= served
                serve(others, taken, school_class, used, limits, missing, allocations, strict)
                if len(allocations[school_class.pk]) < quotas[school_class.pk]:
                    serve(
                        girls, taken, school_class, used, limits,
                        quotas[school_class.pk] - len(allocations[school_class.pk]),
                        allocations, strict,
                    )
            else:
                serve(students, taken, school_class, used, limits, missing, allocations, strict)
        if all(len(allocations[c.pk]) >= quotas[c.pk] for c in classes):
            break


def distribute_group(classes, students, girls_before, rules):
    """Répartit les élèves d'un même niveau et d'une même série.

    Retourne les classes attribuées, élève par élève. Un élève qui n'a pas
    trouvé de place n'apparaît pas : l'appelant compte les manquants.
    """
    classes = sorted(classes, key=natural_class_key)
    ranked = sorted(students, key=student_order(rules))
    # Toutes les classes d'un groupe partagent le niveau et la série : c'est ce
    # couple qui porte les plafonds par tranche.
    limits = band_limits(
        rules,
        classes[0].level_id if classes else None,
        classes[0].series if classes else "",
    )

    quotas, placeable = headcount_quotas(classes, len(ranked), rules)
    if placeable < len(ranked) and rules.allow_overflow:
        # Toutes les classes sont pleines : on rouvre le calcul avec la marge
        # de dépassement plutôt que de laisser des élèves sans classe.
        quotas, placeable = headcount_quotas(classes, len(ranked), rules, overflowing=True)

    allocations, reserved, used = reserve_excellent(classes, quotas, ranked, rules, limits)
    remaining = [enrollment for enrollment in ranked if enrollment.pk not in reserved]

    # Les filles déjà placées par la réserve comptent dans l'équilibre.
    counted_before = dict(girls_before)
    left = {}
    for school_class in classes:
        placed = allocations[school_class.pk]
        counted_before[school_class.pk] = counted_before.get(school_class.pk, 0) + sum(
            1 for enrollment in placed if is_girl(enrollment)
        )
        left[school_class.pk] = quotas[school_class.pk] - len(placed)

    girls_added, gendered = girl_quotas(
        classes, left, counted_before,
        sum(1 for enrollment in remaining if is_girl(enrollment)), rules,
    )
    fill(classes, quotas, allocations, remaining, girls_added, gendered, used, limits)
    return allocations
