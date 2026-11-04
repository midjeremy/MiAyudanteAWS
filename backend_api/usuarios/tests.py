from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

REGISTRO = '/api/v1/auth/registro/'
LOGIN = '/api/v1/auth/login/'
PERFIL = '/api/v1/auth/perfil/'
DATOS = {'correo': 'Ana@Correo.cl', 'nombre': 'Ana', 'apellidos': 'Pérez', 'password': 'Clave-Segura-2026'}


class AutenticacionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = APIClient()

    def registrar(self, **cambios):
        return self.cliente.post(REGISTRO, {**DATOS, **cambios}, format='json')

    def test_registro_crea_cuenta_con_clave_cifrada(self):
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data['usuario'], {'correo': 'ana@correo.cl', 'nombre': 'Ana Pérez'})
        usuario = get_user_model().objects.get(username='ana@correo.cl')
        self.assertNotEqual(usuario.password, DATOS['password'])
        self.assertTrue(usuario.check_password(DATOS['password']))

    def test_registro_rechaza_correo_repetido(self):
        self.registrar()
        self.assertEqual(self.registrar(correo='ana@correo.cl').status_code, 409)

    def test_registro_rechaza_datos_invalidos(self):
        self.assertEqual(self.registrar(nombre='').status_code, 400)
        self.assertEqual(self.registrar(correo='no-es-correo').status_code, 400)
        self.assertEqual(self.registrar(password='123456').status_code, 400)

    def test_login_entrega_tokens_y_permite_ver_perfil(self):
        self.registrar()
        respuesta = self.cliente.post(LOGIN, {'correo': 'ANA@correo.cl', 'password': DATOS['password']}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('refresh', respuesta.data)
        self.cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        perfil = self.cliente.get(PERFIL)
        self.assertEqual(perfil.status_code, 200)
        self.assertEqual(perfil.data['usuario']['correo'], 'ana@correo.cl')

    def test_login_rechaza_clave_incorrecta(self):
        self.registrar()
        respuesta = self.cliente.post(LOGIN, {'correo': DATOS['correo'], 'password': 'otra'}, format='json')
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn('access', respuesta.data)

    def test_perfil_exige_token(self):
        self.assertEqual(self.cliente.get(PERFIL).status_code, 401)

    def test_limita_intentos_por_ip(self):
        codigos = [self.cliente.post(LOGIN, {'correo': 'x@x.cl', 'password': 'x'}, format='json').status_code for _ in range(21)]
        self.assertEqual(codigos[-1], 429)
