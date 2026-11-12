from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede


class ApiCatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        duoc = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')
        diurna = Jornada.objects.create(tipo_jornada='Diurna', modalidad='Presencial')
        online = Jornada.objects.create(tipo_jornada='Online', modalidad='Online')
        maipu_inacap = Sede.objects.create(nombre_sede='Maipú', institucion=inacap, region='Región Metropolitana')
        maipu_duoc = Sede.objects.create(nombre_sede='Maipú', institucion=duoc, region='Región Metropolitana')
        san_joaquin = Sede.objects.create(nombre_sede='San Joaquín', institucion=duoc, region='Región Metropolitana')
        Sede.objects.create(nombre_sede='Sin ofertas', institucion=duoc)

        contador = Carrera.objects.create(nombre_carrera='Contador Público', institucion=inacap, duracion_semestres=8)
        diseno = Carrera.objects.create(nombre_carrera='Diseño Gráfico', institucion=duoc, duracion_semestres=8)
        cls.semestral = OfertaAcademica.objects.create(
            institucion=inacap, carrera=contador, sede=maipu_inacap, jornada=diurna,
            arancel_semestral_clp=Decimal('1628000'), arancel_anual_clp=Decimal('3256000'), matricula_clp=161000,
        )
        cls.mensual = OfertaAcademica.objects.create(
            institucion=duoc, carrera=diseno, sede=maipu_duoc, jornada=diurna,
            arancel_mensual_clp=Decimal('322000'), matricula_clp=138000,
        )
        cls.online = OfertaAcademica.objects.create(
            institucion=duoc, carrera=diseno, sede=san_joaquin, jornada=online,
            arancel_mensual_clp=Decimal('306000'), matricula_clp=138000,
        )

    def setUp(self):
        self.cliente = APIClient()

    def ids(self, url):
        respuesta = self.cliente.get(url)
        self.assertEqual(respuesta.status_code, 200)
        return [oferta['id'] for oferta in respuesta.data['results']]

    def test_lista_paginada_con_ids_reales(self):
        respuesta = self.cliente.get('/api/v1/ofertas/?page_size=2')
        self.assertEqual(respuesta.data['count'], 3)
        self.assertEqual(len(respuesta.data['results']), 2)
        self.assertIsNotNone(respuesta.data['next'])
        self.assertEqual(respuesta.data['results'][0]['id'], self.mensual.id)

    def test_filtros_basicos(self):
        self.assertEqual(self.ids('/api/v1/ofertas/?institucion=inacap'), [self.semestral.id])
        self.assertEqual(self.ids('/api/v1/ofertas/?modalidad=online'), [self.online.id])
        self.assertEqual(self.ids('/api/v1/ofertas/?q=contador'), [self.semestral.id])
        self.assertEqual(self.ids('/api/v1/ofertas/?carrera=diseño&modalidad=presencial'), [self.mensual.id])
        self.assertEqual(self.ids('/api/v1/ofertas/?excluir=diseño'), [self.semestral.id])

    def test_filtro_sede_por_clave_incluye_ambas_instituciones(self):
        self.assertEqual(sorted(self.ids('/api/v1/ofertas/?sede=maipu')), sorted([self.semestral.id, self.mensual.id]))
        self.assertEqual(self.ids('/api/v1/ofertas/?sede=san_joaquin'), [self.online.id])

    def test_ids_para_comparar_y_guardados(self):
        url = f'/api/v1/ofertas/?ids={self.online.id},{self.semestral.id},abc'
        self.assertEqual(sorted(self.ids(url)), sorted([self.online.id, self.semestral.id]))

    def test_arancel_referencia_respeta_periodo_publicado(self):
        detalle = self.cliente.get(f'/api/v1/ofertas/{self.mensual.id}/').data
        self.assertEqual(detalle['arancel_referencia'], {'monto': 322000, 'periodo': 'mensual', 'calculado': False})
        self.assertIsNone(detalle['valor_anual'])
        anual = self.cliente.get(f'/api/v1/ofertas/{self.semestral.id}/').data
        self.assertEqual(anual['arancel_referencia'], {'monto': 3256000, 'periodo': 'anual', 'calculado': False})

    def test_detalle_inexistente(self):
        self.assertEqual(self.cliente.get('/api/v1/ofertas/999999/').status_code, 404)

    def test_filtros_solo_con_ofertas(self):
        datos = self.cliente.get('/api/v1/filtros/').data
        self.assertEqual([s['clave'] for s in datos['sedes']], ['maipu', 'san_joaquin'])
        self.assertEqual([i['clave'] for i in datos['instituciones']], ['duoc', 'inacap'])
        self.assertEqual(datos['modalidades'], ['Online', 'Presencial'])

    def test_catalogo_antiguo_sigue_disponible(self):
        self.assertEqual(len(self.cliente.get('/api/v1/catalogo/').json()), 3)
