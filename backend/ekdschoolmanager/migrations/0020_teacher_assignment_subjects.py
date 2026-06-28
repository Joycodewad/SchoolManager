from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0019_teacher_assignments_and_unavailability")]
    operations = [
        migrations.CreateModel(name="TeacherAssignmentSubject", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subject_links", to="ekdschoolmanager.teacherclassassignment")),
            ("class_subject", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_links", to="ekdschoolmanager.classsubject")),
        ], options={"verbose_name": "matière affectée à un enseignant", "verbose_name_plural": "matières affectées aux enseignants"}),
        migrations.AddConstraint(model_name="teacherassignmentsubject", constraint=models.UniqueConstraint(fields=("assignment","class_subject"), name="unique_subject_per_teacher_assignment")),
        migrations.AddConstraint(model_name="teacherassignmentsubject", constraint=models.UniqueConstraint(fields=("class_subject",), name="one_teacher_per_class_subject")),
    ]
