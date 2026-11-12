"""Cálculo del Test Ikigai con la escala Likert de 1 a 5.

Según el documento de validación, el sistema calcula un puntaje por dimensión y por
área y lo expresa como porcentaje de 0 % a 100 %: el promedio de las respuestas se
lleva a ese rango, de modo que 1 (muy en desacuerdo) = 0 % y 5 (muy de acuerdo) = 100 %.
"""
from .preguntas import AREAS, DIMENSIONES, GENERAL, VALOR_MAXIMO, VALOR_MINIMO


class RespuestasInvalidas(ValueError):
    """Las respuestas no cubren exactamente las preguntas o traen valores fuera de la escala."""


def porcentaje_likert(puntajes):
    """Promedio de respuestas 1-5 convertido a porcentaje 0-100, con dos decimales."""
    if not puntajes:
        return 0.0
    promedio = sum(puntajes) / len(puntajes)
    return round((promedio - VALOR_MINIMO) / (VALOR_MAXIMO - VALOR_MINIMO) * 100, 2)


def _valor_likert(valor):
    # bool es subclase de int: True no debe contar como 1
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str) and valor.strip().isdigit():
        valor = int(valor.strip())
    if isinstance(valor, int) and VALOR_MINIMO <= valor <= VALOR_MAXIMO:
        return valor
    return None


def normalizar_respuestas(respuestas, numeros_validos):
    """Valida {"numero": valor} y devuelve {numero(int): valor(int)}.

    Exige una respuesta por cada pregunta (todas son obligatorias) y ninguna extra.
    """
    if not isinstance(respuestas, dict) or not respuestas:
        raise RespuestasInvalidas('Envía las respuestas como un objeto {"número de pregunta": valor}.')

    limpias = {}
    for clave, valor in respuestas.items():
        try:
            numero = int(clave)
        except (TypeError, ValueError):
            raise RespuestasInvalidas(f'"{clave}" no es un número de pregunta.')
        if numero not in numeros_validos:
            raise RespuestasInvalidas(f'La pregunta {numero} no existe.')
        valor_ok = _valor_likert(valor)
        if valor_ok is None:
            raise RespuestasInvalidas(
                f'La respuesta a la pregunta {numero} debe ser un número entero de {VALOR_MINIMO} a {VALOR_MAXIMO}.'
            )
        limpias[numero] = valor_ok

    faltantes = sorted(set(numeros_validos) - set(limpias))
    if faltantes:
        raise RespuestasInvalidas('Faltan respuestas para las preguntas: ' + ', '.join(map(str, faltantes)) + '.')
    return limpias


def calcular_resultado(respuestas, preguntas):
    """Calcula el porcentaje por dimensión y por área.

    respuestas: {numero: valor 1-5}, ya validadas.
    preguntas: iterable de objetos o tuplas con numero, dimension y area.
    """
    por_dimension = {clave: [] for clave, _, _ in DIMENSIONES}
    por_area = {clave: [] for clave, _, _ in AREAS if clave != GENERAL}

    for pregunta in preguntas:
        valor = respuestas.get(pregunta.numero)
        if valor is None:
            continue
        por_dimension[pregunta.dimension].append(valor)
        # Los ítems generales miden la intensidad de la dimensión, no un área
        if pregunta.area != GENERAL:
            por_area[pregunta.area].append(valor)

    dimensiones = {clave: porcentaje_likert(valores) for clave, valores in por_dimension.items()}
    areas = {clave: porcentaje_likert(valores) for clave, valores in por_area.items()}
    return {'dimensiones': dimensiones, 'areas': areas}


def areas_ordenadas(puntajes_area):
    """Lista de áreas de mayor a menor coincidencia; en empate, el orden del documento."""
    orden = {clave: i for i, (clave, _, _) in enumerate(AREAS)}
    info = {clave: (nombre, ejemplos) for clave, nombre, ejemplos in AREAS}
    claves = sorted(puntajes_area, key=lambda c: (-puntajes_area[c], orden.get(c, len(orden))))
    return [
        {'clave': c, 'nombre': info[c][0], 'ejemplos': info[c][1], 'porcentaje': puntajes_area[c]}
        for c in claves if c in info
    ]
