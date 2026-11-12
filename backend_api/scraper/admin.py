from django.contrib import admin
from scraper.models import (
    Institucion, LoteScrapingS3, Carrera, Sede, Jornada, OfertaAcademica,
    Usuario, HistorialChatRag, PreguntaIkigai, RespuestaUsuario, ResultadoVocacional,
)

admin.site.site_header = 'Mi Ayudante · Administración'
admin.site.site_title = 'Mi Ayudante'
admin.site.index_title = 'Catálogo, ETL y test vocacional'


# --- Catálogo -----------------------------------------------------------------

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'sitio_web')
    search_fields = ('nombre', 'codigo')


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre_carrera', 'institucion', 'nivel_formacion', 'duracion_semestres', 'duracion_texto')
    search_fields = ('nombre_carrera', 'titulo_otorgado')
    list_filter = ('institucion', 'nivel_formacion', 'duracion_semestres')
    list_select_related = ('institucion',)


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre_sede', 'institucion', 'region', 'direccion')
    search_fields = ('nombre_sede', 'direccion')
    list_filter = ('institucion', 'region')
    list_select_related = ('institucion',)


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = ('tipo_jornada', 'modalidad')
    list_filter = ('tipo_jornada', 'modalidad')


@admin.register(OfertaAcademica)
class OfertaAcademicaAdmin(admin.ModelAdmin):
    list_display = ('carrera', 'institucion', 'sede', 'jornada', 'duracion_texto', 'matricula_clp',
                    'arancel_anual_clp', 'aranceles_calculados', 'actualizado_en')
    search_fields = ('carrera__nombre_carrera', 'sede__nombre_sede')
    list_filter = ('institucion', 'aranceles_calculados', 'jornada__modalidad', 'jornada', 'sede__region')
    list_select_related = ('carrera', 'sede', 'jornada', 'institucion')
    raw_id_fields = ('carrera', 'sede', 'lote_scraping')
    readonly_fields = ('actualizado_en',)
    date_hierarchy = 'actualizado_en'


# --- ETL ----------------------------------------------------------------------

@admin.register(LoteScrapingS3)
class LoteScrapingS3Admin(admin.ModelAdmin):
    list_display = ('id', 'institucion', 'estado_etl', 'total_registros', 'total_ofertas', 'errores',
                    'tasa_exito', 'fecha_extraccion')
    list_filter = ('estado_etl', 'institucion')
    readonly_fields = ('fecha_extraccion',)
    date_hierarchy = 'fecha_extraccion'


# --- Test vocacional Ikigai ----------------------------------------------------

@admin.register(PreguntaIkigai)
class PreguntaIkigaiAdmin(admin.ModelAdmin):
    list_display = ('id', 'dimension', 'enunciado')
    list_filter = ('dimension',)
    search_fields = ('enunciado',)


@admin.register(RespuestaUsuario)
class RespuestaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'pregunta', 'puntaje_obtenido')
    list_filter = ('pregunta__dimension',)
    list_select_related = ('usuario', 'pregunta')
    raw_id_fields = ('usuario', 'pregunta')


@admin.register(ResultadoVocacional)
class ResultadoVocacionalAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'puntaje_pasion', 'puntaje_vocacion', 'puntaje_profesion',
                    'puntaje_mision', 'fecha_realizacion')
    list_select_related = ('usuario',)
    readonly_fields = ('fecha_realizacion',)
    date_hierarchy = 'fecha_realizacion'


# --- Usuarios del modelo propio y chat ------------------------------------------
# El login real usa los usuarios de Django (sección "Autenticación y autorización").
# Estas tablas son del modelo de datos del informe; se muestran solo para consulta.

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'rol')
    list_filter = ('rol',)
    search_fields = ('username', 'email')
    exclude = ('password_hash',)  # nunca mostrar el hash de la contraseña


@admin.register(HistorialChatRag)
class HistorialChatRagAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'pregunta_usuario', 'creado_en')
    search_fields = ('pregunta_usuario',)
    list_select_related = ('usuario',)
    readonly_fields = ('creado_en',)
    date_hierarchy = 'creado_en'
