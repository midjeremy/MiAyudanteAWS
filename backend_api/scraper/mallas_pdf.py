"""Mallas en PDF para descargar.

INACAP publica la malla como PDF (el scraper la sube tal cual a S3). Duoc UC la publica como página web
(malla.duoc.cl): aquí se imprime en PDF con Chrome headless, el mismo que usa el scraper de INACAP en la EC2.
Varias carreras y menciones comparten malla, así que la clave en S3 sale de la URL y cada malla se imprime una vez.
"""
import os
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from django.conf import settings

from scraper.models import Carrera, Mencion

NAVEGADORES = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser')
TAMANO_MAXIMO = 20 * 1024 * 1024


def ruta_chrome():
    configurado = getattr(settings, 'CHROME_BIN', '') or os.environ.get('CHROME_BIN', '')
    if configurado:
        return configurado
    return next((ruta for ruta in map(shutil.which, NAVEGADORES) if ruta), None)


def es_pdf(url):
    return bool(url) and urlparse(url).path.lower().endswith('.pdf')


def clave_pdf(url_malla, prefijo='mallas/duoc/pdf'):
    """'https://malla.duoc.cl/mallas/x/047.html' -> 'mallas/duoc/pdf/mallas-x-047.pdf'."""
    ruta = urlparse(url_malla).path.rsplit('.', 1)[0]
    nombre = re.sub(r'[^a-z0-9]+', '-', ruta.lower()).strip('-') or 'malla'
    return f'{prefijo}/{nombre[:150]}.pdf'


def pagina_a_pdf(url, chrome=None, espera_ms=8000, tiempo_maximo=120):
    """Imprime la página en PDF con Chrome headless; deja que el JavaScript de la malla termine de dibujar."""
    if urlparse(url).scheme not in ('http', 'https'):
        raise ValueError(f'URL de malla no válida: {url}')
    chrome = chrome or ruta_chrome()
    if not chrome:
        raise RuntimeError('No se encontró Chrome/Chromium (configura CHROME_BIN)')
    with tempfile.TemporaryDirectory(prefix='malla-') as carpeta:
        salida = os.path.join(carpeta, 'malla.pdf')
        subprocess.run(
            [
                chrome, '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                '--hide-scrollbars', '--no-pdf-header-footer', f'--user-data-dir={carpeta}/perfil',
                f'--virtual-time-budget={espera_ms}', f'--print-to-pdf={salida}', url,
            ],
            check=True, capture_output=True, timeout=tiempo_maximo,
        )
        with open(salida, 'rb') as archivo:
            contenido = archivo.read()
    if not contenido.startswith(b'%PDF') or len(contenido) > TAMANO_MAXIMO:
        raise RuntimeError(f'Chrome no generó un PDF válido para {url}')
    return contenido


def generar_mallas_pdf(s3_client, bucket, institucion, forzar=False, limite=None, imprimir=pagina_a_pdf,
                       avisar=print):
    """Imprime y sube las mallas web (no PDF) de la institución; guarda la clave en la carrera o mención.

    Devuelve (subidas, fallidas). Sin `forzar` solo imprime las que no tienen PDF o cuya malla cambió de URL
    (la clave sale de la URL, así que una clave distinta indica otra malla).
    """
    carreras = Carrera.objects.filter(institucion=institucion, url_malla__isnull=False).exclude(url_malla='')
    menciones = Mencion.objects.filter(carrera__institucion=institucion, url_malla__isnull=False).exclude(url_malla='')
    pendientes = [(c, 's3_url_malla_pdf') for c in carreras.order_by('id')]
    pendientes += [(m, 's3_malla_pdf') for m in menciones.order_by('id')]
    pendientes = [
        (objeto, campo) for objeto, campo in pendientes
        if not es_pdf(objeto.url_malla) and (forzar or getattr(objeto, campo) != clave_pdf(objeto.url_malla))
    ]
    claves = {}  # url -> clave en S3 (None si falló): cada malla se imprime una sola vez
    subidas, fallidas = 0, []
    for objeto, campo in pendientes:
        url = objeto.url_malla
        if url not in claves:
            if limite is not None and len(claves) >= limite:
                break
            try:
                clave = clave_pdf(url)
                s3_client.put_object(
                    Bucket=bucket, Key=clave, Body=imprimir(url), ContentType='application/pdf',
                )
                claves[url] = clave
                subidas += 1
                avisar(f'  [OK] {clave}')
            except Exception as error:  # una malla caída no detiene el resto
                claves[url] = None
                fallidas.append(f'{url}: {str(error)[:200]}')
                avisar(f'  [!] {url}: {str(error)[:200]}')
        if claves[url]:
            setattr(objeto, campo, claves[url])
            objeto.save(update_fields=[campo])
    return subidas, fallidas
