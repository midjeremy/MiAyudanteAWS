"""
URL configuration for miayudante_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from scraper import api, api_carreras, salud, views
from Test_Ikigai.views import PreguntasIkigaiView, ResultadoIkigaiView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Monitoreo (SLA 01): /health/deep compara dos ofertas reales contra PostgreSQL
    path('health', salud.SaludView.as_view(), name='salud'),
    path('health/deep', salud.SaludProfundaView.as_view(), name='salud_profunda'),
    # Documentación de la API (DoD): esquema OpenAPI y Swagger UI
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('api/v1/catalogo/', views.api_catalogo_inacap, name='api_catalogo'),
    path('api/v1/ofertas/', api.OfertaListView.as_view(), name='api_ofertas'),
    path('api/v1/ofertas/<int:pk>/', api.OfertaDetailView.as_view(), name='api_oferta_detalle'),
    path('api/v1/carreras/', api_carreras.CarreraListView.as_view(), name='api_carreras'),
    path('api/v1/carreras/<int:pk>/', api_carreras.CarreraDetailView.as_view(), name='api_carrera_detalle'),
    path('api/v1/filtros/', api.FiltrosView.as_view(), name='api_filtros'),
    # Test vocacional Ikigai: preguntas validadas por juicio de expertos y cálculo del resultado
    path('api/v1/ikigai/preguntas/', PreguntasIkigaiView.as_view(), name='ikigai_preguntas'),
    path('api/v1/ikigai/resultado/', ResultadoIkigaiView.as_view(), name='ikigai_resultado'),
    path('', include('chatbot.urls')),
    path('', include('usuarios.urls')),
]