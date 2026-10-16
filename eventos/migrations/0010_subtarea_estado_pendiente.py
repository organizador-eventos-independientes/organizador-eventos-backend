from django.db import migrations, models


class Migration(migrations.Migration):
    # Vuelve el estado "Pendiente" como valor inicial de las gestiones nuevas.
    # Las existentes conservan su estado: tras 0009 no se distingue cuáles
    # estaban pendientes y cuáles se pospusieron de verdad.

    dependencies = [
        ('eventos', '0009_alter_subtarea_estado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subtarea',
            name='estado',
            field=models.CharField(
                choices=[
                    ('Pendiente', 'Pendiente'),
                    ('Hecha', 'Hecha'),
                    ('Pospuesta', 'Pospuesta'),
                ],
                default='Pendiente',
                max_length=20,
            ),
        ),
    ]
