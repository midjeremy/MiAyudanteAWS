from django.conf import settings
from django.db import models


class Consentimiento(models.Model):
    """Constancia de que el titular aceptó la política de privacidad (Ley N.° 21.719).

    La ley exige que el responsable pueda demostrar el consentimiento: quién lo dio, sobre qué
    versión de la política y cuándo. Por minimización no se guarda la IP ni otros datos.
    Se elimina junto con la cuenta.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consentimientos'
    )
    version_politica = models.CharField(max_length=20)
    declara_edad_minima = models.BooleanField(
        help_text='El titular declaró tener la edad mínima para crear una cuenta (14 años).'
    )
    aceptado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-aceptado_en', '-id']
        verbose_name = 'consentimiento'
        verbose_name_plural = 'consentimientos'

    def __str__(self):
        return f'{self.usuario} aceptó la política {self.version_politica}'
