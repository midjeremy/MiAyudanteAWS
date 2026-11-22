from django.db import models

# --- MODELOS PRINCIPALES DE LA ARQUITECTURA (Scraping y Catálogo) ---

class Institucion(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    sitio_web = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'institución'
        verbose_name_plural = 'instituciones'

    def __str__(self):
        return self.nombre

class LoteScrapingS3(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE)
    s3_url_json_raw = models.TextField(blank=True, null=True)
    fecha_extraccion = models.DateTimeField(auto_now_add=True)
    total_registros = models.IntegerField(default=0)
    estado_etl = models.CharField(max_length=30, default='PENDIENTE')
    total_ofertas = models.IntegerField(default=0)
    errores = models.IntegerField(default=0)
    tasa_exito = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    detalle_errores = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'lote del ETL'
        verbose_name_plural = 'lotes del ETL'

    def __str__(self):
        return f"Lote {self.id} - {self.institucion.nombre}"

class Carrera(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, null=True, blank=True)
    nombre_carrera = models.CharField(max_length=200)
    nivel_formacion = models.CharField(max_length=50, blank=True, null=True)
    duracion_semestres = models.IntegerField(blank=True, null=True)  # solo si se publica en semestres
    duracion_texto = models.CharField(max_length=200, blank=True, default='')  # tal como la publica la institución
    titulo_otorgado = models.CharField(max_length=255, blank=True, null=True)
    s3_url_malla_pdf = models.TextField(blank=True, null=True)
    url_malla = models.URLField(max_length=500, blank=True, null=True)
    # Agrupación tal como la publica la institución (INACAP: área; Duoc UC: escuela)
    area_institucion = models.CharField(max_length=100, blank=True, default='')
    # Área común con el test Ikigai (tecnologia, salud, economia, ...); vacío si no se pudo determinar
    area_estudio = models.CharField(max_length=20, blank=True, default='', db_index=True)
    # Nombre sin la mención: 'Ingeniería en Administración Mención Finanzas' -> 'Ingeniería en Administración'.
    # Agrupa las carreras que la institución publica por separado, una por mención, con sus propias sedes y aranceles.
    nombre_base = models.CharField(max_length=200, blank=True, default='', db_index=True)

    class Meta:
        verbose_name = 'carrera'
        verbose_name_plural = 'carreras'

    def __str__(self):
        return self.nombre_carrera


class Mencion(models.Model):
    """Mención o especialización de una carrera, tal como la publica la institución.

    Una carrera puede tener varias (Duoc UC: Gastronomía Internacional ofrece 'Cocina de Alta Gama' y 'Alta
    Pastelería y Repostería' con las mismas sedes y aranceles). Cuando cada mención tiene su propia página, sedes y
    aranceles, la institución la publica como otra carrera: se guarda como carrera aparte, con su mención, y
    Carrera.nombre_base las agrupa.
    """
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='menciones')
    nombre = models.CharField(max_length=150)
    competencias = models.TextField(blank=True, default='', help_text='Competencias de la mención, una por línea')
    # Malla propia de la mención (Ingeniería en Informática publica una por mención); vacía si la carrera tiene una sola
    url_malla = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = 'mención'
        verbose_name_plural = 'menciones'
        ordering = ['carrera_id', 'nombre']
        constraints = [models.UniqueConstraint(fields=['carrera', 'nombre'], name='mencion_unica_por_carrera')]

    def __str__(self):
        return f'{self.carrera} - Mención {self.nombre}'

class Sede(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, null=True, blank=True)
    nombre_sede = models.CharField(max_length=150)
    region = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'sede'
        verbose_name_plural = 'sedes'

    def __str__(self):
        return self.nombre_sede

class Jornada(models.Model):
    tipo_jornada = models.CharField(max_length=50) # Ej: Diurna, Vespertina
    modalidad = models.CharField(max_length=50, blank=True, null=True) # Ej: Presencial, Online

    class Meta:
        verbose_name = 'jornada'
        verbose_name_plural = 'jornadas'

    def __str__(self):
        return self.tipo_jornada

class OfertaAcademica(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    jornada = models.ForeignKey(Jornada, on_delete=models.CASCADE)
    lote_scraping = models.ForeignKey(LoteScrapingS3, on_delete=models.SET_NULL, null=True, blank=True)
    
    arancel_anual_clp = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    arancel_mensual_clp = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    arancel_semestral_clp = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    matricula_clp = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    # Período de la matrícula publicada ('semestral' o 'anual'); vacío si la fuente no lo indica
    matricula_periodo = models.CharField(max_length=10, blank=True, default='')
    # True si el arancel semestral/anual se calculó desde la cuota mensual publicada (valor referencial)
    aranceles_calculados = models.BooleanField(default=False)
    # Duración de esta modalidad: una misma carrera puede durar 8 semestres presencial y 16 bimestres online
    duracion_texto = models.CharField(max_length=60, blank=True, default='')
    duracion_meses = models.PositiveSmallIntegerField(blank=True, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'oferta académica'
        verbose_name_plural = 'ofertas académicas'

    def __str__(self):
        return f"{self.carrera} - {self.sede} ({self.jornada})"

# --- MODELOS ANTIGUOS (sin uso) ---
# Primer diseño del modelo de datos. La aplicación ya no los usa y sus tablas están vacías:
#   - Usuario            -> el login usa el usuario de Django (get_user_model)
#   - PreguntaIkigai, RespuestaUsuario, ResultadoVocacional -> Test_Ikigai.Pregunta y Test_Ikigai.Resultado
#   - HistorialChatRag   -> el asistente no guarda el historial (lo conserva el navegador)
# Se mantienen para no borrar tablas con una migración; no se muestran en el admin.

class Usuario(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=100, unique=True)
    password_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, default='ESTUDIANTE')

class HistorialChatRag(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    pregunta_usuario = models.TextField()
    contexto_recuperado = models.TextField(blank=True, null=True)
    respuesta_ia = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

class PreguntaIkigai(models.Model):
    enunciado = models.TextField()
    dimension = models.CharField(max_length=20)

class RespuestaUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PreguntaIkigai, on_delete=models.CASCADE)
    puntaje_obtenido = models.IntegerField()

class ResultadoVocacional(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    puntaje_pasion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_vocacion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_profesion = models.DecimalField(max_digits=5, decimal_places=2)
    puntaje_mision = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_realizacion = models.DateTimeField(auto_now_add=True)