from decimal import Decimal

from scraper.test_api import ApiCatalogoTests


class ApiCarrerasTests(ApiCatalogoTests):
    def test_una_fila_por_carrera(self):
        datos = self.cliente.get('/api/v1/carreras/').data
        self.assertEqual(datos['count'], 2)
        diseno = next(c for c in datos['results'] if c['carrera'] == 'Diseño Gráfico')
        self.assertEqual(diseno['total_ofertas'], 2)
        self.assertEqual(diseno['total_sedes'], 2)
        self.assertEqual(diseno['modalidades'], ['Online', 'Presencial'])
        self.assertEqual(diseno['arancel_desde'], {'monto': 306000, 'periodo': 'mensual', 'calculado': False})
        self.assertEqual(diseno['duracion_texto'], '8 semestres')
        self.assertEqual(diseno['duracion_meses'], {'min': 48, 'max': 48})

    def test_filtros_se_aplican_a_las_ofertas(self):
        datos = self.cliente.get('/api/v1/carreras/?modalidad=presencial&institucion=duoc').data
        self.assertEqual(datos['count'], 1)
        self.assertEqual(datos['results'][0]['total_ofertas'], 1)
        self.assertEqual(datos['results'][0]['sedes'], ['Maipú'])
        self.assertEqual(self.cliente.get('/api/v1/carreras/?region=Región Metropolitana').data['count'], 2)

    def test_detalle_con_ofertas(self):
        carrera_id = self.mensual.carrera_id
        datos = self.cliente.get(f'/api/v1/carreras/{carrera_id}/').data
        self.assertEqual(len(datos['ofertas']), 2)
        self.assertEqual(self.cliente.get('/api/v1/carreras/999999/').status_code, 404)

    def test_ofertas_de_una_carrera(self):
        carrera_id = self.mensual.carrera_id
        self.assertEqual(sorted(self.ids(f'/api/v1/ofertas/?carrera_id={carrera_id}')), sorted([self.mensual.id, self.online.id]))

    def test_aranceles_calculados_desde_la_cuota_mensual(self):
        # Como los carga el scraper de Duoc: cuota mensual publicada y semestral/anual calculados con 5 cuotas
        self.online.arancel_semestral_clp = Decimal('1530000')
        self.online.arancel_anual_clp = Decimal('3060000')
        self.online.aranceles_calculados = True
        self.online.matricula_periodo = 'semestral'
        self.online.duracion_texto, self.online.duracion_meses = '16 bimestres', 32
        self.online.save()

        oferta = next(o for o in self.cliente.get('/api/v1/ofertas/?institucion=duoc').data['results']
                      if o['id'] == self.online.id)
        self.assertEqual(oferta['arancel_referencia'], {'monto': 3060000, 'periodo': 'anual', 'calculado': True})
        self.assertEqual(oferta['arancel_publicado'], {'monto': 306000, 'periodo': 'mensual'})
        self.assertEqual(oferta['matricula_periodo'], 'semestral')
        self.assertEqual((oferta['duracion_texto'], oferta['duracion_meses']), ('16 bimestres', 32))

        diseno = self.cliente.get(f'/api/v1/carreras/{self.online.carrera_id}/').data
        self.assertEqual(diseno['arancel_desde'], {'monto': 3060000, 'periodo': 'anual', 'calculado': True})
        self.assertEqual(diseno['duracion_meses'], {'min': 32, 'max': 32})

    def test_inacap_publicado_es_semestral(self):
        oferta = next(o for o in self.cliente.get('/api/v1/ofertas/?institucion=inacap').data['results'])
        self.assertEqual(oferta['arancel_referencia'], {'monto': 3256000, 'periodo': 'anual', 'calculado': False})
        self.assertEqual(oferta['arancel_publicado'], {'monto': 1628000, 'periodo': 'semestral'})
