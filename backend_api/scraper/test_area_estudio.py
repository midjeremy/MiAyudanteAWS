"""Área de estudio: se toma de la agrupación que publica cada institución y se traduce a las áreas del test."""
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from scraper.catalogos import AREAS_ESTUDIO, AREAS_INACAP, ESCUELAS_DUOC, area_duoc, area_inacap, clasificar_area
from scraper.duoc.carga import areas_por_carrera, cargar_items, obtener_institucion
from scraper.duoc.spider import DuocSpider, ruta_carrera
from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede
from scraper.tests import HTML_CARRERA, respuesta
from Test_Ikigai.preguntas import AREAS, GENERAL

HTML_ESCUELA = """
<html><body>
<h1>Escuela de Informática y Telecomunicaciones</h1>
<a href="https://www.duoc.cl/carreras/ingenieria-en-informatica/">Ingeniería en Informática</a>
<a href="/carreras/analista-programador/">Analista Programador</a>
<a href="/carreras/analista-programador/#sedes">Ver sedes</a>
<a href="/escuela/diseno/">Otra escuela</a>
</body></html>
"""


class CatalogoAreasTests(SimpleTestCase):
    def test_areas_son_las_del_test_ikigai(self):
        self.assertEqual(set(AREAS_ESTUDIO), {clave for clave, _, _ in AREAS if clave != GENERAL})

    def test_todas_las_agrupaciones_apuntan_a_un_area_valida(self):
        for _, clave in [*AREAS_INACAP.values(), *ESCUELAS_DUOC.values()]:
            self.assertIn(clave, AREAS_ESTUDIO)

    def test_area_inacap_desde_la_url(self):
        url = 'https://portal.inacap.cl/carreras/area-informatica-ciberseguridad-y-telecomunicaciones/analista-programador'
        self.assertEqual(area_inacap(url), ('Informática, Ciberseguridad y Telecomunicaciones', 'tecnologia'))
        self.assertEqual(area_inacap('https://portal.inacap.cl/carreras/area-nueva-x/carrera'), ('Nueva x', ''))
        self.assertEqual(area_inacap('https://portal.inacap.cl/carreras/sin-area'), ('', ''))

    def test_area_duoc_desde_la_escuela(self):
        self.assertEqual(area_duoc('https://www.duoc.cl/escuela/salud/', 'Escuela de Salud y Bienestar'),
                         ('Salud y Bienestar', 'salud'))
        self.assertEqual(area_duoc('https://www.duoc.cl/escuela/nueva/', 'Escuela de Música'), ('Música', ''))

    def test_la_agrupacion_institucional_manda(self):
        self.assertEqual(clasificar_area('Desarrollo y Diseño Web', 'arte'), 'arte')
        self.assertEqual(clasificar_area('Ingeniería en Minas', 'industria'), 'industria')

    def test_el_nombre_corrige_educacion_naturaleza_y_electricidad(self):
        self.assertEqual(clasificar_area('Técnico en Trabajo Social', 'arte'), 'educacion')
        self.assertEqual(clasificar_area('Ingeniería en Recursos Naturales y Sostenibilidad', 'industria'), 'naturaleza')
        self.assertEqual(clasificar_area('Ingeniería en Prevención de Riesgos y Medio Ambiente', 'industria'), 'industria')
        self.assertEqual(clasificar_area('Técnico en Electricidad Industrial', 'tecnologia'), 'industria')

    def test_sin_agrupacion_se_usa_el_nombre(self):
        self.assertEqual(clasificar_area('Técnico en Enfermería'), 'salud')
        self.assertEqual(clasificar_area('Analista Programador'), 'tecnologia')
        self.assertEqual(clasificar_area('Contador Público'), 'economia')
        self.assertEqual(clasificar_area('Gastronomía Internacional'), 'turismo')
        self.assertEqual(clasificar_area('Carrera Desconocida'), '')


class SpiderEscuelaTests(SimpleTestCase):
    def test_parse_escuela_lista_sus_carreras(self):
        url = 'https://www.duoc.cl/escuela/informatica-telecomunicaciones/'
        item = next(DuocSpider().parse_escuela(respuesta(url, HTML_ESCUELA)))
        self.assertEqual(item['tipo'], 'escuela')
        self.assertEqual(item['nombre'], 'Escuela de Informática y Telecomunicaciones')
        self.assertEqual(item['carreras'], ['/carreras/analista-programador', '/carreras/ingenieria-en-informatica'])

    def test_la_carrera_sigue_los_enlaces_a_escuelas(self):
        html = HTML_CARRERA.replace('<h1>', '<a href="/escuela/salud/">Salud</a><a href="/escuela/">Todas</a><h1>')
        resultados = list(DuocSpider().parse_carrera(respuesta('https://www.duoc.cl/carreras/x/', html)))
        escuelas = [r.url for r in resultados if getattr(getattr(r, 'callback', None), '__name__', '') == 'parse_escuela']
        self.assertEqual(escuelas, ['https://www.duoc.cl/escuela/salud/'])

    def test_ruta_carrera_ignora_dominio_y_barra(self):
        self.assertEqual(ruta_carrera('https://www.duoc.cl/carreras/X/'), '/carreras/x')


class CargaAreaDuocTests(TestCase):
    def items(self, con_escuela=True):
        carrera = {
            'tipo': 'carrera', 'url': 'https://www.duoc.cl/carreras/analista-programador/',
            'nombre': 'Analista Programador', 'duraciones': ['5 semestres'], 'url_malla': None,
            'ofertas': [{'sede': 'Maipú', 'jornadas': ['Diurna'], 'matricula_clp': 138000, 'arancel_mensual_clp': 322000}],
        }
        escuela = {'tipo': 'escuela', 'url': 'https://www.duoc.cl/escuela/informatica-telecomunicaciones/',
                   'nombre': 'Escuela de Informática y Telecomunicaciones', 'carreras': ['/carreras/analista-programador']}
        return [escuela, carrera] if con_escuela else [carrera]

    def test_areas_por_carrera(self):
        self.assertEqual(areas_por_carrera(self.items()),
                         {'/carreras/analista-programador': ('Informática y Telecomunicaciones', 'tecnologia')})

    def test_la_carga_guarda_escuela_y_area(self):
        cargar_items(self.items(), obtener_institucion())
        carrera = Carrera.objects.get()
        self.assertEqual(carrera.area_institucion, 'Informática y Telecomunicaciones')
        self.assertEqual(carrera.area_estudio, 'tecnologia')

    def test_sin_pagina_de_escuela_clasifica_por_nombre(self):
        cargar_items(self.items(con_escuela=False), obtener_institucion())
        carrera = Carrera.objects.get()
        self.assertEqual(carrera.area_institucion, '')
        self.assertEqual(carrera.area_estudio, 'tecnologia')


class ApiAreaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        duoc = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')
        jornada = Jornada.objects.create(tipo_jornada='Diurna', modalidad='Presencial')
        sede = Sede.objects.create(nombre_sede='Maipú', institucion=duoc)
        for nombre, area, escuela in [('Analista Programador', 'tecnologia', 'Informática y Telecomunicaciones'),
                                      ('Técnico en Enfermería', 'salud', 'Salud y Bienestar'),
                                      ('Gastronomía', 'turismo', 'Gastronomía')]:
            carrera = Carrera.objects.create(nombre_carrera=nombre, institucion=duoc, area_estudio=area,
                                             area_institucion=escuela)
            OfertaAcademica.objects.create(institucion=duoc, carrera=carrera, sede=sede, jornada=jornada)

    def setUp(self):
        self.cliente = APIClient()

    def test_filtra_ofertas_por_area(self):
        datos = self.cliente.get('/api/v1/ofertas/', {'area': 'salud'}).json()
        self.assertEqual([o['carrera'] for o in datos['results']], ['Técnico en Enfermería'])
        self.assertEqual(datos['results'][0]['area_estudio_nombre'], 'Salud')
        self.assertEqual(datos['results'][0]['area_institucion'], 'Salud y Bienestar')

    def test_filtra_carreras_por_varias_areas(self):
        datos = self.cliente.get('/api/v1/carreras/', {'area': 'tecnologia,turismo'}).json()
        self.assertEqual(sorted(c['carrera'] for c in datos['results']), ['Analista Programador', 'Gastronomía'])
        self.assertEqual({c['area_estudio'] for c in datos['results']}, {'tecnologia', 'turismo'})

    def test_filtros_lista_las_areas_con_ofertas(self):
        areas = self.cliente.get('/api/v1/filtros/').json()['areas']
        self.assertEqual([a['clave'] for a in areas], ['tecnologia', 'salud', 'turismo'])
        self.assertEqual(areas[0]['nombre'], 'Tecnología')
