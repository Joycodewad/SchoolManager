from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0020_teacher_assignment_subjects")]
    operations = [migrations.AddField(
        model_name="studentenrollment", name="school_class",
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="student_enrollments", to="ekdschoolmanager.schoolclass", verbose_name="classe"),
    )]
