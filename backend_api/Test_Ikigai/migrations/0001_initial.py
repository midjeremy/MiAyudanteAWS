import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Pregunta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveSmallIntegerField(unique=True)),
                ('enunciado', models.TextField()),
                ('dimension', models.CharField(choices=[('pasion', 'Pasión'), ('vocacion', 'Vocación'), ('profesion', 'Profesión'), ('mision', 'Misión')], max_length=20)),
                ('area', models.CharField(choices=[('tecnologia', 'Tecnología'), ('salud', 'Salud'), ('economia', 'Economía y Administración'), ('industria', 'Industria y construcción'), ('arte', 'Arte y comunicación'), ('educacion', 'Educación y social'), ('naturaleza', 'Naturaleza y medio ambiente'), ('turismo', 'Turismo y gastronomía'), ('general', 'General')], max_length=20)),
            ],
            options={
                'ordering': ['numero'],
            },
        ),
        migrations.CreateModel(
            name='Resultado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntaje_pasion', models.DecimalField(decimal_places=2, max_digits=5)),
                ('puntaje_vocacion', models.DecimalField(decimal_places=2, max_digits=5)),
                ('puntaje_profesion', models.DecimalField(decimal_places=2, max_digits=5)),
                ('puntaje_mision', models.DecimalField(decimal_places=2, max_digits=5)),
                ('puntajes_area', models.JSONField(default=dict)),
                ('respuestas', models.JSONField(default=dict)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados_ikigai', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-creado_en', '-id'],
            },
        ),
    ]
