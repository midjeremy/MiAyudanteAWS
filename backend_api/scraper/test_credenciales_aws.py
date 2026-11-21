"""Credenciales de AWS: en la EC2 se usa el rol de la instancia aunque el .env traiga claves del Learner Lab."""
import os
from unittest import mock

import boto3
from django.test import SimpleTestCase

from miayudante_api.credenciales_aws import CLAVES_ESTATICAS, configurar_credenciales_aws

CLAVES_DEL_LAB = {
    'AWS_ACCESS_KEY_ID': 'ASIAVENCIDA',
    'AWS_SECRET_ACCESS_KEY': 'secreta-vencida',
    'AWS_SESSION_TOKEN': 'token-vencido',
}


class CredencialesAwsTests(SimpleTestCase):
    def test_con_rol_de_instancia_ignora_y_quita_las_claves_del_env(self):
        entorno = {**CLAVES_DEL_LAB, 'AWS_USAR_ROL_INSTANCIA': 'True'}
        credenciales = configurar_credenciales_aws(entorno)
        self.assertEqual(credenciales, {clave: None for clave in CLAVES_ESTATICAS})
        for clave in CLAVES_ESTATICAS:
            self.assertNotIn(clave, entorno)
        # Tampoco vale un ~/.aws/credentials hecho a mano
        self.assertEqual(entorno['AWS_SHARED_CREDENTIALS_FILE'], os.devnull)
        self.assertEqual(entorno['AWS_CONFIG_FILE'], os.devnull)

    def test_sin_la_variable_usa_las_claves_del_env_como_antes(self):
        entorno = dict(CLAVES_DEL_LAB)
        self.assertEqual(configurar_credenciales_aws(entorno), CLAVES_DEL_LAB)
        self.assertEqual(entorno, CLAVES_DEL_LAB)

    def test_claves_vacias_quedan_en_none(self):
        self.assertEqual(configurar_credenciales_aws({'AWS_ACCESS_KEY_ID': ''})['AWS_ACCESS_KEY_ID'], None)

    def test_boto3_ya_no_ve_las_claves_vencidas(self):
        """Lo que importaba: boto3 lee os.environ, no settings, y prefería esas claves antes que el rol."""
        with mock.patch.dict(os.environ, {**CLAVES_DEL_LAB, 'AWS_USAR_ROL_INSTANCIA': 'True'}):
            configurar_credenciales_aws()
            credenciales = boto3.session.Session().get_credentials()
            self.assertTrue(credenciales is None or credenciales.access_key != 'ASIAVENCIDA')
