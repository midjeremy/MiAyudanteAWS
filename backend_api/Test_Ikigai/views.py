from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
#importar el calculo para el test ikigai
from .utils import get_ikigai_result

# Create your views here.
#prueba
class EvaluarIkigaiView(APIView):
    #se extrae las respuestas en JSON
    def post(self, request):
        respuestas = request.data.get("respuestas", [])
        #validacion basica de la entrada
        if not respuestas:
            return Response(
                {"error": "No se proporcionaron respuestas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vector_postulante = get_ikigai_result(respuestas)

        #se responde al BFF / cliente con la estructura del JSON terminado
        return Response({
            "status": "success",
            "vector_postulante": vector_postulante
        }, status=status.HTTP_200_OK)