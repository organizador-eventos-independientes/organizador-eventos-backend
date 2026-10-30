from django.db import migrations, models


class Migration(migrations.Migration):
    # Con el tipo "otro" se guarda cuál es. Los eventos que ya existían quedan
    # con el campo vacío.

    dependencies = [
        ('eventos', '0011_evento_contacto'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='tipo_otro',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
    ]
