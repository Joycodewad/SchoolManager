import django.db.models.deletion
from django.db import migrations, models


def select_first_subject_as_primary(apps, schema_editor):
    CustomUser = apps.get_model("ekdschoolmanager", "CustomUser")
    for user in CustomUser.objects.filter(role="enseignant").iterator():
        subject_id = user.subjects.values_list("id", flat=True).first()
        if subject_id:
            user.primary_subject_id = subject_id
            user.save(update_fields=["primary_subject"])


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0036_dynamic_teacher_subjects"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="primary_subject",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="primary_personnel", to="ekdschoolmanager.subject",
                verbose_name="matière principale",
            ),
        ),
        migrations.RunPython(select_first_subject_as_primary, migrations.RunPython.noop),
    ]
