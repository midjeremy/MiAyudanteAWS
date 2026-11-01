from django.db import models

# --- MODELOS PRINCIPALES DE LA ARQUITECTURA (Scraping y Catálogo) ---

class Institucion(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    sitio_web = models.CharField(max_length=255, blank=True, null=True)

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

    def __str__(self):
        return f"Lote {self.id} - {self.institucion.nombre}"

class Carrera(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, null=True, blank=True)
    nombre_carrera = models.CharField(max_length=200)
    nivel_formacion = models.CharField(max_length=50, blank=True, null=True)
    duracion_semestres = models.IntegerField(blank=True, null=True)
    titulo_otorgado = models.CharField(max_length=255, blank=True, null=True)
    s3_url_malla_pdf = models.TextField(blank=True, null=True)
    url_malla = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.nombre_carrera

class Sede(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, null=True, blank=True)
    nombre_sede = models.CharField(max_length=150)
    region = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre_sede

class Jornada(models.Model):
    tipo_jornada = models.CharField(max_length=50) # Ej: Diurna, Vespertina
    modalidad = models.CharField(max_length=50, blank=True, null=True) # Ej: Presencial, Online

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
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.carrera} - {self.sede} ({self.jornada})"

# --- MODELOS DE USUARIO Y RAG (Para la funcionalidad de Mi Ayudante) ---

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