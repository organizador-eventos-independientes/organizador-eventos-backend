from django.db import migrations, models


class Migration(migrations.Migration):
    # El cliente y su contacto pasan a ser campos separados. Los eventos que
    # ya existían quedan con el contacto vacío (el cliente no se modifica).

    dependencies = [
        ('eventos', '0010_subtarea_estado_pendiente'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='contacto',
            field=models.CharField(default='', max_length=200),
        ),
    ]
