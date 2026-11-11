from decimal import Decimal

from django.db import transaction

from scraper.catalogos import (
    clasificar_nivel, elegir_duracion, normalizar_jornada, parsear_duraciones, region_de_sede, semestres_publicados,
)
from scraper.duoc.spider import normalizar_nombre_sede
from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede

MINIMO_CARRERAS = 60

# Resolución VREG 10/2025 de Duoc UC: el "Arancel Semestral [se paga] hasta en 5 cuotas mensuales" y la
# matrícula comprende "dos valores semestrales iguales". El arancel mensual publicado es una de esas cuotas.
CUOTAS_POR_SEMESTRE = 5
PERIODO_MATRICULA = 'semestral'


def duraciones_del_item(item):
    """Duraciones publicadas; acepta lotes antiguos en S3 que solo traían 'duracion_semestres'."""
    if item.get('duraciones'):
        return parsear_duraciones(item['duraciones'])
    if item.get('duracion_semestres'):
        return parsear_duraciones([f"{item['duracion_semestres']} semestres"])
    return []


def obtener_institucion():
    institucion, _ = Institucion.objects.get_or_create(
        codigo='DUOC',
        defaults={'nombre': 'Duoc UC', 'sitio_web': 'https://www.duoc.cl'},
    )
    return institucion


def validar_items(items):
    """Separa las carreras completas de las que no se pueden publicar y explica por qué."""
    carreras = [item for item in items if item['tipo'] == 'carrera']
    validas, errores = [], []
    for carrera in carreras:
        if not carrera['nombre']:
            errores.append(f"Sin nombre: {carrera['url']}")
        elif not carrera['ofertas']:
            errores.append(f"Sin ofertas: {carrera['nombre']}")
        elif any(not o['sede'] or not o['arancel_mensual_clp'] or not o['matricula_clp'] for o in carrera['ofertas']):
            errores.append(f"Oferta incompleta: {carrera['nombre']}")
        else:
            validas.append(carrera)
    return validas, errores


@transaction.atomic
def cargar_items(items, institucion, lote=None, cuotas_por_semestre=CUOTAS_POR_SEMESTRE):
    """Carga las carreras válidas y devuelve los ids de las ofertas vigentes.

    Se guarda lo publicado (cuota mensual, matrícula semestral, duración en su unidad) y además los valores
    comparables: arancel semestral y anual calculados con las cuotas, y la duración en meses por modalidad.
    """
    direcciones = {
        normalizar_nombre_sede(item['nombre']).lower(): item['direccion']
        for item in items if item['tipo'] == 'sede'
    }
    validas, _ = validar_items(items)

    ids_vigentes = []
    for item in validas:
        duraciones = duraciones_del_item(item)
        semestres = semestres_publicados(duraciones)
        principal = elegir_duracion(duraciones, 'Presencial')
        carrera, _ = Carrera.objects.update_or_create(
            nombre_carrera=item['nombre'],
            institucion=institucion,
            defaults={
                'duracion_semestres': semestres,
                'duracion_texto': ' / '.join(d['texto'] for d in duraciones)[:200],
                'nivel_formacion': clasificar_nivel(item['nombre'], semestres, principal and principal['meses']),
                'url_malla': item.get('url_malla'),
                's3_url_malla_pdf': item.get('malla_s3'),
            },
        )

        for oferta in item['ofertas']:
            sede, _ = Sede.objects.get_or_create(nombre_sede=oferta['sede'], institucion=institucion)
            sede.region = region_de_sede(oferta['sede'])
            direccion = direcciones.get(normalizar_nombre_sede(oferta['sede']).lower())
            if direccion:
                sede.direccion = direccion
            sede.save(update_fields=['region', 'direccion'])

            arancel_mensual = oferta['arancel_mensual_clp']
            calculados = bool(cuotas_por_semestre and arancel_mensual)
            arancel_semestral = Decimal(arancel_mensual) * cuotas_por_semestre if calculados else None
            arancel_anual = arancel_semestral * 2 if calculados else None

            for texto_jornada in oferta['jornadas'] or ['']:
                tipo_jornada, modalidad = normalizar_jornada(texto_jornada, oferta['sede'])
                jornada, _ = Jornada.objects.update_or_create(
                    tipo_jornada=tipo_jornada,
                    defaults={'modalidad': modalidad},
                )
                duracion = elegir_duracion(duraciones, modalidad or 'Presencial')
                registro, _ = OfertaAcademica.objects.update_or_create(
                    institucion=institucion,
                    carrera=carrera,
                    sede=sede,
                    jornada=jornada,
                    defaults={
                        'lote_scraping': lote,
                        'matricula_clp': oferta['matricula_clp'],
                        'matricula_periodo': PERIODO_MATRICULA,
                        'arancel_mensual_clp': arancel_mensual,
                        'arancel_semestral_clp': arancel_semestral,
                        'arancel_anual_clp': arancel_anual,
                        'aranceles_calculados': calculados,
                        'duracion_texto': duracion['resumen'] if duracion else '',
                        'duracion_meses': duracion['meses'] if duracion else None,
                    },
                )
                ids_vigentes.append(registro.id)

    return ids_vigentes
