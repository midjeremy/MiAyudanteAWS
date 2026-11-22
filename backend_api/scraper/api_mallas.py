"""Descarga pública de las mallas en PDF (S3 privado: se entrega con un enlace prefirmado que dura minutos)."""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import content_disposition_header
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from scraper.etl import crear_cliente_s3
from scraper.mallas_pdf import es_pdf
from scraper.models import Carrera, Mencion

VIGENCIA_ENLACE = 300  # segundos


def ruta_malla_pdf(carrera):
    """Ruta de descarga de la malla de la carrera, o None si no hay PDF."""
    if carrera.s3_url_malla_pdf or es_pdf(carrera.url_malla):
        return reverse('api_carrera_malla_pdf', args=[carrera.id])
    return None


def ruta_malla_pdf_mencion(mencion):
    """Solo menciones con malla propia; si no, vale la de la carrera."""
    if mencion.s3_malla_pdf or es_pdf(mencion.url_malla):
        return reverse('api_mencion_malla_pdf', args=[mencion.carrera_id, mencion.id])
    return None


CARACTERES_PROHIBIDOS = set('\\/:*?"<>|')


def nombre_archivo(*partes):
    texto = ''.join(c for c in ' - '.join(p for p in partes if p) if c not in CARACTERES_PROHIBIDOS)
    return f'Malla {texto[:150]}.pdf'


class MallaPdfView(APIView):
    """Redirige al PDF de la malla en S3 (descarga) o, si solo existe en la institución, al PDF publicado allí."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'mallas'

    def destino(self, clave, url_institucion, archivo):
        if clave:
            enlace = crear_cliente_s3().generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': clave,
                    'ResponseContentType': 'application/pdf',
                    'ResponseContentDisposition': content_disposition_header(True, archivo),
                },
                ExpiresIn=VIGENCIA_ENLACE,
            )
            return HttpResponseRedirect(enlace)
        if es_pdf(url_institucion):
            return HttpResponseRedirect(url_institucion)
        return Response({'detail': 'Esta malla no está disponible en PDF.'}, status=404)

    @extend_schema(tags=['Catálogo'], summary='Descargar la malla de la carrera en PDF', operation_id='carrera_malla_pdf',
                   responses={302: OpenApiResponse(description='Redirige al PDF'),
                              404: OpenApiResponse(description='Sin PDF')})
    def get(self, request, pk):
        carrera = get_object_or_404(Carrera.objects.select_related('institucion'), pk=pk)
        institucion = carrera.institucion.nombre if carrera.institucion else ''
        return self.destino(carrera.s3_url_malla_pdf, carrera.url_malla,
                            nombre_archivo(carrera.nombre_carrera, institucion))


class MencionMallaPdfView(MallaPdfView):
    @extend_schema(tags=['Catálogo'], summary='Descargar la malla de una mención en PDF',
                   operation_id='mencion_malla_pdf',
                   responses={302: OpenApiResponse(description='Redirige al PDF'),
                              404: OpenApiResponse(description='Sin PDF')})
    def get(self, request, pk, mencion_id):
        mencion = get_object_or_404(Mencion.objects.select_related('carrera__institucion'), pk=mencion_id, carrera_id=pk)
        institucion = mencion.carrera.institucion.nombre if mencion.carrera.institucion else ''
        return self.destino(mencion.s3_malla_pdf, mencion.url_malla,
                            nombre_archivo(mencion.carrera.nombre_base or mencion.carrera.nombre_carrera,
                                           f'Mención {mencion.nombre}', institucion))
