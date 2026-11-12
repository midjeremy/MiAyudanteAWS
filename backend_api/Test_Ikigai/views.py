from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pregunta, Resultado
from .preguntas import DIMENSIONES, ESCALA
from .utils import RespuestasInvalidas, areas_ordenadas, calcular_resultado, normalizar_respuestas


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
