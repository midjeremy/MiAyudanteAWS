"""Elimina las cuentas sin acceso durante el plazo de conservación (Ley N.° 21.719, proporcionalidad).

Los datos personales no se guardan más tiempo del necesario para su finalidad: una cuenta que no
se usa en MESES_INACTIVIDAD_PARA_BORRAR se elimina con sus resultados del test y consentimientos.
Las cuentas del equipo (staff o superusuario) nunca se borran por esta vía.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from usuarios.privacidad import MESES_INACTIVIDAD_PARA_BORRAR


def cuentas_inactivas(meses=MESES_INACTIVIDAD_PARA_BORRAR):
    limite = timezone.now() - timedelta(days=round(meses * 30.44))
    return get_user_model().objects.filter(is_staff=False, is_superuser=False).filter(
        # Sin acceso desde el límite, o nunca inició sesión y la cuenta es anterior al límite
        Q(last_login__lt=limite) | Q(last_login__isnull=True, date_joined__lt=limite)
    )


class Command(BaseCommand):
    help = 'Elimina las cuentas sin acceso en el plazo de conservación (por defecto 24 meses).'

    def add_arguments(self, parser):
        parser.add_argument('--meses', type=int, default=MESES_INACTIVIDAD_PARA_BORRAR,
                            help='Meses sin acceso a partir de los cuales se elimina la cuenta')
        parser.add_argument('--simular', action='store_true', help='Solo informa cuántas cuentas se borrarían')

    def handle(self, *args, **opciones):
        cuentas = cuentas_inactivas(opciones['meses'])
        total = cuentas.count()
        if opciones['simular']:
            self.stdout.write(f'Se eliminarían {total} cuenta(s) sin acceso en {opciones["meses"]} meses.')
            return
        cuentas.delete()  # resultados del test y consentimientos se borran en cascada
        # Solo la cantidad: el registro de la tarea no guarda correos ni nombres
        self.stdout.write(self.style.SUCCESS(f'Cuentas inactivas eliminadas: {total}.'))
