from django.contrib import admin
from scraper.models import Institucion, LoteScrapingS3, Carrera, Sede, Jornada, OfertaAcademica

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'sitio_web')
    search_fields = ('nombre', 'codigo')

@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre_carrera', 'nivel_formacion', 'duracion_semestres')
    search_fields = ('nombre_carrera',)
    list_filter = ('nivel_formacion', 'duracion_semestres')

@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre_sede', 'region', 'direccion')
    search_fields = ('nombre_sede',)
    list_filter = ('region',)

@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = ('tipo_jornada', 'modalidad')
    list_filter = ('tipo_jornada', 'modalidad')

@admin.register(OfertaAcademica)
class OfertaAcademicaAdmin(admin.ModelAdmin):
    list_display = ('carrera', 'sede', 'jornada', 'matricula_clp', 'arancel_anual_clp')
    search_fields = ('carrera__nombre_carrera', 'sede__nombre_sede')
    list_filter = ('sede', 'jornada')
    list_select_related = ('carrera', 'sede', 'jornada', 'institucion') 

@admin.register(LoteScrapingS3)
class LoteScrapingS3Admin(admin.ModelAdmin):
    list_display = ('id', 'institucion', 'estado_etl', 'total_registros', 'fecha_extraccion')
    list_filter = ('estado_etl', 'institucion')