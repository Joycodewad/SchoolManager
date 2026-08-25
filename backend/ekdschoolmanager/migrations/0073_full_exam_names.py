"""Noms d'examen écrits en entier sur les bulletins.

« Admis au BAC 1 » se lit mal sur un document remis à une famille : la
décision nomme désormais l'examen tel qu'il s'appelle officiellement.
"""

from django.db import migrations

RENAMED = {
    "BAC 1": "Baccalauréat Première partie",
    "BAC 2": "Baccalauréat Deuxième partie",
}


def write_full_names(apps, schema_editor):
    SchoolLevel = apps.get_model("ekdschoolmanager", "SchoolLevel")
    for short, full in RENAMED.items():
        SchoolLevel.objects.filter(exam_name=short).update(exam_name=full)


def write_short_names(apps, schema_editor):
    SchoolLevel = apps.get_model("ekdschoolmanager", "SchoolLevel")
    for short, full in RENAMED.items():
        SchoolLevel.objects.filter(exam_name=full).update(exam_name=short)


class Migration(migrations.Migration):

    dependencies = [
        ("ekdschoolmanager", "0072_reportcardsettings_show_censor_name_and_more"),
    ]

    operations = [
        migrations.RunPython(write_full_names, write_short_names),
    ]
