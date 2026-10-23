import json
import os
import time
from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Command(BaseCommand):
    help = 'Itera sobre el portal de carreras de INACAP y extrae el detalle completo incluyendo aranceles'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando scraper maestro...'))
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--headless") # Descomentar cuando lo subas a AWS EC2 para que corra en segundo plano
        
        driver = webdriver.Chrome(options=chrome_options)
        catalogo_completo = []

        try:
            # 1. Obtener los enlaces de TODAS las carreras
            url_principal = "https://portal.inacap.cl/carreras"
            driver.get(url_principal)
            
            self.stdout.write(self.style.WARNING('Buscando enlaces de carreras en el portal principal...'))
            
            # Esperar a que carguen los botones de "Ver Carrera"
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-ver-carrera"))
            )
            
            botones_carrera = driver.find_elements(By.CSS_SELECTOR, ".btn-ver-carrera")
            enlaces_carreras = []
            
            # Limpiar y recolectar URLs únicas
            for boton in botones_carrera:
                href = boton.get_attribute("href")
                if href and href not in enlaces_carreras:
                    enlaces_carreras.append(href)
                    
            self.stdout.write(self.style.SUCCESS(f'✅ Se encontraron {len(enlaces_carreras)} carreras para procesar.'))

            # 2. Iterar sobre cada enlace y extraer la información
            for i, enlace in enumerate(enlaces_carreras, 1):
                self.stdout.write(self.style.WARNING(f'Procesando {i}/{len(enlaces_carreras)}: {enlace}'))
                
                try:
                    driver.get(enlace)
                    
                    # Esperar a que cargue el acordeón principal en la página de detalle
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "accordionCarreras"))
                    )
                    
                    datos_carrera = {
                        "url_origen": enlace,
                        "nombre_carrera": driver.find_element(By.CSS_SELECTOR, "h1.component-heading").text.strip(),
                        "ficha_tecnica": {},
                        "detalles": {},
                        "sedes": [],
                        "opciones_select": [],
                        "aranceles": []
                    }

                    # --- A. Ficha técnica (Título, Duración, Continuidad) ---
                    pares_ficha = driver.find_elements(By.XPATH, "//div[p[contains(@class, 'cabecera-info-carrera')]]")
                    for par in pares_ficha:
                        try:
                            llave = par.find_element(By.CSS_SELECTOR, ".cabecera-info-carrera").text.strip()
                            valor = par.find_element(By.CSS_SELECTOR, ".contenido-info-carrera").text.strip()
                            if llave and valor:
                                datos_carrera["ficha_tecnica"][llave] = valor
                        except:
                            continue

                    # --- B. Acordeones (Descripción, Perfil, etc.) ---
                    acordeones = driver.find_elements(By.CSS_SELECTOR, ".card-acordion-carrera-26")
                    for acordeon in acordeones:
                        try:
                            titulo = acordeon.find_element(By.CSS_SELECTOR, ".buttom-acordion-carrera-26").text.strip()
                            if "Aranceles" not in titulo and "Sedes" not in titulo:
                                cuerpo = acordeon.find_element(By.CSS_SELECTOR, ".card-body")
                                datos_carrera["detalles"][titulo] = cuerpo.get_attribute("innerText").strip()
                        except:
                            continue
                    
                    # --- C. Sedes y Jornadas ---
                    sedes_items = driver.find_elements(By.CSS_SELECTOR, ".lista-sedes .item-sede")
                    for sede in sedes_items:
                        try:
                            nombre_sede = sede.find_element(By.CSS_SELECTOR, ".nombre-sede").text.strip()
                            jornadas = [j.text.strip() for j in sede.find_elements(By.CSS_SELECTOR, ".chip-jornada")]
                            datos_carrera["sedes"].append({
                                "sede": nombre_sede, 
                                "jornadas": jornadas
                            })
                        except:
                            continue
                    
                    # --- D. Opciones de los <select> ---
                    sedes_select = []
                    elementos_select = driver.find_elements(By.TAG_NAME, "select")
                    for select in elementos_select:
                        opciones = select.find_elements(By.TAG_NAME, "option")
                        for op in opciones:
                            texto_opcion = op.text.strip()
                            if texto_opcion and "seleccione" not in texto_opcion.lower():
                                sedes_select.append(texto_opcion)
                    
                    datos_carrera["opciones_select"] = list(set(sedes_select))

                    # --- E. Aranceles (Entrando al Iframe) ---
                    try:
                        # Buscar el iframe y cambiar el foco
                        iframe = driver.find_element(By.CSS_SELECTOR, "iframe.iframe-aranceles")
                        driver.switch_to.frame(iframe)
                        
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, "table-bottom"))
                        )

                        filas_borde = driver.find_elements(By.CSS_SELECTOR, "#table-bottom tr.borde")
                        
                        for fila in filas_borde:
                            columnas = fila.find_elements(By.TAG_NAME, "td")
                            if len(columnas) >= 5:
                                datos_carrera["aranceles"].append({
                                    "sede": columnas[0].text.strip(),
                                    "titulo": columnas[1].text.strip(),
                                    "horario": columnas[2].text.strip(),
                                    "valor_matricula": columnas[3].text.strip(),
                                    "valor_semestral": columnas[4].text.strip()
                                })
                    except Exception as e_iframe:
                        self.stdout.write(self.style.WARNING(f'  -> Sin datos de aranceles en {enlace}'))
                    finally:
                        # CRÍTICO: Siempre volver al contenido principal
                        driver.switch_to.default_content()
                            
                    # Añadir la carrera procesada al catálogo maestro
                    catalogo_completo.append(datos_carrera)
                    
                    # Pausa de cortesía para no saturar al servidor (2 a 3 segundos es ideal)
                    time.sleep(2)
                    
                except Exception as error_carrera:
                    self.stdout.write(self.style.ERROR(f'⚠️ Error al procesar {enlace}: {str(error_carrera)}'))
                    continue

            # 3. Guardar el resultado final
            ruta_json = os.path.join(os.getcwd(), 'catalogo_inacap_completo.json')
            with open(ruta_json, 'w', encoding='utf-8') as archivo_json:
                json.dump(catalogo_completo, archivo_json, ensure_ascii=False, indent=4)

            self.stdout.write(self.style.SUCCESS(f'\n✅ ¡Proceso finalizado! {len(catalogo_completo)} carreras guardadas en {ruta_json}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error crítico en el scraper maestro: {str(e)}'))
        
        finally:
            driver.quit()