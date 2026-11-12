"""Contenido del Test Vocacional Ikigai.

Fuente: "Matriz de Validación por Juicio de Expertos – Test Ikigai" (Proyecto de Título
Mi Ayudante, INACAP). Los 40 ítems, sus dimensiones, sus áreas y la escala Likert se
copian tal como aparecen en la matriz validada. Las sugerencias de redacción de la
persona evaluadora (dictamen "Aplicable con modificaciones") no se aplicaron aquí:
para cambiar un enunciado, edítelo en esta lista y ejecute
`python manage.py cargar_preguntas_ikigai`.
"""

# Escala de respuesta que ve el estudiante (sección II del documento)
ESCALA = [
    (1, 'Muy en desacuerdo'),
    (2, 'En desacuerdo'),
    (3, 'Ni de acuerdo ni en desacuerdo'),
    (4, 'De acuerdo'),
    (5, 'Muy de acuerdo'),
]
VALOR_MINIMO = ESCALA[0][0]
VALOR_MAXIMO = ESCALA[-1][0]

# Dimensiones del test: clave, nombre y qué explora
DIMENSIONES = [
    ('pasion', 'Pasión', 'Lo que me gusta: actividades y temas que disfruto.'),
    ('vocacion', 'Vocación', 'En lo que soy bueno/a: habilidades en las que me destaco.'),
    ('profesion', 'Profesión', 'Dónde me veo trabajando y lo que me puede dar sustento.'),
    ('mision', 'Misión', 'Lo que la sociedad necesita: cómo me gustaría aportar a las personas y a la sociedad.'),
]

# Áreas de carreras (cada área tiene un ítem en cada dimensión). "general" mide la
# intensidad de la dimensión sin apuntar a un área, así que no se usa para sugerir áreas.
GENERAL = 'general'
AREAS = [
    ('tecnologia', 'Tecnología', 'Informática, programación, redes, ciberseguridad'),
    ('salud', 'Salud', 'Enfermería, laboratorio clínico, odontología, preparación física'),
    ('economia', 'Economía y Administración', 'Administración, contabilidad, comercio, logística'),
    ('industria', 'Industria y construcción', 'Mecánica, electricidad, construcción, minería'),
    ('arte', 'Arte y comunicación', 'Diseño gráfico, publicidad, audiovisual, música'),
    ('educacion', 'Educación y social', 'Educación de párvulos, trabajo social, asistente social'),
    ('naturaleza', 'Naturaleza y medio ambiente', 'Agronomía, veterinaria, acuicultura, gestión ambiental'),
    ('turismo', 'Turismo y gastronomía', 'Gastronomía, hotelería, turismo, eventos'),
    (GENERAL, 'General', 'Mide la intensidad de cada dimensión sin apuntar a un área'),
]

# (número, dimensión, área, enunciado)
PREGUNTAS = [
    # Dimensión Pasión (Lo que me gusta)
    (1, 'pasion', 'tecnologia', 'Me entretiene aprender cómo funcionan los computadores, las aplicaciones o internet.'),
    (2, 'pasion', 'salud', 'Me interesan los temas relacionados con el cuerpo humano y el cuidado de la salud.'),
    (3, 'pasion', 'economia', 'Me atrae la idea de organizar, manejar un presupuesto o vender un producto.'),
    (4, 'pasion', 'industria', 'Disfruto armar, reparar o entender cómo funcionan máquinas, motores o instalaciones.'),
    (5, 'pasion', 'arte', 'Disfruto crear cosas visuales o audiovisuales, como dibujos, diseños, fotos, videos o música.'),
    (6, 'pasion', 'educacion', 'Me gusta conversar con otras personas, escucharlas y entender lo que les pasa.'),
    (7, 'pasion', 'naturaleza', 'Disfruto estar en contacto con la naturaleza, los animales o los cultivos.'),
    (8, 'pasion', 'turismo', 'Me entusiasma la cocina, atender a visitantes o conocer lugares y culturas.'),
    (9, 'pasion', GENERAL, 'Hay actividades que disfruto tanto que pierdo la noción del tiempo cuando las hago.'),
    (10, 'pasion', GENERAL, 'En mi tiempo libre aprendo por mi cuenta sobre temas que me interesan.'),
    # Dimensión Vocación (En lo que soy bueno/a)
    (11, 'vocacion', 'tecnologia', 'Aprendo con facilidad a usar programas, aplicaciones o dispositivos nuevos.'),
    (12, 'vocacion', 'salud', 'Mantengo la calma y sé cómo ayudar cuando alguien se siente mal o se lastima.'),
    (13, 'vocacion', 'economia', 'Se me dan bien los cálculos, ordenar información y llevar cuentas.'),
    (14, 'vocacion', 'industria', 'Tengo habilidad manual para usar herramientas o construir objetos.'),
    (15, 'vocacion', 'arte', 'Se me da bien expresar ideas de forma creativa.'),
    (16, 'vocacion', 'educacion', 'Me resulta fácil explicar cosas a otras personas o ayudarlas a aprender.'),
    (17, 'vocacion', 'naturaleza', 'Tengo paciencia y constancia para cuidar espacios naturales.'),
    (18, 'vocacion', 'turismo', 'Me desenvuelvo bien atendiendo a personas que no conozco.'),
    (19, 'vocacion', GENERAL, 'Cuando una tarea me resulta difícil, persisto hasta hacerla bien.'),
    (20, 'vocacion', GENERAL, 'Otras personas reconocen que tengo habilidades en algún tema en particular.'),
    # Dimensión Profesión (Dónde me veo trabajando y lo que me puede dar sustento)
    (21, 'profesion', 'tecnologia', 'Me veo trabajando frente a un computador, desarrollando o administrando sistemas.'),
    (22, 'profesion', 'salud', 'Me veo trabajando en un hospital, clínica, centro de salud o en la atención de pacientes.'),
    (23, 'profesion', 'economia', 'Me veo trabajando en una oficina, una empresa o un emprendimiento propio.'),
    (24, 'profesion', 'industria', 'Me veo trabajando en terreno: en una obra, un taller, una planta o una faena.'),
    (25, 'profesion', 'arte', 'Me veo trabajando en una agencia, un estudio, un medio de comunicación o creando contenidos.'),
    (26, 'profesion', 'educacion', 'Me veo trabajando en un colegio, un jardín infantil, un municipio o una organización social.'),
    (27, 'profesion', 'naturaleza', 'Me veo trabajando al aire libre: en el campo, el mar, un vivero o un área protegida.'),
    (28, 'profesion', 'turismo', 'Me veo trabajando en un hotel, un restaurante, una agencia de viajes o en la organización de eventos.'),
    (29, 'profesion', GENERAL, 'Al elegir una carrera, considero importante conocer sus oportunidades de empleo y su remuneración.'),
    (30, 'profesion', GENERAL, 'Al elegir una carrera, considero cuánto dura y cuánto cuesta estudiarla.'),
    # Dimensión Misión (Lo que la sociedad necesita)
    (31, 'mision', 'tecnologia', 'Me gustaría usar la tecnología para resolver problemas de las personas.'),
    (32, 'mision', 'salud', 'Me gustaría contribuir a que las personas tengan mejor salud y bienestar.'),
    (33, 'mision', 'economia', 'Me gustaría ayudar a que empresas o emprendimientos crezcan y generen empleo.'),
    (34, 'mision', 'industria', 'Me gustaría contribuir a construir o mantener obras que la gente necesita, como viviendas, caminos o redes de energía.'),
    (35, 'mision', 'arte', 'Me gustaría comunicar ideas o mensajes que influyan positivamente en otras personas.'),
    (36, 'mision', 'educacion', 'Me gustaría apoyar a personas o comunidades que enfrentan dificultades.'),
    (37, 'mision', 'naturaleza', 'Me gustaría contribuir al cuidado del medio ambiente y de los recursos naturales.'),
    (38, 'mision', 'turismo', 'Me gustaría que las personas disfruten experiencias agradables gracias a mi trabajo.'),
    (39, 'mision', GENERAL, 'Me motiva que mi trabajo futuro tenga un impacto positivo en mi comunidad.'),
    (40, 'mision', GENERAL, 'Considero importante que mi carrera responda a necesidades reales de la sociedad.'),
]


def cargar_preguntas(modelo_pregunta):
    """Crea o actualiza las 40 preguntas usando el número como clave.

    Recibe el modelo como parámetro para poder usarse desde una migración
    (apps.get_model) y desde el comando de gestión.
    """
    for numero, dimension, area, enunciado in PREGUNTAS:
        modelo_pregunta.objects.update_or_create(
            numero=numero,
            defaults={'dimension': dimension, 'area': area, 'enunciado': enunciado},
        )
    return len(PREGUNTAS)
