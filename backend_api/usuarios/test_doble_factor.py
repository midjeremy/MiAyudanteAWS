"""Doble factor con app autenticadora (TOTP): activación, login en dos pasos, recuperación y límites."""
import base64
import time
from unittest import mock

import pyotp
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .doble_factor import VIGENCIA_TOKEN_TEMPORAL
from .models import SegundoFactor

LOGIN = '/api/v1/auth/login/'
PERFIL = '/api/v1/auth/perfil/'
VERIFICAR = '/api/v1/auth/2fa/verificar/'
ACTIVAR = '/api/v1/auth/2fa/activar/'
CONFIRMAR = '/api/v1/auth/2fa/confirmar/'
DESACTIVAR = '/api/v1/auth/2fa/desactivar/'
CORREO = 'ana@correo.cl'
CLAVE = 'Clave-Segura-2026'


def codigo_incorrecto(secreto, ahora):
    """Un código de 6 dígitos que no es válido en la ventana de ±30 s."""
    totp = pyotp.TOTP(secreto)
    validos = {totp.at(ahora + desfase) for desfase in (-30, 0, 30)}
    return next(c for c in (f'{n:06d}' for n in range(1_000_000)) if c not in validos)


class DobleFactorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = get_user_model().objects.create_user(username=CORREO, email=CORREO, password=CLAVE,
                                                            first_name='Ana', last_name='Pérez')
        self.cliente = APIClient()
        # Reloj controlado del TOTP: cada código se pide en un paso de 30 s nuevo, porque un código ya usado
        # no vuelve a servir (activar y luego iniciar sesión con el mismo código ahora se rechaza)
        self.reloj = time.time()
        reloj = mock.patch('usuarios.doble_factor._ahora', side_effect=lambda: self.reloj)
        reloj.start()
        self.addCleanup(reloj.stop)

    def codigo(self, secreto):
        """Código TOTP del paso siguiente (avanza el reloj 30 s)."""
        self.reloj += 30
        return pyotp.TOTP(secreto).at(self.reloj)

    def login(self):
        return self.cliente.post(LOGIN, {'correo': CORREO, 'password': CLAVE}, format='json')

    def autenticar(self):
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 200)
        self.cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")

    def activar_doble_factor(self):
        """Activa el doble factor por la API. Devuelve el secreto y los códigos de recuperación."""
        self.autenticar()
        activacion = self.cliente.post(ACTIVAR, format='json')
        self.assertEqual(activacion.status_code, 200)
        secreto = activacion.data['secreto']
        confirmacion = self.cliente.post(CONFIRMAR, {'codigo': self.codigo(secreto)}, format='json')
        self.assertEqual(confirmacion.status_code, 200)
        self.cliente.credentials()
        cache.clear()  # cada test parte con los límites de intentos en cero
        return secreto, confirmacion.data['codigos_recuperacion']

    def token_temporal(self):
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.data['token_temporal']

    def verificar(self, token, codigo):
        return self.cliente.post(VERIFICAR, {'token_temporal': token, 'codigo': codigo}, format='json')

    # --- Activación ---

    def test_activar_entrega_uri_y_qr_png(self):
        self.autenticar()
        respuesta = self.cliente.post(ACTIVAR, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data['otpauth_uri'].startswith('otpauth://totp/'))
        self.assertIn('issuer=Mi%20Ayudante', respuesta.data['otpauth_uri'])
        self.assertIn(respuesta.data['secreto'], respuesta.data['otpauth_uri'])
        png = base64.b64decode(respuesta.data['qr_png_base64'])
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        # Hasta confirmar el primer código queda pendiente: el login sigue siendo de un paso
        self.assertFalse(SegundoFactor.objects.get(usuario=self.usuario).activo)
        self.cliente.credentials()
        self.assertIn('access', self.login().data)

    def test_activar_y_confirmar_exigen_sesion(self):
        self.assertEqual(self.cliente.post(ACTIVAR, format='json').status_code, 401)
        self.assertEqual(self.cliente.post(CONFIRMAR, {'codigo': '123456'}, format='json').status_code, 401)
        self.assertEqual(self.cliente.post(DESACTIVAR, {'codigo': '123456'}, format='json').status_code, 401)

    def test_confirmar_rechaza_codigo_incorrecto(self):
        self.autenticar()
        secreto = self.cliente.post(ACTIVAR, format='json').data['secreto']
        respuesta = self.cliente.post(CONFIRMAR, {'codigo': codigo_incorrecto(secreto, self.reloj)}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(SegundoFactor.objects.get(usuario=self.usuario).activo)

    def test_confirmar_activa_y_entrega_8_codigos_una_sola_vez(self):
        secreto, codigos = self.activar_doble_factor()
        self.assertEqual(len(codigos), 8)
        self.assertEqual(len(set(codigos)), 8)
        segundo_factor = SegundoFactor.objects.get(usuario=self.usuario)
        self.assertTrue(segundo_factor.activo)
        # En la base de datos solo quedan hashes, nunca los códigos en claro
        self.assertEqual(len(segundo_factor.codigos_recuperacion), 8)
        for codigo in codigos:
            self.assertNotIn(codigo, segundo_factor.codigos_recuperacion)
            self.assertNotIn(codigo.replace('-', ''), segundo_factor.codigos_recuperacion)
        # Una segunda confirmación no vuelve a entregar códigos
        token = self.token_temporal()
        self.cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {self.verificar(token, self.codigo(secreto)).data['access']}")
        repetida = self.cliente.post(CONFIRMAR, {'codigo': self.codigo(secreto)}, format='json')
        self.assertEqual(repetida.status_code, 409)
        self.assertNotIn('codigos_recuperacion', repetida.data)
        self.assertEqual(self.cliente.post(ACTIVAR, format='json').status_code, 409)
        self.assertTrue(self.cliente.get(PERFIL).data['doble_factor_activo'])

    # --- Login ---

    def test_login_sin_doble_factor_entrega_tokens(self):
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('access', respuesta.data)
        self.assertIn('refresh', respuesta.data)
        self.assertNotIn('requiere_2fa', respuesta.data)

    def test_login_con_doble_factor_no_entrega_tokens(self):
        self.activar_doble_factor()
        respuesta = self.login()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data['requiere_2fa'])
        self.assertTrue(respuesta.data['token_temporal'])
        self.assertNotIn('access', respuesta.data)
        self.assertNotIn('refresh', respuesta.data)

    def test_login_con_doble_factor_y_clave_incorrecta(self):
        self.activar_doble_factor()
        respuesta = self.cliente.post(LOGIN, {'correo': CORREO, 'password': 'otra'}, format='json')
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn('token_temporal', respuesta.data)

    def test_verificar_codigo_correcto_entrega_tokens(self):
        secreto, _ = self.activar_doble_factor()
        respuesta = self.verificar(self.token_temporal(), self.codigo(secreto))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['usuario'], {'correo': CORREO, 'nombre': 'Ana Pérez'})
        self.assertIn('refresh', respuesta.data)
        self.assertIn('consentimiento_vigente', respuesta.data)
        self.cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        self.assertEqual(self.cliente.get(PERFIL).status_code, 200)

    def test_verificar_acepta_codigo_con_espacios(self):
        secreto, _ = self.activar_doble_factor()
        codigo = self.codigo(secreto)
        respuesta = self.verificar(self.token_temporal(), f'{codigo[:3]} {codigo[3:]}')
        self.assertEqual(respuesta.status_code, 200)

    def test_verificar_rechaza_codigo_incorrecto(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        for codigo in (codigo_incorrecto(secreto, self.reloj), '', 'abc', None):
            respuesta = self.verificar(token, codigo)
            self.assertEqual(respuesta.status_code, 401, codigo)
            self.assertNotIn('access', respuesta.data)

    def test_verificar_rechaza_token_vencido(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        mas_tarde = time.time() + VIGENCIA_TOKEN_TEMPORAL + 1
        with mock.patch('django.core.signing.time.time', return_value=mas_tarde):
            respuesta = self.verificar(token, self.codigo(secreto))
        self.assertEqual(respuesta.status_code, 401)
        self.assertIn('venció', respuesta.data['error'])
        self.assertTrue(respuesta.data['reiniciar'])
        self.assertNotIn('access', respuesta.data)

    def test_verificar_acepta_token_justo_antes_de_vencer(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        casi = time.time() + VIGENCIA_TOKEN_TEMPORAL - 5
        with mock.patch('django.core.signing.time.time', return_value=casi):
            respuesta = self.verificar(token, self.codigo(secreto))
        self.assertEqual(respuesta.status_code, 200)

    def test_verificar_rechaza_token_alterado_o_ausente(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        otro = get_user_model().objects.create_user(username='otro@correo.cl', email='otro@correo.cl', password=CLAVE)
        alterado = f'{otro.pk}:' + token.split(':', 1)[1]
        for valor in (alterado, token + 'x', '', None):
            respuesta = self.verificar(valor, self.codigo(secreto))
            self.assertEqual(respuesta.status_code, 401, valor)
            self.assertNotIn('access', respuesta.data)

    def test_codigo_de_recuperacion_sirve_una_sola_vez(self):
        _, codigos = self.activar_doble_factor()
        primero = self.verificar(self.token_temporal(), codigos[0])
        self.assertEqual(primero.status_code, 200)
        self.assertIn('access', primero.data)
        self.assertEqual(len(SegundoFactor.objects.get(usuario=self.usuario).codigos_recuperacion), 7)

        repetido = self.verificar(self.token_temporal(), codigos[0])
        self.assertEqual(repetido.status_code, 401)
        # Los demás siguen sirviendo, también escritos sin guion y en mayúsculas
        otro = self.verificar(self.token_temporal(), codigos[1].replace('-', '').upper())
        self.assertEqual(otro.status_code, 200)
        self.assertEqual(len(SegundoFactor.objects.get(usuario=self.usuario).codigos_recuperacion), 6)

    def test_verificar_limita_intentos(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        malo = codigo_incorrecto(secreto, self.reloj)
        codigos = [self.verificar(token, malo).status_code for _ in range(5)]
        self.assertEqual(codigos, [401] * 5)
        # El sexto intento se bloquea aunque el código sea correcto
        sexto = self.verificar(token, self.codigo(secreto))
        self.assertEqual(sexto.status_code, 429)
        self.assertNotIn('access', sexto.data)

    # --- Desactivación ---

    def test_desactivar_exige_codigo_valido(self):
        secreto, _ = self.activar_doble_factor()
        token = self.token_temporal()
        acceso = self.verificar(token, self.codigo(secreto)).data['access']
        self.cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {acceso}')

        self.assertEqual(self.cliente.post(DESACTIVAR, {'codigo': codigo_incorrecto(secreto, self.reloj)}, format='json').status_code, 400)
        self.assertTrue(SegundoFactor.objects.get(usuario=self.usuario).activo)

        respuesta = self.cliente.post(DESACTIVAR, {'codigo': self.codigo(secreto)}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(SegundoFactor.objects.filter(usuario=self.usuario).exists())
        self.assertFalse(self.cliente.get(PERFIL).data['doble_factor_activo'])
        # Sin doble factor, el login vuelve a entregar los tokens de inmediato
        self.cliente.credentials()
        self.assertIn('access', self.login().data)

    def test_desactivar_con_codigo_de_recuperacion(self):
        secreto, codigos = self.activar_doble_factor()
        acceso = self.verificar(self.token_temporal(), self.codigo(secreto)).data['access']
        self.cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {acceso}')
        respuesta = self.cliente.post(DESACTIVAR, {'codigo': codigos[3]}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(SegundoFactor.objects.filter(usuario=self.usuario).exists())

    def test_mis_datos_no_exporta_el_secreto(self):
        secreto, codigos = self.activar_doble_factor()
        acceso = self.verificar(self.token_temporal(), self.codigo(secreto)).data['access']
        self.cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {acceso}')
        respuesta = self.cliente.get('/api/v1/auth/mis-datos/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['doble_factor'], {'activo': True})
        contenido = respuesta.content.decode()
        self.assertNotIn(secreto, contenido)
        self.assertNotIn(codigos[0], contenido)
