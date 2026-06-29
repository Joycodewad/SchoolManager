from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0032_remove_academic_year_semesters"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AcademicPeriod",
        ),
    ]
