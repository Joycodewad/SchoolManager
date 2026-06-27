from django.db import migrations


LEVELS = [
    ("CEI", "primaire"), ("CP1", "primaire"), ("CP2", "primaire"),
    ("CE1", "primaire"), ("CE2", "primaire"), ("CM1", "primaire"),
    ("CM2", "primaire"), ("6ème", "college"), ("5ème", "college"),
    ("4ème", "college"), ("3ème", "college"), ("Seconde", "lycee"),
    ("Première", "lycee"), ("Terminale", "lycee"),
]


def seed_levels(apps, schema_editor):
    School = apps.get_model("ekdschoolmanager", "School")
    SchoolLevel = apps.get_model("ekdschoolmanager", "SchoolLevel")
    for school in School.objects.all():
        for order, (name, stage) in enumerate(LEVELS, start=1):
            SchoolLevel.objects.get_or_create(
                school=school,
                name=name,
                defaults={"stage": stage, "order": order, "is_active": True},
            )


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0012_schoollevel_studentenrollment_level_and_more")]
    operations = [migrations.RunPython(seed_levels, migrations.RunPython.noop)]
