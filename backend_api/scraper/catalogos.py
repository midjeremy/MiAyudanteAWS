"""Catálogos comunes del ETL: unifican lo que cada institución publica de forma distinta."""
import re
import unicodedata

from Test_Ikigai.preguntas import AREAS as _AREAS_TEST, GENERAL as _AREA_GENERAL

REGION_ONLINE = 'Online'
JORNADA_NO_INFORMADA = 'No informada'
NIVEL_TECNICO = 'Técnico de Nivel Superior'
NIVEL_PROFESIONAL = 'Profesional'

METROPOLITANA = 'Región Metropolitana'
BIOBIO = 'Región del Biobío'

_REGIONES_POR_SEDE = {
    'Arica': 'Región de Arica y Parinacota',
    'Iquique': 'Región de Tarapacá',
    'Antofagasta': 'Región de Antofagasta',
    'Calama': 'Región de Antofagasta',
    'Copiapó': 'Región de Atacama',
    'La Serena': 'Región de Coquimbo',
    'Valparaíso': 'Región de Valparaíso',
    'Viña del Mar': 'Región de Valparaíso',
    'Rancagua': "Región de O'Higgins",
    'Curicó': 'Región del Maule',
    'Talca': 'Región del Maule',
    'Chillán': 'Región de Ñuble',
    'Concepción - Talcahuano': BIOBIO,
    'San Andrés de Concepción': BIOBIO,
    'Los Ángeles': BIOBIO,
    'San Pedro de la Paz': BIOBIO,
    'Campus Arauco': BIOBIO,
    'Campus Nacimiento': BIOBIO,
    'Temuco': 'Región de La Araucanía',
    'Villarrica': 'Región de La Araucanía',
    'Valdivia': 'Región de Los Ríos',
    'Osorno': 'Región de Los Lagos',
    'Puerto Montt': 'Región de Los Lagos',
    'Coyhaique': 'Región de Aysén',
    'Punta Arenas': 'Región de Magallanes',
    'Alameda': METROPOLITANA,
    'Antonio Varas': METROPOLITANA,
    'Apoquindo': METROPOLITANA,
    'Central': METROPOLITANA,
    'La Granja': METROPOLITANA,
    'Maipú': METROPOLITANA,
    'Melipilla': METROPOLITANA,
    'Padre Alonso de Ovalle': METROPOLITANA,
    'Plaza Norte': METROPOLITANA,
    'Plaza Oeste': METROPOLITANA,
    'Plaza Vespucio': METROPOLITANA,
    'Puente Alto': METROPOLITANA,
    'Renca': METROPOLITANA,
    'San Bernardo': METROPOLITANA,
    'San Carlos de Apoquindo': METROPOLITANA,
    'San Joaquín': METROPOLITANA,
    'Santiago Centro': METROPOLITANA,
    'Santiago Sur': METROPOLITANA,
    'Campus Digital': REGION_ONLINE,
    'Duoc Online': REGION_ONLINE,
}


def normalizar_texto(texto):
    sin_tildes = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', sin_tildes.lower()).strip()


_REGIONES_NORMALIZADAS = {normalizar_texto(sede): region for sede, region in _REGIONES_POR_SEDE.items()}


def region_de_sede(nombre_sede):
    """Devuelve la región de la sede, o None si aún no está en el catálogo."""
    return _REGIONES_NORMALIZADAS.get(normalizar_texto(nombre_sede))


def normalizar_jornada(texto, nombre_sede=''):
    """Devuelve (tipo_jornada, modalidad). Un horario vacío no se reemplaza por uno inventado."""
    valor = normalizar_texto(texto)
    if 'online' in valor or region_de_sede(nombre_sede) == REGION_ONLINE:
        return 'Online', 'Online'
    if 'diurn' in valor:
        return 'Diurna', 'Presencial'
    if 'vespertin' in valor:
        return 'Vespertina', 'Presencial'
    if not valor:
        return JORNADA_NO_INFORMADA, None
    return texto.strip().capitalize(), None


MESES_POR_UNIDAD = {'semestre': 6, 'bimestre': 2, 'trimestre': 3, 'ano': 12, 'mes': 1}
NOMBRES_UNIDAD = {
    'semestre': ('semestre', 'semestres'), 'bimestre': ('bimestre', 'bimestres'),
    'trimestre': ('trimestre', 'trimestres'), 'ano': ('año', 'años'), 'mes': ('mes', 'meses'),
}
MAXIMO_MESES_TECNICO = 30  # 5 semestres: solo se usa cuando la duración no está en semestres


def parsear_duraciones(textos):
    """Interpreta las duraciones tal como las publica la institución.

    '8 semestres (Presencial)' y '16 bimestres (Online)' -> una entrada por texto con su valor, unidad,
    meses equivalentes y modalidad (None si el texto no la indica). Lo que no se entiende se descarta.
    """
    duraciones = []
    for texto in textos or []:
        limpio = re.sub(r'\s+', ' ', str(texto)).strip()
        normalizado = normalizar_texto(limpio)
        encontrado = re.search(r'(\d+)\s*(semestre|bimestre|trimestre|ano|mes)', normalizado)
        if not encontrado:
            continue
        valor, unidad = int(encontrado.group(1)), encontrado.group(2)
        if 'online' in normalizado:
            modalidad = 'Online'
        elif 'presencial' in normalizado:
            modalidad = 'Presencial'
        else:
            modalidad = None
        singular, plural = NOMBRES_UNIDAD[unidad]
        duraciones.append({
            'texto': limpio,
            'valor': valor,
            'unidad': unidad,
            'meses': valor * MESES_POR_UNIDAD[unidad],
            'modalidad': modalidad,
            'resumen': f'{valor} {singular if valor == 1 else plural}',
        })
    return duraciones


def elegir_duracion(duraciones, modalidad):
    """La duración que corresponde a una modalidad: la que la nombra, o si no, la que no nombra ninguna."""
    for criterio in (lambda d: d['modalidad'] == modalidad, lambda d: d['modalidad'] is None):
        candidatas = [d for d in duraciones if criterio(d)]
        if candidatas:
            return candidatas[0]
    return duraciones[0] if duraciones else None


def semestres_publicados(duraciones):
    """Semestres solo si la institución los publica así (nunca se convierten bimestres en semestres)."""
    for modalidad in ('Presencial', None, 'Online'):
        for duracion in duraciones:
            if duracion['unidad'] == 'semestre' and duracion['modalidad'] == modalidad:
                return duracion['valor']
    return None


def clasificar_nivel(nombre_carrera, duracion_semestres, duracion_meses=None):
    """Unifica el nivel a partir del nombre y, si no basta, de la duración."""
    nombre = normalizar_texto(nombre_carrera)
    if nombre.startswith('tecnico'):
        return NIVEL_TECNICO
    if nombre.startswith(('ingenieria', 'contador', 'licenciatura')):
        return NIVEL_PROFESIONAL
    if duracion_semestres:
        return NIVEL_TECNICO if duracion_semestres <= 6 else NIVEL_PROFESIONAL
    if duracion_meses:
        return NIVEL_TECNICO if duracion_meses <= MAXIMO_MESES_TECNICO else NIVEL_PROFESIONAL
    return None


# --- Área de estudio ---------------------------------------------------------------------------
# Cada carrera se asocia a una de las 8 áreas del test Ikigai (Test_Ikigai/preguntas.py), para
# poder sugerir carreras del catálogo a partir del resultado. La institución publica su propia
# agrupación (INACAP: "área" en la URL de la carrera; Duoc UC: "escuela"), que se guarda tal cual
# en area_institucion y se traduce a la clave común en area_estudio.
AREAS_ESTUDIO = {clave: nombre for clave, nombre, _ in _AREAS_TEST if clave != _AREA_GENERAL}

# Slug del área en portal.inacap.cl/carreras/<slug>/<carrera> -> (nombre publicado, área común)
AREAS_INACAP = {
    'area-administracion': ('Administración', 'economia'),
    'area-agroindustria-y-medioambiente': ('Agroindustria y Medioambiente', 'naturaleza'),
    'area-automatizacion-electronica-y-robotica': ('Automatización, Electrónica y Robótica', 'industria'),
    'area-construccion': ('Construcción', 'industria'),
    'area-diseno-e-industria-digital': ('Diseño e Industria Digital', 'arte'),
    'area-energia': ('Energía', 'industria'),
    'area-gastronomia': ('Gastronomía', 'turismo'),
    'area-informatica-ciberseguridad-y-telecomunicaciones': ('Informática, Ciberseguridad y Telecomunicaciones', 'tecnologia'),
    'area-logistica': ('Logística', 'economia'),
    'area-mecanica': ('Mecánica', 'industria'),
    'area-mineria': ('Minería', 'industria'),
    'area-salud': ('Salud', 'salud'),
    'area-tecnologias-informacion-y-ciberseguridad': ('Tecnologías de la Información y Ciberseguridad', 'tecnologia'),
    'area-turismo-y-hospitalidad': ('Turismo y Hospitalidad', 'turismo'),
}

# Slug de la escuela en duoc.cl/escuela/<slug>/ -> (nombre publicado, área común)
ESCUELAS_DUOC = {
    'administracion-negocios': ('Administración y Negocios', 'economia'),
    'comunicacion': ('Comunicación', 'arte'),
    'construccion': ('Construcción', 'industria'),
    'diseno': ('Diseño', 'arte'),
    'gastronomia': ('Gastronomía', 'turismo'),
    'informatica-telecomunicaciones': ('Informática y Telecomunicaciones', 'tecnologia'),
    'ingenieria-recursos-naturales': ('Ingeniería y Recursos Naturales', 'industria'),
    'salud': ('Salud y Bienestar', 'salud'),
    'turismo': ('Turismo y Hospitalidad', 'turismo'),
}

# Las agrupaciones institucionales no calzan del todo con las áreas del test: no tienen área de
# educación ni de naturaleza propia (Duoc pone Trabajo Social en Comunicación y Recursos Naturales
# junto a Minería) e INACAP agrupa Electricidad con Informática, mientras el test la ubica en
# Industria. El nombre de la carrera corrige esos casos.
_AREA_POR_NOMBRE_PRIORITARIA = [
    ('educacion', r'trabajo social|asistente social|educacion|parvul|pedagog|psicopedagog'),
    ('industria', r'electric'),
    ('naturaleza', r'agricol|agronom|agropecuari|agroindustri|forestal|acuicult|veterinar|recursos naturales|'
                   r'medio ?ambiente|ambiental|sostenib'),
]
# Solo se usan si la institución no informa su agrupación (por ejemplo, datos cargados antes de este cambio)
_AREA_POR_NOMBRE = _AREA_POR_NOMBRE_PRIORITARIA + [
    ('salud', r'enfermer|kinesiolog|laboratorio clinico|odontolog|nutricion|preparador fisico|fonoaudiolog|farmacia|salud'),
    ('tecnologia', r'informatic|software|programad|ciberseguridad|redes|telecomunicacion|datos|inteligencia artificial|'
                   r'\bia\b|computacion|desarrollo de aplicaciones'),
    ('turismo', r'turismo|hotel|hospitalidad|gastronom|cocina|eventos'),
    ('arte', r'diseno|publicidad|audiovisual|animacion|ilustracion|fotografia|musica|comunicacion|periodismo|'
             r'relaciones publicas'),
    ('economia', r'administracion|contab|contador|auditor|comercio|logistic|finanz|recursos humanos|gestion de personas|'
                 r'marketing|negocios|control de gestion|tributar'),
    ('industria', r'mecanic|electric|electron|construccion|miner|minas|automatizacion|mantenimiento|automotriz|energ|'
                  r'prevencion de riesgos|topograf|geolog|metal|soldadura|industrial|robotic|maquinaria|obras civiles'),
]


def _area_por_nombre(nombre_carrera, reglas):
    nombre = normalizar_texto(nombre_carrera)
    return next((clave for clave, patron in reglas if re.search(patron, nombre)), '')


def clasificar_area(nombre_carrera, area_institucional=''):
    """Área común (clave del test Ikigai) a partir de la agrupación institucional y el nombre.

    La agrupación de la institución manda; el nombre solo corrige educación y naturaleza, o se usa
    completo si la institución no informó su agrupación. Devuelve '' si no hay cómo saberlo.
    """
    corregida = _area_por_nombre(nombre_carrera, _AREA_POR_NOMBRE_PRIORITARIA)
    if corregida == 'naturaleza' and 'prevencion de riesgos' in normalizar_texto(nombre_carrera):
        corregida = ''  # "Prevención de Riesgos y Medio Ambiente" sigue en su área institucional
    if corregida:
        return corregida
    if area_institucional:
        return area_institucional
    return _area_por_nombre(nombre_carrera, _AREA_POR_NOMBRE)


def _nombre_desde_slug(slug, prefijo=''):
    return slug.removeprefix(prefijo).replace('-', ' ').strip().capitalize()


def area_inacap(url_carrera):
    """(área publicada, área común) desde la URL de la carrera: /carreras/area-<x>/<carrera>."""
    coincidencia = re.search(r'/carreras/(area-[^/]+)/', url_carrera or '')
    if not coincidencia:
        return '', ''
    slug = coincidencia.group(1)
    return AREAS_INACAP.get(slug, (_nombre_desde_slug(slug, 'area-'), ''))


def area_duoc(url_escuela, nombre_escuela=''):
    """(escuela publicada, área común) desde la URL de la escuela: /escuela/<slug>/."""
    coincidencia = re.search(r'/escuela/([^/]+)/?', url_escuela or '')
    slug = coincidencia.group(1) if coincidencia else ''
    nombre = re.sub(r'^\s*escuela de\s+', '', nombre_escuela or '', flags=re.IGNORECASE).strip()
    publicado, clave = ESCUELAS_DUOC.get(slug, (nombre or _nombre_desde_slug(slug), ''))
    return nombre or publicado, clave
