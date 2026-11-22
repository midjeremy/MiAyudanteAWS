"""Mallas de INACAP: malla digital (diurna y vespertina), PDF publicado y su salida en la API."""
from django.test import TestCase
from django.urls import reverse

from scraper.mallas_inacap import BASE_MALLA_DIGITAL, extraer_mallas_inacap, normalizar_malla_digital
from scraper.models import Carrera, Institucion

# Fragmento real de "Sobre la carrera" (portal.inacap.cl, noviembre 2026)
HTML_DIURNA_VESPERTINA = '''
<div class="sobre-la-carrera">
  <a class="btn btn-nm btn-link" href="https://inacap.cl/solicitar-info">Solicita más información</a>
  <a class="btn btn-nm btn-link" href="https://siga.inacap.cl/Inacap.Siga.MallaCurricular/?tipomalla=PORTAL&amp;parametros=IEI-IEI-1"
     target="_blank"><span class="icono"></span> Ver malla diurna <span>›</span></a>
  <a class="btn btn-nm btn-link" href="https://siga.inacap.cl/Inacap.Siga.MallaCurricular/?_gl=1*wkb5i6*_gcl_au*MTc1NDI3.#/index?tipomalla=PORTAL&amp;parametros=IEI-IEI-3"
     target="_blank">Ver malla vespertina</a>
  <a class="btn btn-nm btn-link" href="https://repo.inacapmovil.cl/pdf_mallas/TECNOLOGIA-APLICADA/x/INGENIERIA-EN-INFORMATICA-IEI-IEI-1.pdf?utm_source=carrera&amp;utm_medium=pdf"
     target="_blank">Descargar Malla PDF</a>
  <a href="https://siga.inacap.cl/Inacap.Siga.MallaCurricular/?tipomalla=PORTAL&amp;parametros=IEI-IEI-1">Ver malla diurna</a>
  <a href="https://siga.inacap.cl/Inacap.Siga.MallaCurricular/#/index?tipomalla=PORTAL&amp;parametros=EI-EI-1">Ir a Transparencia</a>
</div>'''

HTML_SOLO_DIGITAL = '''
<a href="https://siga.inacap.cl/Inacap.Siga.MallaCurricular/#/index?tipomalla=PORTAL&amp;parametros=TAM-TAM-1">Ver malla digital</a>
<a href="https://repo.inacapmovil.cl/pdf_mallas/MECANICA/MANTENIMIENTO-AERONAUTICO-TAM-TAM-1.pdf">Descargar Malla PDF</a>'''


class ExtraerMallasInacapTests(TestCase):
    def test_diurna_vespertina_y_pdf_sin_seguimiento(self):
        mallas = extraer_mallas_inacap(HTML_DIURNA_VESPERTINA)
        self.assertEqual(mallas['digitales'], [
            {'etiqueta': 'Malla diurna', 'url': BASE_MALLA_DIGITAL + 'IEI-IEI-1'},
            {'etiqueta': 'Malla vespertina', 'url': BASE_MALLA_DIGITAL + 'IEI-IEI-3'},
        ])
        self.assertEqual(
            mallas['pdf'], 'https://repo.inacapmovil.cl/pdf_mallas/TECNOLOGIA-APLICADA/x/INGENIERIA-EN-INFORMATICA-IEI-IEI-1.pdf')

    def test_solo_malla_digital(self):
        mallas = extraer_mallas_inacap(HTML_SOLO_DIGITAL)
        self.assertEqual(mallas['digitales'], [{'etiqueta': 'Malla digital', 'url': BASE_MALLA_DIGITAL + 'TAM-TAM-1'}])
        self.assertTrue(mallas['pdf'].endswith('TAM-TAM-1.pdf'))

    def test_pagina_sin_mallas(self):
        self.assertEqual(extraer_mallas_inacap('<a href="/x">Otra</a>'), {'digitales': [], 'pdf': None})
        self.assertEqual(extraer_mallas_inacap(''), {'digitales': [], 'pdf': None})

    def test_rechaza_codigos_raros(self):
        self.assertIsNone(normalizar_malla_digital(
            'https://siga.inacap.cl/Inacap.Siga.MallaCurricular/?parametros=<script>'))
        self.assertIsNone(normalizar_malla_digital('https://otro.cl/?parametros=IEI-IEI-1'))


class ApiMallasInacapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        inacap = Institucion.objects.create(nombre='INACAP', codigo='INACAP')
        mallas = extraer_mallas_inacap(HTML_DIURNA_VESPERTINA)
        cls.informatica = Carrera.objects.create(
            nombre_carrera='Ingeniería en Informática', institucion=inacap,
            url_malla=mallas['digitales'][0]['url'], mallas_digitales=mallas['digitales'], url_malla_pdf=mallas['pdf'],
            url_carrera='https://portal.inacap.cl/carreras/area-ti/ingenieria-en-informatica',
        )
        # Carrera aún no actualizada por el scraper: el PDF sigue en url_malla
        cls.antigua = Carrera.objects.create(nombre_carrera='Mecánica', institucion=inacap,
                                             url_malla='https://repo.inacapmovil.cl/pdf_mallas/m.pdf')
        cls.duoc = Carrera.objects.create(nombre_carrera='Turismo', url_malla='https://malla.duoc.cl/mallas/t.html')

    def test_detalle_con_malla_diurna_y_vespertina(self):
        datos = self.client.get(reverse('api_carrera_detalle', args=[self.informatica.id])).json()
        self.assertEqual([m['etiqueta'] for m in datos['mallas_digitales']], ['Malla diurna', 'Malla vespertina'])
        self.assertEqual(datos['malla_pdf_url'], f'/api/v1/carreras/{self.informatica.id}/malla.pdf')
        self.assertEqual(datos['url_carrera'], 'https://portal.inacap.cl/carreras/area-ti/ingenieria-en-informatica')

    def test_sin_copia_en_s3_descarga_el_pdf_publicado(self):
        respuesta = self.client.get(reverse('api_carrera_malla_pdf', args=[self.informatica.id]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].endswith('IEI-IEI-1.pdf'))

    def test_carrera_antigua_y_duoc(self):
        antigua = self.client.get(reverse('api_carrera_detalle', args=[self.antigua.id])).json()
        self.assertEqual(antigua['mallas_digitales'], [])  # un PDF no es malla digital
        self.assertIsNotNone(antigua['malla_pdf_url'])
        duoc = self.client.get(reverse('api_carrera_detalle', args=[self.duoc.id])).json()
        self.assertEqual(duoc['mallas_digitales'], [{'etiqueta': 'Malla digital', 'url': 'https://malla.duoc.cl/mallas/t.html'}])
