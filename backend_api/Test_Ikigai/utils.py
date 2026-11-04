#calculo del test ikigai con la escala de likert de 1 a 5.
def calcularvuser(respuestas):
    #se definen las  dimenciones
    dimensiones = {
        "Pasion": [],
        "Vocacion": [],
        "Profesion": [],
        "Mision": []
    }

    for respuesta in respuestas:
        dim = respuesta.get("dimension")
        puntaje = respuesta.get("puntaje")

        if dim in dimensiones and isinstance(puntaje, (int, float)) and 1 <= puntaje <= 5:
            dimensiones[dim].append(puntaje)

    vector_postulante = {}
    #el procesamiento de los puntajes acumulados por cada dimencion
    for dim, puntajes in dimensiones.items():
        if puntajes:
            promedio = sum(puntajes) / len(puntajes)
            normalizado = ((promedio - 1)/4) * 100
            vector_postulante[dim] = round(normalizado, 2)
        else:
            vector_postulante[dim] = 0.0

    return vector_postulante