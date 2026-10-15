from django.db import models

class ProgramaEstudio(models.Model):
    institucion = models.CharField(max_length=100, default="INACAP")
    nombre_carrera = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    # Este campo subirá el archivo a S3 dentro de una carpeta "mallas_pdf/"
    malla_pdf = models.FileField(upload_to='mallas_pdf/', blank=True, null=True)
    fecha_extraccion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_carrera} - {self.institucion}"