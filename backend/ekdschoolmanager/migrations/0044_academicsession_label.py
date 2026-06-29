from django.db import migrations, models


def copy_name_to_label(apps, schema_editor):
    AcademicSession = apps.get_model("ekdschoolmanager", "AcademicSession")
    for session in AcademicSession.objects.all().iterator():
        session.label = session.name
        session.save(update_fields=["label"])


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0043_remove_academicsession_academic_session_end_after_start"),
    ]

    operations = [
        migrations.AddField(
            model_name="academicsession",
            name="label",
            field=models.CharField(default="", max_length=80, verbose_name="label"),
            preserve_default=False,
        ),
        migrations.RunPython(copy_name_to_label, migrations.RunPython.noop),
    ]
