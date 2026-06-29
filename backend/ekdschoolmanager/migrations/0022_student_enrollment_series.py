from django.db import migrations, models


def copy_class_series(apps, schema_editor):
    Enrollment = apps.get_model("ekdschoolmanager", "StudentEnrollment")
    for enrollment in Enrollment.objects.select_related("school_class").filter(school_class__isnull=False):
        enrollment.series = enrollment.school_class.series
        enrollment.save(update_fields=["series"])


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0021_student_enrollment_class")]
    operations = [
        migrations.AddField(model_name="studentenrollment", name="series", field=models.CharField(blank=True, default="", max_length=20, verbose_name="série")),
        migrations.RunPython(copy_class_series, migrations.RunPython.noop),
    ]
