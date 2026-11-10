"""Monitoreo de disponibilidad (SLA 01 y KPI-05 del informe).

/health      -> la API responde (no toca la base de datos).
/health/deep -> compara dos ofertas reales contra PostgreSQL, igual que el comparador.
                Si la base de datos o la API fallan, responde 503 aunque Nginx siga arriba.
"""
import time

from django.db import DatabaseError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from scraper.documentacion import SaludProfundaSerializer, SaludSerializer
from scraper.models import OfertaAcademica
from scraper.serializers import OfertaSerializer


class SaludView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=['Monitoreo'], summary='La API responde', responses=SaludSerializer)
    def get(self, request):
        return Response({'estado': 'ok'})


class SaludProfundaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=['Monitoreo'], summary='Compara dos ofertas reales contra PostgreSQL',
                   responses={200: SaludProfundaSerializer, 503: SaludProfundaSerializer})
    def get(self, request):
        inicio = time.perf_counter()
        try:
            # Las dos primeras ofertas con arancel: el mismo trabajo que hace el comparador
            ofertas = list(
                OfertaAcademica.objects.select_related('institucion', 'carrera', 'sede', 'jornada')
                .exclude(arancel_anual_clp=None, arancel_mensual_clp=None, arancel_semestral_clp=None)
                .order_by('id')[:2]
            )
            comparadas = OfertaSerializer(ofertas, many=True).data
        except DatabaseError:
            return Response(
                {'estado': 'error', 'base_de_datos': 'sin conexión'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        milisegundos = round((time.perf_counter() - inicio) * 1000)
        if len(comparadas) < 2:
            return Response(
                {'estado': 'error', 'base_de_datos': 'ok', 'detalle': 'el catálogo tiene menos de dos ofertas',
                 'milisegundos': milisegundos},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            'estado': 'ok',
            'base_de_datos': 'ok',
            'ofertas_comparadas': [oferta['id'] for oferta in comparadas],
            'milisegundos': milisegundos,
        })
