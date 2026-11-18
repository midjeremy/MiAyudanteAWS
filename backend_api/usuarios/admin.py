from django.contrib import admin

from .models import Consentimiento


@admin.register(Consentimiento)
class ConsentimientoAdmin(admin.ModelAdmin):
    """Evidencia del consentimiento (Ley N.° 21.719): se consulta, no se crea ni se edita a mano."""
    list_display = ('usuario', 'version_politica', 'declara_edad_minima', 'aceptado_en')
    list_filter = ('version_politica',)
    search_fields = ('usuario__email',)
    readonly_fields = ('usuario', 'version_politica', 'declara_edad_minima', 'aceptado_en')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
