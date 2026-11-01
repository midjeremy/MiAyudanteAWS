"""Catálogos comunes del ETL: unifican lo que cada institución publica de forma distinta."""
import re
import unicodedata

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


def clasificar_nivel(nombre_carrera, duracion_semestres):
    """Unifica el nivel a partir del nombre y, si no basta, de la duración."""
    nombre = normalizar_texto(nombre_carrera)
    if nombre.startswith('tecnico'):
        return NIVEL_TECNICO
    if nombre.startswith(('ingenieria', 'contador', 'licenciatura')):
        return NIVEL_PROFESIONAL
    if not duracion_semestres:
        return None
    return NIVEL_TECNICO if duracion_semestres <= 6 else NIVEL_PROFESIONAL
