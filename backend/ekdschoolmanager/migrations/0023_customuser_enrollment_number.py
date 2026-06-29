from django.db import migrations, models


def copy_student_numbers(apps, schema_editor):
    User = apps.get_model("ekdschoolmanager", "CustomUser")
    Enrollment = apps.get_model("ekdschoolmanager", "StudentEnrollment")
    for user in User.objects.filter(role="eleve"):
        enrollment = Enrollment.objects.filter(student=user).order_by("-enrolled_at").first()
        if enrollment:
            user.enrollment_number = enrollment.enrollment_number
            user.save(update_fields=["enrollment_number"])


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0022_student_enrollment_series")]
    operations = [
        migrations.AddField(model_name="customuser", name="enrollment_number", field=models.CharField(blank=True, max_length=50, null=True, verbose_name="numéro matricule")),
        migrations.RunPython(copy_student_numbers, migrations.RunPython.noop),
    ]
