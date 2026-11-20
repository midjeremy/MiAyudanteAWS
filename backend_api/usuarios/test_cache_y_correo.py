"""Caché compartida para los límites de intentos y comando de prueba del correo."""
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

LOGIN = '/api/v1/auth/login/'


class CacheCompartidaTests(TestCase):
    """Con la caché en memoria cada worker de Gunicorn contaba por separado y el límite real era el triple."""

    def setUp(self):
        cache.clear()

    def test_la_cache_esta_en_postgresql(self):
        self.assertEqual(settings.CACHES['default']['BACKEND'], 'django.core.cache.backends.db.DatabaseCache')

    def test_los_intentos_de_login_quedan_en_la_tabla_compartida(self):
        cliente = APIClient()
        for _ in range(3):
            cliente.post(LOGIN, {'correo': 'nadie@correo.cl', 'password': 'x'}, format='json')
        # Lo que cuenta un worker queda en PostgreSQL, donde lo leen los otros workers
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM miayudante_cache WHERE cache_key LIKE '%%throttle_auth%%'")
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_el_limite_se_aplica_con_el_contador_guardado(self):
        cliente = APIClient()
        respuestas = [cliente.post(LOGIN, {'correo': 'nadie@correo.cl', 'password': 'x'}, format='json').status_code
                      for _ in range(21)]
        self.assertEqual(respuestas[:20], [401] * 20)
        self.assertEqual(respuestas[20], 429)


@override_settings(CORREO_ALERTAS='alertas@mi-ayudante.cl', DEFAULT_FROM_EMAIL='Mi Ayudante <alertas@mi-ayudante.cl>')
class ProbarCorreoTests(TestCase):
    def test_envia_a_alertas_por_defecto(self):
        call_command('probar_correo', stdout=mock.Mock())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alertas@mi-ayudante.cl'])
        self.assertEqual(mail.outbox[0].from_email, 'Mi Ayudante <alertas@mi-ayudante.cl>')

    def test_envia_a_la_direccion_indicada(self):
        call_command('probar_correo', 'contacto@mi-ayudante.cl', stdout=mock.Mock())
        self.assertEqual(mail.outbox[0].to, ['contacto@mi-ayudante.cl'])
