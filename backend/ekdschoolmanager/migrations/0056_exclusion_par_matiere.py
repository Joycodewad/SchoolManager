"""L'exclusion passe d'une classe entière à un couple (matière, classes).

La table ne contient aucune ligne à ce stade : on remplace la structure
plutôt que de migrer des données inexistantes.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ekdschoolmanager', '0055_classgroupsession_excludedtimetableclass_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='excludedtimetableclass',
            name='unique_excluded_class_per_timetable',
        ),
        migrations.RemoveField(
            model_name='excludedtimetableclass',
            name='school_class',
        ),
        migrations.AddField(
            model_name='excludedtimetableclass',
            name='subject',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='timetable_exclusions',
                to='ekdschoolmanager.subject',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='excludedtimetableclass',
            name='classes',
            field=models.ManyToManyField(
                related_name='timetable_exclusions',
                to='ekdschoolmanager.schoolclass',
                verbose_name='classes exclues',
            ),
        ),
        migrations.AlterModelOptions(
            name='excludedtimetableclass',
            options={
                'ordering': ['subject__name'],
                'verbose_name': 'exclusion de matière',
                'verbose_name_plural': 'exclusions de matière',
            },
        ),
        migrations.AddConstraint(
            model_name='excludedtimetableclass',
            constraint=models.UniqueConstraint(
                fields=('timetable', 'subject'), name='unique_excluded_subject_per_timetable',
            ),
        ),
    ]
