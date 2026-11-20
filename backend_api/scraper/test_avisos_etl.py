"""Scrapers: aviso por correo de lotes fallidos, código de salida, ejecución cada hora y clave única de las mallas."""
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from scraper.etl import avisar_lote, motivo_para_omitir
from scraper.management.commands import run_duoc_scraper
from scraper.management.commands.run_inacap_scraper import clave_malla
from scraper.models import Institucion, LoteScrapingS3


def crear_lote(institucion, estado, horas_atras=0, **campos):
    lote = LoteScrapingS3.objects.create(institucion=institucion, estado_etl=estado, **campos)
    LoteScrapingS3.objects.filter(pk=lote.pk).update(fecha_extraccion=timezone.now() - timedelta(hours=horas_atras))
    lote.refresh_from_db()
    return lote


@override_settings(ADMINS=['alertas@mi-ayudante.cl'])
class AvisarLoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.duoc = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')

    def test_lote_en_error_avisa_a_alertas(self):
        lote = crear_lote(self.duoc, 'ERROR', errores=2, detalle_errores='Sin nombre: https://www.duoc.cl/x')
        self.assertTrue(avisar_lote(lote))
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['alertas@mi-ayudante.cl'])
        self.assertIn(f'lote {lote.id} terminó en ERROR', correo.subject)
        self.assertIn('no se modificaron los datos publicados', correo.body)
        self.assertIn('Sin nombre: https://www.duoc.cl/x', correo.body)

    def test_lote_parcial_avisa_y_completado_no(self):
        self.assertTrue(avisar_lote(crear_lote(self.duoc, 'PARCIAL')))
        self.assertFalse(avisar_lote(crear_lote(self.duoc, 'COMPLETADO')))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('no se retiraron las ofertas obsoletas', mail.outbox[0].body)

    def test_un_fallo_del_correo_no_detiene_el_etl(self):
        lote = crear_lote(self.duoc, 'ERROR')
        with mock.patch('scraper.etl.mail_admins', side_effect=OSError('SMTP caído')), \
                self.assertLogs('scraper.etl', level='ERROR'):
            self.assertFalse(avisar_lote(lote))


class MotivoParaOmitirTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inacap = Institucion.objects.create(codigo='INACAP', nombre='INACAP')
        cls.duoc = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')

    def test_sin_lotes_se_ejecuta(self):
        self.assertIsNone(motivo_para_omitir(self.inacap, dias=7))

    def test_lote_con_carga_reciente_omite(self):
        crear_lote(self.inacap, 'COMPLETADO', horas_atras=3 * 24)
        self.assertIn('menos de 7 días', motivo_para_omitir(self.inacap, dias=7))
        # Un lote PARCIAL también cargó datos
        crear_lote(self.duoc, 'PARCIAL', horas_atras=2 * 24)
        self.assertIsNotNone(motivo_para_omitir(self.duoc, dias=7))

    def test_catalogo_vencido_se_ejecuta(self):
        crear_lote(self.inacap, 'COMPLETADO', horas_atras=8 * 24)
        self.assertIsNone(motivo_para_omitir(self.inacap, dias=7))

    def test_un_intento_fallido_reciente_espera_24_horas(self):
        crear_lote(self.inacap, 'COMPLETADO', horas_atras=10 * 24)
        crear_lote(self.inacap, 'ERROR', horas_atras=5)
        self.assertIn('últimas 24 horas', motivo_para_omitir(self.inacap, dias=7))
        LoteScrapingS3.objects.filter(estado_etl='ERROR').update(fecha_extraccion=timezone.now() - timedelta(hours=25))
        self.assertIsNone(motivo_para_omitir(self.inacap, dias=7))

    def test_no_mira_lotes_de_otra_institucion(self):
        crear_lote(self.duoc, 'COMPLETADO', horas_atras=1)
        self.assertIsNone(motivo_para_omitir(self.inacap, dias=7))


@override_settings(ADMINS=['alertas@mi-ayudante.cl'])
class ComandoDuocTests(TestCase):
    """El comando sale con error (código 1 en cron) y avisa cuando rechaza el lote."""

    def setUp(self):
        self.respaldo = mock.patch.object(run_duoc_scraper.Command, 'respaldar_en_s3', return_value=None)
        self.respaldo.start()
        self.addCleanup(self.respaldo.stop)

    def test_lote_rechazado_sale_con_error_y_avisa(self):
        with mock.patch.object(run_duoc_scraper.Command, 'extraer', return_value=[]):
            with self.assertRaisesMessage(CommandError, 'posible cambio en el sitio'):
                call_command('run_duoc_scraper', stdout=mock.Mock())
        lote = LoteScrapingS3.objects.get()
        self.assertEqual(lote.estado_etl, 'ERROR')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ERROR', mail.outbox[0].subject)

    def test_si_desactualizado_no_extrae_con_catalogo_al_dia(self):
        institucion = Institucion.objects.create(codigo='DUOC', nombre='Duoc UC')
        crear_lote(institucion, 'COMPLETADO', horas_atras=24)
        with mock.patch.object(run_duoc_scraper.Command, 'extraer') as extraer:
            call_command('run_duoc_scraper', si_desactualizado=7, stdout=mock.Mock())
        extraer.assert_not_called()
        self.assertEqual(LoteScrapingS3.objects.count(), 1)
        self.assertEqual(mail.outbox, [])


class ClaveMallaTests(SimpleTestCase):
    def test_carreras_con_el_mismo_nombre_no_se_pisan(self):
        a = clave_malla('https://portal.inacap.cl/carreras/area-informatica/analista-programador', 'Analista Programador')
        b = clave_malla('https://portal.inacap.cl/carreras/area-informatica/analista-programador-online/', 'Analista Programador')
        self.assertNotEqual(a, b)
        self.assertEqual(a, 'analista_programador')

    def test_sin_url_usa_el_nombre_sin_tildes(self):
        self.assertEqual(clave_malla('', 'Ingeniería en Informática'), 'ingenieria_en_informatica')
        self.assertEqual(clave_malla('', ''), 'sin_nombre')
