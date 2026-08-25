"""Reconduction des paramètres d'une année académique sur la suivante.

Clôturer une année sans rien préparer pour la suivante, c'est repartir d'une
feuille blanche : plus une seule classe, donc nulle part où faire passer les
élèves admis, plus de barème de scolarité, et des règles de bulletin qui ne
visent plus rien. La clôture recopie donc ce qui se reconduit d'une année à
l'autre :

* les **classes** et leur configuration — matières, coefficients, heures
  hebdomadaires, capacité ;
* les **barèmes de scolarité** — modules de frais, montants garçon/fille,
  tranches, avec les échéances décalées d'un an ;
* la **portée des règles de bulletin** qui visent des classes nommées.

Deux principes tiennent tout le module :

1. **on complète, on ne remplace jamais** — ce que l'établissement a déjà
   saisi pour l'année suivante fait foi, la reconduction passe son chemin ;
2. **rien n'est copié deux fois** — reconduire une année déjà préparée ne crée
   aucun doublon, ce qui rend l'opération rejouable sans dégât.

Le bilan retourné ne compte pas seulement : il note l'identifiant de chaque
objet créé. C'est ce qui permet d'annuler une clôture sans toucher à ce que
l'établissement aurait saisi par ailleurs dans l'année neuve (voir
`yearreopen`).

Le paramétrage des bulletins lui-même — modèle, filigranes, appréciations,
choix des signataires — est réglé par établissement et non par année : il vaut
déjà pour l'année suivante, il n'y a rien à recopier. Seules les règles d'ordre
des matières visant des classes précises ont besoin d'être étendues, puisque
les classes, elles, changent d'identité chaque année.
"""

from .models import (
    ClassFeeItem,
    ClassSubject,
    FeeInstallment,
    FeeModule,
    SchoolClass,
    SubjectCategoryOrder,
    TuitionFeePlan,
)


def shift_years(value, years):
    """Le même jour, `years` ans plus tard.

    Une échéance au 29 février recule au 28 : l'année suivante n'est pas
    forcément bissextile.
    """
    if value is None or not years:
        return value
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def class_identity(school_class):
    """Ce qui fait qu'une classe est « la même » d'une année sur l'autre.

    C'est aussi la clé d'unicité en base, à l'année près : reconduire une
    classe déjà présente violerait la contrainte.
    """
    return (school_class.level_id, school_class.series, school_class.group)


# ── Classes et configuration pédagogique ─────────────────────────────────────

def copy_class_subjects(source_class, target_class):
    """Recopie les matières d'une classe et retourne les identifiants créés.

    Une classe cible qui a déjà des matières est laissée telle quelle : elle a
    été configurée à la main, et compléter sa liste rendrait une matière
    volontairement retirée. Les matières désactivées depuis ne suivent pas.
    """
    if ClassSubject.objects.filter(school_class=target_class).exists():
        return []
    rows = [
        ClassSubject(
            school_class=target_class,
            subject=configuration.subject,
            weekly_hours=configuration.weekly_hours,
            coefficient=configuration.coefficient,
            can_schedule_after_break=configuration.can_schedule_after_break,
            can_schedule_afternoon=configuration.can_schedule_afternoon,
        )
        for configuration in source_class.subject_configurations.select_related("subject")
        if configuration.subject.is_active
    ]
    return [row.id for row in ClassSubject.objects.bulk_create(rows)]


def copy_classes(source_year, target_year, report):
    """Reconduit les classes actives et retourne la correspondance ancienne → nouvelle.

    La correspondance sert ensuite aux barèmes et aux règles de bulletin, qui
    désignent des classes : sans elle, ils ne sauraient pas quoi viser dans
    l'année neuve.
    """
    existing = {
        class_identity(school_class): school_class
        for school_class in SchoolClass.objects.filter(academic_year=target_year)
    }
    mapping = {}
    for source_class in (
        SchoolClass.objects
        .filter(academic_year=source_year, is_active=True)
        .select_related("level")
        .order_by("level__order", "series", "group")
    ):
        target_class = existing.get(class_identity(source_class))
        if target_class is None:
            target_class = SchoolClass.objects.create(
                school=source_class.school,
                academic_year=target_year,
                level=source_class.level,
                series=source_class.series,
                group=source_class.group,
                maximum_capacity=source_class.maximum_capacity,
                # Le titulaire n'est pas reconduit : la répartition des
                # enseignants se refait chaque rentrée, et hériter de celle de
                # l'an dernier donnerait une grille fausse d'avance.
                is_active=True,
            )
            existing[class_identity(source_class)] = target_class
            report["classes"] += 1
            report["created_classes"].append(target_class.id)
        else:
            report["classes_kept"] += 1
        created = copy_class_subjects(source_class, target_class)
        report["class_subjects"] += len(created)
        report["created_class_subjects"] += created
        mapping[source_class.id] = target_class
    return mapping


# ── Barèmes de scolarité ─────────────────────────────────────────────────────

def copy_fee_modules(source_year, target_year, report):
    """Reconduit les modules de frais et retourne la correspondance par module.

    Un module porte l'année : « Écolage » de 2025-2026 et « Écolage » de
    2026-2027 sont deux lignes, pour que les montants et les recettes de
    chaque année restent séparés.
    """
    existing = {
        module.name.casefold(): module
        for module in FeeModule.objects.filter(
            school=target_year.school, academic_year=target_year,
        )
    }
    mapping = {}
    for module in FeeModule.objects.filter(
        school=source_year.school, academic_year=source_year, is_active=True,
    ):
        target = existing.get(module.name.casefold())
        if target is None:
            target = FeeModule.objects.create(
                school=module.school, academic_year=target_year, name=module.name,
            )
            existing[module.name.casefold()] = target
            report["created_fee_modules"].append(target.id)
        mapping[module.id] = target
    return mapping


def copy_fee_plans(source_year, target_year, class_map, report):
    """Reconduit le barème de chaque classe : montants, tranches, échéances.

    Une classe qui a déjà son barème dans l'année neuve n'est pas touchée. Les
    échéances des tranches sont décalées du nombre d'années qui sépare les
    deux rentrées : une première tranche due au 15 octobre 2025 reste due au
    15 octobre 2026.
    """
    modules = copy_fee_modules(source_year, target_year, report)
    years = target_year.start_date.year - source_year.start_date.year
    # Le barème est unique par classe : on regarde la classe et non l'année,
    # pour qu'un barème mal rattaché ne fasse pas échouer la reconduction.
    already_planned = set(
        TuitionFeePlan.objects
        .filter(school_class__in=list(class_map.values()))
        .values_list("school_class_id", flat=True)
    )
    plans = (
        TuitionFeePlan.objects
        .filter(academic_year=source_year, school_class_id__in=class_map)
        .prefetch_related("items__installments")
    )
    for plan in plans:
        target_class = class_map[plan.school_class_id]
        if target_class.id in already_planned:
            continue
        target_plan = TuitionFeePlan.objects.create(
            school=plan.school, academic_year=target_year, school_class=target_class,
        )
        report["fee_plans"] += 1
        report["created_fee_plans"].append(target_plan.id)
        for item in plan.items.all():
            fee_module = modules.get(item.fee_module_id)
            if fee_module is None:
                # Module désactivé depuis : ses frais ne sont plus appelés.
                continue
            target_item = ClassFeeItem.objects.create(
                plan=target_plan,
                fee_module=fee_module,
                male_amount=item.male_amount,
                female_amount=item.female_amount,
                payable_in_installments=item.payable_in_installments,
            )
            report["fee_items"] += 1
            FeeInstallment.objects.bulk_create([
                FeeInstallment(
                    class_fee=target_item,
                    name=installment.name,
                    percentage=installment.percentage,
                    due_date=shift_years(installment.due_date, years),
                    order=installment.order,
                )
                for installment in item.installments.all()
            ])


# ── Règles d'affichage des bulletins ─────────────────────────────────────────

def extend_report_card_rules(school, class_map, report):
    """Étend aux classes reconduites les règles de bulletin qui visent des classes.

    L'ordre des types de matières se règle par établissement, sauf les règles
    de portée « des classes choisies », qui nomment des classes — donc une
    année précise. On leur ajoute les nouvelles classes sans retirer les
    anciennes : les bulletins déjà édités doivent rester lisibles tels quels.
    """
    rules = SubjectCategoryOrder.objects.filter(
        school=school, scope=SubjectCategoryOrder.Scope.CLASSES,
    ).prefetch_related("classes")
    for rule in rules:
        aimed = list(rule.classes.all())
        known = {school_class.id for school_class in aimed}
        additions = [
            class_map[school_class.id] for school_class in aimed
            if school_class.id in class_map and class_map[school_class.id].id not in known
        ]
        if additions:
            rule.classes.add(*additions)
            report["report_card_rules"] += 1
            report["rule_additions"] += [
                [rule.id, school_class.id] for school_class in additions
            ]


# ── Reconduction complète ────────────────────────────────────────────────────

def copy_year_settings(source_year, target_year):
    """Reconduit classes, barèmes et règles de bulletin ; retourne le bilan.

    Appelée par la clôture avant de faire passer les élèves : c'est parce que
    les classes de l'année neuve existent déjà que chaque admis peut y être
    affecté.
    """
    report = {
        "classes": 0, "classes_kept": 0, "class_subjects": 0,
        "fee_plans": 0, "fee_items": 0, "report_card_rules": 0,
        # Ce qui a réellement été créé, objet par objet : l'annulation d'une
        # clôture ne défait que cela, et laisse le reste de l'année neuve.
        "created_classes": [], "created_class_subjects": [],
        "created_fee_plans": [], "created_fee_modules": [], "rule_additions": [],
    }
    class_map = copy_classes(source_year, target_year, report)
    copy_fee_plans(source_year, target_year, class_map, report)
    extend_report_card_rules(source_year.school, class_map, report)
    return report
