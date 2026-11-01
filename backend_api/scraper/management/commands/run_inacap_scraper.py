import os
import time
import re
import requests
import io
from urllib.parse import urlsplit
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
from scraper.catalogos import clasificar_nivel, normalizar_jornada, normalizar_texto, region_de_sede
from scraper.etl import TASA_MINIMA_EXITO, cerrar_lote, crear_cliente_s3, retirar_ofertas_obsoletas, subir_json_crudo, tasa_exito
from scraper.models import Institucion, Carrera, LoteScrapingS3, Sede, Jornada, OfertaAcademica

URL_ARANCELES_SIGA3 = "https://siga3.inacap.cl/fup1.5/ofertas/contenidoCarrerasPorArea.asp"
MINIMO_CARRERAS = 60

class Command(BaseCommand):
    help = 'Extrae el catálogo de INACAP, sube mallas a S3, procesa aranceles y actualiza direcciones de sedes'

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, help='Procesa solo esta cantidad de carreras')
        parser.add_argument('--con-ventana', action='store_true', help='Muestra Chrome en lugar de usar modo headless')
        parser.add_argument('--carrera', action='append', help='Procesa solo las carreras cuya URL contiene este texto (repetible)')

    def abrir_acordeon_aranceles(self, driver):
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

    def aranceles_cargados(self, driver):
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.iframe-aranceles")
        if not iframes:
            return True
        driver.switch_to.frame(iframes[0])
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "table-bottom")))
            return True
        except TimeoutException:
            return False
        finally:
            driver.switch_to.default_content()

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
            respuesta = requests.get(url_pdf, timeout=30)
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
        
        s3_client = crear_cliente_s3()
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'tu-bucket-mallas')

        institucion, _ = Institucion.objects.get_or_create(
            codigo="INACAP",
            defaults={"nombre": "Instituto Nacional de Capacitación Profesional", "sitio_web": "https://www.inacap.cl"}
        )

        lote = LoteScrapingS3.objects.create(institucion=institucion, estado_etl='EN_PROCESO')
        errores = []
        carreras_ok = 0
        total_carreras = 0
        ids_vigentes = set()
        filas_crudas = []

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        if not kwargs['con_ventana']:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
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
            if kwargs['carrera']:
                enlaces_carreras = [e for e in enlaces_carreras if any(c in e for c in kwargs['carrera'])]
            if kwargs['limite']:
                enlaces_carreras = enlaces_carreras[:kwargs['limite']]

            total_carreras = len(enlaces_carreras)
            self.stdout.write(self.style.SUCCESS(f'✅ Se detectaron {len(enlaces_carreras)} carreras.'))

            for i, enlace in enumerate(enlaces_carreras, 1):
                self.stdout.write(self.style.WARNING(f'\nProcesando {i}/{len(enlaces_carreras)}: {enlace}'))
                
                try:
                    driver.get(enlace)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "accordionCarreras")))
                    
                    nombre_carrera = driver.find_element(By.CSS_SELECTOR, "h1.component-heading").text.strip()
                    
                    # --- A. Ficha Técnica ---
                    duracion_semestres = None
                    titulo_otorgado = None
                    pares_ficha = driver.find_elements(By.XPATH, "//div[p[contains(@class, 'cabecera-info-carrera')]]")
                    for par in pares_ficha:
                        try:
                            llave = par.find_element(By.CSS_SELECTOR, ".cabecera-info-carrera").text.strip().lower()
                            valor = par.find_element(By.CSS_SELECTOR, ".contenido-info-carrera").text.strip()
                            if "duración" in llave:
                                duracion_semestres = self.extraer_semestres(valor)
                            elif llave.startswith("título"):
                                titulo_otorgado = valor
                        except:
                            continue

                    # --- B. Captura de PDF y Subida a S3 ---
                    ruta_s3 = None
                    url_pdf = None
                    try:
                        enlace_pdf = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'repo.inacapmovil.cl/pdf_mallas')]"))
                        )
                        url_pdf = enlace_pdf.get_attribute("href")
                        ruta_s3 = self.procesar_malla_s3(url_pdf, nombre_carrera, s3_client, bucket_name)
                    except TimeoutException:
                        self.stdout.write(self.style.WARNING(f"  [!] Sin enlace PDF visible para {nombre_carrera}"))
                        errores.append(f"Sin malla: {nombre_carrera}")

                    # --- C. Guardar Carrera en PostgreSQL ---
                    carrera_obj, _ = Carrera.objects.update_or_create(
                        nombre_carrera=nombre_carrera,
                        institucion=institucion,
                        defaults={
                            'nivel_formacion': clasificar_nivel(nombre_carrera, duracion_semestres),
                            'titulo_otorgado': titulo_otorgado[:255] if titulo_otorgado else None,
                            'duracion_semestres': duracion_semestres,
                            's3_url_malla_pdf': ruta_s3,
                            'url_malla': url_pdf
                        }
                    )

                    # --- D. Aranceles ---
                    ofertas_carrera = 0
                    self.abrir_acordeon_aranceles(driver)

                    # El iframe nuevo del portal puede responder 404; el servicio siga3 entrega la misma tabla
                    if not self.aranceles_cargados(driver):
                        iframe = driver.find_element(By.CSS_SELECTOR, "iframe.iframe-aranceles")
                        url_aranceles = f"{URL_ARANCELES_SIGA3}?{urlsplit(iframe.get_attribute('src')).query}"
                        driver.execute_script("arguments[0].src = arguments[1];", iframe, url_aranceles)
                        time.sleep(2)

                    try:
                        if not driver.find_elements(By.CSS_SELECTOR, "iframe.iframe-aranceles"):
                            self.stdout.write(self.style.WARNING("    [*] No hay tabla de aranceles publicada para esta carrera."))
                            errores.append(f"Sin tabla de aranceles: {nombre_carrera}")
                        else:
                            WebDriverWait(driver, 15).until(
                                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe.iframe-aranceles"))
                            )
                            WebDriverWait(driver, 10).until(
                                EC.visibility_of_element_located((By.ID, "table-bottom"))
                            )

                            def extraer_datos_tabla():
                                nonlocal ofertas_carrera
                                filas_borde = driver.find_elements(By.CSS_SELECTOR, "#table-bottom tr.borde")
                                for fila in filas_borde:
                                    try:
                                        columnas = fila.find_elements(By.TAG_NAME, "td")
                                        if len(columnas) >= 5:
                                            nombre_sede_bruto = columnas[0].text.strip() or "Sede No Especificada"
                                            horario_bruto = columnas[2].text.strip()
                                            
                                            texto_matricula = columnas[3].text.strip() if columnas[3].text.strip() else "0"
                                            texto_semestral = columnas[4].text.strip() if columnas[4].text.strip() else "0"
                                            
                                            matricula_clp = self.limpiar_dinero(texto_matricula)
                                            semestral_clp = self.limpiar_dinero(texto_semestral)
                                            arancel_anual_clp = semestral_clp * 2
                                            
                                            sede_obj, _ = Sede.objects.get_or_create(
                                                nombre_sede=nombre_sede_bruto,
                                                institucion=institucion,
                                            )
                                            sede_obj.region = region_de_sede(nombre_sede_bruto)
                                            sede_obj.save(update_fields=['region'])

                                            tipo_jornada, modalidad = normalizar_jornada(horario_bruto, nombre_sede_bruto)
                                            jornada_obj, _ = Jornada.objects.update_or_create(
                                                tipo_jornada=tipo_jornada,
                                                defaults={'modalidad': modalidad}
                                            )

                                            oferta_obj, _ = OfertaAcademica.objects.update_or_create(
                                                institucion=institucion,
                                                carrera=carrera_obj,
                                                sede=sede_obj,
                                                jornada=jornada_obj,
                                                defaults={
                                                    'lote_scraping': lote,
                                                    'matricula_clp': matricula_clp,
                                                    'arancel_semestral_clp': semestral_clp,
                                                    'arancel_anual_clp': arancel_anual_clp
                                                }
                                            )
                                            ids_vigentes.add(oferta_obj.id)
                                            ofertas_carrera += 1
                                            filas_crudas.append({
                                                'carrera': nombre_carrera,
                                                'sede': nombre_sede_bruto,
                                                'horario': horario_bruto,
                                                'matricula': texto_matricula,
                                                'semestral': texto_semestral,
                                            })
                                    except StaleElementReferenceException:
                                        continue

                            try:
                                select_element_initial = WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.NAME, "o[0][sede_ccod]"))
                                )
                                opciones_validas = len(Select(select_element_initial).options)
                                
                                for i in range(1, opciones_validas):
                                    # Cada selección recarga la tabla: se reintenta si el selector queda obsoleto
                                    for intento in range(1, 4):
                                        try:
                                            select_element = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.NAME, "o[0][sede_ccod]"))
                                            )
                                            driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                                            time.sleep(0.5)

                                            Select(select_element).select_by_index(i)
                                            WebDriverWait(driver, 15).until(EC.staleness_of(select_element))
                                            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "table-bottom")))

                                            extraer_datos_tabla()
                                            break
                                        except (StaleElementReferenceException, TimeoutException) as e_sede_tabla:
                                            if intento == 3:
                                                self.stdout.write(self.style.WARNING(f"    [!] Sede {i}/{opciones_validas - 1} omitida: {type(e_sede_tabla).__name__}"))
                                                errores.append(f"Sede omitida en {nombre_carrera}: {i}/{opciones_validas - 1}")
                                            time.sleep(2)

                            except TimeoutException:
                                extraer_datos_tabla()

                            if ofertas_carrera:
                                carreras_ok += 1
                                self.stdout.write(self.style.SUCCESS(f"  [OK] Ofertas guardadas para {nombre_carrera}"))
                            else:
                                self.stdout.write(self.style.WARNING(f"    [!] Sin ofertas leídas para {nombre_carrera}"))
                                errores.append(f"Sin ofertas: {nombre_carrera}")

                    except TimeoutException:
                        self.stdout.write(self.style.WARNING("    [!] Tiempo de espera agotado cargando los aranceles."))
                        errores.append(f"Tiempo agotado en aranceles: {nombre_carrera}")
                    except Exception as e_iframe:
                        self.stdout.write(self.style.ERROR(f"    [!] Error leyendo aranceles de {nombre_carrera}: {type(e_iframe).__name__}: {e_iframe}"))
                        errores.append(f"Error en aranceles de {nombre_carrera}: {type(e_iframe).__name__}")
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
                    errores.append(f"Error en {enlace}: {type(error_carrera).__name__}")
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
                        
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h2.component-heading"))
                        )

                        # El título de la página puede venir vacío o como "Red Crea Empresa X": el nombre sale de la URL
                        nombre_slug = url_sede.rstrip('/').rsplit('/', 1)[-1].removeprefix('sede-')

                        # La dirección es la primera línea del bloque de contacto
                        direccion_limpia = "Dirección no disponible"
                        try:
                            contacto = driver.find_element(By.CSS_SELECTOR, ".container-contacto-sede")
                            direccion_limpia = contacto.text.strip().splitlines()[0].strip()
                        except:
                            try:
                                dir_element = driver.find_element(By.ID, "fragment-mtpt-link")
                                direccion_limpia = dir_element.text.strip()
                            except:
                                pass
                                
                        # Actualizar la Base de Datos
                        nombre_buscado = normalizar_texto(nombre_slug)
                        sede_obj = next((s for s in Sede.objects.filter(institucion=institucion) if normalizar_texto(s.nombre_sede) == nombre_buscado), None)
                        if sede_obj:
                            sede_obj.direccion = direccion_limpia
                            sede_obj.save()
                            self.stdout.write(self.style.SUCCESS(f"  [OK] Dirección actualizada en BD: {direccion_limpia}"))
                        else:
                            # Por seguridad, si la sede no existía en aranceles, se crea
                            Sede.objects.create(nombre_sede=nombre_slug.replace('-', ' ').title(), institucion=institucion, direccion=direccion_limpia, region=region_de_sede(nombre_slug))
                            self.stdout.write(self.style.SUCCESS(f"  [+] Sede creada en BD con dirección: {direccion_limpia}"))
                            
                    except Exception as e_sede:
                        self.stdout.write(self.style.ERROR(f"  [!] Error al visitar la sede {url_sede}: {e_sede}"))
                    
                    time.sleep(1) # Pausa entre páginas de sedes

            try:
                lote.s3_url_json_raw = subir_json_crudo(s3_client, filas_crudas, 'inacap')
                lote.save(update_fields=['s3_url_json_raw'])
            except Exception as e_s3:
                self.stdout.write(self.style.WARNING(f'[!] No se pudo guardar el JSON crudo en S3: {e_s3}'))

            tasa = tasa_exito(carreras_ok, total_carreras)
            carga_completa = (
                not kwargs['carrera'] and not kwargs['limite']
                and total_carreras >= MINIMO_CARRERAS and tasa >= TASA_MINIMA_EXITO and not errores
            )
            retiradas = retirar_ofertas_obsoletas(institucion, ids_vigentes) if carga_completa else 0
            estado = 'COMPLETADO' if tasa >= TASA_MINIMA_EXITO and not errores else 'PARCIAL'
            cerrar_lote(lote, estado, carreras_ok, total_carreras, len(ids_vigentes), errores)
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Lote {lote.id} ({estado}): {carreras_ok}/{total_carreras} carreras, '
                f'{len(ids_vigentes)} ofertas, {retiradas} retiradas, {len(errores)} errores. KPI-01: {tasa}%.'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error crítico en el scraper maestro: {str(e)}'))
            cerrar_lote(lote, 'ERROR', carreras_ok, total_carreras, len(ids_vigentes), [*errores, f'Crítico: {e}'])
        finally:
            driver.quit()