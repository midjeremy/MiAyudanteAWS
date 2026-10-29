import os
from openai import OpenAI
from django.db.models import Q
from scraper.models import OfertaAcademica 

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def recuperar_contexto(consulta_usuario):
    """Busca en PostgreSQL la información fáctica sobre carreras y aranceles"""
    palabras_clave = consulta_usuario.split()
    query = Q()
    
    for palabra in palabras_clave:
        if len(palabra) > 3:
            # Filtramos usando los campos exactos de la tabla del scraper
            query |= Q(carrera__nombre__icontains=palabra) | Q(institucion__nombre__icontains=palabra) | Q(sede__nombre__icontains=palabra)
    
    ofertas_encontradas = OfertaAcademica.objects.filter(query)[:5]
    
    if not ofertas_encontradas:
        return "No se encontró información estructurada en la base de datos sobre esta consulta."

    contexto = "Información académica oficial recuperada de la base de datos:\n"
    for oferta in ofertas_encontradas:
        contexto += f"- Institución: {oferta.institucion} | Carrera: {oferta.carrera} | Sede: {oferta.sede} | Arancel: ${oferta.arancel}.\n"
    
    return contexto

def generar_respuesta_rag(consulta_usuario):
    """Genera la respuesta con OpenAI usando el contexto de la BD"""
    contexto_factual = recuperar_contexto(consulta_usuario)

    prompt_sistema = (
        "Eres el asistente conversacional de 'Mi Ayudante'. "
        "Tu objetivo es responder utilizando ÚNICAMENTE el contexto fáctico proporcionado. "
        "Si la información no está en el contexto, indica que no la tienes."
    )

    respuesta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "system", "content": f"Contexto inyectado:\n{contexto_factual}"},
            {"role": "user", "content": consulta_usuario}
        ],
        temperature=0.2
    )

    return respuesta.choices[0].message.content