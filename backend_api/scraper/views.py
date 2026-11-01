from django.http import JsonResponse
from scraper.models import OfertaAcademica

def api_catalogo_inacap(request):
    ofertas = OfertaAcademica.objects.select_related('carrera', 'sede', 'jornada', 'institucion').all()
    
    datos = []
    for oferta in ofertas:
        datos.append({
            "institucion": oferta.institucion.nombre,
            "carrera": oferta.carrera.nombre_carrera,
            "nivel": oferta.carrera.nivel_formacion,
            "duracion_semestres": oferta.carrera.duracion_semestres,
            "sede": oferta.sede.nombre_sede,
            "jornada": oferta.jornada.tipo_jornada,
            "valor_matricula": str(oferta.matricula_clp) if oferta.matricula_clp else "0",
            "valor_mensual": str(oferta.arancel_mensual_clp) if oferta.arancel_mensual_clp else None,
            "valor_anual": str(oferta.arancel_anual_clp) if oferta.arancel_anual_clp else None
        })
        
    return JsonResponse(datos, safe=False)