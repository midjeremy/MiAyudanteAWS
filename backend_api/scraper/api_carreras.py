"""Catálogo agrupado por carrera: una tarjeta por carrera, sin repetirla por cada sede o jornada."""
from django.db.models import Count, Min
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from scraper.api import OfertaListView, PaginacionCatalogo
from scraper.documentacion import FILTROS_CATALOGO, CarreraDetalleSerializer, CarreraPaginadaSerializer
from scraper.models import Carrera
from scraper.serializers import OfertaSerializer


def ofertas_filtradas(request):
    """Reutiliza los mismos filtros de /api/v1/ofertas/ (q, institucion, region, modalidad, ...)."""
    vista = OfertaListView()
    vista.request = request
    vista.kwargs = {}
    return vista.get_queryset()


def arancel_desde(resumen):
    """Arancel más bajo de la carrera, con el período que publica la institución."""
    for periodo in ('anual', 'semestral', 'mensual'):
        monto = resumen.get(f'min_{periodo}')
        if monto is not None:
            return {'monto': int(monto), 'periodo': periodo}
    return None


def datos_carrera(carrera, resumen, detalle):
    return {
        'id': carrera.id,
        'carrera': carrera.nombre_carrera,
        'institucion': carrera.institucion.nombre if carrera.institucion else '',
        'institucion_codigo': carrera.institucion.codigo if carrera.institucion else '',
        'nivel': carrera.nivel_formacion,
        'titulo': carrera.titulo_otorgado,
        'duracion_semestres': carrera.duracion_semestres,
        'malla_url': carrera.url_malla,
        'total_ofertas': resumen.get('total_ofertas', 0),
        'total_sedes': resumen.get('total_sedes', 0),
        'sedes': sorted(detalle['sedes']),
        'regiones': sorted(detalle['regiones']),
        'modalidades': sorted(detalle['modalidades']),
        'arancel_desde': arancel_desde(resumen),
    }


def resumir(ofertas, ids_carrera):
    """Cuenta ofertas y sedes, y junta sedes, regiones y modalidades de cada carrera."""
    ofertas = ofertas.filter(carrera_id__in=ids_carrera).order_by()
    resumenes = {
        fila['carrera_id']: fila
        for fila in ofertas.values('carrera_id').annotate(
            total_ofertas=Count('id'),
            total_sedes=Count('sede', distinct=True),
            min_anual=Min('arancel_anual_clp'),
            min_semestral=Min('arancel_semestral_clp'),
            min_mensual=Min('arancel_mensual_clp'),
        )
    }
    detalles = {i: {'sedes': set(), 'regiones': set(), 'modalidades': set()} for i in ids_carrera}
    for carrera_id, sede, region, modalidad in ofertas.values_list(
        'carrera_id', 'sede__nombre_sede', 'sede__region', 'jornada__modalidad'
    ).distinct():
        detalle = detalles[carrera_id]
        detalle['sedes'].add(sede)
        if region:
            detalle['regiones'].add(region)
        if modalidad:
            detalle['modalidades'].add(modalidad)
    return resumenes, detalles


class CarreraListView(APIView):
    """GET /api/v1/carreras/: mismos filtros que /api/v1/ofertas/, pero una fila por carrera."""
    permission_classes = [AllowAny]

    @extend_schema(tags=['Catálogo'], summary='Carreras agrupadas (una fila por carrera)', operation_id='carreras_listar',
                   parameters=FILTROS_CATALOGO, responses=CarreraPaginadaSerializer)
    def get(self, request):
        ofertas = ofertas_filtradas(request)
        carreras = (
            Carrera.objects.filter(id__in=ofertas.order_by().values('carrera_id'))
            .select_related('institucion')
            .order_by('institucion__codigo', 'nombre_carrera', 'id')
        )
        paginador = PaginacionCatalogo()
        pagina = paginador.paginate_queryset(carreras, request, view=self)
        ids = [carrera.id for carrera in pagina]
        resumenes, detalles = resumir(ofertas, ids)
        return paginador.get_paginated_response(
            [datos_carrera(c, resumenes.get(c.id, {}), detalles[c.id]) for c in pagina]
        )


class CarreraDetailView(APIView):
    """GET /api/v1/carreras/<id>/: la carrera con todas sus ofertas (sedes, jornadas y aranceles)."""
    permission_classes = [AllowAny]

    @extend_schema(tags=['Catálogo'], summary='Detalle de una carrera con todas sus ofertas',
                   responses=CarreraDetalleSerializer)
    def get(self, request, pk):
        carrera = get_object_or_404(Carrera.objects.select_related('institucion'), pk=pk)
        ofertas = OfertaListView.queryset.filter(carrera=carrera)
        resumenes, detalles = resumir(ofertas, [carrera.id])
        datos = datos_carrera(carrera, resumenes.get(carrera.id, {}), detalles[carrera.id])
        datos['ofertas'] = OfertaSerializer(ofertas, many=True).data
        return Response(datos)
