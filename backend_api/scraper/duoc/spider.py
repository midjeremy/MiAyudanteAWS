import re

from scrapy import Request
from scrapy.spiders import SitemapSpider


def limpiar_dinero(texto):
    solo_numeros = re.sub(r'[^\d]', '', texto or '')
    return int(solo_numeros) if solo_numeros else None


def extraer_jornadas(texto):
    """Separa 'Jornada y Modalidad: Diurna y vespertina' en cada jornada publicada."""
    valor = (texto or '').split(':', 1)[-1]
    partes = re.split(r'\s*(?:,|/|\sy\s)\s*', valor.strip())
    return [parte.strip() for parte in partes if parte.strip()]


def normalizar_nombre_sede(texto):
    return re.sub(r'^(sede|campus)\s+', '', (texto or '').strip(), flags=re.IGNORECASE).strip()


class DuocSpider(SitemapSpider):
    name = 'duoc'
    allowed_domains = ['duoc.cl']
    sitemap_urls = [
        'https://www.duoc.cl/wp-sitemap-posts-carrera_post_type-1.xml',
        'https://www.duoc.cl/wp-sitemap-posts-sedes_post_type-1.xml',
    ]
    sitemap_rules = [
        (r'/carreras/[^/]+/$', 'parse_carrera'),
        (r'/sedes/[^/]+/$', 'parse_sede'),
    ]
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'MiAyudanteBot/1.0 (proyecto de titulo INACAP)',
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'LOG_LEVEL': 'WARNING',
    }

    def parse_carrera(self, response):
        nombre = (response.css('h1::text').get() or '').strip()
        duracion = response.xpath(
            '//h2[contains(., "DURACIÓN")]/following-sibling::div[1]//li/text()'
        ).get()
        url_malla = response.css('[data-dmc-src]::attr(data-dmc-src)').get()

        ofertas = []
        for tarjeta in response.css('section.dma-sa .dma-sa__card'):
            valores = ' '.join(tarjeta.css('.dma-sa__valores p::text').getall())
            matricula = re.search(r'Matrícula semestral:\s*(\$[\d.]+)', valores)
            arancel = re.search(r'Arancel mensual:\s*(\$[\d.]+)', valores)
            ofertas.append({
                'sede': (tarjeta.css('.dma-sa__sede::text').get() or '').strip(),
                'jornadas': extraer_jornadas(tarjeta.css('.dma-sa__jornada::text').get()),
                'matricula_clp': limpiar_dinero(matricula.group(1)) if matricula else None,
                'arancel_mensual_clp': limpiar_dinero(arancel.group(1)) if arancel else None,
            })

        item = {
            'tipo': 'carrera',
            'url': response.url,
            'nombre': nombre,
            'duracion_semestres': limpiar_dinero(duracion),
            'url_malla': url_malla,
            'ofertas': ofertas,
        }
        if not url_malla:
            yield item
            return

        # Varias carreras pueden compartir malla: dont_filter evita que se descarte la segunda
        yield Request(
            url_malla,
            callback=self.parse_malla,
            errback=self.malla_fallida,
            cb_kwargs={'item': item},
            dont_filter=True,
        )

    def parse_malla(self, response, item):
        item['malla_html'] = response.text
        yield item

    def malla_fallida(self, failure):
        self.logger.warning('No se pudo descargar la malla %s', failure.request.url)
        yield failure.request.cb_kwargs['item']

    def parse_sede(self, response):
        direccion = response.xpath('//b[contains(., "Dirección:")]/following-sibling::text()[1]').get()
        if not direccion:
            return
        yield {
            'tipo': 'sede',
            'url': response.url,
            'nombre': normalizar_nombre_sede(response.css('h3.font-weight-bold::text').get()),
            'direccion': direccion.strip().rstrip('.'),
        }
