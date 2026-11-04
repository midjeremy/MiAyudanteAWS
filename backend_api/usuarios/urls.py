from django.urls import path

from .views import LoginView, PerfilView, RegistroView

urlpatterns = [
    path('api/v1/auth/registro/', RegistroView.as_view(), name='auth_registro'),
    path('api/v1/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/v1/auth/perfil/', PerfilView.as_view(), name='auth_perfil'),
]
