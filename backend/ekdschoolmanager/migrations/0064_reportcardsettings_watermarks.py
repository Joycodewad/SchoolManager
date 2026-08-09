from django.db import migrations, models


def fill_watermarks(apps, schema_editor):
    """Reprend le choix unique existant dans la nouvelle liste combinée."""
    ReportCardSettings = apps.get_model("ekdschoolmanager", "ReportCardSettings")
    for configuration in ReportCardSettings.objects.exclude(watermark="aucun"):
        configuration.watermarks = [configuration.watermark]
        configuration.save(update_fields=["watermarks"])


def clear_watermarks(apps, schema_editor):
    """Retour arrière : le premier filigrane coché redevient le choix unique."""
    ReportCardSettings = apps.get_model("ekdschoolmanager", "ReportCardSettings")
    for configuration in ReportCardSettings.objects.all():
        chosen = configuration.watermarks or []
        configuration.watermark = chosen[0] if chosen else "aucun"
        configuration.save(update_fields=["watermark"])


class Migration(migrations.Migration):

    dependencies = [
        ("ekdschoolmanager", "0063_reportcardsettings_configured_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportcardsettings",
            name="watermarks",
            field=models.JSONField(
                blank=True, default=list,
                help_text="Marques de fond imprimées derrière le bulletin, contre la "
                          "photocopie. Elles se cumulent : mosaïque + diagonale + logo "
                          "peuvent être imprimées ensemble.",
                verbose_name="filigranes",
            ),
        ),
        migrations.AddField(
            model_name="reportcardsettings",
            name="watermark_density",
            field=models.CharField(
                choices=[
                    ("normale", "Normale (lignes espacées)"),
                    ("pleine", "Pleine (motif serré)"),
                    ("max", "Maximale (page saturée)"),
                ],
                default="normale", max_length=8,
                help_text="Serrage du texte répété, sans effet sur les autres filigranes.",
                verbose_name="densité de la mosaïque",
            ),
        ),
        migrations.AlterField(
            model_name="reportcardsettings",
            name="watermark",
            field=models.CharField(
                choices=[
                    ("aucun", "Aucun"),
                    ("mosaique", "Mosaïque (texte répété)"),
                    ("diagonale", "Bandeau en diagonale"),
                    ("logo", "Logo en fond"),
                ],
                default="aucun", max_length=12,
                help_text="Ancien réglage à choix unique, conservé pour les établissements "
                          "paramétrés avant les filigranes combinés. C'est « watermarks » "
                          "qui fait foi à l'impression.",
                verbose_name="filigrane",
            ),
        ),
        migrations.RunPython(fill_watermarks, clear_watermarks),
    ]
