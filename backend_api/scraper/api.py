"""API REST del catálogo para la capa BFF en PHP: filtra y pagina en el servidor."""
from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from scraper.catalogos import normalizar_texto
from scraper.models import Institucion, Jornada, OfertaAcademica, Sede
from scraper.serializers import OfertaSerializer

MAXIMO_IDS = 50


def clave_sede(nombre):
    """Identificador de sede para URLs y selects, por ejemplo 'san_joaquin'."""
    return normalizar_texto(nombre).replace(' ', '_')


class PaginacionCatalogo(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OfertasBaseView:
    permission_classes = [AllowAny]
    serializer_class = OfertaSerializer
    queryset = OfertaAcademica.objects.select_related('institucion', 'carrera', 'sede', 'jornada').order_by(
        'institucion__codigo', 'carrera__nombre_carrera', 'sede__nombre_sede', 'jornada__tipo_jornada', 'id'
    )


class OfertaListView(OfertasBaseView, ListAPIView):
    """
    Filtros: q, institucion, sede, modalidad, region, nivel, carrera (contiene), excluir (no contiene)
    e ids (lista separada por comas, para comparar o mostrar guardados).
    """
    pagination_class = PaginacionCatalogo

    def get_queryset(self):
        consulta = super().get_queryset()
        parametros = self.request.query_params

        if ids := parametros.get('ids'):
            numeros = [int(valor) for valor in ids.split(',') if valor.strip().isdigit()][:MAXIMO_IDS]
            consulta = consulta.filter(id__in=numeros)
        if texto := parametros.get('q', '').strip():
            consulta = consulta.filter(
                Q(carrera__nombre_carrera__icontains=texto) | Q(institucion__nombre__icontains=texto)
                | Q(institucion__codigo__iexact=texto)
            )
        if institucion := parametros.get('institucion'):
            consulta = consulta.filter(institucion__codigo__iexact=institucion)
        if sede := parametros.get('sede'):
            ids_sede = [s.id for s in Sede.objects.only('id', 'nombre_sede') if clave_sede(s.nombre_sede) == clave_sede(sede)]
            consulta = consulta.filter(sede_id__in=ids_sede)
        if modalidad := parametros.get('modalidad'):
            consulta = consulta.filter(jornada__modalidad__iexact=modalidad)
        if region := parametros.get('region'):
            consulta = consulta.filter(sede__region__iexact=region)
        if nivel := parametros.get('nivel'):
            consulta = consulta.filter(carrera__nivel_formacion__iexact=nivel)
        if carrera := parametros.get('carrera', '').strip():
            consulta = consulta.filter(carrera__nombre_carrera__icontains=carrera)
        if excluir := parametros.get('excluir', '').strip():
            consulta = consulta.exclude(carrera__nombre_carrera__icontains=excluir)
        return consulta


class OfertaDetailView(OfertasBaseView, RetrieveAPIView):
    pass


class FiltrosView(APIView):
    """Opciones reales para los selects del buscador."""
    permission_classes = [AllowAny]

    def get(self, request):
        sedes = {}
        for sede in Sede.objects.filter(ofertaacademica__isnull=False).distinct().order_by('nombre_sede'):
            sedes.setdefault(clave_sede(sede.nombre_sede), sede.nombre_sede)

        def distintos(consulta, campo):
            return sorted(valor for valor in consulta.values_list(campo, flat=True).distinct() if valor)

        return Response({
            'instituciones': [
                {'clave': i.codigo.lower(), 'nombre': i.nombre}
                for i in Institucion.objects.filter(ofertaacademica__isnull=False).distinct().order_by('codigo')
            ],
            'sedes': [{'clave': clave, 'nombre': nombre} for clave, nombre in sedes.items()],
            'modalidades': distintos(Jornada.objects.filter(ofertaacademica__isnull=False), 'modalidad'),
            'regiones': distintos(Sede.objects.filter(ofertaacademica__isnull=False), 'region'),
            'niveles': distintos(OfertaAcademica.objects.all(), 'carrera__nivel_formacion'),
        })
