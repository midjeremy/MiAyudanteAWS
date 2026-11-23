import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .services import generar_respuesta_rag

logger = logging.getLogger(__name__)

MAX_LARGO_MENSAJE = 500
MAX_TURNOS_HISTORIAL = 10
MAX_LARGO_TURNO = 2000


def limpiar_historial(historial):
    """El historial llega desde el navegador: solo se aceptan turnos bien formados."""
    if not isinstance(historial, list):
        return []
    return [
        {"role": turno["role"], "content": turno["content"][:MAX_LARGO_TURNO]}
        for turno in historial[-MAX_TURNOS_HISTORIAL:]
        if isinstance(turno, dict)
        and turno.get("role") in ("user", "assistant")
        and isinstance(turno.get("content"), str)
    ]


class ChatbotAPIView(APIView):
    permission_classes = [AllowAny]
    # Cada mensaje consume la cuenta de OpenAI: se limita por IP del visitante
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'chatbot'

    @extend_schema(
        tags=['Asistente'], summary='Preguntar al asistente (RAG con tool calling)', operation_id='chatbot_preguntar',
        description='Uso interno del BFF: Nginx no publica /api/chatbot/. No exige sesión y no guarda la conversación.',
        request=inline_serializer('PreguntaAsistente', {
            'mensaje': serializers.CharField(max_length=MAX_LARGO_MENSAJE),
            'historial': serializers.ListField(
                child=inline_serializer('TurnoAsistente', {
                    'role': serializers.ChoiceField(choices=['user', 'assistant']),
                    'content': serializers.CharField(max_length=MAX_LARGO_TURNO),
                }), required=False, help_text=f'Últimos {MAX_TURNOS_HISTORIAL} turnos, guardados en el navegador'),
        }),
        responses={200: inline_serializer('RespuestaAsistente', {'respuesta': serializers.CharField()}),
                   400: inline_serializer('ErrorAsistente', {'error': serializers.CharField()}),
                   429: OpenApiResponse(description='Más de 10 mensajes por minuto desde la misma IP'),
                   500: OpenApiResponse(description='Falla del asistente (por ejemplo, OpenAI no responde)')},
    )
    def post(self, request):
        mensaje_usuario = request.data.get("mensaje")

        if not isinstance(mensaje_usuario, str) or not mensaje_usuario.strip():
            return Response(
                {"error": "El campo 'mensaje' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(mensaje_usuario) > MAX_LARGO_MENSAJE:
            return Response(
                {"error": f"El mensaje no puede superar los {MAX_LARGO_MENSAJE} caracteres."},
                status=status.HTTP_400_BAD_REQUEST
            )

        historial = limpiar_historial(request.data.get("historial"))

        try:
            respuesta_chatbot = generar_respuesta_rag(mensaje_usuario.strip(), historial)
            return Response({"respuesta": respuesta_chatbot}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error al generar la respuesta del asistente")
            return Response(
                {"error": "Error interno del asistente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
