from unittest import mock

from django.db import DatabaseError
from django.test import TestCase
from rest_framework.test import APIClient

from scraper.models import OfertaAcademica
from scraper.test_api import ApiCatalogoTests


class SaludTests(ApiCatalogoTests):
    def test_health_responde_sin_base_de_datos(self):
        respuesta = self.cliente.get('/health')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['estado'], 'ok')

    def test_health_deep_compara_dos_ofertas(self):
        respuesta = self.cliente.get('/health/deep')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['estado'], 'ok')
        self.assertEqual(len(datos['ofertas_comparadas']), 2)
        self.assertIn('milisegundos', datos)

    def test_health_deep_falla_sin_ofertas(self):
        OfertaAcademica.objects.all().delete()
        respuesta = self.cliente.get('/health/deep')
        self.assertEqual(respuesta.status_code, 503)

    def test_health_deep_falla_si_la_base_no_responde(self):
        with mock.patch('scraper.salud.OfertaSerializer', side_effect=DatabaseError('caída')):
            respuesta = self.cliente.get('/health/deep')
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()['base_de_datos'], 'sin conexión')


class DocumentacionApiTests(TestCase):
    def test_esquema_openapi_incluye_catalogo(self):
        respuesta = APIClient().get('/api/v1/schema/', {'format': 'json'})
        self.assertEqual(respuesta.status_code, 200)
        rutas = respuesta.json()['paths']
        self.assertIn('/api/v1/carreras/', rutas)
        self.assertIn('/api/v1/ofertas/', rutas)

    def test_swagger_ui_disponible(self):
        respuesta = APIClient().get('/api/v1/docs/')
        self.assertEqual(respuesta.status_code, 200)
