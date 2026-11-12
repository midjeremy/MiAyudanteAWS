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
