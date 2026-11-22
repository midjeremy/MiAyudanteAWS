from django.contrib import admin
from django.db.models import Count, Prefetch, Q
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from scraper.api_mallas import ruta_malla_pdf
from scraper.models import Institucion, LoteScrapingS3, Carrera, Mencion, Sede, Jornada, OfertaAcademica

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


class MencionInline(admin.TabularInline):
    model = Mencion
    extra = 0
    fields = ('nombre', 'competencias', 'url_malla', 's3_malla_pdf')


class TieneMencionesFilter(admin.SimpleListFilter):
    title = 'menciones'
    parameter_name = 'con_menciones'

    def lookups(self, request, model_admin):
        return (('si', 'Con menciones'), ('no', 'Sin menciones'))

    def queryset(self, request, queryset):
        if self.value() == 'si':
            return queryset.filter(total_menciones__gt=0)
        if self.value() == 'no':
            return queryset.filter(total_menciones=0)
        return queryset


class TieneMallaPdfFilter(admin.SimpleListFilter):
    title = 'malla en PDF'
    parameter_name = 'con_pdf'

    def lookups(self, request, model_admin):
        return (('si', 'Con PDF'), ('no', 'Sin PDF'))

    def queryset(self, request, queryset):
        sin_pdf = Q(s3_url_malla_pdf__isnull=True) | Q(s3_url_malla_pdf='')
        if self.value() == 'si':
            return queryset.exclude(sin_pdf)
        if self.value() == 'no':
            return queryset.filter(sin_pdf)
        return queryset


def enlace_externo(url, texto):
    return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, texto) if url else '—'


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    inlines = [MencionInline]
    list_display = ('nombre_carrera', 'institucion', 'lista_menciones', 'malla', 'area_estudio', 'nivel_formacion',
                    'duracion_texto')
    search_fields = ('nombre_carrera', 'nombre_base', 'titulo_otorgado', 'area_institucion', 'menciones__nombre')
    list_filter = ('institucion', TieneMencionesFilter, TieneMallaPdfFilter, 'area_estudio', 'nivel_formacion',
                   'duracion_semestres')
    list_select_related = ('institucion',)
    readonly_fields = ('enlaces_malla',)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .annotate(total_menciones=Count('menciones', distinct=True))
            .prefetch_related(Prefetch('menciones', queryset=Mencion.objects.only('id', 'carrera_id', 'nombre')))
        )

    @admin.display(description='Menciones', ordering='total_menciones')
    def lista_menciones(self, carrera):
        nombres = [m.nombre for m in carrera.menciones.all()]
        if not nombres:
            return '—'
        return format_html_join(mark_safe('<br>'), '• {}', ((n,) for n in nombres))

    @admin.display(description='Malla')
    def malla(self, carrera):
        pdf = ruta_malla_pdf(carrera)
        partes = [enlace_externo(carrera.url_malla, 'Sitio')] if carrera.url_malla else []
        if pdf:
            partes.append(enlace_externo(pdf, 'PDF'))
        return format_html_join(' · ', '{}', ((p,) for p in partes)) if partes else '—'

    @admin.display(description='Malla publicada')
    def enlaces_malla(self, carrera):
        return self.malla(carrera)


@admin.register(Mencion)
class MencionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'carrera', 'institucion', 'malla_propia', 'tiene_pdf')
    search_fields = ('nombre', 'carrera__nombre_carrera', 'carrera__nombre_base', 'competencias')
    list_filter = ('carrera__institucion',)
    list_select_related = ('carrera__institucion',)
    raw_id_fields = ('carrera',)
    ordering = ('carrera__nombre_carrera', 'nombre')

    @admin.display(description='Institución', ordering='carrera__institucion__nombre')
    def institucion(self, mencion):
        return mencion.carrera.institucion

    @admin.display(description='Malla propia')
    def malla_propia(self, mencion):
        return enlace_externo(mencion.url_malla, 'Ver en el sitio')

    @admin.display(description='PDF', boolean=True)
    def tiene_pdf(self, mencion):
        return bool(mencion.s3_malla_pdf)


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
