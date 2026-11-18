from django.urls import path

from .views import (
    ActivarDobleFactorView, ConfirmarDobleFactorView, ConsentimientoView, CuentaView, DesactivarDobleFactorView,
    LoginView, MisDatosView, PerfilView, RegistroView, ResultadoTestView, VerificarDobleFactorView,
)

urlpatterns = [
    path('api/v1/auth/registro/', RegistroView.as_view(), name='auth_registro'),
    path('api/v1/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/v1/auth/perfil/', PerfilView.as_view(), name='auth_perfil'),
    # Doble factor con app autenticadora (TOTP)
    path('api/v1/auth/2fa/verificar/', VerificarDobleFactorView.as_view(), name='auth_2fa_verificar'),
    path('api/v1/auth/2fa/activar/', ActivarDobleFactorView.as_view(), name='auth_2fa_activar'),
    path('api/v1/auth/2fa/confirmar/', ConfirmarDobleFactorView.as_view(), name='auth_2fa_confirmar'),
    path('api/v1/auth/2fa/desactivar/', DesactivarDobleFactorView.as_view(), name='auth_2fa_desactivar'),
    # Ley N.° 21.719: consentimiento y derechos del titular
    path('api/v1/auth/consentimiento/', ConsentimientoView.as_view(), name='auth_consentimiento'),
    path('api/v1/auth/mis-datos/', MisDatosView.as_view(), name='auth_mis_datos'),
    path('api/v1/auth/mis-datos/resultados/<int:pk>/', ResultadoTestView.as_view(), name='auth_borrar_resultado'),
    path('api/v1/auth/cuenta/', CuentaView.as_view(), name='auth_cuenta'),
]
