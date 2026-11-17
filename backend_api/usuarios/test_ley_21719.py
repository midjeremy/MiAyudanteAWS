"""Adecuación a la Ley N.° 21.719: consentimiento, edad mínima, derechos del titular y conservación."""
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from Test_Ikigai.models import Resultado
from usuarios.management.commands.purgar_cuentas_inactivas import cuentas_inactivas
from usuarios.models import Consentimiento
from usuarios.privacidad import VERSION_POLITICA

Usuario = get_user_model()
REGISTRO = '/api/v1/auth/registro/'
LOGIN = '/api/v1/auth/login/'
CLAVE = 'Clave-Segura-2026'
DATOS = {'correo': 'ana@correo.cl', 'nombre': 'Ana', 'apellidos': 'Pérez', 'password': CLAVE,
         'acepta_privacidad': True, 'mayor_14': True}


def crear_resultado(usuario, pasion=80):
    return Resultado.objects.create(usuario=usuario, puntaje_pasion=pasion, puntaje_vocacion=60,
                                    puntaje_profesion=50, puntaje_mision=40,
                                    puntajes_area={'tecnologia': 90.0}, respuestas={'1': 5})


class BaseLey(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = APIClient()

    def autenticar(self, usuario):
        self.cliente.force_authenticate(usuario)


class ConsentimientoRegistroTests(BaseLey):
    def test_registro_sin_aceptar_la_politica_no_crea_la_cuenta(self):
        respuesta = self.cliente.post(REGISTRO, {**DATOS, 'acepta_privacidad': False}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('política de privacidad', respuesta.data['error'])
        self.assertFalse(Usuario.objects.exists())

    def test_casilla_ausente_cuenta_como_no_aceptada(self):
        datos = {k: v for k, v in DATOS.items() if k != 'acepta_privacidad'}
        self.assertEqual(self.cliente.post(REGISTRO, datos, format='json').status_code, 400)

    def test_menor_de_14_no_crea_cuenta_y_se_le_ofrece_usarla_sin_cuenta(self):
        respuesta = self.cliente.post(REGISTRO, {**DATOS, 'mayor_14': False}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('sin cuenta', respuesta.data['error'])
        self.assertFalse(Usuario.objects.exists())

    def test_registro_guarda_la_constancia_con_version_y_fecha(self):
        self.assertEqual(self.cliente.post(REGISTRO, DATOS, format='json').status_code, 201)
        consentimiento = Consentimiento.objects.get()
        self.assertEqual(consentimiento.usuario.email, 'ana@correo.cl')
        self.assertEqual(consentimiento.version_politica, VERSION_POLITICA)
        self.assertTrue(consentimiento.declara_edad_minima)
        self.assertIsNotNone(consentimiento.aceptado_en)

    def test_acepta_casillas_de_formulario(self):
        datos = {**DATOS, 'acepta_privacidad': 'on', 'mayor_14': '1'}
        self.assertEqual(self.cliente.post(REGISTRO, datos, format='json').status_code, 201)

    def test_login_informa_si_falta_aceptar_la_politica_vigente(self):
        Usuario.objects.create_user('antiguo@correo.cl', 'antiguo@correo.cl', CLAVE)  # creado antes de la política
        respuesta = self.cliente.post(LOGIN, {'correo': 'antiguo@correo.cl', 'password': CLAVE}, format='json')
        self.assertFalse(respuesta.data['consentimiento_vigente'])

    def test_cuenta_antigua_acepta_la_politica(self):
        usuario = Usuario.objects.create_user('antiguo@correo.cl', 'antiguo@correo.cl', CLAVE)
        self.autenticar(usuario)
        self.assertEqual(self.cliente.post('/api/v1/auth/consentimiento/', {'acepta_privacidad': True},
                                           format='json').status_code, 400)
        respuesta = self.cliente.post('/api/v1/auth/consentimiento/',
                                      {'acepta_privacidad': True, 'mayor_14': True}, format='json')
        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(self.cliente.get('/api/v1/auth/perfil/').data['consentimiento_vigente'])
        # Repetir la aceptación no duplica la constancia
        self.cliente.post('/api/v1/auth/consentimiento/', {'acepta_privacidad': True, 'mayor_14': True}, format='json')
        self.assertEqual(usuario.consentimientos.count(), 1)


class DerechosTitularTests(BaseLey):
    def setUp(self):
        super().setUp()
        self.usuario = Usuario.objects.create_user('ana@correo.cl', 'ana@correo.cl', CLAVE,
                                                   first_name='Ana', last_name='Pérez')
        Consentimiento.objects.create(usuario=self.usuario, version_politica=VERSION_POLITICA, declara_edad_minima=True)
        self.resultado = crear_resultado(self.usuario)
        self.otro = Usuario.objects.create_user('otro@correo.cl', 'otro@correo.cl', CLAVE)
        self.resultado_ajeno = crear_resultado(self.otro)

    def test_derechos_exigen_sesion(self):
        self.assertEqual(self.cliente.get('/api/v1/auth/mis-datos/').status_code, 401)
        self.assertEqual(self.cliente.delete('/api/v1/auth/cuenta/').status_code, 401)

    def test_acceso_y_portabilidad_entrega_todos_sus_datos_y_solo_los_suyos(self):
        self.autenticar(self.usuario)
        respuesta = self.cliente.get('/api/v1/auth/mis-datos/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta['Content-Disposition'])
        datos = respuesta.json()
        self.assertEqual(datos['cuenta']['correo'], 'ana@correo.cl')
        self.assertEqual(datos['cuenta']['apellidos'], 'Pérez')
        self.assertEqual(len(datos['consentimientos']), 1)
        self.assertEqual([r['id'] for r in datos['resultados_test']], [self.resultado.id])
        self.assertEqual(datos['resultados_test'][0]['respuestas'], {'1': 5})

    def test_rectificacion_del_nombre(self):
        self.autenticar(self.usuario)
        respuesta = self.cliente.patch('/api/v1/auth/perfil/', {'nombre': ' Ana María '}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['usuario']['nombre'], 'Ana María Pérez')
        self.assertEqual(self.cliente.patch('/api/v1/auth/perfil/', {'apellidos': ''}, format='json').status_code, 400)
        self.assertEqual(self.cliente.patch('/api/v1/auth/perfil/', {}, format='json').status_code, 400)

    def test_borrar_un_resultado_propio_pero_no_uno_ajeno(self):
        self.autenticar(self.usuario)
        ajeno = self.cliente.delete(f'/api/v1/auth/mis-datos/resultados/{self.resultado_ajeno.id}/')
        self.assertEqual(ajeno.status_code, 404)
        self.assertTrue(Resultado.objects.filter(pk=self.resultado_ajeno.id).exists())
        propio = self.cliente.delete(f'/api/v1/auth/mis-datos/resultados/{self.resultado.id}/')
        self.assertEqual(propio.status_code, 204)
        self.assertFalse(Resultado.objects.filter(pk=self.resultado.id).exists())

    def test_eliminar_cuenta_exige_la_contrasena(self):
        self.autenticar(self.usuario)
        respuesta = self.cliente.delete('/api/v1/auth/cuenta/', {'password': 'otra'}, format='json')
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=self.usuario.pk).exists())

    def test_eliminar_cuenta_borra_resultados_y_consentimientos(self):
        self.autenticar(self.usuario)
        respuesta = self.cliente.delete('/api/v1/auth/cuenta/', {'password': CLAVE}, format='json')
        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())
        self.assertFalse(Resultado.objects.filter(usuario_id=self.usuario.pk).exists())
        self.assertFalse(Consentimiento.objects.filter(usuario_id=self.usuario.pk).exists())
        # Los datos de otras personas no se tocan
        self.assertTrue(Resultado.objects.filter(pk=self.resultado_ajeno.id).exists())


class ConservacionTests(TestCase):
    def setUp(self):
        hace = lambda meses: timezone.now() - timedelta(days=meses * 31)
        self.inactiva = Usuario.objects.create_user('inactiva@correo.cl', 'inactiva@correo.cl', CLAVE)
        Usuario.objects.filter(pk=self.inactiva.pk).update(last_login=hace(25), date_joined=hace(30))
        crear_resultado(self.inactiva)
        self.nunca = Usuario.objects.create_user('nunca@correo.cl', 'nunca@correo.cl', CLAVE)
        Usuario.objects.filter(pk=self.nunca.pk).update(last_login=None, date_joined=hace(26))
        self.activa = Usuario.objects.create_user('activa@correo.cl', 'activa@correo.cl', CLAVE)
        Usuario.objects.filter(pk=self.activa.pk).update(last_login=hace(3), date_joined=hace(30))
        self.admin = Usuario.objects.create_superuser('admin@correo.cl', 'admin@correo.cl', CLAVE)
        Usuario.objects.filter(pk=self.admin.pk).update(last_login=hace(40), date_joined=hace(40))

    def test_selecciona_solo_cuentas_inactivas_que_no_son_del_equipo(self):
        self.assertEqual(set(cuentas_inactivas().values_list('email', flat=True)),
                         {'inactiva@correo.cl', 'nunca@correo.cl'})

    def test_simular_no_borra_nada(self):
        salida = StringIO()
        call_command('purgar_cuentas_inactivas', '--simular', stdout=salida)
        self.assertIn('2 cuenta(s)', salida.getvalue())
        self.assertEqual(Usuario.objects.count(), 4)

    def test_purga_borra_cuentas_y_sus_resultados_sin_mostrar_correos(self):
        salida = StringIO()
        call_command('purgar_cuentas_inactivas', stdout=salida)
        self.assertEqual(set(Usuario.objects.values_list('email', flat=True)), {'activa@correo.cl', 'admin@correo.cl'})
        self.assertFalse(Resultado.objects.filter(usuario_id=self.inactiva.pk).exists())
        self.assertIn('2', salida.getvalue())
        self.assertNotIn('@', salida.getvalue())


class CookiesSegurasTests(TestCase):
    def test_con_dominio_https_las_cookies_del_admin_son_seguras(self):
        from django.conf import settings
        if settings.DOMINIO:
            self.assertTrue(settings.SESSION_COOKIE_SECURE)
            self.assertTrue(settings.CSRF_COOKIE_SECURE)

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_cookie_de_sesion_segura_lleva_el_atributo_secure(self):
        admin = Usuario.objects.create_superuser('admin@correo.cl', 'admin@correo.cl', CLAVE)
        self.client.force_login(admin)
        self.assertTrue(self.client.cookies['sessionid']['secure'])
