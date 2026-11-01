from decimal import Decimal

from django.db import transaction

from scraper.duoc.spider import normalizar_nombre_sede
from scraper.models import Carrera, Institucion, Jornada, OfertaAcademica, Sede


def obtener_institucion():
    institucion, _ = Institucion.objects.get_or_create(
        codigo='DUOC',
        defaults={'nombre': 'Duoc UC', 'sitio_web': 'https://www.duoc.cl'},
    )
    return institucion


@transaction.atomic
def cargar_items(items, institucion, lote=None, cuotas_anuales=None):
    """Carga en PostgreSQL los items extraídos y devuelve cuántas ofertas quedaron guardadas."""
    direcciones = {
        normalizar_nombre_sede(item['nombre']).lower(): item['direccion']
        for item in items if item['tipo'] == 'sede'
    }

    total_ofertas = 0
    for item in items:
        if item['tipo'] != 'carrera' or not item['nombre']:
            continue

        carrera, _ = Carrera.objects.update_or_create(
            nombre_carrera=item['nombre'],
            institucion=institucion,
            defaults={'duracion_semestres': item['duracion_semestres']},
        )

        for oferta in item['ofertas']:
            sede, _ = Sede.objects.get_or_create(
                nombre_sede=oferta['sede'],
                institucion=institucion,
                defaults={'region': oferta['region']},
            )
            direccion = direcciones.get(normalizar_nombre_sede(oferta['sede']).lower())
            if direccion and sede.direccion != direccion:
                sede.direccion = direccion
                sede.save(update_fields=['direccion'])

            arancel_mensual = oferta['arancel_mensual_clp']
            arancel_anual = None
            if cuotas_anuales and arancel_mensual:
                arancel_anual = Decimal(arancel_mensual) * cuotas_anuales

            for tipo_jornada in oferta['jornadas']:
                modalidad = 'Online' if tipo_jornada == 'Online' else 'Presencial'
                jornada, _ = Jornada.objects.get_or_create(
                    tipo_jornada=tipo_jornada,
                    defaults={'modalidad': modalidad},
                )
                OfertaAcademica.objects.update_or_create(
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
                total_ofertas += 1

    return total_ofertas
