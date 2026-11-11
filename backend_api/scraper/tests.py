from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from scrapy.http import HtmlResponse, Request

from scraper.catalogos import (
    NIVEL_PROFESIONAL, NIVEL_TECNICO, clasificar_nivel, elegir_duracion, normalizar_jornada, parsear_duraciones,
    region_de_sede, semestres_publicados,
)
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
        # Solo en bimestres: se usa la duración en meses
        self.assertEqual(clasificar_nivel('Desarrollo de Aplicaciones', None, 20), NIVEL_TECNICO)
        self.assertEqual(clasificar_nivel('Auditoría y Análisis de Negocios', None, 36), NIVEL_PROFESIONAL)

    def test_parsear_duraciones_publicadas_por_duoc(self):
        # Textos reales de las páginas de carreras de Duoc UC
        casos = {
            '18 bimestres': (18, 'bimestre', 36, None, '18 bimestres'),
            '8 semestres (Presencial)': (8, 'semestre', 48, 'Presencial', '8 semestres'),
            '16 bimestres (Online)': (16, 'bimestre', 32, 'Online', '16 bimestres'),
            '18 bimestres (Carrera online)': (18, 'bimestre', 36, 'Online', '18 bimestres'),
            '100% Online de 18 bimestres': (18, 'bimestre', 36, 'Online', '18 bimestres'),
            '9 bimestres (Online)': (9, 'bimestre', 18, 'Online', '9 bimestres'),
        }
        for texto, esperado in casos.items():
            d = parsear_duraciones([texto])[0]
            self.assertEqual((d['valor'], d['unidad'], d['meses'], d['modalidad'], d['resumen']), esperado, texto)
        self.assertEqual(parsear_duraciones(['Consultar', '']), [])

    def test_elegir_duracion_por_modalidad(self):
        duraciones = parsear_duraciones(['8 semestres', '100% Online de 18 bimestres'])
        self.assertEqual(elegir_duracion(duraciones, 'Presencial')['resumen'], '8 semestres')
        self.assertEqual(elegir_duracion(duraciones, 'Online')['resumen'], '18 bimestres')
        self.assertEqual(semestres_publicados(duraciones), 8)
        self.assertIsNone(semestres_publicados(parsear_duraciones(['18 bimestres'])))

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
        self.assertEqual(item['duraciones'], ['5 semestres'])
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
                'duraciones': ['5 semestres'],
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

    def test_sin_cuotas_no_inventa_semestral_ni_anual(self):
        cargar_items(self.items, obtener_institucion(), cuotas_por_semestre=0)
        oferta = OfertaAcademica.objects.first()
        self.assertEqual(oferta.arancel_mensual_clp, Decimal('322000'))
        self.assertIsNone(oferta.arancel_semestral_clp)
        self.assertIsNone(oferta.arancel_anual_clp)
        self.assertFalse(oferta.aranceles_calculados)

    def test_calcula_semestral_y_anual_con_cinco_cuotas(self):
        # Resolución Duoc: arancel semestral en 5 cuotas mensuales; la matrícula publicada es semestral
        cargar_items(self.items, obtener_institucion())
        oferta = OfertaAcademica.objects.first()
        self.assertEqual(oferta.arancel_mensual_clp, Decimal('322000'))
        self.assertEqual(oferta.arancel_semestral_clp, Decimal('1610000'))
        self.assertEqual(oferta.arancel_anual_clp, Decimal('3220000'))
        self.assertTrue(oferta.aranceles_calculados)
        self.assertEqual(oferta.matricula_periodo, 'semestral')

    def test_lote_antiguo_con_duracion_semestres_sigue_cargando(self):
        item = self.items[1]
        item.pop('duraciones')
        item['duracion_semestres'] = 5
        cargar_items(self.items, obtener_institucion())
        self.assertEqual(Carrera.objects.get().duracion_semestres, 5)
        self.assertEqual(OfertaAcademica.objects.first().duracion_meses, 30)

    def test_carrera_solo_online_en_bimestres(self):
        self.items[1].update(nombre='Desarrollo de Aplicaciones', duraciones=['10 bimestres'])
        self.items[1]['ofertas'][0].update(sede='Duoc Online', jornadas=['100% online'])
        cargar_items(self.items, obtener_institucion())
        carrera = Carrera.objects.get()
        self.assertIsNone(carrera.duracion_semestres)  # antes quedaba como 10 semestres (5 años)
        self.assertEqual(carrera.duracion_texto, '10 bimestres')
        self.assertEqual(carrera.nivel_formacion, NIVEL_TECNICO)  # 20 meses
        oferta = OfertaAcademica.objects.get()
        self.assertEqual((oferta.duracion_texto, oferta.duracion_meses), ('10 bimestres', 20))

    def test_carrera_mixta_usa_la_duracion_de_cada_modalidad(self):
        self.items[1].update(nombre='Ingeniería en Marketing Digital',
                             duraciones=['8 semestres (Presencial)', '16 bimestres (Online)'])
        self.items[1]['ofertas'].append({'sede': 'Duoc Online', 'jornadas': ['100% online'],
                                         'matricula_clp': 138000, 'arancel_mensual_clp': 280000})
        cargar_items(self.items, obtener_institucion())
        self.assertEqual(Carrera.objects.get().duracion_semestres, 8)
        por_modalidad = {o.jornada.modalidad: (o.duracion_texto, o.duracion_meses) for o in OfertaAcademica.objects.all()}
        self.assertEqual(por_modalidad['Presencial'], ('8 semestres', 48))
        self.assertEqual(por_modalidad['Online'], ('16 bimestres', 32))

    def test_no_mezcla_sedes_entre_instituciones(self):
        inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        sede_inacap = Sede.objects.create(nombre_sede='Maipú', institucion=inacap, direccion='Av. Americo Vespucio 974')
        cargar_items(self.items, obtener_institucion())
        sede_inacap.refresh_from_db()
        self.assertEqual(sede_inacap.direccion, 'Av. Americo Vespucio 974')
        self.assertEqual(Sede.objects.filter(nombre_sede='Maipú').count(), 2)
        self.assertEqual(Carrera.objects.get().institucion.codigo, 'DUOC')
