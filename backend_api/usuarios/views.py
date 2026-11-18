from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from Test_Ikigai.models import Resultado

from . import doble_factor
from .models import Consentimiento, SegundoFactor
from .privacidad import EDAD_MINIMA_CUENTA, VERSION_POLITICA

Usuario = get_user_model()

VALORES_ACEPTADOS = {'true', '1', 'on', 'si', 'sí'}


def datos_usuario(usuario):
    return {
        'correo': usuario.email,
        'nombre': f'{usuario.first_name} {usuario.last_name}'.strip(),
    }


def aceptado(valor):
    """Una casilla marcada llega como true (JSON) o como 'on'/'1' (formulario). Ausente = no aceptado."""
    if isinstance(valor, bool):
        return valor
    return isinstance(valor, (str, int)) and str(valor).strip().lower() in VALORES_ACEPTADOS


def doble_factor_activo(usuario):
    return SegundoFactor.objects.filter(usuario=usuario, activo=True).exists()


def consentimiento_vigente(usuario):
    """Ley 21.719: el consentimiento vale para la versión de la política que se aceptó."""
    return usuario.consentimientos.filter(version_politica=VERSION_POLITICA).exists()


class AuthThrottledView(APIView):
    """Limita los intentos por IP para frenar ataques de fuerza bruta."""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class RegistroView(AuthThrottledView):
    def post(self, request):
        correo = (request.data.get('correo') or '').strip().lower()
        nombre = (request.data.get('nombre') or '').strip()
        apellidos = (request.data.get('apellidos') or '').strip()
        password = request.data.get('password') or ''

        if not all([correo, nombre, apellidos, password]):
            return Response({'error': 'Completa todos los campos.'}, status=status.HTTP_400_BAD_REQUEST)
        # Ley 21.719: el consentimiento debe ser libre, informado y expreso. Se exige en la API, no solo
        # en el formulario, para que ninguna cuenta se cree sin él (ni llamando a la API directamente).
        if not aceptado(request.data.get('acepta_privacidad')):
            return Response({'error': 'Debes aceptar la política de privacidad para crear una cuenta.'},
                            status=status.HTTP_400_BAD_REQUEST)
        # Art. 16 quáter: bajo 14 años se requiere autorización de padres o representantes. Las cuentas
        # son solo para mayores de esa edad; los menores usan la plataforma sin cuenta.
        if not aceptado(request.data.get('mayor_14')):
            return Response({'error': f'Las cuentas son para personas de {EDAD_MINIMA_CUENTA} años o más. '
                                      'Puedes usar el buscador, el comparador, el test y el asistente sin cuenta.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(correo)
        except ValidationError:
            return Response({'error': 'Ingresa un correo válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if Usuario.objects.filter(username=correo).exists():
            return Response({'error': 'Este correo ya está registrado.'}, status=status.HTTP_409_CONFLICT)

        usuario = Usuario(username=correo, email=correo, first_name=nombre[:150], last_name=apellidos[:150])
        try:
            validate_password(password, usuario)
        except ValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(password)
        try:
            # La cuenta y la constancia del consentimiento se guardan juntas o no se guarda ninguna
            with transaction.atomic():
                usuario.save()
                Consentimiento.objects.create(usuario=usuario, version_politica=VERSION_POLITICA,
                                              declara_edad_minima=True)
        except IntegrityError:
            # Dos registros simultáneos con el mismo correo
            return Response({'error': 'Este correo ya está registrado.'}, status=status.HTTP_409_CONFLICT)
        return Response({'usuario': datos_usuario(usuario)}, status=status.HTTP_201_CREATED)


class LoginView(AuthThrottledView):
    def post(self, request):
        correo = (request.data.get('correo') or '').strip().lower()
        password = request.data.get('password') or ''

        usuario = authenticate(request, username=correo, password=password)
        if usuario is None:
            return Response({'error': 'Correo o contraseña incorrectos.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Con el doble factor activo, la contraseña sola no basta: no se entrega el JWT, sino un token
        # temporal (5 minutos) que se canjea en /2fa/verificar/ junto con el código de la app.
        if doble_factor_activo(usuario):
            return Response({'requiere_2fa': True, 'token_temporal': doble_factor.crear_token_temporal(usuario)})

        return respuesta_sesion(usuario)


def respuesta_sesion(usuario):
    """Entrega los tokens JWT. La usan el login y la verificación del doble factor."""
    # El login con JWT no pasa por django.contrib.auth.login(), así que last_login no se actualizaba
    # solo. Hace falta para el plazo de conservación: sin esto, purgar_cuentas_inactivas borraría
    # cuentas que sí se usan (Ley 21.719, proporcionalidad).
    update_last_login(None, usuario)
    token = RefreshToken.for_user(usuario)
    return Response({
        'access': str(token.access_token),
        'refresh': str(token),
        'usuario': datos_usuario(usuario),
        # Cuentas creadas antes de la política (o con una versión anterior) deben aceptarla
        'consentimiento_vigente': consentimiento_vigente(usuario),
    })


class DobleFactorThrottledView(APIView):
    """Los códigos de 6 dígitos se adivinan probando: se limitan a 5 intentos por minuto."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_2fa'


class VerificarDobleFactorView(DobleFactorThrottledView):
    """Segundo paso del login: canjea el token temporal y un código (TOTP o de recuperación) por el JWT."""
    permission_classes = [AllowAny]
    # Sin JWT todavía: no se intenta autenticar (un token vencido en la cabecera no debe dar 401)
    authentication_classes = []

    def post(self, request):
        datos = request.data if isinstance(request.data, dict) else {}
        codigo = datos.get('codigo')
        try:
            usuario_id = doble_factor.leer_token_temporal(datos.get('token_temporal'))
        except doble_factor.TokenVencido:
            # reiniciar: el frontend debe volver a pedir la contraseña (no sirve reintentar el código)
            return Response({'error': 'La verificación venció. Inicia sesión de nuevo.', 'reiniciar': True},
                            status=status.HTTP_401_UNAUTHORIZED)
        except doble_factor.TokenInvalido:
            return Response({'error': 'La verificación no es válida. Inicia sesión de nuevo.', 'reiniciar': True},
                            status=status.HTTP_401_UNAUTHORIZED)

        with transaction.atomic():
            # Bloquea la fila: dos peticiones simultáneas no pueden gastar el mismo código de recuperación
            segundo_factor = (SegundoFactor.objects.select_for_update().select_related('usuario')
                              .filter(usuario_id=usuario_id, activo=True, usuario__is_active=True).first())
            if segundo_factor is None:
                return Response({'error': 'La verificación no es válida. Inicia sesión de nuevo.', 'reiniciar': True},
                                status=status.HTTP_401_UNAUTHORIZED)
            if not doble_factor.verificar_codigo(segundo_factor, codigo, permitir_recuperacion=True):
                return Response({'error': 'El código no es correcto.'}, status=status.HTTP_401_UNAUTHORIZED)
        return respuesta_sesion(segundo_factor.usuario)


class ActivarDobleFactorView(APIView):
    """Paso 1 de la activación: genera el secreto y lo entrega como URI otpauth:// y como QR."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        existente = SegundoFactor.objects.filter(usuario=request.user).first()
        if existente is not None and existente.activo:
            return Response({'error': 'El doble factor ya está activo. Desactívalo antes de configurarlo de nuevo.'},
                            status=status.HTTP_409_CONFLICT)
        # Cada intento de activación genera un secreto nuevo: un QR mostrado antes deja de servir
        secreto = doble_factor.nuevo_secreto()
        SegundoFactor.objects.update_or_create(
            usuario=request.user, defaults={'secreto': secreto, 'activo': False, 'codigos_recuperacion': []}
        )
        uri = doble_factor.uri_aprovisionamiento(secreto, request.user)
        return Response({
            'otpauth_uri': uri,
            'qr_png_base64': doble_factor.qr_png_base64(uri),
            # Para escribirlo a mano si la app no puede leer el QR
            'secreto': secreto,
        })


class ConfirmarDobleFactorView(DobleFactorThrottledView):
    """Paso 2 de la activación: el primer código prueba que la app quedó bien configurada."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        segundo_factor = SegundoFactor.objects.filter(usuario=request.user).first()
        if segundo_factor is None:
            return Response({'error': 'Primero genera el código QR.'}, status=status.HTTP_400_BAD_REQUEST)
        if segundo_factor.activo:
            return Response({'error': 'El doble factor ya está activo.'}, status=status.HTTP_409_CONFLICT)
        if not doble_factor.verificar_codigo(segundo_factor, request.data.get('codigo')):
            return Response({'error': 'El código no es correcto.'}, status=status.HTTP_400_BAD_REQUEST)

        codigos = doble_factor.nuevos_codigos_recuperacion()
        segundo_factor.activo = True
        segundo_factor.codigos_recuperacion = [doble_factor.hash_codigo(c) for c in codigos]
        segundo_factor.save(update_fields=['activo', 'codigos_recuperacion'])
        # Los códigos en claro solo se entregan aquí, una vez: en la base de datos quedan como hash
        return Response({'activo': True, 'codigos_recuperacion': codigos})


class DesactivarDobleFactorView(DobleFactorThrottledView):
    """Desactiva el doble factor. Pide un código válido (de la app o de recuperación)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            segundo_factor = SegundoFactor.objects.select_for_update().filter(
                usuario=request.user, activo=True).first()
            if segundo_factor is None:
                return Response({'error': 'El doble factor no está activo.'}, status=status.HTTP_400_BAD_REQUEST)
            if not doble_factor.verificar_codigo(segundo_factor, request.data.get('codigo'),
                                                 permitir_recuperacion=True):
                return Response({'error': 'El código no es correcto.'}, status=status.HTTP_400_BAD_REQUEST)
            segundo_factor.delete()
        return Response({'activo': False})


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'usuario': datos_usuario(request.user),
                         'consentimiento_vigente': consentimiento_vigente(request.user),
                         'doble_factor_activo': doble_factor_activo(request.user)})

    def patch(self, request):
        """Derecho de rectificación: el titular corrige su nombre y apellidos."""
        usuario = request.user
        cambios = {}
        for campo, atributo in (('nombre', 'first_name'), ('apellidos', 'last_name')):
            if campo in request.data:
                valor = (request.data.get(campo) or '').strip()
                if not valor:
                    return Response({'error': f'El campo {campo} no puede quedar vacío.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                cambios[atributo] = valor[:150]
        if not cambios:
            return Response({'error': 'Indica el nombre o los apellidos a corregir.'},
                            status=status.HTTP_400_BAD_REQUEST)
        for atributo, valor in cambios.items():
            setattr(usuario, atributo, valor)
        usuario.save(update_fields=list(cambios))
        return Response({'usuario': datos_usuario(usuario)})


class ConsentimientoView(APIView):
    """Para cuentas que aún no aceptaron la versión vigente de la política (p. ej. creadas antes de ella)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not aceptado(request.data.get('acepta_privacidad')) or not aceptado(request.data.get('mayor_14')):
            return Response({'error': 'Debes aceptar la política de privacidad y declarar tener '
                                      f'{EDAD_MINIMA_CUENTA} años o más.'}, status=status.HTTP_400_BAD_REQUEST)
        if not consentimiento_vigente(request.user):
            Consentimiento.objects.create(usuario=request.user, version_politica=VERSION_POLITICA,
                                          declara_edad_minima=True)
        return Response({'consentimiento_vigente': True, 'version_politica': VERSION_POLITICA},
                        status=status.HTTP_201_CREATED)


class MisDatosView(APIView):
    """Derechos de acceso y portabilidad: entrega todos los datos del titular en un formato reutilizable (JSON)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        datos = {
            'generado_en': timezone.now().isoformat(),
            'responsable': 'Mi Ayudante (proyecto de título, Ingeniería en Informática, INACAP)',
            'cuenta': {
                'correo': usuario.email,
                'nombre': usuario.first_name,
                'apellidos': usuario.last_name,
                'fecha_registro': usuario.date_joined.isoformat(),
                'ultimo_acceso': usuario.last_login.isoformat() if usuario.last_login else None,
            },
            'consentimientos': [
                {'version_politica': c.version_politica, 'declara_edad_minima': c.declara_edad_minima,
                 'aceptado_en': c.aceptado_en.isoformat()}
                for c in usuario.consentimientos.all()
            ],
            'resultados_test': [
                {
                    'id': r.id,
                    'creado_en': r.creado_en.isoformat(),
                    'dimensiones': {
                        'pasion': float(r.puntaje_pasion), 'vocacion': float(r.puntaje_vocacion),
                        'profesion': float(r.puntaje_profesion), 'mision': float(r.puntaje_mision),
                    },
                    'areas': r.puntajes_area,
                    'respuestas': r.respuestas,
                }
                for r in Resultado.objects.filter(usuario=usuario)
            ],
            # El secreto y los códigos de recuperación no se exportan: son credenciales, no datos personales
            'doble_factor': {'activo': doble_factor_activo(usuario)},
            'no_almacenado': 'Los mensajes del asistente no se guardan en Mi Ayudante.',
        }
        respuesta = Response(datos)
        respuesta['Content-Disposition'] = 'attachment; filename="mis-datos-mi-ayudante.json"'
        return respuesta


class CuentaView(APIView):
    """Derecho de supresión (y revocación del consentimiento): elimina la cuenta y todos sus datos."""
    permission_classes = [IsAuthenticated]
    # Pide la contraseña: se limitan los intentos igual que en el login
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def delete(self, request):
        if not request.user.check_password(request.data.get('password') or ''):
            return Response({'error': 'La contraseña no es correcta.'}, status=status.HTTP_403_FORBIDDEN)
        # Los resultados del test y los consentimientos se borran en cascada (on_delete=CASCADE)
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResultadoTestView(APIView):
    """Supresión parcial: el titular borra uno de sus resultados del test (su perfil vocacional)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        borrados, _ = Resultado.objects.filter(pk=pk, usuario=request.user).delete()
        if not borrados:
            # Un resultado de otra persona responde igual que uno inexistente: no se revela que existe
            return Response({'error': 'No encontramos ese resultado en tu cuenta.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
