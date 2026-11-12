from django.core.management.base import BaseCommand

from Test_Ikigai.models import Pregunta
from Test_Ikigai.preguntas import cargar_preguntas


class Command(BaseCommand):
    help = 'Crea o actualiza las 40 preguntas del Test Ikigai desde Test_Ikigai/preguntas.py.'

    def handle(self, *args, **options):
        total = cargar_preguntas(Pregunta)
        self.stdout.write(self.style.SUCCESS(f'{total} preguntas del Test Ikigai cargadas.'))
