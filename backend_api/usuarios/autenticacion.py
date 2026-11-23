"""Revocación de JWT al cerrar sesión (ISO/IEC 27002, control de acceso).

Un JWT de acceso es válido hasta que vence (1 hora): sin revocación, cerrar sesión no lo invalidaba. Al cerrar
sesión, el token de refresco pasa a la lista negra de simplejwt (tabla token_blacklist) y el identificador (jti) del
token de acceso se guarda en la caché compartida (PostgreSQL) hasta su vencimiento, por lo que deja de servir en todos
los workers de Gunicorn.
"""
import time

from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

PREFIJO = 'jwt_revocado:'


def revocar_acceso(token):
    """Invalida un token de acceso hasta su vencimiento."""
    jti, vence = token.get('jti'), token.get('exp')
    if not jti or not vence:
        return
    restante = int(vence - time.time()) + 1
    if restante > 0:
        cache.set(PREFIJO + str(jti), True, timeout=restante)


def acceso_revocado(token):
    return bool(token.get('jti')) and cache.get(PREFIJO + str(token['jti'])) is not None


class JWTConRevocacion(JWTAuthentication):
    """JWTAuthentication que además rechaza los tokens de acceso de una sesión cerrada."""

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if acceso_revocado(token):
            raise InvalidToken('La sesión fue cerrada. Inicia sesión de nuevo.')
        return token


try:  # Swagger: el mismo esquema Bearer JWT que simplejwt, para la clase propia
    from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme

    class JWTConRevocacionScheme(SimpleJWTScheme):
        target_class = 'usuarios.autenticacion.JWTConRevocacion'
except ImportError:  # pragma: no cover
    pass
