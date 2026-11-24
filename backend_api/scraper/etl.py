"""Reglas comunes de control del pipeline: KPI-01, lotes y retiro de ofertas obsoletas."""
import json
import re
import logging
from datetime import timedelta

import boto3
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone

from scraper.models import LoteScrapingS3, OfertaAcademica

TASA_MINIMA_EXITO = 95
# Una carga completa de INACAP tarda cerca de una hora; un lote abierto por más tiempo quedó interrumpido
HORAS_LOTE_COLGADO = 6
# Estados de un lote que dejaron el catálogo actualizado (PARCIAL carga lo extraído, pero no retira obsoletas)
ESTADOS_CON_CARGA = ('COMPLETADO', 'PARCIAL')

logger = logging.getLogger(__name__)


def crear_cliente_s3():
    return boto3.client(
        's3',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        aws_session_token=getattr(settings, 'AWS_SESSION_TOKEN', None),
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
    )


def subir_json_crudo(s3_client, datos, fuente):
    ruta_s3 = f"raw/{fuente}/{timezone.now():%Y-%m-%d_%H%M%S}.json"
    s3_client.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=ruta_s3,
        Body=json.dumps(datos, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )
    return ruta_s3


def tasa_exito(correctos, total):
    """KPI-01: registros extraídos correctamente sobre el total de registros objetivo."""
    return round(correctos / total * 100, 2) if total else 0


def cerrar_lote(lote, estado, correctos, total, total_ofertas=0, errores=None):
    errores = errores or []
    lote.estado_etl = estado
    lote.total_registros = total
    lote.total_ofertas = total_ofertas
    lote.errores = len(errores)
    lote.tasa_exito = tasa_exito(correctos, total)
    lote.detalle_errores = '\n'.join(errores)[:5000]
    lote.save()


# Si más de esta fracción de las ofertas del lote llega sin arancel, lo más probable es que la página de la
# institución esté fallando (no que haya dejado de publicar los precios): se avisa por correo.
UMBRAL_SIN_ARANCEL = 0.05


def monto_publicado(valor):
    """Monto en pesos o None. Un precio vacío o en 0 significa «no publicado»: nunca es un arancel real."""
    if valor is None:
        return None
    numero = int(valor) if isinstance(valor, (int, float)) else int(re.sub(r'[^\d]', '', str(valor)) or 0)
    return numero if numero > 0 else None


def revisar_aranceles(lote):
    """Registra en el lote las ofertas que quedaron sin arancel y avisa si son demasiadas.

    El catálogo las muestra como «Sin información (arancel no publicado)» y el asistente responde que el dato no
    está; no se usan valores antiguos. Devuelve la lista de ofertas sin arancel («carrera – sede – jornada»).
    """
    ofertas = OfertaAcademica.objects.filter(lote_scraping=lote)
    total = ofertas.count()
    faltantes = [
        f'{o.carrera.nombre_carrera} – {o.sede.nombre_sede} – {o.jornada.tipo_jornada}'
        for o in ofertas.filter(arancel_anual_clp__isnull=True, arancel_semestral_clp__isnull=True,
                                arancel_mensual_clp__isnull=True).select_related('carrera', 'sede', 'jornada')
                        .order_by('carrera__nombre_carrera', 'sede__nombre_sede')
    ]
    if not faltantes:
        return faltantes
    resumen = f'Aviso: {len(faltantes)} de {total} ofertas sin arancel publicado por la institución'
    lote.detalle_errores = '\n'.join(filter(None, [lote.detalle_errores, resumen + ':', *faltantes]))[:5000]
    lote.save(update_fields=['detalle_errores'])
    if total and len(faltantes) / total > UMBRAL_SIN_ARANCEL:
        try:
            mail_admins(
                f'ETL {lote.institucion.nombre}: {len(faltantes)} ofertas sin arancel en el lote {lote.id}',
                '\n'.join([
                    f'{resumen} ({len(faltantes) / total:.0%}, umbral {UMBRAL_SIN_ARANCEL:.0%}).',
                    'Probablemente la página de aranceles de la institución está fallando. El catálogo muestra',
                    '«Sin información (arancel no publicado)» en esas ofertas hasta la próxima carga.',
                    'Qué hacer: revisar la página de la carrera; si ya publica los valores, volver a ejecutar el scraper.',
                    '', *faltantes[:100],
                ]),
            )
        except Exception:
            logger.exception('No se pudo enviar el aviso de ofertas sin arancel del lote %s', lote.id)
    return faltantes


def describir_error(error, largo=200):
    """Tipo y primera línea del mensaje (Selenium agrega el stacktrace después), para detalle_errores."""
    mensaje = (getattr(error, 'msg', None) or str(error)).strip().splitlines()
    texto = f"{type(error).__name__}: {mensaje[0]}" if mensaje else type(error).__name__
    return texto[:largo]


def cerrar_lotes_colgados(institucion, horas=HORAS_LOTE_COLGADO):
    """Marca como ERROR los lotes EN_PROCESO que un proceso interrumpido dejó sin cerrar."""
    limite = timezone.now() - timedelta(hours=horas)
    return LoteScrapingS3.objects.filter(
        institucion=institucion, estado_etl='EN_PROCESO', fecha_extraccion__lt=limite,
    ).update(estado_etl='ERROR', detalle_errores='Interrumpido: el proceso terminó sin cerrar el lote.')


def retirar_ofertas_obsoletas(institucion, ids_vigentes):
    """Elimina las ofertas que la institución ya no publica. Solo debe usarse tras una carga completa."""
    eliminadas, _ = OfertaAcademica.objects.filter(institucion=institucion).exclude(id__in=ids_vigentes).delete()
    return eliminadas


def avisar_lote(lote):
    """Avisa por correo (ADMINS = alertas@) cuando un lote termina en ERROR o PARCIAL.

    Un fallo del correo se registra en el log y no detiene el ETL: el estado ya quedó guardado en el lote.
    """
    if lote.estado_etl not in ('ERROR', 'PARCIAL'):
        return False
    asunto = f'ETL {lote.institucion.nombre}: lote {lote.id} terminó en {lote.estado_etl}'
    cuerpo = '\n'.join([
        f'Institución: {lote.institucion.nombre}',
        f'Lote: {lote.id} ({lote.fecha_extraccion:%Y-%m-%d %H:%M} UTC)',
        f'Estado: {lote.estado_etl}',
        f'Carreras válidas / extraídas: tasa {lote.tasa_exito} % de {lote.total_registros}',
        f'Ofertas cargadas: {lote.total_ofertas}',
        f'Errores: {lote.errores}',
        '',
        'ERROR: no se modificaron los datos publicados; el catálogo sigue con el último lote válido.'
        if lote.estado_etl == 'ERROR' else
        'PARCIAL: se cargó lo extraído, pero no se retiraron las ofertas obsoletas.',
        '',
        'Detalle de errores:',
        lote.detalle_errores or '(sin detalle)',
    ])
    try:
        mail_admins(asunto, cuerpo)
        return True
    except Exception:
        logger.exception('No se pudo enviar el aviso del lote %s', lote.id)
        return False


def motivo_para_omitir(institucion, dias, horas_entre_intentos=24):
    """Para ejecutar el scraper cada hora (--si-desactualizado): devuelve por qué NO correr ahora, o None.

    En AWS Learner Lab la EC2 solo está encendida durante las sesiones, así que un cron fijo (domingo 03:00 UTC)
    casi nunca coincide. Cada hora se revisa si hace falta: se corre si no hay un lote con carga en los últimos
    `dias` y no hubo otro intento (de cualquier resultado) en las últimas `horas_entre_intentos`, para no
    repetir cada hora un rastreo que falla ni enviar un aviso por hora.
    """
    ahora = timezone.now()
    lotes = LoteScrapingS3.objects.filter(institucion=institucion)
    ultimo_con_carga = (lotes.filter(estado_etl__in=ESTADOS_CON_CARGA)
                        .order_by('-fecha_extraccion').values_list('fecha_extraccion', flat=True).first())
    if ultimo_con_carga and ultimo_con_carga >= ahora - timedelta(days=dias):
        return f'el último lote con carga es del {ultimo_con_carga:%Y-%m-%d} (menos de {dias} días)'
    if lotes.filter(fecha_extraccion__gte=ahora - timedelta(hours=horas_entre_intentos)).exists():
        return f'ya hubo un intento en las últimas {horas_entre_intentos} horas'
    return None
