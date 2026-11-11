import json
import re
import time
import unicodedata
from functools import cache, reduce
from itertools import zip_longest
from operator import or_

from django.conf import settings
from django.db.models import Q
from openai import OpenAI

from scraper.models import Institucion, OfertaAcademica

MODELO = "gpt-4o-mini"
# Veces que el modelo puede consultar el catálogo antes de responder
MAX_RONDAS_BUSQUEDA = 4
# Segundos para responder: chat.php espera 50 y Nginx 60
TIEMPO_MAXIMO = 40
MAX_OFERTAS_LEIDAS = 400
MAX_CARRERAS = 25
MAX_SEDES = 12

VARIANTES_LETRAS = {"a": "[aá]", "e": "[eé]", "i": "[ií]", "o": "[oó]", "u": "[uúü]", "n": "[nñ]"}

CAMPOS_COSTO = [
    ("arancel_anual", "arancel_anual_clp"),
    ("arancel_semestral", "arancel_semestral_clp"),
    ("arancel_mensual", "arancel_mensual_clp"),
    ("matricula", "matricula_clp"),
]

PROMPT_SISTEMA = """Eres el asistente de 'Mi Ayudante', una plataforma chilena que ayuda a estudiantes a elegir carrera. \
Responde en español, con un tono cercano y claro.

Tienes acceso al catálogo oficial de la plataforma con la herramienta buscar_carreras. \
Instituciones del catálogo: {instituciones}.

Reglas:
- Ante cualquier pregunta sobre carreras, aranceles, matrículas, sedes, jornadas o duración, usa buscar_carreras antes de responder. \
Puedes llamarla varias veces, por ejemplo una vez por institución o con otros términos si no encuentras resultados.
- Si la persona cuenta sus gustos o intereses (por ejemplo, "me gusta crear programas"), deduce qué carreras se relacionan \
(en ese caso informática, programación, desarrollo de software, ciberseguridad) y búscalas.
- Cuando pidan comparar, compara tú con los datos obtenidos: carreras disponibles, duración, aranceles, matrícula, jornadas y sedes. \
Señala las diferencias concretas y termina con una sugerencia breve según lo que contó la persona.
- No le pidas a la persona que revise por su cuenta las páginas de las instituciones: tu trabajo es entregarle esa información.
- Todo dato concreto debe salir de los resultados de buscar_carreras. Nunca lo inventes ni lo estimes. \
Si algo no está en el catálogo, dilo.
- El chat es pequeño: responde en unas 150 palabras como máximo, en texto plano sin Markdown (sin asteriscos ni #). \
Para listas usa guiones."""

HERRAMIENTAS = [{
    "type": "function",
    "function": {
        "name": "buscar_carreras",
        "description": (
            "Busca en el catálogo de Mi Ayudante y devuelve las carreras agrupadas por institución, con duración, "
            "título, sedes, jornadas, aranceles y matrícula. Todos los filtros son opcionales, pero se debe usar al menos uno."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "terminos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Palabras o raíces que se buscan en el nombre de la carrera; basta con que coincida una. "
                        "Usa raíces cortas para abarcar variantes, por ejemplo ['informat', 'program', 'software'] o ['enfermer']."
                    ),
                },
                "instituciones": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Instituciones del catálogo para filtrar, por ejemplo ['Duoc UC'].",
                },
                "sede": {"type": "string", "description": "Sede, comuna o región, por ejemplo 'Maipú'."},
                "jornada": {"type": "string", "description": "Jornada o modalidad, por ejemplo 'Vespertina' u 'Online'."},
            },
            "additionalProperties": False,
        },
    },
}]


def quitar_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra))


def normalizar(texto):
    """Minúsculas, sin tildes ni signos: 'Duoc-UC!' queda 'duoc uc'."""
    if not isinstance(texto, str):
        return ""
    limpio = re.sub(r"[^\w\s]", " ", quitar_tildes(texto.lower()))
    return " ".join(limpio.split())


def como_lista(valor):
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        return []
    return [texto for texto in (normalizar(v) for v in valor) if texto]


def patron_flexible(texto):
    """Permite que 'informatica' encuentre 'Informática' y 'diseno' encuentre 'Diseño'."""
    return "".join(VARIANTES_LETRAS.get(letra, letra) for letra in texto)


def ids_instituciones(nombres):
    """Acepta variantes como 'duocUC', 'Duoc' o 'inacap'."""
    buscados = [nombre.replace(" ", "") for nombre in nombres]
    return [
        institucion.id
        for institucion in Institucion.objects.all()
        if any(
            buscado in normalizar(institucion.nombre).replace(" ", "")
            or buscado == normalizar(institucion.codigo).replace(" ", "")
            for buscado in buscados
        )
    ]


def formatear_clp(valor):
    return f"${valor:,.0f}".replace(",", ".")


def rango_clp(valores):
    menor, mayor = min(valores), max(valores)
    if menor == mayor:
        return formatear_clp(menor)
    return f"desde {formatear_clp(menor)} hasta {formatear_clp(mayor)}"


def resumir_carrera(grupo):
    resumen = {"institucion": grupo["institucion"], "carrera": grupo["carrera"]}
    if grupo["duracion"]:
        resumen["duracion"] = f"{grupo['duracion']} semestres"
    if grupo["titulo"]:
        resumen["titulo"] = grupo["titulo"]

    sedes = sorted(grupo["sedes"])
    resumen["sedes"] = sedes[:MAX_SEDES]
    if len(sedes) > MAX_SEDES:
        resumen["otras_sedes"] = len(sedes) - MAX_SEDES
    resumen["jornadas"] = sorted(grupo["jornadas"])

    for nombre, valores in grupo["costos"].items():
        if valores:
            resumen[nombre] = rango_clp(valores)
    return resumen


def buscar_carreras(terminos=None, instituciones=None, sede="", jornada=""):
    """Herramienta del asistente: consulta el catálogo y agrupa las ofertas por carrera."""
    terminos = como_lista(terminos)
    nombres_instituciones = como_lista(instituciones)
    sede = normalizar(sede)
    jornada = normalizar(jornada)

    if not (terminos or nombres_instituciones or sede or jornada):
        return {"error": "Indica al menos un criterio: términos de la carrera, institución, sede o jornada."}

    ofertas = OfertaAcademica.objects.select_related("institucion", "carrera", "sede", "jornada")
    if terminos:
        ofertas = ofertas.filter(
            reduce(or_, (Q(carrera__nombre_carrera__iregex=patron_flexible(t)) for t in terminos))
        )
    if nombres_instituciones:
        ofertas = ofertas.filter(institucion_id__in=ids_instituciones(nombres_instituciones))
    if sede:
        patron = patron_flexible(sede)
        ofertas = ofertas.filter(Q(sede__nombre_sede__iregex=patron) | Q(sede__region__iregex=patron))
    if jornada:
        patron = patron_flexible(jornada)
        ofertas = ofertas.filter(Q(jornada__tipo_jornada__iregex=patron) | Q(jornada__modalidad__iregex=patron))

    ofertas = list(
        ofertas.order_by("institucion__nombre", "carrera__nombre_carrera", "sede__nombre_sede", "id")[:MAX_OFERTAS_LEIDAS]
    )

    grupos = {}
    for oferta in ofertas:
        clave = (oferta.institucion.nombre, oferta.carrera.nombre_carrera)
        grupo = grupos.setdefault(clave, {
            "institucion": oferta.institucion.nombre,
            "carrera": oferta.carrera.nombre_carrera,
            "duracion": oferta.carrera.duracion_semestres,
            "titulo": oferta.carrera.titulo_otorgado,
            "sedes": set(),
            "jornadas": set(),
            "costos": {nombre: [] for nombre, _ in CAMPOS_COSTO},
        })
        grupo["sedes"].add(oferta.sede.nombre_sede)
        grupo["jornadas"].add(oferta.jornada.tipo_jornada)
        for nombre, campo in CAMPOS_COSTO:
            valor = getattr(oferta, campo)
            if valor is not None:
                grupo["costos"][nombre].append(valor)

    if not grupos:
        disponibles = list(Institucion.objects.order_by("nombre").values_list("nombre", flat=True))
        return {
            "total_carreras": 0,
            "aviso": "No hay resultados. Prueba con otros términos o raíces más cortas.",
            "instituciones_disponibles": disponibles,
        }

    # Al recortar se alternan las instituciones para que una comparación no quede solo con una
    por_institucion = {}
    for grupo in grupos.values():
        por_institucion.setdefault(grupo["institucion"], []).append(grupo)
    intercaladas = [grupo for fila in zip_longest(*por_institucion.values()) for grupo in fila if grupo]

    resultado = {
        "total_carreras": len(grupos),
        "carreras": [resumir_carrera(grupo) for grupo in intercaladas[:MAX_CARRERAS]],
    }
    if len(grupos) > MAX_CARRERAS or len(ofertas) == MAX_OFERTAS_LEIDAS:
        resultado["aviso"] = "Hay más resultados de los que se muestran: usa términos, institución o sede más específicos."
    return resultado


def ejecutar_herramienta(llamada):
    if llamada.function.name != "buscar_carreras":
        resultado = {"error": f"La herramienta {llamada.function.name} no existe."}
    else:
        try:
            argumentos = json.loads(llamada.function.arguments or "{}")
        except json.JSONDecodeError:
            argumentos = None
        if isinstance(argumentos, dict):
            resultado = buscar_carreras(
                argumentos.get("terminos"), argumentos.get("instituciones"),
                argumentos.get("sede", ""), argumentos.get("jornada", ""),
            )
        else:
            resultado = {"error": "Los argumentos deben ser un objeto JSON."}
    return json.dumps(resultado, ensure_ascii=False)


def prompt_sistema():
    nombres = list(Institucion.objects.order_by("nombre").values_list("nombre", flat=True))
    return PROMPT_SISTEMA.format(instituciones=", ".join(nombres) or "ninguna cargada todavía")


@cache
def obtener_cliente():
    # Se crea al primer uso: sin clave solo falla el chat, no el resto de la API
    return OpenAI(api_key=settings.OPENAI_API_KEY, max_retries=0)


def generar_respuesta_rag(consulta_usuario, historial=()):
    """Responde con OpenAI. El modelo consulta el catálogo con buscar_carreras las veces que necesite."""
    cliente = obtener_cliente()
    mensajes = [
        {"role": "system", "content": prompt_sistema()},
        *historial,
        {"role": "user", "content": consulta_usuario},
    ]
    inicio = time.monotonic()

    for ronda in range(MAX_RONDAS_BUSQUEDA + 1):
        restante = TIEMPO_MAXIMO - (time.monotonic() - inicio)
        # En la última ronda, o con poco tiempo, se le pide responder con lo que ya encontró
        ultima = ronda == MAX_RONDAS_BUSQUEDA or restante < 15
        respuesta = cliente.chat.completions.create(
            model=MODELO,
            messages=mensajes,
            tools=HERRAMIENTAS,
            tool_choice="none" if ultima else "auto",
            temperature=0.2,
            timeout=max(restante, 5),
        )
        mensaje = respuesta.choices[0].message

        if ultima or not mensaje.tool_calls:
            return mensaje.content or "No pude generar una respuesta. ¿Puedes intentarlo de nuevo?"

        mensajes.append({
            "role": "assistant",
            "content": mensaje.content,
            "tool_calls": [
                {
                    "id": llamada.id,
                    "type": "function",
                    "function": {"name": llamada.function.name, "arguments": llamada.function.arguments},
                }
                for llamada in mensaje.tool_calls
            ],
        })
        mensajes.extend(
            {"role": "tool", "tool_call_id": llamada.id, "content": ejecutar_herramienta(llamada)}
            for llamada in mensaje.tool_calls
        )
