import json

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from scrapy import signals
from scrapy.crawler import CrawlerProcess

from scraper.duoc.carga import cargar_items, obtener_institucion
from scraper.duoc.spider import DuocSpider
from scraper.models import LoteScrapingS3


class Command(BaseCommand):
    help = 'Extrae con Scrapy el catálogo de Duoc UC, guarda el JSON crudo en S3 y carga las ofertas en PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, help='Detiene el rastreo tras esta cantidad de páginas')
        parser.add_argument('--cuotas-anuales', type=int, help='Calcula el arancel anual multiplicando el mensual por este valor')

    def extraer(self, limite):
        items = []

        # Scrapy guarda una referencia débil al receptor: debe ser una función con nombre
        def guardar_item(item, **_):
            items.append(dict(item))

        proceso = CrawlerProcess({'CLOSESPIDER_ITEMCOUNT': limite or 0})
        crawler = proceso.create_crawler(DuocSpider)
        crawler.signals.connect(guardar_item, signal=signals.item_scraped)
        proceso.crawl(crawler)
        proceso.start(install_signal_handlers=False)
        return items

    def subir_json_crudo(self, items):
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        ruta_s3 = f"raw/duoc/{timezone.now():%Y-%m-%d_%H%M%S}.json"
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                aws_session_token=getattr(settings, 'AWS_SESSION_TOKEN', None),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            )
            s3_client.put_object(
                Bucket=bucket,
                Key=ruta_s3,
                Body=json.dumps(items, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json',
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] JSON crudo en S3: {ruta_s3}'))
            return ruta_s3
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'[!] No se pudo guardar el JSON crudo en S3: {e}'))
            return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando extracción de Duoc UC con Scrapy...'))
        items = self.extraer(kwargs['limite'])

        carreras = sum(1 for item in items if item['tipo'] == 'carrera')
        self.stdout.write(f'Extraídas {carreras} carreras de {len(items)} páginas.')
        if not carreras:
            self.stdout.write(self.style.ERROR('❌ No se extrajo ninguna carrera; no se modifica la base de datos.'))
            return

        institucion = obtener_institucion()
        lote = LoteScrapingS3.objects.create(
            institucion=institucion,
            s3_url_json_raw=self.subir_json_crudo(items),
            total_registros=carreras,
        )

        try:
            total_ofertas = cargar_items(items, institucion, lote, kwargs['cuotas_anuales'])
        except Exception:
            lote.estado_etl = 'ERROR'
            lote.save(update_fields=['estado_etl'])
            raise

        lote.estado_etl = 'COMPLETADO'
        lote.save(update_fields=['estado_etl'])
        self.stdout.write(self.style.SUCCESS(f'✅ Lote {lote.id}: {carreras} carreras y {total_ofertas} ofertas cargadas.'))
