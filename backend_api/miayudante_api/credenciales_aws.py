"""De dónde salen las credenciales de AWS (S3 del ETL y django-storages).

En la EC2 se usa el rol de la instancia (LabInstanceProfile): boto3 obtiene credenciales temporales que se
renuevan solas. El problema era que el .env traía AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_SESSION_TOKEN
copiadas de una sesión del Learner Lab: caducan a las pocas horas y, como boto3 prefiere las variables de
entorno (load_dotenv las copia a os.environ) antes que el rol, el ETL dejaba de poder subir a S3.

Con AWS_USAR_ROL_INSTANCIA=True (el deploy lo escribe en el .env de la EC2) esas claves se ignoran y se
quitan del entorno del proceso, junto con los archivos ~/.aws/credentials y ~/.aws/config, para que boto3
llegue siempre al rol. Sin la variable (desarrollo local) se usan las claves del .env como antes.
"""
import os

CLAVES_ESTATICAS = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')


def configurar_credenciales_aws(entorno=None):
    """Devuelve {clave: valor o None} para settings y limpia el entorno si se usa el rol de la instancia."""
    entorno = os.environ if entorno is None else entorno
    if entorno.get('AWS_USAR_ROL_INSTANCIA', '').strip() == 'True':
        for clave in CLAVES_ESTATICAS:
            entorno.pop(clave, None)
        # Un "aws configure" hecho a mano en la EC2 también ganaría al rol en la cadena de boto3
        entorno['AWS_SHARED_CREDENTIALS_FILE'] = os.devnull
        entorno['AWS_CONFIG_FILE'] = os.devnull
        return {clave: None for clave in CLAVES_ESTATICAS}
    return {clave: (entorno.get(clave) or None) for clave in CLAVES_ESTATICAS}
