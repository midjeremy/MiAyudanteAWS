"""Mallas en PDF: impresión de las mallas web de Duoc UC, descarga pública y admin con menciones."""
import http.server
import os
import threading
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from scraper.mallas_pdf import clave_pdf, es_pdf, generar_mallas_pdf, pagina_a_pdf, ruta_chrome
from scraper.models import Carrera, Institucion, Mencion

URL_INFORMATICA = 'https://malla.duoc.cl/mallas/informatica/automatizacion.html'
URL_BIG_DATA = 'https://malla.duoc.cl/mallas/informatica/big-data.html'


def pdf_falso(url):
    return b'%PDF-1.4 ' + url.encode()


class ClavesTests(TestCase):
    def test_clave_sale_de_la_url(self):
        self.assertEqual(clave_pdf(URL_INFORMATICA), 'mallas/duoc/pdf/mallas-informatica-automatizacion.pdf')

    def test_es_pdf(self):
        self.assertTrue(es_pdf('https://www.inacap.cl/malla/x.PDF?v=2'))
        self.assertFalse(es_pdf(URL_INFORMATICA))
        self.assertFalse(es_pdf(None))

    def test_solo_imprime_http(self):
        with self.assertRaises(ValueError):
            pagina_a_pdf('file:///etc/passwd', chrome='/bin/true')


class GenerarMallasTests(TestCase):
    def setUp(self):
        self.duoc = Institucion.objects.create(nombre='Duoc UC', codigo='DUOC')
        self.informatica = Carrera.objects.create(
            nombre_carrera='Ingeniería en Informática', institucion=self.duoc, url_malla=URL_INFORMATICA,
        )
        self.automatizacion = Mencion.objects.create(
            carrera=self.informatica, nombre='Automatización', url_malla=URL_INFORMATICA,
        )
        self.big_data = Mencion.objects.create(carrera=self.informatica, nombre='Big Data', url_malla=URL_BIG_DATA)
        self.s3 = mock.Mock()

    def generar(self, **opciones):
        return generar_mallas_pdf(self.s3, 'bucket', self.duoc, imprimir=pdf_falso, avisar=lambda _: None, **opciones)

    def test_imprime_cada_malla_una_vez_y_guarda_la_clave(self):
        subidas, fallidas = self.generar()
        self.assertEqual((subidas, fallidas), (2, []))
        self.assertEqual(self.s3.put_object.call_count, 2)
        self.informatica.refresh_from_db()
        self.automatizacion.refresh_from_db()
        self.big_data.refresh_from_db()
        self.assertEqual(self.informatica.s3_url_malla_pdf, clave_pdf(URL_INFORMATICA))
        self.assertEqual(self.automatizacion.s3_malla_pdf, clave_pdf(URL_INFORMATICA))
        self.assertEqual(self.big_data.s3_malla_pdf, clave_pdf(URL_BIG_DATA))

    def test_sin_forzar_no_repite_y_si_cambia_la_url_vuelve_a_imprimir(self):
        self.generar()
        self.s3.reset_mock()
        self.assertEqual(self.generar(), (0, []))
        self.big_data.url_malla = 'https://malla.duoc.cl/mallas/informatica/big-data-2027.html'
        self.big_data.save()
        self.assertEqual(self.generar(), (1, []))
        self.assertEqual(self.generar(forzar=True), (2, []))  # 2 URLs distintas

    def test_una_malla_caida_no_detiene_las_demas(self):
        def imprimir(url):
            if url == URL_BIG_DATA:
                raise RuntimeError('timeout')
            return pdf_falso(url)

        subidas, fallidas = generar_mallas_pdf(self.s3, 'b', self.duoc, imprimir=imprimir, avisar=lambda _: None)
        self.assertEqual(subidas, 1)
        self.assertEqual(len(fallidas), 1)
        self.big_data.refresh_from_db()
        self.assertEqual(self.big_data.s3_malla_pdf, '')

    def test_las_mallas_que_ya_son_pdf_no_se_imprimen(self):
        inacap = Institucion.objects.create(nombre='INACAP', codigo='INACAP')
        Carrera.objects.create(nombre_carrera='Mecánica', institucion=inacap, url_malla='https://inacap.cl/m.pdf')
        self.assertEqual(generar_mallas_pdf(self.s3, 'b', inacap, imprimir=pdf_falso, avisar=print), (0, []))

    def test_limite(self):
        self.assertEqual(self.generar(limite=1)[0], 1)


class ChromeTests(TestCase):
    def test_imprime_una_pagina_real(self):
        chrome = ruta_chrome() or os.environ.get('CHROME_PRUEBAS', '')
        if not chrome or not os.path.exists(chrome):
            self.skipTest('Sin Chrome en este equipo')
        # Solo se imprimen URLs http(s): un servidor local mínimo hace de malla.duoc.cl
        servidor = http.server.HTTPServer(('127.0.0.1', 0), _PaginaMalla)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        try:
            contenido = pagina_a_pdf(f'http://127.0.0.1:{servidor.server_port}/malla.html', chrome=chrome, espera_ms=500)
        finally:
            servidor.shutdown()
        self.assertTrue(contenido.startswith(b'%PDF'))


class _PaginaMalla(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('<h1>Malla</h1><p>Semestre 1: Programación</p>'.encode())

    def log_message(self, *args):
        pass


class DescargaMallaTests(TestCase):
    def setUp(self):
        cache.clear()
        duoc = Institucion.objects.create(nombre='Duoc UC', codigo='DUOC')
        self.carrera = Carrera.objects.create(
            nombre_carrera='Ingeniería en Informática', nombre_base='Ingeniería en Informática', institucion=duoc,
            url_malla=URL_INFORMATICA, s3_url_malla_pdf='mallas/duoc/pdf/a.pdf',
        )
        self.mencion = Mencion.objects.create(
            carrera=self.carrera, nombre='Big Data', url_malla=URL_BIG_DATA, s3_malla_pdf='mallas/duoc/pdf/b.pdf',
        )
        self.sin_malla = Mencion.objects.create(carrera=self.carrera, nombre='Ciberseguridad')

    @mock.patch('scraper.api_mallas.crear_cliente_s3')
    def test_redirige_a_un_enlace_prefirmado_de_descarga(self, crear):
        crear.return_value.generate_presigned_url.return_value = 'https://s3.example/a.pdf?firma'
        respuesta = self.client.get(reverse('api_carrera_malla_pdf', args=[self.carrera.id]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta['Location'], 'https://s3.example/a.pdf?firma')
        _, kwargs = crear.return_value.generate_presigned_url.call_args
        self.assertEqual(kwargs['Params']['Key'], 'mallas/duoc/pdf/a.pdf')
        self.assertIn('attachment', kwargs['Params']['ResponseContentDisposition'])
        self.assertLessEqual(kwargs['ExpiresIn'], 300)

    @mock.patch('scraper.api_mallas.crear_cliente_s3')
    def test_mencion_con_malla_propia(self, crear):
        crear.return_value.generate_presigned_url.return_value = 'https://s3.example/b.pdf'
        url = reverse('api_mencion_malla_pdf', args=[self.carrera.id, self.mencion.id])
        self.assertEqual(self.client.get(url).status_code, 302)
        _, kwargs = crear.return_value.generate_presigned_url.call_args
        self.assertEqual(kwargs['Params']['Key'], 'mallas/duoc/pdf/b.pdf')
        self.assertIn('Big%20Data', kwargs['Params']['ResponseContentDisposition'])

    def test_sin_pdf_responde_404(self):
        url = reverse('api_mencion_malla_pdf', args=[self.carrera.id, self.sin_malla.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        otra = Carrera.objects.create(nombre_carrera='Otra')
        self.assertEqual(self.client.get(reverse('api_mencion_malla_pdf', args=[otra.id, self.mencion.id])).status_code, 404)

    def test_pdf_publicado_por_la_institucion_sin_copia_en_s3(self):
        carrera = Carrera.objects.create(nombre_carrera='Mecánica', url_malla='https://www.inacap.cl/m.pdf')
        respuesta = self.client.get(reverse('api_carrera_malla_pdf', args=[carrera.id]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta['Location'], 'https://www.inacap.cl/m.pdf')

    def test_la_api_de_carreras_entrega_malla_digital_y_pdf(self):
        datos = self.client.get(reverse('api_carrera_detalle', args=[self.carrera.id])).json()
        self.assertEqual(datos['malla_url'], URL_INFORMATICA)
        self.assertEqual(datos['malla_pdf_url'], f'/api/v1/carreras/{self.carrera.id}/malla.pdf')
        menciones = {m['nombre']: m for m in datos['menciones']}
        self.assertEqual(menciones['Big Data']['malla_url'], URL_BIG_DATA)
        self.assertEqual(menciones['Big Data']['malla_pdf_url'],
                         f'/api/v1/carreras/{self.carrera.id}/menciones/{self.mencion.id}/malla.pdf')
        self.assertIsNone(menciones['Ciberseguridad']['malla_pdf_url'])

    def test_la_api_de_ofertas_tambien(self):
        from scraper.models import Jornada, OfertaAcademica, Sede

        sede = Sede.objects.create(nombre_sede='San Joaquín', institucion=self.carrera.institucion)
        oferta = OfertaAcademica.objects.create(
            carrera=self.carrera, institucion=self.carrera.institucion, sede=sede,
            jornada=Jornada.objects.create(tipo_jornada='Diurna', modalidad='Presencial'),
        )
        datos = self.client.get(reverse('api_oferta_detalle', args=[oferta.id])).json()
        self.assertEqual(datos['malla_pdf_url'], f'/api/v1/carreras/{self.carrera.id}/malla.pdf')
        self.assertEqual(datos['mallas_menciones'], [{
            'nombre': 'Big Data', 'malla_url': URL_BIG_DATA,
            'malla_pdf_url': f'/api/v1/carreras/{self.carrera.id}/menciones/{self.mencion.id}/malla.pdf',
        }])


class AdminMencionesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser('admin', 'a@a.cl', 'x'))
        duoc = Institucion.objects.create(nombre='Duoc UC', codigo='DUOC')
        self.carrera = Carrera.objects.create(nombre_carrera='Ingeniería en Informática', institucion=duoc,
                                              url_malla=URL_INFORMATICA, s3_url_malla_pdf='mallas/duoc/pdf/a.pdf')
        Mencion.objects.create(carrera=self.carrera, nombre='Big Data')
        Mencion.objects.create(carrera=self.carrera, nombre='Ciberseguridad')
        Carrera.objects.create(nombre_carrera='Turismo', institucion=duoc)

    def test_lista_de_carreras_muestra_menciones_y_malla(self):
        html = self.client.get('/admin/scraper/carrera/').content.decode()
        self.assertIn('Big Data', html)
        self.assertIn('Ciberseguridad', html)
        self.assertIn(URL_INFORMATICA, html)
        self.assertIn(f'/api/v1/carreras/{self.carrera.id}/malla.pdf', html)

    def test_filtro_con_menciones(self):
        html = self.client.get('/admin/scraper/carrera/?con_menciones=si').content.decode()
        self.assertIn('Ingeniería en Informática', html)
        self.assertNotIn('Turismo', html)
        html = self.client.get('/admin/scraper/carrera/?con_menciones=no&con_pdf=no').content.decode()
        self.assertIn('Turismo', html)
        self.assertNotIn('Big Data', html)

    def test_busqueda_por_mencion_y_lista_de_menciones(self):
        html = self.client.get('/admin/scraper/carrera/?q=Big+Data').content.decode()
        self.assertIn('Ingeniería en Informática', html)
        self.assertNotIn('Turismo', html)
        respuesta = self.client.get('/admin/scraper/mencion/?q=ciber')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Ciberseguridad', respuesta.content.decode())
        self.assertEqual(self.client.get(f'/admin/scraper/carrera/{self.carrera.id}/change/').status_code, 200)
