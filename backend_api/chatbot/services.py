import re
import unicodedata
from functools import cache, reduce
from operator import add

from django.conf import settings
from django.db.models import Case, IntegerField, Q, Value, When
from openai import OpenAI

from scraper.models import OfertaAcademica

MODELO = "gpt-4o-mini"
MAX_OFERTAS = 15
MAX_PALABRAS = 8

# Palabras frecuentes en las preguntas que no ayudan a encontrar una carrera
PALABRAS_IGNORADAS = {
    "algo", "algun", "alguna", "ahora", "anual", "aqui", "arancel", "aranceles", "ayuda", "ayudar",
    "buenas", "buenos", "carrera", "carreras", "como", "comparar", "costo", "costos",
    "cual", "cuales", "cuando", "cuanto", "cuanta", "cuesta", "cuestan", "dame", "desde", "donde",
    "dura", "duracion", "esta", "estas", "este", "estos", "estudiar", "gracias", "hola",
    "informacion", "institucion", "instituciones", "matricula", "mejor", "mensual", "necesito",
    "ofrece", "ofrecen", "para", "pero", "precio", "precios", "puede", "puedes", "puedo", "quiero",
    "quisiera", "saber", "sede", "sedes", "semestral", "sobre", "tiene", "tienen", "valor", "valores",
}

VARIANTES_LETRAS = {"a": "[aá]", "e": "[eé]", "i": "[ií]", "o": "[oó]", "u": "[uúü]", "n": "[nñ]"}

PROMPT_SISTEMA = (
    "Eres el asistente conversacional de 'Mi Ayudante', una plataforma chilena de orientación "
    "para estudiantes que eligen carrera. Responde en español, con un tono cercano y en pocas frases. "
    "Puedes saludar y orientar de forma general sobre cómo elegir una carrera. "
    "Todo dato concreto (aranceles, matrículas, sedes, jornadas, duraciones o instituciones) debe salir "
    "ÚNICAMENTE del contexto entregado: nunca lo inventes ni lo estimes. "
    "Si el dato no está en el contexto, di que no lo tienes y pide más detalles, como la carrera, "
    "la institución o la sede. "
    "Escribe en texto plano, sin Markdown."
)


def quitar_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra))


def extraer_palabras(texto):
    """Devuelve las palabras útiles para buscar, sin tildes y sin repetir."""
    palabras = (quitar_tildes(palabra) for palabra in re.findall(r"\w+", texto.lower()))
    utiles = [palabra for palabra in palabras if len(palabra) > 3 and palabra not in PALABRAS_IGNORADAS]
    return list(dict.fromkeys(utiles))


def patron_flexible(palabra):
    """Permite que 'informatica' encuentre 'Informática' y 'diseno' encuentre 'Diseño'."""
    return "".join(VARIANTES_LETRAS.get(letra, letra) for letra in palabra)


def filtro_palabra(palabra):
    patron = patron_flexible(palabra)
    return (
        Q(carrera__nombre_carrera__iregex=patron)
        | Q(institucion__nombre__iregex=patron)
        | Q(sede__nombre_sede__iregex=patron)
        | Q(sede__region__iregex=patron)
        | Q(jornada__tipo_jornada__iregex=patron)
    )


def formatear_clp(valor):
    return f"${valor:,.0f}".replace(",", ".")


def describir_oferta(oferta):
    datos = [
        f"Institución: {oferta.institucion}",
        f"Carrera: {oferta.carrera}",
        f"Sede: {oferta.sede}",
        f"Jornada: {oferta.jornada}",
    ]
    if oferta.jornada.modalidad:
        datos.append(f"Modalidad: {oferta.jornada.modalidad}")
    if oferta.carrera.duracion_semestres:
        datos.append(f"Duración: {oferta.carrera.duracion_semestres} semestres")

    costos = [
        ("Arancel anual", oferta.arancel_anual_clp),
        ("Arancel semestral", oferta.arancel_semestral_clp),
        ("Arancel mensual", oferta.arancel_mensual_clp),
        ("Matrícula", oferta.matricula_clp),
    ]
    datos += [f"{nombre}: {formatear_clp(valor)}" for nombre, valor in costos if valor is not None]
    return "- " + " | ".join(datos)


def recuperar_contexto(consulta_usuario, pregunta_anterior=""):
    """Busca en PostgreSQL la información fáctica sobre carreras y aranceles."""
    palabras = extraer_palabras(consulta_usuario)
    # "¿Y en Maipú?" o "¿cuánto dura?" solo se entienden junto con la pregunta anterior
    if len(palabras) < 2:
        palabras += [p for p in extraer_palabras(pregunta_anterior) if p not in palabras]
    palabras = palabras[:MAX_PALABRAS]

    if not palabras:
        return "No se buscó en la base de datos: el mensaje no menciona carreras, instituciones ni sedes."

    # Primero las ofertas que coinciden con más palabras de la pregunta
    puntajes = [
        Case(When(filtro_palabra(palabra), then=Value(1)), default=Value(0), output_field=IntegerField())
        for palabra in palabras
    ]
    ofertas = (
        OfertaAcademica.objects
        .select_related("institucion", "carrera", "sede", "jornada")
        .annotate(coincidencias=reduce(add, puntajes))
        .filter(coincidencias__gt=0)
        .order_by("-coincidencias", "carrera__nombre_carrera", "sede__nombre_sede", "id")[:MAX_OFERTAS]
    )

    lineas = [describir_oferta(oferta) for oferta in ofertas]
    if not lineas:
        return "No se encontró información en la base de datos sobre esta consulta."
    return "Información académica oficial recuperada de la base de datos:\n" + "\n".join(lineas)


@cache
def obtener_cliente():
    # Se crea al primer uso: sin clave solo falla el chat, no el resto de la API.
    # El tiempo máximo debe ser menor que el que espera chat.php (35 s en total).
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=15, max_retries=1)


def generar_respuesta_rag(consulta_usuario, historial=()):
    """Genera la respuesta con OpenAI usando el contexto de la BD y la conversación previa."""
    preguntas_previas = [turno["content"] for turno in historial if turno["role"] == "user"]
    pregunta_anterior = preguntas_previas[-1] if preguntas_previas else ""
    contexto_factual = recuperar_contexto(consulta_usuario, pregunta_anterior)

    respuesta = obtener_cliente().chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "system", "content": f"Contexto inyectado:\n{contexto_factual}"},
            *historial,
            {"role": "user", "content": consulta_usuario},
        ],
        temperature=0.2,
    )

    return respuesta.choices[0].message.content
