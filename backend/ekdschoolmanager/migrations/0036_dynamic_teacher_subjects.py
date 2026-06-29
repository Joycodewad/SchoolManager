from django.db import migrations, models


def copy_existing_subjects(apps, schema_editor):
    CustomUser = apps.get_model("ekdschoolmanager", "CustomUser")
    through = CustomUser.subjects.through
    links = []
    for user in CustomUser.objects.all().iterator():
        subject_ids = {
            user.primary_subject_id,
            user.secondary_subject_id,
            user.tertiary_subject_id,
        } - {None}
        links.extend(through(customuser_id=user.id, subject_id=subject_id) for subject_id in subject_ids)
    through.objects.bulk_create(links, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0035_classfeeitem_feeinstallment_feemodule_feepayment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="subjects",
            field=models.ManyToManyField(blank=True, related_name="personnel", to="ekdschoolmanager.subject", verbose_name="matières enseignées"),
        ),
        migrations.RunPython(copy_existing_subjects, migrations.RunPython.noop),
        migrations.RemoveField(model_name="customuser", name="primary_subject"),
        migrations.RemoveField(model_name="customuser", name="secondary_subject"),
        migrations.RemoveField(model_name="customuser", name="tertiary_subject"),
    ]
