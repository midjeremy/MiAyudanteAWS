import re
from urllib.parse import urlsplit

from scrapy import Request
from scrapy.spiders import SitemapSpider

from scraper.catalogos import normalizar_texto


def limpiar_dinero(texto):
    solo_numeros = re.sub(r'[^\d]', '', texto or '')
    # Un monto en 0 tampoco es un precio publicado
    return int(solo_numeros) if solo_numeros and int(solo_numeros) > 0 else None


def extraer_jornadas(texto):
    """Separa 'Jornada y Modalidad: Diurna y vespertina' en cada jornada publicada."""
    valor = (texto or '').split(':', 1)[-1]
    partes = re.split(r'\s*(?:,|/|\sy\s)\s*', valor.strip())
    return [parte.strip() for parte in partes if parte.strip()]


def ruta_carrera(url):
    """Clave para cruzar una carrera con su escuela: la ruta sin dominio ni barra final."""
    return urlsplit(url or '').path.rstrip('/').lower()


_PATRON_MENCION_EN_NOMBRE = re.compile(r'\smenci[oó]n\s', re.IGNORECASE)


def limpiar_mencion(texto):
    """'Competencias de la Mención: "Mención Finanzas"' -> 'Finanzas'; 'Mención Administración Hotelera' -> 'Administración Hotelera'."""
    limpio = ' '.join((texto or '').split())
    limpio = re.sub(r'^competencias de la menci[oó]n\s*:\s*', '', limpio, flags=re.IGNORECASE)
    limpio = limpio.strip(' "\'\u201c\u201d')
    limpio = re.sub(r'^menci[oó]n\s+', '', limpio, flags=re.IGNORECASE)
    return limpio.strip()


def nombre_sin_mencion(nombre):
    """'Ingeniería en Administración Mención Finanzas' -> 'Ingeniería en Administración' (sin mención, igual)."""
    return _PATRON_MENCION_EN_NOMBRE.split(' '.join((nombre or '').split()), maxsplit=1)[0].strip()


def mencion_del_nombre(nombre):
    """La mención que viene en el nombre de la carrera, o '' si no tiene."""
    partes = _PATRON_MENCION_EN_NOMBRE.split(' '.join((nombre or '').split()), maxsplit=1)
    return partes[1].strip() if len(partes) == 2 else ''


_CONECTORES = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'en', 'o', 'u', 'a', 'al', 'para', 'con', 'por'}


def formatear_mencion(texto):
    """'INTELIGENCIA ARTIFICIAL' -> 'Inteligencia Artificial'; 'EN INGENIERÍA DE DATOS' -> 'Ingeniería de Datos'.

    Los títulos de las mallas vienen en mayúsculas; un nombre que ya trae mayúsculas y minúsculas se respeta.
    """
    limpio = ' '.join((texto or '').split()).strip(' "\'\u201c\u201d.')
    limpio = re.sub(r'^en\s+', '', limpio, flags=re.IGNORECASE)
    if limpio != limpio.upper():
        return limpio
    palabras = []
    for posicion, palabra in enumerate(limpio.lower().split()):
        if any(caracter.isdigit() for caracter in palabra):
            palabras.append(palabra.upper())  # 2D, 3D
        elif posicion and palabra in _CONECTORES:
            palabras.append(palabra)
        else:
            palabras.append(palabra[:1].upper() + palabra[1:])
    return ' '.join(palabras)


def mallas_de_menciones(response):
    """[(mención, URL de su malla)] desde los títulos 'MALLA: INGENIERO(A) EN INFORMÁTICA MENCIÓN EN …'.

    Cada título va seguido de un botón que enlaza a '#dmc-malla-<id>'; el contenedor con data-dmc-id="<id>"
    tiene en data-dmc-src la URL de esa malla. Los títulos sin mención (por ejemplo, '(ONLINE)') se ignoran.
    """
    fuentes = {el.attrib.get('data-dmc-id'): el.attrib.get('data-dmc-src')
               for el in response.css('[data-dmc-id][data-dmc-src]')}
    # Con una sola malla el botón enlaza a '#dmc-malla' y el contenedor no trae data-dmc-id
    todas = response.css('[data-dmc-src]::attr(data-dmc-src)').getall()
    unica = todas[0] if len(todas) == 1 else None
    resultado = []
    for titulo_malla in response.xpath('//h3[starts-with(normalize-space(.), "MALLA:")]'):
        titulo = ' '.join(' '.join(titulo_malla.xpath('.//text()').getall()).split())
        partes = _PATRON_MENCION_EN_NOMBRE.split(titulo, maxsplit=1)
        if len(partes) != 2:
            continue
        enlace = titulo_malla.xpath('following-sibling::*[1]//a/@href').get() or ''
        clave = enlace.split('#dmc-malla-', 1)[1] if '#dmc-malla-' in enlace else ''
        resultado.append((formatear_mencion(partes[1]), fuentes.get(clave) or unica))
    return resultado


def extraer_menciones(response, nombre=''):
    """Menciones de la página de una carrera, con sus competencias y su malla.

    Duoc UC las publica de tres formas, que se combinan sin repetir (se comparan sin tildes ni mayúsculas):
    1. En el acordeón de competencias: 'Competencias de la Mención: "Cocina de Alta Gama"' o
       'Mención Administración Hotelera' (aparte de 'Competencias de la Carrera').
    2. Como varias mallas: 'MALLA: INGENIERO(A) EN INFORMÁTICA MENCIÓN EN INGENIERÍA DE DATOS', cada una con su
       URL (Ingeniería en Informática tiene 5).
    3. En el nombre de la carrera ('Ingeniería en Administración Mención Finanzas'), si no hay ninguna de las otras.
    """
    menciones = {}

    def agregar(titulo, competencias=None, url_malla=None):
        clave = normalizar_texto(titulo)
        if not clave:
            return
        mencion = menciones.setdefault(clave, {'nombre': titulo, 'competencias': [], 'url_malla': None})
        if competencias and not mencion['competencias']:
            mencion['competencias'] = competencias
        if url_malla and not mencion['url_malla']:
            mencion['url_malla'] = url_malla

    for cabecera in response.xpath('//div[contains(@class, "card-header")][.//h4[contains(., "Mención")]]'):
        titulo = limpiar_mencion(' '.join(cabecera.xpath('.//h4//text()').getall()))
        if not titulo or titulo.lower().startswith('competencias de la carrera'):
            continue
        competencias = [
            ' '.join(' '.join(li.xpath('.//text()').getall()).split())
            for li in cabecera.xpath('following-sibling::div[1]//li')
        ]
        agregar(titulo, [c for c in competencias if c])
    for titulo, url_malla in mallas_de_menciones(response):
        agregar(titulo, url_malla=url_malla)
    if not menciones and mencion_del_nombre(nombre):
        agregar(mencion_del_nombre(nombre))
    return list(menciones.values())


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
        # El menú de cada carrera enlaza a las escuelas; Scrapy descarta las URL ya visitadas
        for href in set(response.css('a[href*="/escuela/"]::attr(href)').getall()):
            if re.search(r'/escuela/[^/]+/?$', href):
                yield response.follow(href, callback=self.parse_escuela)

        nombre = (response.css('h1::text').get() or '').strip()
        # Todas las líneas: algunas carreras publican '8 semestres (Presencial)' y '16 bimestres (Online)'
        duraciones = [
            re.sub(r'\s+', ' ', ''.join(li.xpath('.//text()').getall())).strip()
            for li in response.xpath('//h2[contains(., "DURACIÓN")]/following-sibling::div[1]//li')
        ]
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
            'duraciones': [texto for texto in duraciones if texto],
            'url_malla': url_malla,
            'ofertas': ofertas,
            'menciones': extraer_menciones(response, nombre),
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

    def parse_escuela(self, response):
        """Escuela y las carreras que lista: así se sabe el área de cada carrera."""
        carreras = {
            ruta_carrera(response.urljoin(href))
            for href in response.css('a[href*="/carreras/"]::attr(href)').getall()
            if re.search(r'/carreras/[^/]+/?$', href)
        }
        yield {
            'tipo': 'escuela',
            'url': response.url,
            'nombre': ' '.join((response.css('h1::text').get() or '').split()),
            'carreras': sorted(carreras),
        }

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
