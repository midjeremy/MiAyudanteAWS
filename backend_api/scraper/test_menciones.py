"""Menciones de Duoc UC: extracción desde la página, carga en la base, API y asistente."""
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from scrapy.http import HtmlResponse, Request

from chatbot.services import buscar_carreras
from scraper.duoc.carga import cargar_items, guardar_menciones, obtener_institucion
from scraper.duoc.spider import (
    DuocSpider, extraer_menciones, limpiar_mencion, mencion_del_nombre, nombre_sin_mencion,
)
from scraper.models import Carrera, Mencion

# Estructura del acordeón de competencias de www.duoc.cl (noviembre de 2026)
HTML_GASTRONOMIA = """
<html><body>
<h1 class=" name">Gastronomía Internacional</h1>
<section class="dma-sa">
  <ul><li class="dma-sa__card">
    <h4 class="dma-sa__sede">Maipú</h4>
    <p class="dma-sa__jornada">Jornada y Modalidad: Diurna</p>
    <div class="dma-sa__valores"><p>Matrícula semestral: $150.000</p><p>Arancel mensual: $360.000</p></div>
  </li></ul>
</section>
<div class="card">
  <div class="card-header collapsed"><h4 class="mb-0">Competencias de la Carrera</h4></div>
  <div class="collapse"><ul><li>Elaborar productos gastronómicos.</li></ul></div>
</div>
<div class="card">
  <div class="card-header collapsed"><h4 class="mb-0">Competencias de la Mención: "Cocina de Alta Gama"</h4></div>
  <div class="collapse"><ul><li>Elaborar productos de alta gama.</li></ul></div>
</div>
<div class="card">
  <div class="card-header collapsed"><h4 class="mb-0">Competencias de la Mención: "Alta Pastelería y Repostería"</h4></div>
  <div class="collapse"><ul><li>Elaborar pastelería de alta gama.</li><li>Presentar con fina técnica.</li></ul></div>
</div>
</body></html>
"""


def respuesta(html, url='https://www.duoc.cl/carreras/gastronomia-internacional-2/'):
    return HtmlResponse(url=url, body=html.encode('utf-8'), encoding='utf-8', request=Request(url))


class LimpiezaMencionTests(SimpleTestCase):
    def test_limpia_los_formatos_que_publica_duoc(self):
        self.assertEqual(limpiar_mencion('Competencias de la Mención: "Cocina de Alta Gama"'), 'Cocina de Alta Gama')
        self.assertEqual(limpiar_mencion('Competencias de la Mención: "Mención Finanzas"'), 'Finanzas')
        self.assertEqual(limpiar_mencion('Mención Administración Hotelera'), 'Administración Hotelera')
        self.assertEqual(limpiar_mencion('  Competencias de la Mención:  “Gestión de Personas” '), 'Gestión de Personas')

    def test_nombre_sin_mencion_y_mencion_del_nombre(self):
        nombre = 'Ingeniería en Administración Mención Finanzas'
        self.assertEqual(nombre_sin_mencion(nombre), 'Ingeniería en Administración')
        self.assertEqual(mencion_del_nombre(nombre), 'Finanzas')
        self.assertEqual(nombre_sin_mencion('Analista Programador'), 'Analista Programador')
        self.assertEqual(mencion_del_nombre('Analista Programador'), '')


class ExtraerMencionesTests(SimpleTestCase):
    def test_una_carrera_con_dos_menciones_y_sus_competencias(self):
        self.assertEqual(extraer_menciones(respuesta(HTML_GASTRONOMIA), 'Gastronomía Internacional'), [
            {'nombre': 'Cocina de Alta Gama', 'competencias': ['Elaborar productos de alta gama.']},
            {'nombre': 'Alta Pastelería y Repostería',
             'competencias': ['Elaborar pastelería de alta gama.', 'Presentar con fina técnica.']},
        ])

    def test_sin_tarjeta_usa_la_mencion_del_nombre(self):
        html = '<html><body><h1>Contabilidad General Mención Legislación Tributaria</h1></body></html>'
        self.assertEqual(extraer_menciones(respuesta(html), 'Contabilidad General Mención Legislación Tributaria'),
                         [{'nombre': 'Legislación Tributaria', 'competencias': []}])

    def test_carrera_sin_mencion(self):
        html = HTML_GASTRONOMIA.split('<div class="card">')[0] + '</body></html>'
        self.assertEqual(extraer_menciones(respuesta(html), 'Analista Programador'), [])

    def test_el_spider_entrega_las_menciones_en_el_item(self):
        item = next(DuocSpider().parse_carrera(respuesta(HTML_GASTRONOMIA)))
        self.assertEqual([m['nombre'] for m in item['menciones']], ['Cocina de Alta Gama', 'Alta Pastelería y Repostería'])


def item_carrera(nombre, menciones, sede='Maipú', url='https://www.duoc.cl/carreras/x/'):
    item = {
        'tipo': 'carrera', 'url': url, 'nombre': nombre, 'duraciones': ['8 semestres'], 'url_malla': None,
        'ofertas': [{'sede': sede, 'jornadas': ['Diurna'], 'matricula_clp': 150000, 'arancel_mensual_clp': 360000}],
    }
    if menciones is not None:
        item['menciones'] = menciones
    return item


class CargaMencionesTests(TestCase):
    def test_guarda_menciones_y_nombre_base(self):
        cargar_items([item_carrera('Ingeniería en Administración Mención Finanzas',
                                   [{'nombre': 'Finanzas', 'competencias': ['Gestionar', 'Evaluar']}])],
                     obtener_institucion())
        carrera = Carrera.objects.get()
        self.assertEqual(carrera.nombre_base, 'Ingeniería en Administración')
        mencion = carrera.menciones.get()
        self.assertEqual((mencion.nombre, mencion.competencias), ('Finanzas', 'Gestionar\nEvaluar'))

    def test_quita_las_menciones_que_ya_no_se_publican(self):
        duoc = obtener_institucion()
        cargar_items([item_carrera('Gastronomía Internacional', [{'nombre': 'A'}, {'nombre': 'B'}])], duoc)
        cargar_items([item_carrera('Gastronomía Internacional', [{'nombre': 'B'}])], duoc)
        self.assertEqual(list(Mencion.objects.values_list('nombre', flat=True)), ['B'])

    def test_lote_antiguo_sin_menciones_no_borra_las_guardadas(self):
        duoc = obtener_institucion()
        cargar_items([item_carrera('Gastronomía Internacional', [{'nombre': 'A'}])], duoc)
        cargar_items([item_carrera('Gastronomía Internacional', None)], duoc)
        self.assertEqual(Mencion.objects.count(), 1)

    def test_ignora_nombres_vacios_y_repetidos(self):
        carrera = Carrera.objects.create(nombre_carrera='X', institucion=obtener_institucion())
        guardar_menciones(carrera, [{'nombre': ' '}, {'nombre': 'A'}, {'nombre': 'A'}])
        self.assertEqual(list(carrera.menciones.values_list('nombre', flat=True)), ['A'])


class ApiMencionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cargar_items([
            item_carrera('Gastronomía Internacional',
                         [{'nombre': 'Cocina de Alta Gama', 'competencias': ['Elaborar']},
                          {'nombre': 'Alta Pastelería y Repostería', 'competencias': []}],
                         url='https://www.duoc.cl/carreras/g/'),
            item_carrera('Analista Programador', [], url='https://www.duoc.cl/carreras/a/'),
        ], obtener_institucion())
        cls.gastronomia = Carrera.objects.get(nombre_carrera='Gastronomía Internacional')

    def test_detalle_de_carrera_incluye_menciones(self):
        datos = APIClient().get(f'/api/v1/carreras/{self.gastronomia.id}/').json()
        self.assertEqual(datos['nombre_base'], 'Gastronomía Internacional')
        self.assertEqual(datos['menciones'], [
            {'nombre': 'Alta Pastelería y Repostería', 'competencias': []},
            {'nombre': 'Cocina de Alta Gama', 'competencias': ['Elaborar']},
        ])

    def test_listado_de_carreras_y_ofertas_incluye_menciones(self):
        carreras = {c['carrera']: c for c in APIClient().get('/api/v1/carreras/').json()['results']}
        self.assertEqual(carreras['Analista Programador']['menciones'], [])
        self.assertEqual(len(carreras['Gastronomía Internacional']['menciones']), 2)
        ofertas = APIClient().get('/api/v1/ofertas/', {'q': 'Gastronomía'}).json()['results']
        self.assertEqual(ofertas[0]['menciones'], ['Alta Pastelería y Repostería', 'Cocina de Alta Gama'])

    def test_el_listado_no_hace_una_consulta_por_carrera(self):
        with self.assertNumQueries(5):
            APIClient().get('/api/v1/carreras/')

    def test_el_asistente_recibe_las_menciones(self):
        resultado = buscar_carreras(terminos=['gastronom'])
        self.assertEqual(resultado['carreras'][0]['menciones'],
                         ['Alta Pastelería y Repostería', 'Cocina de Alta Gama'])
