from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

Usuario = get_user_model()


def datos_usuario(usuario):
    return {
        'correo': usuario.email,
        'nombre': f'{usuario.first_name} {usuario.last_name}'.strip(),
    }


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
        usuario.save()
        return Response({'usuario': datos_usuario(usuario)}, status=status.HTTP_201_CREATED)


class LoginView(AuthThrottledView):
    def post(self, request):
        correo = (request.data.get('correo') or '').strip().lower()
        password = request.data.get('password') or ''

        usuario = authenticate(request, username=correo, password=password)
        if usuario is None:
            return Response({'error': 'Correo o contraseña incorrectos.'}, status=status.HTTP_401_UNAUTHORIZED)

        token = RefreshToken.for_user(usuario)
        return Response({
            'access': str(token.access_token),
            'refresh': str(token),
            'usuario': datos_usuario(usuario),
        })


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'usuario': datos_usuario(request.user)})
