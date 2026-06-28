from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0018_class_subjects_and_homeroom_teacher")]
    operations = [
        migrations.CreateModel(name="TeacherClassAssignment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_class_assignments", to="ekdschoolmanager.academicyear")),
            ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_class_assignments", to="ekdschoolmanager.school")),
            ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_assignments", to="ekdschoolmanager.schoolclass")),
            ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_assignments", to=settings.AUTH_USER_MODEL)),
        ], options={"verbose_name": "affectation d’enseignant", "verbose_name_plural": "affectations d’enseignants"}),
        migrations.CreateModel(name="TeacherUnavailability", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("day", models.PositiveSmallIntegerField(choices=[(0,"Lundi"),(1,"Mardi"),(2,"Mercredi"),(3,"Jeudi"),(4,"Vendredi"),(5,"Samedi"),(6,"Dimanche")], verbose_name="jour")),
            ("all_day", models.BooleanField(default=False, verbose_name="toute la journée")),
            ("start_time", models.TimeField(blank=True, null=True, verbose_name="heure de début")),
            ("end_time", models.TimeField(blank=True, null=True, verbose_name="heure de fin")),
            ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_unavailabilities", to="ekdschoolmanager.academicyear")),
            ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_unavailabilities", to="ekdschoolmanager.school")),
            ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="unavailabilities", to=settings.AUTH_USER_MODEL)),
        ], options={"verbose_name": "indisponibilité d’enseignant", "verbose_name_plural": "indisponibilités d’enseignants", "ordering": ["day","start_time"]}),
        migrations.AddConstraint(model_name="teacherclassassignment", constraint=models.UniqueConstraint(fields=("teacher","school_class"), name="unique_teacher_class_assignment")),
        migrations.AddConstraint(model_name="teacherunavailability", constraint=models.CheckConstraint(condition=models.Q(models.Q(("all_day", True), ("end_time__isnull", True), ("start_time__isnull", True)), models.Q(("all_day", False), ("end_time__isnull", False), ("start_time__isnull", False)), _connector="OR"), name="teacher_unavailability_valid_times")),
    ]
