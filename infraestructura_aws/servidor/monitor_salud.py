"""Monitor sintético (SLA 01): consulta /health/deep y publica el resultado en CloudWatch.

Lo ejecuta cron cada minuto (archivo miayudante-monitor). Publica en el espacio "MiAyudante":
  HealthDeep   -> 1 si /health/deep respondió 200, 0 si no
  HealthDeepMs -> tiempo total de la consulta en milisegundos
Las credenciales salen del rol de la instancia (LabInstanceProfile). Solo escribe en el log si algo falla.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import boto3

RAIZ = Path(__file__).resolve().parents[2]
REGION = os.environ.get('AWS_REGION_MONITOR', 'us-east-1')


def leer_dominio():
    """DOMINIO del .env de la raíz (lo escribe el deploy cuando hay HTTPS)."""
    try:
        for linea in (RAIZ / '.env').read_text(encoding='utf8').splitlines():
            if linea.startswith('DOMINIO='):
                return linea.split('=', 1)[1].strip()
    except OSError:
        pass
    return ''


def consultar(url):
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as respuesta:
            codigo, cuerpo = respuesta.status, respuesta.read(2000)
    except urllib.error.HTTPError as error:
        codigo, cuerpo = error.code, error.read(2000)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        codigo, cuerpo = 0, str(error).encode()
    return codigo, cuerpo, round((time.perf_counter() - inicio) * 1000)


def main():
    dominio = leer_dominio()
    url = f'https://{dominio}/health/deep' if dominio else 'http://127.0.0.1/health/deep'
    codigo, cuerpo, milisegundos = consultar(url)
    exito = codigo == 200

    boto3.client('cloudwatch', region_name=REGION).put_metric_data(
        Namespace='MiAyudante',
        MetricData=[
            {'MetricName': 'HealthDeep', 'Value': 1 if exito else 0, 'Unit': 'Count'},
            {'MetricName': 'HealthDeepMs', 'Value': milisegundos, 'Unit': 'Milliseconds'},
        ],
    )
    if not exito:
        detalle = cuerpo.decode('utf8', 'replace')[:300]
        print(json.dumps({'hora': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'url': url,
                          'codigo': codigo, 'ms': milisegundos, 'detalle': detalle}, ensure_ascii=False))


if __name__ == '__main__':
    main()
