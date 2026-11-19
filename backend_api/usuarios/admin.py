from django.contrib import admin

from .models import Consentimiento, SegundoFactor


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


@admin.register(SegundoFactor)
class SegundoFactorAdmin(admin.ModelAdmin):
    """Solo muestra si el doble factor está activo. El secreto y los códigos no se muestran nunca.

    Si alguien pierde el teléfono y sus códigos de recuperación, un administrador puede borrar el
    registro para que vuelva a entrar solo con la contraseña.
    """
    list_display = ('usuario', 'activo', 'creado_en')
    list_filter = ('activo',)
    search_fields = ('usuario__email',)
    fields = ('usuario', 'activo', 'creado_en')
    readonly_fields = ('usuario', 'activo', 'creado_en')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
