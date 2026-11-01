from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from scrapy.http import HtmlResponse, Request

from scraper.duoc.carga import cargar_items, obtener_institucion
from scraper.duoc.spider import DuocSpider, extraer_jornadas, limpiar_dinero, normalizar_nombre_sede, normalizar_region
from scraper.models import Carrera, Institucion, OfertaAcademica, Sede

HTML_CARRERA = """
<html><body>
<h1>Analista Programador</h1>
<h2><b>DURACIÓN</b></h2>
<div><div><ul><li class="info-descripcion">5 semestres</li></ul></div></div>
<section class="dma-sa" id="sedes-y-aranceles">
  <div class="dma-sa__grupo">
    <h3 class="dma-sa__grupo-titulo">Sedes región Metropolitana</h3>
    <ul class="dma-sa__track">
      <li class="dma-sa__card">
        <h4 class="dma-sa__sede">Maipú</h4>
        <p class="dma-sa__jornada">Jornada y Modalidad: Diurna y vespertina</p>
        <div class="dma-sa__valores">
          <p>Matrícula semestral: $138.000</p>
          <p>Arancel mensual: $322.000</p>
        </div>
      </li>
    </ul>
  </div>
</section>
</body></html>
"""

HTML_SEDE = """
<html><body>
<h3 class="font-weight-bold">Campus Villarrica</h3>
<b>Dirección:</b> Anfión Muñoz 51, Villarrica. <b>Teléfono:</b> 123
</body></html>
"""


def respuesta(url, html):
    return HtmlResponse(url=url, body=html.encode('utf-8'), encoding='utf-8', request=Request(url))


class TransformacionTests(SimpleTestCase):
    def test_limpiar_dinero(self):
        self.assertEqual(limpiar_dinero('$322.000'), 322000)
        self.assertIsNone(limpiar_dinero(''))

    def test_extraer_jornadas(self):
        self.assertEqual(extraer_jornadas('Jornada y Modalidad: Diurna y vespertina'), ['Diurna', 'Vespertina'])
        self.assertEqual(extraer_jornadas('Jornada y Modalidad: 100% online'), ['Online'])

    def test_normalizar_nombre_sede(self):
        self.assertEqual(normalizar_nombre_sede('Sede Maipú'), 'Maipú')
        self.assertEqual(normalizar_nombre_sede('Campus Villarrica'), 'Villarrica')

    def test_normalizar_region(self):
        self.assertEqual(normalizar_region('Sedes región Metropolitana'), 'Región metropolitana')
        self.assertEqual(normalizar_region('Sedes en regiones'), 'Regiones')
        self.assertEqual(normalizar_region('Duoc Online'), 'Online')


class DuocSpiderTests(SimpleTestCase):
    def test_parse_carrera(self):
        item = next(DuocSpider().parse_carrera(respuesta('https://www.duoc.cl/carreras/x/', HTML_CARRERA)))
        self.assertEqual(item['nombre'], 'Analista Programador')
        self.assertEqual(item['duracion_semestres'], 5)
        self.assertEqual(item['ofertas'], [{
            'sede': 'Maipú',
            'region': 'Región metropolitana',
            'jornadas': ['Diurna', 'Vespertina'],
            'matricula_clp': 138000,
            'arancel_mensual_clp': 322000,
        }])

    def test_parse_sede(self):
        item = next(DuocSpider().parse_sede(respuesta('https://www.duoc.cl/sedes/x/', HTML_SEDE)))
        self.assertEqual(item['nombre'], 'Villarrica')
        self.assertEqual(item['direccion'], 'Anfión Muñoz 51, Villarrica')


class CargaDuocTests(TestCase):
    def setUp(self):
        self.items = [
            {'tipo': 'sede', 'nombre': 'Maipú', 'direccion': 'Av. Esquina Blanca 501, Maipú'},
            {
                'tipo': 'carrera',
                'nombre': 'Analista Programador',
                'duracion_semestres': 5,
                'ofertas': [{
                    'sede': 'Maipú',
                    'region': 'Región metropolitana',
                    'jornadas': ['Diurna', 'Vespertina'],
                    'matricula_clp': 138000,
                    'arancel_mensual_clp': 322000,
                }],
            },
        ]

    def test_carga_es_idempotente(self):
        institucion = obtener_institucion()
        self.assertEqual(cargar_items(self.items, institucion), 2)
        cargar_items(self.items, institucion)
        self.assertEqual(OfertaAcademica.objects.count(), 2)

    def test_no_inventa_arancel_anual(self):
        cargar_items(self.items, obtener_institucion())
        oferta = OfertaAcademica.objects.first()
        self.assertEqual(oferta.arancel_mensual_clp, Decimal('322000'))
        self.assertIsNone(oferta.arancel_anual_clp)

    def test_calcula_anual_con_cuotas_indicadas(self):
        cargar_items(self.items, obtener_institucion(), cuotas_anuales=10)
        self.assertEqual(OfertaAcademica.objects.first().arancel_anual_clp, Decimal('3220000'))

    def test_no_mezcla_sedes_entre_instituciones(self):
        inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        sede_inacap = Sede.objects.create(nombre_sede='Maipú', institucion=inacap, direccion='Av. Americo Vespucio 974')
        cargar_items(self.items, obtener_institucion())
        sede_inacap.refresh_from_db()
        self.assertEqual(sede_inacap.direccion, 'Av. Americo Vespucio 974')
        self.assertEqual(Sede.objects.filter(nombre_sede='Maipú').count(), 2)
        self.assertEqual(Carrera.objects.get().institucion.codigo, 'DUOC')
