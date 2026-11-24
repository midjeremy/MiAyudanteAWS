from django.db import migrations

CAMPOS = ('matricula_clp', 'arancel_mensual_clp', 'arancel_semestral_clp', 'arancel_anual_clp')


def ceros_a_nulo(apps, schema_editor):
    """El scraper de INACAP guardaba $0 cuando la institución no publicaba el valor: pasa a NULL (no publicado).

    Con $0 la tarjeta de la carrera mostraba «arancel desde $0» y el comparador lo tomaba como el más barato.
    """
    oferta = apps.get_model('scraper', 'OfertaAcademica')
    for campo in CAMPOS:
        oferta.objects.filter(**{campo: 0}).update(**{campo: None})


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0012_mallas_digitales_inacap'),
    ]

    operations = [
        migrations.RunPython(ceros_a_nulo, migrations.RunPython.noop),
    ]
