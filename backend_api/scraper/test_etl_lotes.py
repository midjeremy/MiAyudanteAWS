"""Control de lotes: mensaje de error legible y cierre de lotes que un proceso interrumpido dejó abiertos."""
from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from selenium.common.exceptions import WebDriverException

from scraper.etl import HORAS_LOTE_COLGADO, cerrar_lotes_colgados, describir_error
from scraper.models import Institucion, LoteScrapingS3


class DescribirErrorTests(SimpleTestCase):
    def test_selenium_sin_stacktrace(self):
        error = WebDriverException('unknown error: net::ERR_CONNECTION_RESET\n  (Session info: chrome=131)',
                                   stacktrace=['#0 0x55d...', '#1 0x55e...'])
        self.assertEqual(describir_error(error), 'WebDriverException: unknown error: net::ERR_CONNECTION_RESET')

    def test_excepcion_comun_y_sin_mensaje(self):
        self.assertEqual(describir_error(ValueError('dato inválido')), 'ValueError: dato inválido')
        self.assertEqual(describir_error(RuntimeError()), 'RuntimeError')

    def test_recorta_mensajes_largos(self):
        self.assertEqual(len(describir_error(ValueError('x' * 1000))), 200)
        self.assertEqual(len(describir_error(ValueError('x' * 1000), 500)), 500)


class LotesColgadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        cls.duoc = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')

    def lote(self, institucion, estado, horas_atras):
        lote = LoteScrapingS3.objects.create(institucion=institucion, estado_etl=estado)
        # fecha_extraccion es auto_now_add: se ajusta después de crear
        LoteScrapingS3.objects.filter(pk=lote.pk).update(
            fecha_extraccion=timezone.now() - timedelta(hours=horas_atras))
        return lote

    def test_marca_como_error_solo_los_lotes_antiguos_en_proceso(self):
        colgado = self.lote(self.inacap, 'EN_PROCESO', HORAS_LOTE_COLGADO + 1)
        en_curso = self.lote(self.inacap, 'EN_PROCESO', 1)
        terminado = self.lote(self.inacap, 'COMPLETADO', 48)

        self.assertEqual(cerrar_lotes_colgados(self.inacap), 1)

        colgado.refresh_from_db()
        self.assertEqual(colgado.estado_etl, 'ERROR')
        self.assertIn('Interrumpido', colgado.detalle_errores)
        en_curso.refresh_from_db()
        terminado.refresh_from_db()
        self.assertEqual((en_curso.estado_etl, terminado.estado_etl), ('EN_PROCESO', 'COMPLETADO'))

    def test_no_toca_lotes_de_otra_institucion(self):
        ajeno = self.lote(self.duoc, 'EN_PROCESO', 48)
        self.assertEqual(cerrar_lotes_colgados(self.inacap), 0)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.estado_etl, 'EN_PROCESO')
