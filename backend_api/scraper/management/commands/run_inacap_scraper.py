import os
import time
import re
import boto3
import requests
import io
from django.core.management.base import BaseCommand
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Importar modelos de la aplicación 'scraper'
from scraper.models import Institucion, Carrera, Sede, Jornada, OfertaAcademica

class Command(BaseCommand):
    help = 'Extrae el catálogo de INACAP, sube mallas a S3, procesa aranceles y actualiza direcciones de sedes'

    def limpiar_dinero(self, valor_str):
        try:
            solo_numeros = re.sub(r'[^\d]', '', valor_str)
            return int(solo_numeros) if solo_numeros else 0
        except:
            return 0

    def extraer_semestres(self, texto_duracion):
        try:
            numeros = re.findall(r'\d+', texto_duracion)
            return int(numeros[0]) if numeros else None
        except:
            return None

    def procesar_malla_s3(self, url_pdf, nombre_carrera, s3_client, bucket_name):
        try:
            self.stdout.write(f"  -> Descargando malla: {url_pdf}")
            respuesta = requests.get(url_pdf)
            respuesta.raise_for_status()
            
            archivo_en_memoria = io.BytesIO(respuesta.content)
            nombre_limpio = nombre_carrera.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            ruta_s3 = f"mallas/inacap/{nombre_limpio}.pdf"
            
            s3_client.upload_fileobj(
                archivo_en_memoria, 
                bucket_name, 
                ruta_s3,
                ExtraArgs={'ContentType': 'application/pdf'}
            )
            self.stdout.write(self.style.SUCCESS(f"  [OK] Malla en S3: {ruta_s3}"))
            return ruta_s3
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  [!] Error S3 para {nombre_carrera}: {e}"))
            return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando pipeline ETL maestro de INACAP...'))
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
            aws_session_token=getattr(settings, 'AWS_SESSION_TOKEN', ''),
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
        )
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'tu-bucket-mallas')

        institucion, _ = Institucion.objects.get_or_create(
            codigo="INACAP",
            defaults={"nombre": "Instituto Nacional de Capacitación Profesional", "sitio_web": "https://www.inacap.cl"}
        )

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--headless") # Habilitar para servidores
        driver = webdriver.Chrome(options=chrome_options)
        
        # ====================================================================
        # LISTA GLOBAL PARA SEDES (Evita duplicados)
        # ====================================================================
        lista_urls_sedes = []

        try:
            url_principal = "https://portal.inacap.cl/carreras"
            driver.get(url_principal)
            self.stdout.write(self.style.WARNING('Extrayendo catálogo de carreras...'))
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-ver-carrera")))
            botones_carrera = driver.find_elements(By.CSS_SELECTOR, ".btn-ver-carrera")
            enlaces_carreras = list(set([b.get_attribute("href") for b in botones_carrera if b.get_attribute("href")]))
                    
            self.stdout.write(self.style.SUCCESS(f'✅ Se detectaron {len(enlaces_carreras)} carreras.'))

            for i, enlace in enumerate(enlaces_carreras, 1):
                self.stdout.write(self.style.WARNING(f'\nProcesando {i}/{len(enlaces_carreras)}: {enlace}'))
                
                try:
                    driver.get(enlace)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "accordionCarreras")))
                    
                    nombre_carrera = driver.find_element(By.CSS_SELECTOR, "h1.component-heading").text.strip()
                    
                    # --- A. Ficha Técnica ---
                    duracion_semestres = None
                    nivel_formacion = "Profesional"
                    pares_ficha = driver.find_elements(By.XPATH, "//div[p[contains(@class, 'cabecera-info-carrera')]]")
                    for par in pares_ficha:
                        try:
                            llave = par.find_element(By.CSS_SELECTOR, ".cabecera-info-carrera").text.strip().lower()
                            valor = par.find_element(By.CSS_SELECTOR, ".contenido-info-carrera").text.strip()
                            if "duración" in llave:
                                duracion_semestres = self.extraer_semestres(valor)
                            elif "título" in llave:
                                nivel_formacion = valor
                        except:
                            continue

                    # --- B. Captura de PDF y Subida a S3 ---
                    ruta_s3 = None
                    try:
                        enlace_pdf = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'repo.inacapmovil.cl/pdf_mallas')]"))
                        )
                        url_pdf = enlace_pdf.get_attribute("href")
                        ruta_s3 = self.procesar_malla_s3(url_pdf, nombre_carrera, s3_client, bucket_name)
                    except TimeoutException:
                        self.stdout.write(self.style.WARNING(f"  [!] Sin enlace PDF visible para {nombre_carrera}"))

                    # --- C. Guardar Carrera en PostgreSQL ---
                    carrera_obj, _ = Carrera.objects.update_or_create(
                        nombre_carrera=nombre_carrera,
                        defaults={
                            'nivel_formacion': nivel_formacion[:50],
                            'duracion_semestres': duracion_semestres,
                            's3_url_malla_pdf': ruta_s3
                        }
                    )

                    # --- D. Aranceles ---
                    try:
                        botones_acordeon = driver.find_elements(By.CSS_SELECTOR, "button.buttom-acordion-carrera-26")
                        for boton in botones_acordeon:
                            if "aranceles" in boton.text.lower():
                                driver.execute_script("arguments[0].scrollIntoView(true);", boton)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", boton)
                                time.sleep(2) 
                                break
                    except Exception as e_acordeon:
                        self.stdout.write(self.style.WARNING(f"    [*] No se pudo abrir el acordeón de aranceles: {e_acordeon}"))

                    try:
                        if not driver.find_elements(By.CSS_SELECTOR, "iframe.iframe-aranceles"):
                            self.stdout.write(self.style.WARNING("    [*] No hay tabla de aranceles publicada para esta carrera."))
                        else:
                            WebDriverWait(driver, 15).until(
                                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe.iframe-aranceles"))
                            )
                            WebDriverWait(driver, 10).until(
                                EC.visibility_of_element_located((By.ID, "table-bottom"))
                            )

                            def extraer_datos_tabla():
                                filas_borde = driver.find_elements(By.CSS_SELECTOR, "#table-bottom tr.borde")
                                for fila in filas_borde:
                                    try:
                                        columnas = fila.find_elements(By.TAG_NAME, "td")
                                        if len(columnas) >= 5:
                                            nombre_sede_bruto = columnas[0].text.strip() or "Sede No Especificada"
                                            horario_bruto = columnas[2].text.strip() or "Diurna"
                                            
                                            texto_matricula = columnas[3].text.strip() if columnas[3].text.strip() else "0"
                                            texto_semestral = columnas[4].text.strip() if columnas[4].text.strip() else "0"
                                            
                                            matricula_clp = self.limpiar_dinero(texto_matricula)
                                            semestral_clp = self.limpiar_dinero(texto_semestral)
                                            arancel_anual_clp = semestral_clp * 2
                                            
                                            sede_obj, _ = Sede.objects.get_or_create(
                                                nombre_sede=nombre_sede_bruto,
                                                defaults={'region': 'Por definir'}
                                            )
                                            jornada_obj, _ = Jornada.objects.get_or_create(
                                                tipo_jornada=horario_bruto
                                            )

                                            OfertaAcademica.objects.update_or_create(
                                                institucion=institucion,
                                                carrera=carrera_obj,
                                                sede=sede_obj,
                                                jornada=jornada_obj,
                                                defaults={
                                                    'matricula_clp': matricula_clp,
                                                    'arancel_anual_clp': arancel_anual_clp
                                                }
                                            )
                                    except StaleElementReferenceException:
                                        continue

                            try:
                                select_element_initial = WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.NAME, "o[0][sede_ccod]"))
                                )
                                opciones_validas = len(Select(select_element_initial).options)
                                
                                for i in range(1, opciones_validas):
                                    select_element = WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable((By.NAME, "o[0][sede_ccod]"))
                                    )
                                    driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                                    time.sleep(0.5) 
                                    
                                    Select(select_element).select_by_index(i)
                                    time.sleep(3) 
                                    
                                    extraer_datos_tabla()
                                    
                            except TimeoutException:
                                extraer_datos_tabla()

                            self.stdout.write(self.style.SUCCESS(f"  [OK] Ofertas guardadas para {nombre_carrera}"))

                    except TimeoutException:
                        self.stdout.write(self.style.WARNING("    [!] Tiempo de espera agotado cargando los aranceles."))
                    except Exception as e_iframe:
                        pass
                    finally:
                        driver.switch_to.default_content()
                    
                    # ====================================================================
                    # --- E. RECOLECCIÓN DE URLS DE SEDES EN LISTA ÚNICA ---
                    # ====================================================================
                    try:
                        # Buscar todos los botones de acordeón
                        botones_acordeon = driver.find_elements(By.CSS_SELECTOR, "button.buttom-acordion-carrera-26")
                        
                        # Identificar el de "Sedes que Imparten la Carrera" y hacer clic
                        for boton in botones_acordeon:
                            if "sedes que imparten" in boton.text.lower():
                                driver.execute_script("arguments[0].scrollIntoView(true);", boton)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", boton)
                                time.sleep(1.5) # Pausa para que se despliegue el menú
                                break
                        
                        # Capturar los links desplegados usando la clase descubierta
                        enlaces_sedes = driver.find_elements(By.CSS_SELECTOR, ".enlace-sede")
                        
                        # Validar si existe en la lista, si no, agregarlo
                        for enlace in enlaces_sedes:
                            href = enlace.get_attribute("href")
                            if href and href not in lista_urls_sedes:
                                lista_urls_sedes.append(href)
                                self.stdout.write(self.style.SUCCESS(f"    [+] Link de sede agregado a la cola: {href.split('/')[-1]}"))
                                
                    except Exception as e_sedes:
                        self.stdout.write(self.style.WARNING(f"    [!] No se pudieron extraer URLs de sedes: {e_sedes}"))
                    
                    time.sleep(2) 
                    
                except Exception as error_carrera:
                    self.stdout.write(self.style.ERROR(f'⚠️ Error al procesar {enlace}: {str(error_carrera)}'))
                    continue

            self.stdout.write(self.style.SUCCESS(f'\n✅ Fase 1 completada. Se guardaron {len(lista_urls_sedes)} URLs de sedes únicas.'))

            # ====================================================================
            # FASE 2: ACTUALIZACIÓN FÍSICA DE SEDES RECOLECTADAS
            # ====================================================================
            if lista_urls_sedes:
                self.stdout.write(self.style.WARNING('\nIniciando Fase 2: Visitando links y actualizando direcciones...'))
                
                for index, url_sede in enumerate(lista_urls_sedes, 1):
                    self.stdout.write(self.style.WARNING(f'\nActualizando Sede {index}/{len(lista_urls_sedes)}: {url_sede}'))
                    try:
                        driver.get(url_sede)
                        
                        # Extraer el nombre de la sede limpiando el "INACAP"
                        h2_element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h2.component-heading"))
                        )
                        nombre_limpio = h2_element.text.replace("INACAP", "").strip()
                        
                        # Extraer dirección usando el enlace de Google Maps o el ID del fragmento
                        direccion_limpia = "Dirección no disponible"
                        try:
                            dir_element = driver.find_element(By.CSS_SELECTOR, ".container-contacto-sede a[href*='google.com/maps']")
                            direccion_limpia = dir_element.text.strip()
                        except:
                            try:
                                dir_element = driver.find_element(By.ID, "fragment-mtpt-link")
                                direccion_limpia = dir_element.text.strip()
                            except:
                                pass
                                
                        # Actualizar la Base de Datos
                        sede_obj = Sede.objects.filter(nombre_sede__icontains=nombre_limpio).first()
                        if sede_obj:
                            sede_obj.direccion = direccion_limpia
                            sede_obj.save()
                            self.stdout.write(self.style.SUCCESS(f"  [OK] Dirección actualizada en BD: {direccion_limpia}"))
                        else:
                            # Por seguridad, si la sede no existía en aranceles, se crea
                            Sede.objects.create(nombre_sede=nombre_limpio, direccion=direccion_limpia, region="Por definir")
                            self.stdout.write(self.style.SUCCESS(f"  [+] Sede creada en BD con dirección: {direccion_limpia}"))
                            
                    except Exception as e_sede:
                        self.stdout.write(self.style.ERROR(f"  [!] Error al visitar la sede {url_sede}: {e_sede}"))
                    
                    time.sleep(1) # Pausa entre páginas de sedes

            self.stdout.write(self.style.SUCCESS('\n✅ ¡Proceso maestro finalizado! Todo sincronizado con PostgreSQL.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error crítico en el scraper maestro: {str(e)}'))
        finally:
            driver.quit()