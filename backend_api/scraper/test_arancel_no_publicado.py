"""Arancel no publicado por la institución: se guarda NULL (no $0), se registra en el lote y se avisa si son muchos."""
import importlib

from django.apps import apps
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from scraper.etl import UMBRAL_SIN_ARANCEL, monto_publicado, revisar_aranceles
from scraper.management.commands.run_inacap_scraper import Command as ScraperInacap
from scraper.models import Carrera, Institucion, Jornada, LoteScrapingS3, OfertaAcademica, Sede


class MontoPublicadoTests(SimpleTestCase):
    def test_vacio_o_cero_no_es_un_precio(self):
        for valor in ('', '   ', '$0', '0', None, 0, '-'):
            self.assertIsNone(monto_publicado(valor), valor)

    def test_montos_publicados(self):
        self.assertEqual(monto_publicado('$161.000'), 161000)
        self.assertEqual(monto_publicado(2221000), 2221000)

    def test_scraper_de_inacap(self):
        scraper = ScraperInacap()
        self.assertIsNone(scraper.limpiar_dinero(''))  # celda vacía en la tabla de aranceles
        self.assertEqual(scraper.limpiar_dinero('$ 2.221.000'), 2221000)


@override_settings(ADMINS=[('Alertas', 'alertas@mi-ayudante.cl')])
class RevisarArancelesTests(TestCase):
    def setUp(self):
        self.inacap = Institucion.objects.create(nombre='INACAP', codigo='INACAP')
        self.lote = LoteScrapingS3.objects.create(institucion=self.inacap, estado_etl='COMPLETADO')
        self.carrera = Carrera.objects.create(nombre_carrera='Administración Gastronómica', institucion=self.inacap)
        self.diurna = Jornada.objects.create(tipo_jornada='Diurna')

    def oferta(self, sede, semestral):
        return OfertaAcademica.objects.create(
            institucion=self.inacap, carrera=self.carrera, jornada=self.diurna, lote_scraping=self.lote,
            sede=Sede.objects.create(nombre_sede=sede, institucion=self.inacap),
            matricula_clp=161000 if semestral else None, arancel_semestral_clp=semestral,
            arancel_anual_clp=semestral * 2 if semestral else None,
        )

    def test_pocas_ofertas_sin_arancel_quedan_en_el_lote_sin_correo(self):
        for i in range(30):
            self.oferta(f'Sede {i}', 2221000)
        self.oferta('La Serena', None)
        faltantes = revisar_aranceles(self.lote)
        self.assertEqual(faltantes, ['Administración Gastronómica – La Serena – Diurna'])
        self.lote.refresh_from_db()
        self.assertIn('1 de 31 ofertas sin arancel', self.lote.detalle_errores)
        self.assertIn('La Serena', self.lote.detalle_errores)
        self.assertEqual(self.lote.estado_etl, 'COMPLETADO')  # no es un error del scraper
        self.assertEqual(len(mail.outbox), 0)

    def test_muchas_ofertas_sin_arancel_avisan_por_correo(self):
        self.oferta('Apoquindo', 2221000)
        for sede in ('La Serena', 'Temuco'):
            self.oferta(sede, None)
        self.assertGreater(2 / 3, UMBRAL_SIN_ARANCEL)
        revisar_aranceles(self.lote)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('2 ofertas sin arancel', mail.outbox[0].subject)
        self.assertIn('Temuco', mail.outbox[0].body)

    def test_sin_faltantes_no_toca_el_lote(self):
        self.oferta('Apoquindo', 2221000)
        self.assertEqual(revisar_aranceles(self.lote), [])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.detalle_errores, '')

    def test_la_carrera_ya_no_muestra_arancel_desde_cero(self):
        self.oferta('Apoquindo', 2221000)
        self.oferta('La Serena', None)
        datos = self.client.get(reverse('api_carrera_detalle', args=[self.carrera.id])).json()
        self.assertEqual(datos['arancel_desde']['monto'], 4442000)
        serena = next(o for o in datos['ofertas'] if o['sede'] == 'La Serena')
        self.assertIsNone(serena['arancel_referencia'])  # el frontend muestra «Sin información»

    def test_la_migracion_pasa_los_ceros_a_nulo(self):
        oferta = self.oferta('La Serena', 2221000)
        OfertaAcademica.objects.filter(pk=oferta.pk).update(matricula_clp=0, arancel_semestral_clp=0, arancel_anual_clp=0)
        migracion = importlib.import_module('scraper.migrations.0013_montos_cero_a_nulo')
        migracion.ceros_a_nulo(apps, None)
        oferta.refresh_from_db()
        self.assertIsNone(oferta.matricula_clp)
        self.assertIsNone(oferta.arancel_semestral_clp)
        self.assertIsNone(oferta.arancel_anual_clp)
