from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0023_customuser_enrollment_number")]
    operations = [
        migrations.AddField(
            model_name="customuser", name="student_status",
            field=models.CharField(choices=[("nouveau", "Nouveau"), ("redoublant", "Redoublant")], default="nouveau", max_length=12, verbose_name="statut de l’élève"),
        ),
        migrations.AddField(
            model_name="customuser", name="year_result",
            field=models.CharField(blank=True, choices=[("reussi", "Réussi"), ("echoue", "Échoué")], default=None, max_length=8, null=True, verbose_name="résultat de fin d’année"),
        ),
    ]
