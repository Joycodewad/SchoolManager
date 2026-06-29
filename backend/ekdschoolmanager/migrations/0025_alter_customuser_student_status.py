from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0024_customuser_student_status_and_result")]
    operations = [migrations.AlterField(
        model_name="customuser", name="student_status",
        field=models.CharField(
            choices=[("nouveau", "Nouveau"), ("redoublant", "Redoublant"), ("abandon", "Abandon")],
            default="nouveau", max_length=12, verbose_name="statut de l’élève",
        ),
    )]
