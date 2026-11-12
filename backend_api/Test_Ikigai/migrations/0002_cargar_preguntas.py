"""Carga los 40 ítems validados por juicio de expertos (ver Test_Ikigai/preguntas.py)."""
from django.db import migrations

from Test_Ikigai.preguntas import cargar_preguntas


def cargar(apps, schema_editor):
    cargar_preguntas(apps.get_model('Test_Ikigai', 'Pregunta'))


def borrar(apps, schema_editor):
    apps.get_model('Test_Ikigai', 'Pregunta').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Test_Ikigai', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, borrar),
    ]
