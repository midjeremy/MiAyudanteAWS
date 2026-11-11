from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from scraper.models import OfertaAcademica


class OfertaSerializer(serializers.ModelSerializer):
    """Oferta lista para el BFF: incluye institución, carrera, sede y aranceles en un solo objeto."""
    institucion = serializers.CharField(source='institucion.nombre')
    institucion_codigo = serializers.CharField(source='institucion.codigo')
    carrera_id = serializers.IntegerField(source='carrera.id')
    carrera = serializers.CharField(source='carrera.nombre_carrera')
    nivel = serializers.CharField(source='carrera.nivel_formacion')
    titulo = serializers.CharField(source='carrera.titulo_otorgado')
    duracion_semestres = serializers.IntegerField(source='carrera.duracion_semestres')
    malla_url = serializers.CharField(source='carrera.url_malla')
    sede = serializers.CharField(source='sede.nombre_sede')
    region = serializers.CharField(source='sede.region')
    direccion = serializers.CharField(source='sede.direccion')
    jornada = serializers.CharField(source='jornada.tipo_jornada')
    modalidad = serializers.CharField(source='jornada.modalidad')
    valor_matricula = serializers.DecimalField(source='matricula_clp', max_digits=12, decimal_places=2)
    valor_mensual = serializers.DecimalField(source='arancel_mensual_clp', max_digits=12, decimal_places=2)
    valor_semestral = serializers.DecimalField(source='arancel_semestral_clp', max_digits=12, decimal_places=2)
    valor_anual = serializers.DecimalField(source='arancel_anual_clp', max_digits=12, decimal_places=2)
    arancel_referencia = serializers.SerializerMethodField()
    arancel_publicado = serializers.SerializerMethodField()
    duracion_texto = serializers.SerializerMethodField()
    duracion_meses = serializers.SerializerMethodField()

    class Meta:
        model = OfertaAcademica
        fields = [
            'id', 'institucion', 'institucion_codigo', 'carrera_id', 'carrera', 'nivel', 'titulo',
            'duracion_semestres', 'duracion_texto', 'duracion_meses', 'malla_url', 'sede', 'region', 'direccion',
            'jornada', 'modalidad', 'valor_matricula', 'matricula_periodo', 'valor_mensual', 'valor_semestral',
            'valor_anual', 'aranceles_calculados', 'arancel_referencia', 'arancel_publicado',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_arancel_referencia(self, oferta):
        """Monto para comparar entre instituciones: el anual si existe. 'calculado' indica que se derivó de cuotas."""
        for periodo, monto in (
            ('anual', oferta.arancel_anual_clp),
            ('semestral', oferta.arancel_semestral_clp),
            ('mensual', oferta.arancel_mensual_clp),
        ):
            if monto:
                return {'monto': int(monto), 'periodo': periodo,
                        'calculado': oferta.aranceles_calculados and periodo != 'mensual'}
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_arancel_publicado(self, oferta):
        """El monto tal como lo publica la institución (Duoc: cuota mensual; INACAP: semestral)."""
        orden = (('mensual', oferta.arancel_mensual_clp),) if oferta.aranceles_calculados else (
            ('semestral', oferta.arancel_semestral_clp),
            ('anual', oferta.arancel_anual_clp),
            ('mensual', oferta.arancel_mensual_clp),
        )
        for periodo, monto in orden:
            if monto:
                return {'monto': int(monto), 'periodo': periodo}
        return None

    def get_duracion_texto(self, oferta) -> str:
        """Duración de esta modalidad tal como se publica, por ejemplo '16 bimestres' u '8 semestres'."""
        if oferta.duracion_texto:
            return oferta.duracion_texto
        semestres = oferta.carrera.duracion_semestres
        return f'{semestres} semestres' if semestres else ''

    def get_duracion_meses(self, oferta) -> int | None:
        """Duración en meses para comparar y ordenar (semestre = 6, bimestre = 2)."""
        if oferta.duracion_meses:
            return oferta.duracion_meses
        semestres = oferta.carrera.duracion_semestres
        return semestres * 6 if semestres else None
