from decimal import Decimal

from django.db import transaction

from scraper.catalogos import clasificar_nivel, normalizar_jornada, region_de_sede
from scraper.duoc.spider import normalizar_nombre_sede
from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede

MINIMO_CARRERAS = 60


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
def cargar_items(items, institucion, lote=None, cuotas_anuales=None):
    """Carga las carreras válidas y devuelve los ids de las ofertas vigentes."""
    direcciones = {
        normalizar_nombre_sede(item['nombre']).lower(): item['direccion']
        for item in items if item['tipo'] == 'sede'
    }
    validas, _ = validar_items(items)

    ids_vigentes = []
    for item in validas:
        duracion = item['duracion_semestres']
        carrera, _ = Carrera.objects.update_or_create(
            nombre_carrera=item['nombre'],
            institucion=institucion,
            defaults={
                'duracion_semestres': duracion,
                'nivel_formacion': clasificar_nivel(item['nombre'], duracion),
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
            arancel_anual = Decimal(arancel_mensual) * cuotas_anuales if cuotas_anuales else None

            for texto_jornada in oferta['jornadas'] or ['']:
                tipo_jornada, modalidad = normalizar_jornada(texto_jornada, oferta['sede'])
                jornada, _ = Jornada.objects.update_or_create(
                    tipo_jornada=tipo_jornada,
                    defaults={'modalidad': modalidad},
                )
                registro, _ = OfertaAcademica.objects.update_or_create(
                    institucion=institucion,
                    carrera=carrera,
                    sede=sede,
                    jornada=jornada,
                    defaults={
                        'lote_scraping': lote,
                        'matricula_clp': oferta['matricula_clp'],
                        'arancel_mensual_clp': arancel_mensual,
                        'arancel_anual_clp': arancel_anual,
                    },
                )
                ids_vigentes.append(registro.id)

    return ids_vigentes
