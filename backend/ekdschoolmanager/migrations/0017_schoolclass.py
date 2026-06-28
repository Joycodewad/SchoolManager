from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0016_link_personnel_subjects")]
    operations = [
        migrations.CreateModel(
            name="SchoolClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("series", models.CharField(blank=True, default="", max_length=20, verbose_name="série")),
                ("group", models.CharField(max_length=20, verbose_name="groupe")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classes", to="ekdschoolmanager.academicyear")),
                ("level", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="classes", to="ekdschoolmanager.schoollevel")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classes", to="ekdschoolmanager.school")),
            ],
            options={"verbose_name": "classe", "verbose_name_plural": "classes", "ordering": ["level__order", "series", "group"]},
        ),
        migrations.AddConstraint(model_name="schoolclass", constraint=models.UniqueConstraint(fields=("academic_year", "level", "series", "group"), name="unique_class_per_academic_year")),
    ]
