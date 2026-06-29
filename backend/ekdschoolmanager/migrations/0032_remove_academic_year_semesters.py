from datetime import timedelta

from django.db import migrations


def convert_semesters_to_trimesters(apps, schema_editor):
    AcademicYear = apps.get_model("ekdschoolmanager", "AcademicYear")
    AcademicPeriod = apps.get_model("ekdschoolmanager", "AcademicPeriod")

    for academic_year in AcademicYear.objects.filter(division_system="semestre"):
        total_days = (academic_year.end_date - academic_year.start_date).days + 1
        academic_year.periods.all().delete()
        periods = []
        for index in range(3):
            start = academic_year.start_date + timedelta(days=(total_days * index) // 3)
            next_start = academic_year.start_date + timedelta(days=(total_days * (index + 1)) // 3)
            periods.append(AcademicPeriod(
                academic_year=academic_year,
                number=index + 1,
                name=f"{index + 1}{'er' if index == 0 else 'e'} trimestre",
                start_date=start,
                end_date=academic_year.end_date if index == 2 else next_start - timedelta(days=1),
                is_active=index == 0 and academic_year.is_active,
                is_closed=academic_year.is_closed,
            ))
        AcademicPeriod.objects.bulk_create(periods)


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0031_remove_customuser_allergies_and_more"),
    ]

    operations = [
        migrations.RunPython(convert_semesters_to_trimesters, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="academicyear",
            name="division_system",
        ),
    ]
