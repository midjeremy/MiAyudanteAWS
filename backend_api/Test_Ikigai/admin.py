from django.contrib import admin

from .models import Pregunta, Resultado


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'dimension', 'area', 'enunciado')
    list_filter = ('dimension', 'area')


@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'puntaje_pasion', 'puntaje_vocacion', 'puntaje_profesion', 'puntaje_mision', 'creado_en')
    readonly_fields = ('creado_en',)
