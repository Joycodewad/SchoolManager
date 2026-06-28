from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0017_schoolclass")]
    operations = [
        migrations.AddField(
            model_name="schoolclass", name="homeroom_teacher",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="homeroom_classes", to=settings.AUTH_USER_MODEL, verbose_name="enseignant titulaire"),
        ),
        migrations.CreateModel(
            name="ClassSubject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weekly_hours", models.PositiveSmallIntegerField(verbose_name="heures par semaine")),
                ("coefficient", models.DecimalField(decimal_places=2, max_digits=5, verbose_name="coefficient")),
                ("can_schedule_after_break", models.BooleanField(default=True, verbose_name="programmable après la récréation")),
                ("can_schedule_afternoon", models.BooleanField(default=True, verbose_name="programmable l’après-midi")),
                ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subject_configurations", to="ekdschoolmanager.schoolclass")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="class_configurations", to="ekdschoolmanager.subject")),
            ],
            options={"verbose_name": "matière de classe", "verbose_name_plural": "matières de classe", "ordering": ["subject__name"]},
        ),
        migrations.AddConstraint(model_name="classsubject", constraint=models.UniqueConstraint(fields=("school_class", "subject"), name="unique_subject_per_class")),
        migrations.AddConstraint(model_name="classsubject", constraint=models.CheckConstraint(condition=models.Q(("weekly_hours__gt", 0)), name="class_subject_weekly_hours_positive")),
        migrations.AddConstraint(model_name="classsubject", constraint=models.CheckConstraint(condition=models.Q(("coefficient__gt", 0)), name="class_subject_coefficient_positive")),
    ]
