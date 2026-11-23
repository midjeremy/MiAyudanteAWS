"""Cierre de sesión con revocación de JWT y TOTP de un solo uso (ISO/IEC 27002, control de acceso)."""
import time
from datetime import timedelta
from unittest import mock

import pyotp
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from . import doble_factor
from .models import SegundoFactor

LOGIN = '/api/v1/auth/login/'
LOGOUT = '/api/v1/auth/logout/'
REFRESH = '/api/v1/auth/refresh/'
PERFIL = '/api/v1/auth/perfil/'
VERIFICAR = '/api/v1/auth/2fa/verificar/'
CLAVE = 'Clave-Segura-2026'


def crear_usuario(correo='ana@correo.cl'):
    return get_user_model().objects.create_user(username=correo, email=correo, password=CLAVE, first_name='Ana')


class CierreSesionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario()
        self.cliente = APIClient()
        datos = self.cliente.post(LOGIN, {'correo': 'ana@correo.cl', 'password': CLAVE}, format='json').data
        self.acceso, self.refresco = datos['access'], datos['refresh']

    def con_token(self, token):
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return cliente

    def test_antes_de_cerrar_los_tokens_sirven(self):
        self.assertEqual(self.con_token(self.acceso).get(PERFIL).status_code, 200)
        self.assertEqual(self.cliente.post(REFRESH, {'refresh': self.refresco}, format='json').status_code, 200)

    def test_cerrar_sesion_revoca_el_acceso_y_el_refresco(self):
        respuesta = self.con_token(self.acceso).post(LOGOUT, {'refresh': self.refresco}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data['sesion_cerrada'])
        # El token de acceso no esperó a vencer (1 hora): dejó de servir de inmediato
        perfil = self.con_token(self.acceso).get(PERFIL)
        self.assertEqual(perfil.status_code, 401)
        # Y el de refresco ya no entrega tokens nuevos
        self.assertEqual(self.cliente.post(REFRESH, {'refresh': self.refresco}, format='json').status_code, 401)

    def test_otra_sesion_de_la_misma_cuenta_sigue_activa(self):
        otra = self.cliente.post(LOGIN, {'correo': 'ana@correo.cl', 'password': CLAVE}, format='json').data
        self.con_token(self.acceso).post(LOGOUT, {'refresh': self.refresco}, format='json')
        self.assertEqual(self.con_token(otra['access']).get(PERFIL).status_code, 200)

    def test_con_el_acceso_vencido_igual_revoca_el_refresco(self):
        vencido = AccessToken.for_user(self.usuario)
        vencido.set_exp(lifetime=-timedelta(seconds=1))
        respuesta = self.con_token(str(vencido)).post(LOGOUT, {'refresh': self.refresco}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cliente.post(REFRESH, {'refresh': self.refresco}, format='json').status_code, 401)

    def test_cerrar_dos_veces_o_sin_tokens_no_falla(self):
        self.con_token(self.acceso).post(LOGOUT, {'refresh': self.refresco}, format='json')
        self.assertEqual(self.cliente.post(LOGOUT, {'refresh': self.refresco}, format='json').status_code, 200)
        self.assertEqual(self.cliente.post(LOGOUT, {}, format='json').status_code, 200)
        self.assertEqual(self.cliente.post(LOGOUT, {'refresh': 'basura'}, format='json').status_code, 200)

    def test_no_revoca_la_sesion_de_otra_persona(self):
        otra = crear_usuario('beto@correo.cl')
        refresco_ajeno = str(RefreshToken.for_user(otra))
        respuesta = self.con_token(self.acceso).post(LOGOUT, {'refresh': refresco_ajeno}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cliente.post(REFRESH, {'refresh': refresco_ajeno}, format='json').status_code, 200)
        self.assertEqual(self.con_token(self.acceso).get(PERFIL).status_code, 200)

    def test_la_revocacion_dura_lo_que_le_queda_al_token(self):
        token = AccessToken(self.acceso)
        with mock.patch('usuarios.autenticacion.cache.set') as guardar:
            self.con_token(self.acceso).post(LOGOUT, {}, format='json')
        clave, _valor = guardar.call_args.args[:2]
        self.assertEqual(clave, f"jwt_revocado:{token['jti']}")
        self.assertLessEqual(guardar.call_args.kwargs['timeout'], 3601)


class TotpUnSoloUsoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario()
        self.secreto = pyotp.random_base32()
        self.segundo = SegundoFactor.objects.create(usuario=self.usuario, secreto=self.secreto, activo=True)
        self.reloj = time.time()
        reloj = mock.patch('usuarios.doble_factor._ahora', side_effect=lambda: self.reloj)
        reloj.start()
        self.addCleanup(reloj.stop)

    def token_temporal(self):
        return doble_factor.crear_token_temporal(self.usuario)

    def verificar(self, codigo):
        cache.clear()  # el límite de 5 intentos por minuto no es lo que se prueba aquí
        return APIClient().post(VERIFICAR, {'token_temporal': self.token_temporal(), 'codigo': codigo}, format='json')

    def test_el_mismo_codigo_no_sirve_dos_veces(self):
        codigo = pyotp.TOTP(self.secreto).at(self.reloj)
        self.assertEqual(self.verificar(codigo).status_code, 200)
        repetido = self.verificar(codigo)
        self.assertEqual(repetido.status_code, 401)
        self.assertNotIn('access', repetido.data)

    def test_tampoco_un_codigo_anterior_al_usado(self):
        anterior = pyotp.TOTP(self.secreto).at(self.reloj - 30)
        actual = pyotp.TOTP(self.secreto).at(self.reloj)
        self.assertEqual(self.verificar(actual).status_code, 200)
        self.assertEqual(self.verificar(anterior).status_code, 401)

    def test_el_codigo_del_paso_siguiente_si_sirve(self):
        self.assertEqual(self.verificar(pyotp.TOTP(self.secreto).at(self.reloj)).status_code, 200)
        self.reloj += 30
        self.assertEqual(self.verificar(pyotp.TOTP(self.secreto).at(self.reloj)).status_code, 200)

    def test_dos_usos_simultaneos_del_mismo_paso(self):
        paso = int(self.reloj // 30)
        otra_copia = SegundoFactor.objects.get(pk=self.segundo.pk)
        self.assertTrue(doble_factor.usar_paso_totp(self.segundo, paso))
        self.assertFalse(doble_factor.usar_paso_totp(otra_copia, paso))

    def test_reactivar_reinicia_el_registro_de_pasos(self):
        self.verificar(pyotp.TOTP(self.secreto).at(self.reloj))
        self.segundo.delete()
        cliente = APIClient()
        cliente.force_authenticate(self.usuario)
        nuevo = cliente.post('/api/v1/auth/2fa/activar/', format='json').data['secreto']
        self.assertIsNone(SegundoFactor.objects.get(usuario=self.usuario).ultimo_paso_totp)
        confirmar = cliente.post('/api/v1/auth/2fa/confirmar/', {'codigo': pyotp.TOTP(nuevo).at(self.reloj)},
                                 format='json')
        self.assertEqual(confirmar.status_code, 200)
