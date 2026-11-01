from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from scrapy.http import HtmlResponse, Request

from scraper.catalogos import NIVEL_PROFESIONAL, NIVEL_TECNICO, clasificar_nivel, normalizar_jornada, region_de_sede
from scraper.duoc.carga import cargar_items, obtener_institucion, validar_items
from scraper.duoc.spider import DuocSpider, extraer_jornadas, limpiar_dinero, normalizar_nombre_sede
from scraper.etl import retirar_ofertas_obsoletas, tasa_exito
from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede

HTML_CARRERA = """
<html><body>
<h1>Analista Programador</h1>
<h2><b>DURACIÓN</b></h2>
<div><div><ul><li class="info-descripcion">5 semestres</li></ul></div></div>
<div class="dmc-root" data-dmc-src="https://malla.duoc.cl/mallas/x/047.html"></div>
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
        self.assertEqual(extraer_jornadas('Jornada y Modalidad: Diurna y vespertina'), ['Diurna', 'vespertina'])
        self.assertEqual(extraer_jornadas('Jornada y Modalidad: 100% online'), ['100% online'])

    def test_normalizar_nombre_sede(self):
        self.assertEqual(normalizar_nombre_sede('Sede Maipú'), 'Maipú')
        self.assertEqual(normalizar_nombre_sede('Campus Villarrica'), 'Villarrica')


class CatalogosTests(SimpleTestCase):
    def test_region_de_sede_unifica_instituciones(self):
        self.assertEqual(region_de_sede('San Pedro De La Paz'), 'Región del Biobío')
        self.assertEqual(region_de_sede('Maipú'), 'Región Metropolitana')
        self.assertEqual(region_de_sede('Duoc Online'), 'Online')
        self.assertIsNone(region_de_sede('Sede desconocida'))

    def test_normalizar_jornada(self):
        self.assertEqual(normalizar_jornada('vespertina'), ('Vespertina', 'Presencial'))
        self.assertEqual(normalizar_jornada('100% online', 'Duoc Online'), ('Online', 'Online'))
        self.assertEqual(normalizar_jornada('', 'Campus Digital'), ('Online', 'Online'))

    def test_horario_vacio_no_se_inventa(self):
        self.assertEqual(normalizar_jornada('', 'Maipú'), ('No informada', None))

    def test_clasificar_nivel(self):
        self.assertEqual(clasificar_nivel('Técnico en Logística', 4), NIVEL_TECNICO)
        self.assertEqual(clasificar_nivel('Ingeniería Industrial Online', 4), NIVEL_PROFESIONAL)
        self.assertEqual(clasificar_nivel('Analista Programador', 5), NIVEL_TECNICO)
        self.assertEqual(clasificar_nivel('Diseño Gráfico', 8), NIVEL_PROFESIONAL)
        self.assertIsNone(clasificar_nivel('Diseño Gráfico', None))

    def test_tasa_exito(self):
        self.assertEqual(tasa_exito(76, 80), 95)
        self.assertEqual(tasa_exito(0, 0), 0)


class DuocSpiderTests(SimpleTestCase):
    def test_parse_carrera(self):
        solicitud = next(DuocSpider().parse_carrera(respuesta('https://www.duoc.cl/carreras/x/', HTML_CARRERA)))
        item = solicitud.cb_kwargs['item']
        self.assertEqual(solicitud.url, 'https://malla.duoc.cl/mallas/x/047.html')
        self.assertTrue(solicitud.dont_filter)
        self.assertEqual(item['nombre'], 'Analista Programador')
        self.assertEqual(item['duracion_semestres'], 5)
        self.assertEqual(item['url_malla'], 'https://malla.duoc.cl/mallas/x/047.html')
        self.assertEqual(item['ofertas'], [{
            'sede': 'Maipú',
            'jornadas': ['Diurna', 'vespertina'],
            'matricula_clp': 138000,
            'arancel_mensual_clp': 322000,
        }])

    def test_sin_malla_entrega_la_carrera(self):
        html = HTML_CARRERA.replace('data-dmc-src="https://malla.duoc.cl/mallas/x/047.html"', '')
        item = next(DuocSpider().parse_carrera(respuesta('https://www.duoc.cl/carreras/x/', html)))
        self.assertIsNone(item['url_malla'])

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
                'url': 'https://www.duoc.cl/carreras/x/',
                'nombre': 'Analista Programador',
                'duracion_semestres': 5,
                'url_malla': 'https://malla.duoc.cl/mallas/x/047.html',
                'ofertas': [{
                    'sede': 'Maipú',
                    'jornadas': ['Diurna', 'vespertina'],
                    'matricula_clp': 138000,
                    'arancel_mensual_clp': 322000,
                }],
            },
        ]

    def test_carga_es_idempotente(self):
        institucion = obtener_institucion()
        self.assertEqual(len(cargar_items(self.items, institucion)), 2)
        cargar_items(self.items, institucion)
        self.assertEqual(OfertaAcademica.objects.count(), 2)

    def test_normaliza_datos_al_cargar(self):
        cargar_items(self.items, obtener_institucion())
        sede = Sede.objects.get()
        carrera = Carrera.objects.get()
        self.assertEqual(sede.region, 'Región Metropolitana')
        self.assertEqual(carrera.nivel_formacion, NIVEL_TECNICO)
        self.assertEqual(carrera.url_malla, 'https://malla.duoc.cl/mallas/x/047.html')
        self.assertEqual(sorted(Jornada.objects.values_list('tipo_jornada', 'modalidad')), [('Diurna', 'Presencial'), ('Vespertina', 'Presencial')])

    def test_rechaza_carrera_incompleta(self):
        self.items[1]['ofertas'][0]['arancel_mensual_clp'] = None
        validas, errores = validar_items(self.items)
        self.assertEqual(validas, [])
        self.assertEqual(errores, ['Oferta incompleta: Analista Programador'])
        self.assertEqual(cargar_items(self.items, obtener_institucion()), [])

    def test_retira_solo_ofertas_obsoletas_de_la_institucion(self):
        duoc = obtener_institucion()
        vigentes = cargar_items(self.items, duoc)
        inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        OfertaAcademica.objects.create(
            institucion=inacap,
            carrera=Carrera.objects.create(nombre_carrera='Otra', institucion=inacap),
            sede=Sede.objects.create(nombre_sede='Renca', institucion=inacap),
            jornada=Jornada.objects.first(),
        )
        self.assertEqual(retirar_ofertas_obsoletas(duoc, vigentes[:1]), 1)
        self.assertEqual(OfertaAcademica.objects.filter(institucion=duoc).count(), 1)
        self.assertEqual(OfertaAcademica.objects.filter(institucion=inacap).count(), 1)

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
