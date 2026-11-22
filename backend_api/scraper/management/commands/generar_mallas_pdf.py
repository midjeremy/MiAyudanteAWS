from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from scraper.etl import crear_cliente_s3
from scraper.mallas_pdf import generar_mallas_pdf, ruta_chrome
from scraper.models import Institucion


class Command(BaseCommand):
    help = 'Imprime en PDF las mallas que la institución publica como página web (Duoc UC) y las sube a S3'

    def add_arguments(self, parser):
        parser.add_argument('--institucion', default='DUOC', help='Código de la institución (por defecto DUOC)')
        parser.add_argument('--forzar', action='store_true', help='Vuelve a imprimir también las que ya tienen PDF')
        parser.add_argument('--limite', type=int, help='Imprime como máximo esta cantidad de mallas')

    def handle(self, *args, **opciones):
        institucion = Institucion.objects.filter(codigo__iexact=opciones['institucion']).first()
        if not institucion:
            raise CommandError(f"No existe la institución {opciones['institucion']}")
        if not ruta_chrome():
            raise CommandError('No se encontró Chrome/Chromium: instala google-chrome o configura CHROME_BIN')
        subidas, fallidas = generar_mallas_pdf(
            crear_cliente_s3(), settings.AWS_STORAGE_BUCKET_NAME, institucion,
            forzar=opciones['forzar'], limite=opciones['limite'], avisar=self.stdout.write,
        )
        self.stdout.write(self.style.SUCCESS(f'Mallas en PDF subidas: {subidas}. Fallidas: {len(fallidas)}.'))
        if fallidas and not subidas:
            raise CommandError('No se pudo generar ninguna malla en PDF')
