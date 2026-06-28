from django.db import migrations, models
import django.db.models.deletion


def copy_subject_links(apps, schema_editor):
    User = apps.get_model("ekdschoolmanager", "CustomUser")
    Subject = apps.get_model("ekdschoolmanager", "Subject")
    for user in User.objects.prefetch_related("school_memberships"):
        school_ids = list(user.school_memberships.filter(is_active=True).values_list("school_id", flat=True))
        updates = {}
        for old_name, new_name in (
            ("primary_subject", "primary_subject_ref"),
            ("secondary_subject", "secondary_subject_ref"),
            ("tertiary_subject", "tertiary_subject_ref"),
        ):
            value = getattr(user, old_name, "")
            if value:
                subject = Subject.objects.filter(school_id__in=school_ids, name__iexact=value).first()
                if subject:
                    updates[f"{new_name}_id"] = subject.id
        if updates:
            User.objects.filter(pk=user.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0015_alter_studentenrollment_enrollment_number_and_more")]
    operations = [
        migrations.AddField(model_name="customuser", name="primary_subject_ref", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_personnel", to="ekdschoolmanager.subject")),
        migrations.AddField(model_name="customuser", name="secondary_subject_ref", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="secondary_personnel", to="ekdschoolmanager.subject")),
        migrations.AddField(model_name="customuser", name="tertiary_subject_ref", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tertiary_personnel", to="ekdschoolmanager.subject")),
        migrations.RunPython(copy_subject_links, migrations.RunPython.noop),
        migrations.RemoveField(model_name="customuser", name="primary_subject"),
        migrations.RemoveField(model_name="customuser", name="secondary_subject"),
        migrations.RemoveField(model_name="customuser", name="tertiary_subject"),
        migrations.RenameField(model_name="customuser", old_name="primary_subject_ref", new_name="primary_subject"),
        migrations.RenameField(model_name="customuser", old_name="secondary_subject_ref", new_name="secondary_subject"),
        migrations.RenameField(model_name="customuser", old_name="tertiary_subject_ref", new_name="tertiary_subject"),
        migrations.AlterField(model_name="customuser", name="primary_subject", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_personnel", to="ekdschoolmanager.subject", verbose_name="matière principale")),
        migrations.AlterField(model_name="customuser", name="secondary_subject", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="secondary_personnel", to="ekdschoolmanager.subject", verbose_name="matière secondaire")),
        migrations.AlterField(model_name="customuser", name="tertiary_subject", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tertiary_personnel", to="ekdschoolmanager.subject", verbose_name="matière tertiaire")),
    ]
