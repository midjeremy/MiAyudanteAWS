from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .services import generar_respuesta_rag

class ChatbotAPIView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        mensaje_usuario = request.data.get("mensaje")
        
        if not mensaje_usuario:
            return Response(
                {"error": "El campo 'mensaje' es obligatorio."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            respuesta_chatbot = generar_respuesta_rag(mensaje_usuario)
            return Response({"respuesta": respuesta_chatbot}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "Error interno del asistente.", "detalle": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )