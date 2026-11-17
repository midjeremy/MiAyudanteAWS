"""Parámetros de la adecuación a la Ley N.° 21.719 (protección de datos personales).

Se cambian aquí cuando cambie la política de privacidad o los plazos acordados por el equipo.
"""

# Versión vigente de la política de privacidad publicada en el sitio. Al cambiar el texto de la
# política se sube la versión: los usuarios con una versión anterior deben aceptarla de nuevo.
VERSION_POLITICA = '2026-11'

# Art. 16 quáter: desde los 14 años el adolescente puede consentir por sí mismo el tratamiento
# de sus datos (no sensibles). Las cuentas se crean solo desde esa edad; los menores de 14 usan
# la plataforma sin cuenta, sin que se guarden datos suyos.
EDAD_MINIMA_CUENTA = 14

# Principio de proporcionalidad (plazo de conservación): una cuenta sin acceso en este periodo
# se elimina junto con sus resultados del test.
MESES_INACTIVIDAD_PARA_BORRAR = 24
