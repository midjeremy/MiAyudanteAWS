from django.urls import path

from .views import (
    ConsentimientoView, CuentaView, LoginView, MisDatosView, PerfilView, RegistroView, ResultadoTestView,
)

urlpatterns = [
    path('api/v1/auth/registro/', RegistroView.as_view(), name='auth_registro'),
    path('api/v1/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/v1/auth/perfil/', PerfilView.as_view(), name='auth_perfil'),
    # Ley N.° 21.719: consentimiento y derechos del titular
    path('api/v1/auth/consentimiento/', ConsentimientoView.as_view(), name='auth_consentimiento'),
    path('api/v1/auth/mis-datos/', MisDatosView.as_view(), name='auth_mis_datos'),
    path('api/v1/auth/mis-datos/resultados/<int:pk>/', ResultadoTestView.as_view(), name='auth_borrar_resultado'),
    path('api/v1/auth/cuenta/', CuentaView.as_view(), name='auth_cuenta'),
]
