from django.contrib import admin
from scraper.models import Institucion, LoteScrapingS3, Carrera, Sede, Jornada, OfertaAcademica

admin.site.site_header = 'Mi Ayudante · Administración'
admin.site.site_title = 'Mi Ayudante'
admin.site.index_title = 'Catálogo, ETL, test vocacional y usuarios'

# Los modelos antiguos de scraper (Usuario, PreguntaIkigai, RespuestaUsuario, ResultadoVocacional y
# HistorialChatRag) no se registran: están vacíos y duplicaban secciones reales del admin.
#   - Usuarios: "Autenticación y autorización" (usuario de Django, el que usa el login)
#   - Preguntas y resultados del test: "Test vocacional Ikigai"


# --- Catálogo -----------------------------------------------------------------

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'sitio_web')
    search_fields = ('nombre', 'codigo')


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre_carrera', 'institucion', 'area_estudio', 'area_institucion', 'nivel_formacion',
                    'duracion_semestres', 'duracion_texto')
    search_fields = ('nombre_carrera', 'titulo_otorgado', 'area_institucion')
    list_filter = ('institucion', 'area_estudio', 'nivel_formacion', 'duracion_semestres')
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
    """Los lotes los crea el pipeline: se consultan (evidencia del KPI-01), no se crean ni editan a mano."""
    list_display = ('id', 'institucion', 'estado_etl', 'total_registros', 'total_ofertas', 'errores',
                    'tasa_exito', 'fecha_extraccion')
    list_filter = ('estado_etl', 'institucion')
    list_select_related = ('institucion',)
    date_hierarchy = 'fecha_extraccion'
    readonly_fields = ('institucion', 'estado_etl', 'fecha_extraccion', 'total_registros', 'total_ofertas',
                       'errores', 'tasa_exito', 's3_url_json_raw', 'detalle_errores')

    def has_add_permission(self, request):
        return False
