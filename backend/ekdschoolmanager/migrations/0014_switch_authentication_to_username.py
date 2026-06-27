from django.db import migrations, models


def populate_usernames(apps, schema_editor):
    CustomUser = apps.get_model("ekdschoolmanager", "CustomUser")
    used = set()
    for user in CustomUser.objects.order_by("id"):
        base = (user.phone or f"user{user.id}").strip() or f"user{user.id}"
        username = base
        suffix = 1
        while username.lower() in used or CustomUser.objects.filter(username=username).exclude(pk=user.pk).exists():
            suffix += 1
            username = f"{base}-{suffix}"
        user.username = username
        user.save(update_fields=["username"])
        used.add(username.lower())


class Migration(migrations.Migration):
    dependencies = [("ekdschoolmanager", "0013_seed_school_levels")]
    operations = [
        migrations.AddField(
            model_name="customuser",
            name="username",
            field=models.CharField(max_length=150, null=True, unique=True, verbose_name="nom d’utilisateur"),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="adresse courriel"),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="phone",
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name="numéro de téléphone"),
        ),
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="customuser",
            name="username",
            field=models.CharField(max_length=150, unique=True, verbose_name="nom d’utilisateur"),
        ),
    ]
