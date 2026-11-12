from io import StringIO
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Pregunta, Resultado
from .preguntas import AREAS, DIMENSIONES, ESCALA, GENERAL, PREGUNTAS
from .utils import (
    RespuestasInvalidas,
    areas_ordenadas,
    calcular_resultado,
    normalizar_respuestas,
    porcentaje_likert,
)

PREGUNTAS_URL = '/api/v1/ikigai/preguntas/'
RESULTADO_URL = '/api/v1/ikigai/resultado/'
NUMEROS = set(range(1, 41))


def todas(valor):
    return {str(n): valor for n in range(1, 41)}


def preguntas_en_memoria():
    return [SimpleNamespace(numero=n, dimension=d, area=a) for n, d, a, _ in PREGUNTAS]


class ContenidoDelDocumentoTests(SimpleTestCase):
    """El contenido debe calzar con la matriz de validación por juicio de expertos."""

    def test_cuarenta_items_numerados_del_1_al_40(self):
        self.assertEqual([p[0] for p in PREGUNTAS], list(range(1, 41)))

    def test_diez_items_por_dimension_en_el_orden_del_documento(self):
        for indice, (clave, _, _) in enumerate(DIMENSIONES):
            numeros = [n for n, d, _, _ in PREGUNTAS if d == clave]
            self.assertEqual(numeros, list(range(indice * 10 + 1, indice * 10 + 11)))

    def test_cada_area_tiene_un_item_por_dimension_y_dos_generales(self):
        for clave, _, _ in AREAS:
            items = [(d, n) for n, d, a, _ in PREGUNTAS if a == clave]
            if clave == GENERAL:
                self.assertEqual([n for _, n in items], [9, 10, 19, 20, 29, 30, 39, 40])
            else:
                self.assertEqual(sorted(d for d, _ in items), sorted(c for c, _, _ in DIMENSIONES))

    def test_escala_likert_de_1_a_5(self):
        self.assertEqual([v for v, _ in ESCALA], [1, 2, 3, 4, 5])
        self.assertEqual(ESCALA[0][1], 'Muy en desacuerdo')
        self.assertEqual(ESCALA[2][1], 'Ni de acuerdo ni en desacuerdo')
        self.assertEqual(ESCALA[4][1], 'Muy de acuerdo')


class CalculoTests(SimpleTestCase):
    def test_porcentaje_va_de_0_a_100(self):
        self.assertEqual(porcentaje_likert([1, 1]), 0.0)
        self.assertEqual(porcentaje_likert([5, 5]), 100.0)
        self.assertEqual(porcentaje_likert([3]), 50.0)
        self.assertEqual(porcentaje_likert([4, 5]), 87.5)
        self.assertEqual(porcentaje_likert([]), 0.0)

    def test_resultado_por_dimension(self):
        # Pasión todo 5, Vocación todo 1, Profesión todo 3, Misión mitad 4 y mitad 2
        respuestas = {}
        for n in range(1, 11):
            respuestas[n] = 5
        for n in range(11, 21):
            respuestas[n] = 1
        for n in range(21, 31):
            respuestas[n] = 3
        for n in range(31, 41):
            respuestas[n] = 4 if n <= 35 else 2
        resultado = calcular_resultado(respuestas, preguntas_en_memoria())
        self.assertEqual(resultado['dimensiones'], {'pasion': 100.0, 'vocacion': 0.0, 'profesion': 50.0, 'mision': 50.0})

    def test_resultado_por_area_ignora_items_generales(self):
        respuestas = {n: 1 for n in NUMEROS}
        # Salud: ítems 2, 12, 22 y 32. Los generales en 5 no deben mover ningún área.
        for n in (2, 12, 22, 32, 9, 10, 19, 20, 29, 30, 39, 40):
            respuestas[n] = 5
        resultado = calcular_resultado(respuestas, preguntas_en_memoria())
        self.assertNotIn(GENERAL, resultado['areas'])
        self.assertEqual(resultado['areas']['salud'], 100.0)
        self.assertEqual(resultado['areas']['tecnologia'], 0.0)
        self.assertEqual(len(resultado['areas']), 8)

    def test_areas_ordenadas_de_mayor_a_menor_y_empate_en_orden_del_documento(self):
        orden = areas_ordenadas({'tecnologia': 50.0, 'salud': 75.0, 'economia': 50.0})
        self.assertEqual([a['clave'] for a in orden], ['salud', 'tecnologia', 'economia'])
        self.assertEqual(orden[0]['nombre'], 'Salud')

    def test_valida_que_esten_todas_las_respuestas(self):
        respuestas = todas(3)
        del respuestas['40']
        with self.assertRaisesMessage(RespuestasInvalidas, '40'):
            normalizar_respuestas(respuestas, NUMEROS)

    def test_rechaza_valores_fuera_de_la_escala(self):
        for valor in (0, 6, 2.5, True, 'cuatro', None):
            with self.subTest(valor=valor), self.assertRaises(RespuestasInvalidas):
                normalizar_respuestas({**todas(3), '1': valor}, NUMEROS)

    def test_rechaza_preguntas_que_no_existen(self):
        with self.assertRaises(RespuestasInvalidas):
            normalizar_respuestas({**todas(3), '41': 3}, NUMEROS)
        with self.assertRaises(RespuestasInvalidas):
            normalizar_respuestas([3] * 40, NUMEROS)

    def test_acepta_numeros_como_texto(self):
        self.assertEqual(normalizar_respuestas(todas('4'), NUMEROS)[1], 4)


class PreguntasApiTests(TestCase):
    def test_la_migracion_carga_las_40_preguntas(self):
        self.assertEqual(Pregunta.objects.count(), 40)
        self.assertEqual(
            Pregunta.objects.get(numero=1).enunciado,
            'Me entretiene aprender cómo funcionan los computadores, las aplicaciones o internet.',
        )
        self.assertEqual(Pregunta.objects.get(numero=40).dimension, 'mision')

    def test_comando_de_carga_es_idempotente(self):
        Pregunta.objects.filter(numero=5).update(enunciado='cambiado')
        call_command('cargar_preguntas_ikigai', stdout=StringIO())
        self.assertEqual(Pregunta.objects.count(), 40)
        self.assertTrue(Pregunta.objects.get(numero=5).enunciado.startswith('Disfruto crear cosas visuales'))

    def test_lista_preguntas_escala_y_dimensiones_sin_mostrar_el_area(self):
        respuesta = APIClient().get(PREGUNTAS_URL)
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(len(datos['preguntas']), 40)
        self.assertEqual([p['numero'] for p in datos['preguntas']], list(range(1, 41)))
        self.assertEqual(datos['escala'][0], {'valor': 1, 'etiqueta': 'Muy en desacuerdo'})
        self.assertEqual(len(datos['escala']), 5)
        self.assertEqual([d['clave'] for d in datos['dimensiones']], ['pasion', 'vocacion', 'profesion', 'mision'])
        self.assertNotIn('area', datos['preguntas'][0])


class ResultadoApiTests(TestCase):
    def setUp(self):
        self.cliente = APIClient()
        self.usuario = get_user_model().objects.create_user(
            username='ana@correo.cl', email='ana@correo.cl', password='Clave-Segura-2026'
        )

    def autenticar(self):
        token = RefreshToken.for_user(self.usuario).access_token
        self.cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_anonimo_recibe_resultado_sin_guardar(self):
        respuesta = self.cliente.post(RESULTADO_URL, {'respuestas': todas(5)}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertFalse(datos['guardado'])
        self.assertIsNone(datos['id'])
        self.assertEqual([d['porcentaje'] for d in datos['dimensiones']], [100.0] * 4)
        self.assertEqual(len(datos['areas']), 8)
        self.assertEqual(Resultado.objects.count(), 0)

    def test_usuario_con_jwt_guarda_su_resultado(self):
        self.autenticar()
        respuestas = todas(3)
        respuestas.update({'1': 5, '11': 5, '21': 5, '31': 5})  # todo Tecnología en 5
        respuesta = self.cliente.post(RESULTADO_URL, {'respuestas': respuestas}, format='json')
        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertTrue(datos['guardado'])
        self.assertEqual(datos['areas'][0]['clave'], 'tecnologia')
        self.assertEqual(datos['areas'][0]['porcentaje'], 100.0)

        resultado = Resultado.objects.get()
        self.assertEqual(resultado.usuario, self.usuario)
        self.assertEqual(float(resultado.puntaje_pasion), 55.0)  # nueve 3 y un 5
        self.assertEqual(resultado.respuestas['1'], 5)
        self.assertEqual(resultado.puntajes_area['tecnologia'], 100.0)

    def test_respuestas_incompletas_dan_400(self):
        respuestas = todas(4)
        del respuestas['17']
        respuesta = self.cliente.post(RESULTADO_URL, {'respuestas': respuestas}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('17', respuesta.json()['error'])

    def test_sin_respuestas_da_400(self):
        self.assertEqual(self.cliente.post(RESULTADO_URL, {}, format='json').status_code, 400)

    def test_ultimo_resultado_requiere_sesion(self):
        self.assertEqual(self.cliente.get(RESULTADO_URL).status_code, 401)

    def test_ultimo_resultado_del_usuario(self):
        self.autenticar()
        self.assertEqual(self.cliente.get(RESULTADO_URL).status_code, 404)
        self.cliente.post(RESULTADO_URL, {'respuestas': todas(2)}, format='json')
        self.cliente.post(RESULTADO_URL, {'respuestas': todas(4)}, format='json')
        respuesta = self.cliente.get(RESULTADO_URL)
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['guardado'])
        self.assertEqual([d['porcentaje'] for d in datos['dimensiones']], [75.0] * 4)
