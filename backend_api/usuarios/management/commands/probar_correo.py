"""Envía un correo de prueba para comprobar la configuración SMTP del .env (SMTP_HOST, SMTP_USUARIO, ...).

Uso en la EC2:  venv/bin/python manage.py probar_correo            (a CORREO_ALERTAS)
                venv/bin/python manage.py probar_correo otra@direccion.cl
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Envía un correo de prueba con la configuración SMTP actual.'

    def add_arguments(self, parser):
        parser.add_argument('destino', nargs='?', default=None,
                            help='Dirección de destino (por defecto CORREO_ALERTAS)')

    def handle(self, *args, **opciones):
        destino = opciones['destino'] or settings.CORREO_ALERTAS
        if not settings.SMTP_HOST:
            self.stdout.write(self.style.WARNING(
                'SMTP_HOST no está definido en el .env: el correo se escribe en la consola y no sale del servidor.'))
        try:
            send_mail(
                f'{settings.EMAIL_SUBJECT_PREFIX}Correo de prueba',
                f'Prueba de envío desde Mi Ayudante ({timezone.now():%Y-%m-%d %H:%M} UTC).\n'
                f'Remitente configurado: {settings.DEFAULT_FROM_EMAIL}',
                None,
                [destino],
            )
        except Exception as error:
            # El mensaje del servidor SMTP (credenciales, TLS, puerto) es lo que hace falta para corregirlo
            raise CommandError(f'No se pudo enviar el correo a {destino}: {error}') from error
        self.stdout.write(self.style.SUCCESS(f'Correo de prueba enviado a {destino}.'))
