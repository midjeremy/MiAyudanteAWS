"""El admin muestra solo los modelos en uso: sin duplicados de usuarios ni del test Ikigai."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from scraper.models import (
    Carrera, HistorialChatRag, Institucion, LoteScrapingS3, OfertaAcademica, PreguntaIkigai,
    RespuestaUsuario, ResultadoVocacional, Usuario,
)
from Test_Ikigai.models import Pregunta, Resultado


class AdminModelosTests(TestCase):
    def setUp(self):
        self.cliente = self.client
        superusuario = get_user_model().objects.create_superuser('admin@test.cl', 'admin@test.cl', 'Clave-segura-123')
        self.cliente.force_login(superusuario)

    def test_los_modelos_antiguos_no_aparecen(self):
        for modelo in (Usuario, HistorialChatRag, PreguntaIkigai, RespuestaUsuario, ResultadoVocacional):
            self.assertFalse(admin.site.is_registered(modelo), modelo.__name__)

    def test_las_secciones_reales_siguen_disponibles(self):
        for modelo in (Carrera, OfertaAcademica, LoteScrapingS3, Pregunta, Resultado, get_user_model()):
            self.assertTrue(admin.site.is_registered(modelo), modelo.__name__)

    def test_portada_del_admin_sin_duplicados(self):
        html = self.cliente.get('/admin/').content.decode()
        self.assertIn('Catálogo y ETL', html)
        self.assertIn('Ofertas académicas', html)
        self.assertNotIn('Pregunta ikigais', html)
        self.assertNotIn('Historial chat rags', html)

    def test_los_lotes_son_de_solo_lectura(self):
        institucion = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        lote = LoteScrapingS3.objects.create(institucion=institucion, estado_etl='COMPLETADO')
        self.assertEqual(self.cliente.get('/admin/scraper/lotescrapings3/add/').status_code, 403)
        respuesta = self.cliente.get(f'/admin/scraper/lotescrapings3/{lote.id}/change/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'name="estado_etl"')
