from scraper.test_api import ApiCatalogoTests


class ApiCarrerasTests(ApiCatalogoTests):
    def test_una_fila_por_carrera(self):
        datos = self.cliente.get('/api/v1/carreras/').data
        self.assertEqual(datos['count'], 2)
        diseno = next(c for c in datos['results'] if c['carrera'] == 'Diseño Gráfico')
        self.assertEqual(diseno['total_ofertas'], 2)
        self.assertEqual(diseno['total_sedes'], 2)
        self.assertEqual(diseno['modalidades'], ['Online', 'Presencial'])
        self.assertEqual(diseno['arancel_desde'], {'monto': 306000, 'periodo': 'mensual'})

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
