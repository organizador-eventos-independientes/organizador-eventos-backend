
from django.db import migrations, models


def convertir_pendientes_a_pospuestas(apps, schema_editor):
    Subtarea = apps.get_model('eventos', 'Subtarea')
    Subtarea.objects.filter(estado='Pendiente').update(
        estado='Pospuesta'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0008_subtarea_estado_subtarea_nota_estado'),
    ]

    operations = [
        migrations.RunPython(
            convertir_pendientes_a_pospuestas,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='subtarea',
            name='estado',
            field=models.CharField(
                choices=[
                    ('Hecha', 'Hecha'),
                    ('Pospuesta', 'Pospuesta'),
                ],
                default='Pospuesta',
                max_length=20,
            ),
        ),
    ]
