from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pregunta, Resultado
from .preguntas import DIMENSIONES, ESCALA
from .utils import RespuestasInvalidas, areas_ordenadas, calcular_resultado, normalizar_respuestas

ETIQUETA = 'Test Ikigai'
ErrorTest = inline_serializer('ErrorTest', {'error': serializers.CharField()})
ResultadoTest = inline_serializer('ResultadoTest', {
    'dimensiones': serializers.ListField(child=inline_serializer('DimensionResultado', {
        'clave': serializers.CharField(), 'nombre': serializers.CharField(), 'descripcion': serializers.CharField(),
        'porcentaje': serializers.FloatField(help_text='0 a 100'),
    })),
    'areas': serializers.ListField(child=serializers.DictField(), help_text='Áreas vocacionales de mayor a menor afinidad'),
    'guardado': serializers.BooleanField(help_text='true si se guardó en la cuenta (petición con JWT)'),
    'id': serializers.IntegerField(allow_null=True),
    'creado_en': serializers.DateTimeField(allow_null=True),
})


def respuesta_resultado(dimensiones, areas, resultado=None):
    """Formato común del resultado, recién calculado o leído de la base."""
    return {
        'dimensiones': [
            {'clave': clave, 'nombre': nombre, 'descripcion': descripcion, 'porcentaje': float(dimensiones[clave])}
            for clave, nombre, descripcion in DIMENSIONES
        ],
        'areas': areas_ordenadas({clave: float(valor) for clave, valor in areas.items()}),
        'guardado': resultado is not None,
        'id': resultado.id if resultado else None,
        'creado_en': resultado.creado_en.isoformat() if resultado else None,
    }


class PreguntasIkigaiView(APIView):
    """Lista las 40 preguntas con la escala Likert. El área no se envía: el estudiante no la ve."""
    permission_classes = [AllowAny]

    @extend_schema(tags=[ETIQUETA], summary='Preguntas del test y escala Likert', operation_id='ikigai_preguntas',
                   responses={200: inline_serializer('PreguntasTest', {
                       'escala': serializers.ListField(child=inline_serializer('ValorEscala', {
                           'valor': serializers.IntegerField(), 'etiqueta': serializers.CharField()})),
                       'dimensiones': serializers.ListField(child=inline_serializer('DimensionTest', {
                           'clave': serializers.CharField(), 'nombre': serializers.CharField(),
                           'descripcion': serializers.CharField()})),
                       'preguntas': serializers.ListField(child=inline_serializer('PreguntaTest', {
                           'numero': serializers.IntegerField(), 'enunciado': serializers.CharField(),
                           'dimension': serializers.CharField()})),
                   })})
    def get(self, request):
        preguntas = Pregunta.objects.all()
        return Response({
            'escala': [{'valor': valor, 'etiqueta': etiqueta} for valor, etiqueta in ESCALA],
            'dimensiones': [
                {'clave': clave, 'nombre': nombre, 'descripcion': descripcion}
                for clave, nombre, descripcion in DIMENSIONES
            ],
            'preguntas': [
                {'numero': p.numero, 'enunciado': p.enunciado, 'dimension': p.dimension}
                for p in preguntas
            ],
        })


class ResultadoIkigaiView(APIView):
    """POST: calcula el resultado (y lo guarda si viene un JWT válido). GET: último resultado guardado."""
    permission_classes = [AllowAny]

    @extend_schema(tags=[ETIQUETA], summary='Calcular el resultado (y guardarlo si hay sesión)',
                   operation_id='ikigai_calcular',
                   request=inline_serializer('RespuestasTest', {
                       'respuestas': serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=5),
                                                           help_text='{"número de pregunta": valor de 1 a 5}, las 40'),
                   }),
                   responses={200: OpenApiResponse(ResultadoTest, description='Calculado sin guardar (sin sesión)'),
                              201: OpenApiResponse(ResultadoTest, description='Calculado y guardado en la cuenta'),
                              400: ErrorTest, 503: ErrorTest})
    def post(self, request):
        preguntas = list(Pregunta.objects.all())
        if not preguntas:
            return Response({'error': 'El test no tiene preguntas cargadas.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            respuestas = normalizar_respuestas(request.data.get('respuestas'), {p.numero for p in preguntas})
        except RespuestasInvalidas as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        calculo = calcular_resultado(respuestas, preguntas)
        resultado = None
        if request.user and request.user.is_authenticated:
            dims = calculo['dimensiones']
            with transaction.atomic():
                resultado = Resultado.objects.create(
                    usuario=request.user,
                    puntaje_pasion=dims['pasion'],
                    puntaje_vocacion=dims['vocacion'],
                    puntaje_profesion=dims['profesion'],
                    puntaje_mision=dims['mision'],
                    puntajes_area=calculo['areas'],
                    respuestas={str(n): v for n, v in sorted(respuestas.items())},
                )

        return Response(
            respuesta_resultado(calculo['dimensiones'], calculo['areas'], resultado),
            status=status.HTTP_201_CREATED if resultado else status.HTTP_200_OK,
        )

    @extend_schema(tags=[ETIQUETA], summary='Último resultado guardado', operation_id='ikigai_ultimo_resultado',
                   responses={200: ResultadoTest, 401: ErrorTest, 404: ErrorTest})
    def get(self, request):
        if not (request.user and request.user.is_authenticated):
            return Response({'error': 'Inicia sesión para ver tu resultado.'}, status=status.HTTP_401_UNAUTHORIZED)
        resultado = request.user.resultados_ikigai.first()
        if resultado is None:
            return Response({'error': 'Todavía no tienes resultados del test.'}, status=status.HTTP_404_NOT_FOUND)
        dimensiones = {
            'pasion': resultado.puntaje_pasion,
            'vocacion': resultado.puntaje_vocacion,
            'profesion': resultado.puntaje_profesion,
            'mision': resultado.puntaje_mision,
        }
        return Response(respuesta_resultado(dimensiones, resultado.puntajes_area, resultado))
