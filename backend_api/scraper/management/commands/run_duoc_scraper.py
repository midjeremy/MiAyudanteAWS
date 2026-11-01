from django.conf import settings
from django.core.management.base import BaseCommand
from scrapy import signals
from scrapy.crawler import CrawlerProcess

from scraper.duoc.carga import MINIMO_CARRERAS, cargar_items, obtener_institucion, validar_items
from scraper.duoc.spider import DuocSpider
from scraper.etl import TASA_MINIMA_EXITO, cerrar_lote, crear_cliente_s3, retirar_ofertas_obsoletas, subir_json_crudo, tasa_exito
from scraper.models import LoteScrapingS3


class Command(BaseCommand):
    help = 'Extrae con Scrapy el catálogo de Duoc UC, guarda el crudo en S3, valida y carga las ofertas en PostgreSQL'

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

    def respaldar_en_s3(self, items):
        """Sube mallas y JSON crudo. Un fallo de S3 no invalida los datos extraídos."""
        try:
            s3_client = crear_cliente_s3()
            for item in items:
                html = item.pop('malla_html', None)
                if html:
                    ruta = f"mallas/duoc/{item['url'].rstrip('/').rsplit('/', 1)[-1]}.html"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=ruta,
                        Body=html.encode('utf-8'),
                        ContentType='text/html; charset=utf-8',
                    )
                    item['malla_s3'] = ruta
            ruta_json = subir_json_crudo(s3_client, items, 'duoc')
            self.stdout.write(self.style.SUCCESS(f'[OK] Mallas y JSON crudo en S3: {ruta_json}'))
            return ruta_json
        except Exception as e:
            for item in items:
                item.pop('malla_html', None)
            self.stdout.write(self.style.WARNING(f'[!] No se pudo completar el respaldo en S3: {e}'))
            return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando extracción de Duoc UC con Scrapy...'))
        items = self.extraer(kwargs['limite'])

        institucion = obtener_institucion()
        lote = LoteScrapingS3.objects.create(institucion=institucion, estado_etl='EN_PROCESO')
        lote.s3_url_json_raw = self.respaldar_en_s3(items)
        lote.save(update_fields=['s3_url_json_raw'])

        validas, errores = validar_items(items)
        total = sum(1 for item in items if item['tipo'] == 'carrera')
        tasa = tasa_exito(len(validas), total)
        self.stdout.write(f'Extraídas {total} carreras, válidas {len(validas)} ({tasa}%).')
        for error in errores:
            self.stdout.write(self.style.WARNING(f'  [!] {error}'))

        rastreo_completo = not kwargs['limite']
        if rastreo_completo and (len(validas) < MINIMO_CARRERAS or tasa < TASA_MINIMA_EXITO):
            cerrar_lote(lote, 'ERROR', len(validas), total, errores=errores)
            self.stdout.write(self.style.ERROR(
                f'❌ Lote {lote.id} rechazado: posible cambio en el sitio. No se modifican los datos publicados.'
            ))
            return

        try:
            ids_vigentes = cargar_items(items, institucion, lote, kwargs['cuotas_anuales'])
        except Exception as e:
            cerrar_lote(lote, 'ERROR', 0, total, errores=[*errores, f'Carga: {e}'])
            raise

        retiradas = retirar_ofertas_obsoletas(institucion, ids_vigentes) if rastreo_completo else 0
        cerrar_lote(lote, 'COMPLETADO', len(validas), total, len(ids_vigentes), errores)
        self.stdout.write(self.style.SUCCESS(
            f'✅ Lote {lote.id}: {len(validas)} carreras, {len(ids_vigentes)} ofertas, {retiradas} retiradas. KPI-01: {tasa}%.'
        ))
