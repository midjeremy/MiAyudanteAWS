from django.conf import settings
from django.db import models

from .preguntas import AREAS, DIMENSIONES

# Las tablas antiguas de scraper (PreguntaIkigai, RespuestaUsuario, ResultadoVocacional)
# apuntan a scraper.Usuario, que no es el usuario real del login. Por eso el test usa
# estos modelos, enlazados al usuario de django.contrib.auth.
OPCIONES_DIMENSION = [(clave, nombre) for clave, nombre, _ in DIMENSIONES]
OPCIONES_AREA = [(clave, nombre) for clave, nombre, _ in AREAS]


class Pregunta(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    enunciado = models.TextField()
    dimension = models.CharField(max_length=20, choices=OPCIONES_DIMENSION)
    area = models.CharField(max_length=20, choices=OPCIONES_AREA)

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f'{self.numero}. {self.enunciado}'


class Resultado(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resultados_ikigai'
    )
    # Porcentaje de 0 a 100 por dimensión
    puntaje_pasion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_vocacion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_profesion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_mision = models.DecimalField(max_digits=5, decimal_places=2)
    # {"tecnologia": 87.5, ...} y {"1": 4, ...}: respaldo para mostrar o recalcular
    puntajes_area = models.JSONField(default=dict)
    respuestas = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en', '-id']

    def __str__(self):
        return f'Resultado Ikigai de {self.usuario} ({self.creado_en:%Y-%m-%d})'
