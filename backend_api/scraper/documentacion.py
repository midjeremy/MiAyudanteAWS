"""Descripción OpenAPI (Swagger) de la API del catálogo. Solo documenta: no cambia respuestas."""
from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers

from scraper.serializers import OfertaSerializer

FILTROS_CATALOGO = [
    OpenApiParameter('q', str, description='Texto en el nombre de la carrera o de la institución.'),
    OpenApiParameter('institucion', str, description='Código de institución: inacap o duoc.'),
    OpenApiParameter('sede', str, description='Clave de sede, como la entrega /api/v1/filtros/ (ej. san_joaquin).'),
    OpenApiParameter('region', str, description='Región exacta de la sede.'),
    OpenApiParameter('modalidad', str, description='Presencial, Online, etc.'),
    OpenApiParameter('nivel', str, description='Nivel de formación de la carrera.'),
    OpenApiParameter('carrera', str, description='La carrera contiene este texto.'),
    OpenApiParameter('excluir', str, description='La carrera NO contiene este texto.'),
    OpenApiParameter('carrera_id', int, description='Solo las ofertas de esta carrera.'),
    OpenApiParameter('ids', str, description='IDs de ofertas separados por coma (máximo 50), para comparar.'),
    OpenApiParameter('page', int, description='Número de página.'),
    OpenApiParameter('page_size', int, description='Resultados por página (máximo 100, por defecto 20).'),
]

ArancelSerializer = inline_serializer('Arancel', {
    'monto': serializers.IntegerField(),
    'periodo': serializers.ChoiceField(choices=['anual', 'semestral', 'mensual']),
}, allow_null=True)

CAMPOS_CARRERA = {
    'id': serializers.IntegerField(),
    'carrera': serializers.CharField(),
    'institucion': serializers.CharField(),
    'institucion_codigo': serializers.CharField(),
    'nivel': serializers.CharField(allow_null=True),
    'titulo': serializers.CharField(allow_null=True),
    'duracion_semestres': serializers.IntegerField(allow_null=True),
    'malla_url': serializers.CharField(allow_null=True),
    'total_ofertas': serializers.IntegerField(),
    'total_sedes': serializers.IntegerField(),
    'sedes': serializers.ListField(child=serializers.CharField()),
    'regiones': serializers.ListField(child=serializers.CharField()),
    'modalidades': serializers.ListField(child=serializers.CharField()),
    'arancel_desde': ArancelSerializer,
}

CarreraSerializer = inline_serializer('Carrera', CAMPOS_CARRERA)

CarreraPaginadaSerializer = inline_serializer('CarrerasPaginadas', {
    'count': serializers.IntegerField(),
    'next': serializers.CharField(allow_null=True),
    'previous': serializers.CharField(allow_null=True),
    'results': CarreraSerializer.__class__(many=True),
})

CarreraDetalleSerializer = inline_serializer('CarreraDetalle', {
    **CAMPOS_CARRERA,
    'ofertas': OfertaSerializer(many=True),
})

OpcionSerializer = inline_serializer('Opcion', {
    'clave': serializers.CharField(),
    'nombre': serializers.CharField(),
})

FiltrosSerializer = inline_serializer('Filtros', {
    'instituciones': OpcionSerializer.__class__(many=True),
    'sedes': OpcionSerializer.__class__(many=True),
    'modalidades': serializers.ListField(child=serializers.CharField()),
    'regiones': serializers.ListField(child=serializers.CharField()),
    'niveles': serializers.ListField(child=serializers.CharField()),
})

SaludSerializer = inline_serializer('Salud', {'estado': serializers.CharField()})

SaludProfundaSerializer = inline_serializer('SaludProfunda', {
    'estado': serializers.CharField(),
    'base_de_datos': serializers.CharField(),
    'ofertas_comparadas': serializers.ListField(child=serializers.IntegerField(), required=False),
    'milisegundos': serializers.IntegerField(required=False),
    'detalle': serializers.CharField(required=False),
})
