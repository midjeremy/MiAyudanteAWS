"""Enlaces de malla de una página de carrera de INACAP.

La página publica, en "Sobre la carrera", uno o más botones a la malla digital (siga.inacap.cl) y uno al PDF:
  - "Ver malla digital", o "Ver malla diurna" y "Ver malla vespertina" cuando cambia por jornada
  - "Descargar Malla PDF" (repo.inacapmovil.cl)
Los enlaces traen parámetros de seguimiento (_gl, utm_*), y el código de la malla puede ir en la query o
después de '#/index?': se normalizan para guardar siempre la misma URL.
"""
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

from parsel import Selector

BASE_MALLA_DIGITAL = 'https://siga.inacap.cl/Inacap.Siga.MallaCurricular/#/index?tipomalla=PORTAL&parametros='
_PATRON_CODIGO = re.compile(r'^[A-Za-z0-9_-]{1,40}$')


def normalizar_malla_digital(url):
    """'…/MallaCurricular/?_gl=…#/index?tipomalla=PORTAL&parametros=IEI-IEI-3' -> URL canónica, o None."""
    partes = urlsplit(url or '')
    if 'MallaCurricular' not in partes.path:
        return None
    parametros = parse_qs(partes.query).get('parametros') or parse_qs(partes.fragment.split('?', 1)[-1]).get('parametros')
    if not parametros or not _PATRON_CODIGO.match(parametros[0]):
        return None
    return BASE_MALLA_DIGITAL + parametros[0]


def normalizar_pdf(url):
    """Quita utm_* y demás parámetros de seguimiento del PDF de repo.inacapmovil.cl."""
    partes = urlsplit(url or '')
    if partes.scheme not in ('http', 'https') or not partes.path.lower().endswith('.pdf'):
        return None
    return urlunsplit((partes.scheme, partes.netloc, partes.path, '', ''))


def etiqueta_malla(texto):
    """'Ver malla vespertina >' -> 'Malla vespertina'; 'Ver malla digital' -> 'Malla digital'."""
    texto = re.sub(r'\s+', ' ', texto or '').strip(' >›')
    texto = re.sub(r'^ver\s+', '', texto, flags=re.IGNORECASE)
    return (texto[:1].upper() + texto[1:])[:60] if texto else 'Malla digital'


def extraer_mallas_inacap(html):
    """{'digitales': [{'etiqueta', 'url'}], 'pdf': url o None}, en el orden de la página y sin repetir."""
    selector = Selector(text=html or '')
    digitales, vistas, pdf = [], set(), None
    for enlace in selector.css('a[href]'):
        href = enlace.attrib.get('href', '')
        texto = ' '.join(enlace.css('::text').getall())
        # Solo botones de malla: 'Ir a Transparencia' también apunta a siga.inacap.cl
        url = normalizar_malla_digital(href) if 'malla' in texto.lower() else None
        if url and url not in vistas:
            vistas.add(url)
            digitales.append({'etiqueta': etiqueta_malla(texto), 'url': url})
        elif not pdf and 'pdf_mallas' in href:
            pdf = normalizar_pdf(href)
    return {'digitales': digitales, 'pdf': pdf}
