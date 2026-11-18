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


class SegundoFactor(models.Model):
    """Doble factor con app autenticadora (TOTP, RFC 6238).

    Se usa TOTP y no un código por correo porque en AWS Learner Lab el envío de correos (SES) suele
    estar restringido. Los códigos de recuperación se guardan como hash: son de un solo uso y solo se
    muestran al titular una vez, al activar el doble factor.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='segundo_factor'
    )
    secreto = models.CharField(max_length=64, help_text='Secreto TOTP en base32.')
    activo = models.BooleanField(default=False)
    codigos_recuperacion = models.JSONField(
        default=list, blank=True, help_text='Hashes de los códigos de recuperación aún no usados.'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'segundo factor'
        verbose_name_plural = 'segundos factores'

    def __str__(self):
        estado = 'activo' if self.activo else 'pendiente'
        return f'Doble factor de {self.usuario} ({estado})'
