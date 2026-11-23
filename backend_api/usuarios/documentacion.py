"""Esquemas OpenAPI de autenticación, doble factor y derechos del titular (Swagger en /api/v1/docs/).

Las vistas son APIView sin serializer: drf-spectacular no podía deducir sus entradas ni salidas y las omitía.
"""
from drf_spectacular.utils import OpenApiResponse, PolymorphicProxySerializer, extend_schema, inline_serializer
from rest_framework import serializers

ETIQUETA_AUTH = 'Autenticación'
ETIQUETA_2FA = 'Doble factor (TOTP)'
ETIQUETA_TITULAR = 'Derechos del titular (Ley N.° 21.719)'

Error = inline_serializer('Error', {'error': serializers.CharField()})
ErrorReiniciar = inline_serializer('ErrorReinicioLogin', {
    'error': serializers.CharField(),
    'reiniciar': serializers.BooleanField(help_text='true: hay que volver a pedir la contraseña'),
})
Usuario = inline_serializer('UsuarioResumen', {'correo': serializers.EmailField(), 'nombre': serializers.CharField()})
Sesion = inline_serializer('Sesion', {
    'access': serializers.CharField(help_text='JWT de acceso (1 hora)'),
    'refresh': serializers.CharField(help_text='JWT de refresco (1 día)'),
    'usuario': Usuario,
    'consentimiento_vigente': serializers.BooleanField(help_text='false: debe aceptar la versión vigente de la política'),
})
Requiere2fa = inline_serializer('LoginRequiereDobleFactor', {
    'requiere_2fa': serializers.BooleanField(),
    'token_temporal': serializers.CharField(help_text='Se canjea en /api/v1/auth/2fa/verificar/ (5 minutos)'),
})
Codigo = inline_serializer('CodigoDobleFactor', {
    'codigo': serializers.CharField(help_text='Código de 6 dígitos de la app o código de recuperación'),
})

REGISTRO = extend_schema(
    tags=[ETIQUETA_AUTH], summary='Crear una cuenta', operation_id='auth_registro',
    request=inline_serializer('Registro', {
        'correo': serializers.EmailField(), 'nombre': serializers.CharField(), 'apellidos': serializers.CharField(),
        'password': serializers.CharField(),
        'acepta_privacidad': serializers.BooleanField(help_text='Consentimiento expreso (Ley N.° 21.719)'),
        'mayor_14': serializers.BooleanField(help_text='Declara tener 14 años o más'),
    }),
    responses={201: inline_serializer('RegistroCreado', {'usuario': Usuario}), 400: Error,
               409: OpenApiResponse(Error, description='El correo ya está registrado'),
               429: OpenApiResponse(description='Demasiados intentos (20 por minuto)')},
)
LOGIN = extend_schema(
    tags=[ETIQUETA_AUTH], summary='Iniciar sesión', operation_id='auth_login',
    request=inline_serializer('Login', {'correo': serializers.EmailField(), 'password': serializers.CharField()}),
    responses={200: OpenApiResponse(
                   PolymorphicProxySerializer(component_name='RespuestaLogin', serializers=[Sesion, Requiere2fa],
                                              resource_type_field_name=None),
                   description='Sesión iniciada, o token temporal si la cuenta tiene doble factor activo'),
               401: Error, 429: OpenApiResponse(description='Demasiados intentos (20 por minuto)')},
)
LOGOUT = extend_schema(
    tags=[ETIQUETA_AUTH], summary='Cerrar sesión y revocar los JWT', operation_id='auth_logout',
    description='El token de refresco pasa a la lista negra y el de acceso (cabecera Authorization) deja de servir '
                'de inmediato. Funciona aunque el token de acceso ya haya vencido.',
    request=inline_serializer('Logout', {'refresh': serializers.CharField(required=False)}),
    responses={200: inline_serializer('SesionCerrada', {'sesion_cerrada': serializers.BooleanField()}),
               400: OpenApiResponse(Error, description='Los dos tokens son de cuentas distintas')},
)
VERIFICAR_2FA = extend_schema(
    tags=[ETIQUETA_2FA], summary='Segundo paso del login: canjear el código por el JWT', operation_id='auth_2fa_verificar',
    request=inline_serializer('Verificar2fa', {
        'token_temporal': serializers.CharField(),
        'codigo': serializers.CharField(help_text='Código de 6 dígitos (un solo uso) o código de recuperación'),
    }),
    responses={200: Sesion, 401: ErrorReiniciar, 429: OpenApiResponse(description='Más de 5 intentos por minuto')},
)
ACTIVAR_2FA = extend_schema(
    tags=[ETIQUETA_2FA], summary='Generar el secreto y el QR', operation_id='auth_2fa_activar', request=None,
    responses={200: inline_serializer('Activar2fa', {
        'otpauth_uri': serializers.CharField(), 'qr_png_base64': serializers.CharField(),
        'secreto': serializers.CharField(help_text='Para escribirlo a mano si la app no lee el QR'),
    }), 409: Error},
)
CONFIRMAR_2FA = extend_schema(
    tags=[ETIQUETA_2FA], summary='Confirmar la activación con el primer código', operation_id='auth_2fa_confirmar',
    request=Codigo,
    responses={200: inline_serializer('Confirmar2fa', {
        'activo': serializers.BooleanField(),
        'codigos_recuperacion': serializers.ListField(child=serializers.CharField(), help_text='Se muestran solo una vez'),
    }), 400: Error, 409: Error},
)
DESACTIVAR_2FA = extend_schema(
    tags=[ETIQUETA_2FA], summary='Desactivar el doble factor', operation_id='auth_2fa_desactivar', request=Codigo,
    responses={200: inline_serializer('Desactivar2fa', {'activo': serializers.BooleanField()}), 400: Error},
)
PERFIL_GET = extend_schema(
    tags=[ETIQUETA_AUTH], summary='Perfil del usuario', operation_id='auth_perfil',
    responses={200: inline_serializer('Perfil', {
        'usuario': Usuario, 'consentimiento_vigente': serializers.BooleanField(),
        'doble_factor_activo': serializers.BooleanField(),
    })},
)
PERFIL_PATCH = extend_schema(
    tags=[ETIQUETA_TITULAR], summary='Rectificar nombre y apellidos', operation_id='auth_perfil_rectificar',
    request=inline_serializer('Rectificacion', {
        'nombre': serializers.CharField(required=False), 'apellidos': serializers.CharField(required=False),
    }),
    responses={200: inline_serializer('PerfilRectificado', {'usuario': Usuario}), 400: Error},
)
CONSENTIMIENTO = extend_schema(
    tags=[ETIQUETA_TITULAR], summary='Aceptar la versión vigente de la política', operation_id='auth_consentimiento',
    request=inline_serializer('Consentimiento', {
        'acepta_privacidad': serializers.BooleanField(), 'mayor_14': serializers.BooleanField(),
    }),
    responses={201: inline_serializer('ConsentimientoVigente', {
        'consentimiento_vigente': serializers.BooleanField(), 'version_politica': serializers.CharField(),
    }), 400: Error},
)
MIS_DATOS = extend_schema(
    tags=[ETIQUETA_TITULAR], summary='Descargar mis datos (acceso y portabilidad)', operation_id='auth_mis_datos',
    responses={200: inline_serializer('MisDatos', {
        'generado_en': serializers.DateTimeField(), 'responsable': serializers.CharField(),
        'cuenta': serializers.DictField(), 'consentimientos': serializers.ListField(child=serializers.DictField()),
        'resultados_test': serializers.ListField(child=serializers.DictField()),
        'doble_factor': serializers.DictField(), 'no_almacenado': serializers.CharField(),
    })},
)
CUENTA = extend_schema(
    tags=[ETIQUETA_TITULAR], summary='Eliminar la cuenta y todos sus datos (supresión)', operation_id='auth_cuenta_eliminar',
    request=inline_serializer('EliminarCuenta', {'password': serializers.CharField()}),
    responses={204: OpenApiResponse(description='Cuenta eliminada'), 403: Error},
)
BORRAR_RESULTADO = extend_schema(
    tags=[ETIQUETA_TITULAR], summary='Borrar un resultado del test', operation_id='auth_resultado_borrar',
    responses={204: OpenApiResponse(description='Resultado borrado'), 404: Error},
)

