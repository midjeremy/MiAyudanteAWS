"""Doble factor con app autenticadora (TOTP): secretos, códigos, QR y token temporal del login."""
import base64
import io
import re
import secrets
import time

import pyotp
import qrcode
from django.core import signing
from django.db.models import Q
from django.utils.crypto import constant_time_compare, salted_hmac
from qrcode.image.pure import PyPNGImage

from .models import SegundoFactor

EMISOR = 'Mi Ayudante'
VIGENCIA_TOKEN_TEMPORAL = 5 * 60  # segundos
CANTIDAD_CODIGOS_RECUPERACION = 8

_SAL_TOKEN = 'usuarios.doble_factor.token_temporal'
_SAL_RECUPERACION = 'usuarios.doble_factor.codigo_recuperacion'


class TokenInvalido(Exception):
    pass


class TokenVencido(TokenInvalido):
    pass


def crear_token_temporal(usuario):
    """Token firmado con el id del usuario: prueba que ya dio la contraseña correcta hace menos de 5 minutos."""
    return signing.TimestampSigner(salt=_SAL_TOKEN).sign(str(usuario.pk))


def leer_token_temporal(token):
    """Devuelve el id del usuario. Lanza TokenVencido o TokenInvalido."""
    if not isinstance(token, str) or not token:
        raise TokenInvalido()
    try:
        valor = signing.TimestampSigner(salt=_SAL_TOKEN).unsign(token, max_age=VIGENCIA_TOKEN_TEMPORAL)
    except signing.SignatureExpired as e:
        raise TokenVencido() from e
    except signing.BadSignature as e:
        raise TokenInvalido() from e
    if not valor.isdigit():
        raise TokenInvalido()
    return int(valor)


def nuevo_secreto():
    return pyotp.random_base32()


def uri_aprovisionamiento(secreto, usuario):
    return pyotp.TOTP(secreto).provisioning_uri(name=usuario.email or usuario.get_username(), issuer_name=EMISOR)


def qr_png_base64(uri):
    """QR en PNG (base64) generado con pypng, sin depender de Pillow."""
    imagen = qrcode.make(uri, image_factory=PyPNGImage, box_size=6, border=2)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def _normalizar(codigo):
    """Quita espacios y guiones: '123 456' y 'ab12c-d34ef' se aceptan igual que '123456' y 'ab12cd34ef'."""
    if not isinstance(codigo, (str, int)):
        return ''
    return re.sub(r'[\s-]', '', str(codigo)).lower()


def nuevos_codigos_recuperacion():
    """Códigos de un solo uso, 10 caracteres hexadecimales (40 bits) con un guion al medio para leerlos mejor."""
    codigos = []
    for _ in range(CANTIDAD_CODIGOS_RECUPERACION):
        crudo = secrets.token_hex(5)
        codigos.append(f'{crudo[:5]}-{crudo[5:]}')
    return codigos


def hash_codigo(codigo):
    # HMAC con la SECRET_KEY: los códigos son aleatorios (no hace falta un hash lento como el de las
    # contraseñas) y una copia filtrada de la base de datos no basta para probarlos fuera de línea.
    return salted_hmac(_SAL_RECUPERACION, _normalizar(codigo), algorithm='sha256').hexdigest()


def _ahora():
    return time.time()


def paso_del_codigo(secreto, codigo, ahora=None):
    """Paso de 30 s (RFC 6238) al que corresponde el código, aceptando el anterior y el siguiente; None si no vale."""
    totp = pyotp.TOTP(secreto)
    actual = int((_ahora() if ahora is None else ahora) // totp.interval)
    for paso in (actual - 1, actual, actual + 1):
        if constant_time_compare(totp.generate_otp(paso), codigo):
            return paso
    return None


def usar_paso_totp(segundo_factor, paso):
    """Marca el paso como usado. False si ya se usó ese paso o uno posterior (código repetido).

    La comparación y la escritura van en un solo UPDATE condicional: dos peticiones simultáneas con el mismo código
    no pueden aceptarse las dos.
    """
    actualizados = (SegundoFactor.objects.filter(pk=segundo_factor.pk)
                    .filter(Q(ultimo_paso_totp__isnull=True) | Q(ultimo_paso_totp__lt=paso))
                    .update(ultimo_paso_totp=paso))
    if actualizados:
        segundo_factor.ultimo_paso_totp = paso
    return bool(actualizados)


def verificar_codigo(segundo_factor, codigo, permitir_recuperacion=False):
    """True si el código es un TOTP vigente (±30 s) y sin usar o, si se permite, un código de recuperación sin usar.

    Ambos son de un solo uso: un TOTP aceptado no vuelve a servir aunque siga dentro de su ventana (RFC 6238,
    sección 5.2), y un código de recuperación correcto se elimina de inmediato.
    """
    codigo = _normalizar(codigo)
    if not codigo:
        return False
    if re.fullmatch(r'\d{6}', codigo):
        paso = paso_del_codigo(segundo_factor.secreto, codigo)
        return paso is not None and usar_paso_totp(segundo_factor, paso)
    if not permitir_recuperacion:
        return False
    buscado = hash_codigo(codigo)
    for guardado in segundo_factor.codigos_recuperacion:
        if constant_time_compare(guardado, buscado):
            segundo_factor.codigos_recuperacion = [h for h in segundo_factor.codigos_recuperacion if h != guardado]
            segundo_factor.save(update_fields=['codigos_recuperacion'])
            return True
    return False
