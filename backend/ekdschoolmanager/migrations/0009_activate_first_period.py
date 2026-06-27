from django.db import migrations


def activate_first_period(apps, schema_editor):
    AcademicYear = apps.get_model("ekdschoolmanager", "AcademicYear")
    for academic_year in AcademicYear.objects.filter(is_active=True, is_closed=False):
        if not academic_year.periods.filter(is_active=True).exists():
            first_period = academic_year.periods.filter(is_closed=False).order_by("number").first()
            if first_period:
                first_period.is_active = True
                first_period.save(update_fields=["is_active"])


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0008_academicperiod_is_active_and_more")]
    operations = [migrations.RunPython(activate_first_period, migrations.RunPython.noop)]
