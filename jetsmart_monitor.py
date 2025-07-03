import time
import requests
import json
import os
import random
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import logging
import shutil
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JetSmartScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless moderno
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # User agents rotativos más realistas
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Desactivar características que delatan automatización
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Headers adicionales
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Simular preferencias de navegador real
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,  # No cargar imágenes para ser más rápido
            "profile.default_content_setting_values.geolocation": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Detectar binarios de Chromium y ChromeDriver
        chromium_path = shutil.which("chromium-browser") or shutil.which("chromium")
        chromedriver_path = shutil.which("chromedriver")
    
        if not chromium_path or not chromedriver_path:
            raise EnvironmentError("❌ No se encontró Chromium o ChromeDriver en el sistema.")
    
        chrome_options.binary_location = chromium_path
        try:
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("✅ Driver de Chromium iniciado correctamente")
        except Exception as e:
            logger.error(f"❌ Error al iniciar Chromium: {e}")
            raise

    def save_screenshot(self, name="error.png"):
        try:
            os.makedirs("screenshots", exist_ok=True)
            self.driver.save_screenshot(f"screenshots/{name}")
            logger.info(f"🖼 Captura guardada: screenshots/{name}")
        except Exception as e:
            logger.error(f"❌ Error guardando captura: {e}")

    def wait_and_click(self, selector, by=By.CSS_SELECTOR, timeout=20):
        try:
            logger.info(f"🔍 Esperando y haciendo click en: {selector}")
            self.wait.until(EC.presence_of_element_located((by, selector)))
            element = self.wait.until(EC.element_to_be_clickable((by, selector)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(1)
            try:
                element.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", element)
            return element
        except Exception as e:
            logger.error(f"❌ Error haciendo click en {selector}: {e}")
            self.save_screenshot("click_error.png")
            raise

    def human_like_delay(self, min_delay=1, max_delay=3):
        """Simula delays humanos aleatorios"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def simulate_human_mouse_movement(self):
        """Simula movimientos de mouse humanos"""
        try:
            action = ActionChains(self.driver)
            # Movimientos aleatorios
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                action.move_by_offset(x, y)
            action.perform()
        except Exception as e:
            logger.warning(f"⚠️ Error simulando movimiento de mouse: {e}")

    
    def seleccionar_ciudad_por_codigo(self, codigo_pais, codigo_ciudad):
        # Espera y selecciona el país correcto
        self.human_like_delay(1, 2)
        country_selector = f"ul[data-test-id='ROUTE_COUNTRY_LIST'] li[data-test-value='{codigo_pais.upper()}']"
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, country_selector)))
        country_elem = self.driver.find_element(By.CSS_SELECTOR, country_selector)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", country_elem)
        country_elem.click()
        time.sleep(10)

        # Espera a que la lista de ciudades esté visible
        city_list_selector = "ul[data-test-id='ROUTE_CITY_LIST'] li[data-test-id*='ROUTE_CITY_LIST_ITEM']"
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, city_list_selector)))
        cities = self.driver.find_elements(By.CSS_SELECTOR, city_list_selector)
        self.human_like_delay(0.5, 1.0)
        if len(cities) == 1:
            # Si solo hay una ciudad, haz click directo
            city = cities[0]
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", city)
            city.click()
            logger.info(f"✅ Ciudad seleccionada automáticamente: {city.text}")
            self.save_screenshot(f"city_selected_{codigo_ciudad}.png")
            return True

        # Si hay varias, busca la correcta
        for city in cities:
            if codigo_ciudad.upper() == city.get_attribute("data-test-value").upper() or city.text.lower() in city.text.lower():
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", city)
                city.click()
                logger.info(f"✅ Ciudad seleccionada: {city.text} ({codigo_ciudad})")
                self.save_screenshot(f"city_selected_{codigo_ciudad}.png")
                return True

        logger.warning(f"⚠️ Ciudad no encontrada: {city.text} ({codigo_ciudad})")
        self.save_screenshot(f"city_not_found_{codigo_ciudad}.png")
        return False
    
    #La función para seleccionar la fecha en el calendario es la 
    # que esta fallando ahora, tenemos que ver como se interactua y cambiar acorde

    def seleccionar_fechas(self, fecha_salida: str, fecha_regreso: str):
        time.sleep(2)  # Asegura renderizado básico
        self.human_like_delay(2, 4)
        logger.info("📅 Iniciando selección de fechas")
    
        def abrir_calendario():
            try:
                ida_y_vuelta_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "[data-test-id='DATE_ONE_WAY_SELECTOR']")))
                ida_y_vuelta_btn.click()
                logger.info("✅ Click en 'Solo Ida'")
                time.sleep(1)
            except Exception as e:
                logger.warning("⚠️ Calendario ya abierto o botón inaccesible: %s", e)
    
        def avanzar_hasta_mes(fecha_objetivo: str):
            mes_objetivo = fecha_objetivo[:7]
            max_intentos = 24
        
            for _ in range(max_intentos):
                # Verificar si el mes ya es visible
                meses_visibles = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-id='DATE_MONTH_NAME']")
                for mes in meses_visibles:
                    if mes.get_attribute("data-test-value") == mes_objetivo:
                        logger.info(f"✅ Mes {mes_objetivo} visible")
                        return True
        
                # Buscar y clicar el botón de avanzar
                botones_forward = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-id='DATE_MOVE_FORWARD']")
                for boton in botones_forward:
                    if boton.is_displayed() and boton.is_enabled():
                        try:
                            # Scroll al contenedor principal del calendario para evitar overlays
                            calendario = self.driver.find_element(By.CSS_SELECTOR, "[data-test-id='DATE_MONTH_CONTAINER']")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", calendario)
                            time.sleep(0.3)
        
                            # Scroll al botón
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                            time.sleep(0.2)
        
                            # Intentar click directo con JS (evita overlays flotantes)
                            self.driver.execute_script("arguments[0].click();", boton)
                            logger.info("➡️ Avanzando un mes...")
                            time.sleep(0.8)
                            break
                        except Exception as e:
                            logger.warning(f"⚠️ Error al avanzar mes: {e}")
                            return False
                else:
                    logger.error("❌ No se pudo hacer click en botón 'avanzar mes'")
                    return False
        
            logger.warning(f"⚠️ No se encontró el mes {mes_objetivo}")
            return False

    
        def seleccionar_dia(fecha: str):
            try:
                dia_elem = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f"[data-test-id='DATE_DATE'][data-test-value='{fecha}']")))
                dia_elem.click()
                logger.info(f"✅ Día seleccionado: {fecha}")
            except Exception as e:
                logger.error(f"❌ No se pudo seleccionar el día {fecha}: {e}")
                self.save_screenshot("error_seleccionar_dia.png")
    
        # 🟢 Lógica principal
        abrir_calendario()
        self.driver.save_screenshot("antes_calendario.png")
    
        if avanzar_hasta_mes(fecha_salida):
            seleccionar_dia(fecha_salida)
            time.sleep(0.5)
    
        if avanzar_hasta_mes(fecha_regreso):
            seleccionar_dia(fecha_regreso)
            time.sleep(0.5)
    
        self.driver.save_screenshot("despues_fechas.png")
        return True

    def close_cookies_banner(self):
        try:
            # Espera hasta 15 segundos a que el div esté presente y visible
            for _ in range(15):
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, "div#consent_prompt_submit")
                    if btn.is_displayed():
                        try:
                            btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        logger.info("🍪 Banner de cookies cerrado")
                        time.sleep(1)
                        return
                except Exception:
                    pass
                time.sleep(1)
            logger.error("❌ No se pudo cerrar el banner de cookies.")
            self.save_screenshot("cookies_not_closed.png")
        except Exception as e:
            logger.error(f"❌ Error cerrando banner de cookies: {e}")
            self.save_screenshot("cookies_error.png")

    def close_subscription_popup(self):
        try:
            # Elimina overlays que puedan estar bloqueando el click
            self.driver.execute_script("""
                let overlays = document.querySelectorAll('.modal-backdrop, .fade, .show, .modal');
                overlays.forEach(el => el.style.zIndex = '1');
            """)
            # Espera hasta 30 segundos a que aparezca el botón de cerrar del modal
            for _ in range(30):
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.close.modal-close")
                    if close_btn.is_displayed() and close_btn.is_enabled():
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_btn)
                            self.driver.execute_script("arguments[0].removeAttribute('disabled');", close_btn)
                            self.driver.execute_script("arguments[0].click();", close_btn)
                            logger.info("🛑 Popup de suscripción cerrado (JS click)")
                            time.sleep(1)
                            return
                        except Exception as e_js:
                            try:
                                actions = ActionChains(self.driver)
                                actions.move_to_element(close_btn).click().perform()
                                logger.info("🛑 Popup de suscripción cerrado (ActionChains)")
                                time.sleep(1)
                                return
                            except Exception as e_ac:
                                logger.error(f"❌ No se pudo clickear el botón de cerrar: JS: {e_js}, AC: {e_ac}")
                                self.save_screenshot("subscription_popup_click_fail.png")
                                return
                except Exception:
                    pass
                time.sleep(1)
            # Si el botón existe pero no se pudo clickear
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.close.modal-close")
                self.save_screenshot("subscription_popup_visible_but_not_closed.png")
                logger.error("❌ El botón de cerrar está visible pero no se pudo clickear.")
            except Exception:
                logger.warning("❌ No se pudo cerrar el popup de suscripción (no se encontró el botón).")
                self.save_screenshot("subscription_popup_not_found.png")
        except Exception as e:
            logger.error(f"❌ Error cerrando popup de suscripción: {e}")
            self.save_screenshot("subscription_popup_error.png")

    def search_flights(self, origen_code, origen_name, destino_code, destino_name, fecha_start, fecha_end):
        try:
            logger.info(f"🚀 Iniciando búsqueda: {origen_name} → {destino_name} para vacaciones")
            self.driver.get("https://jetsmart.com/uy/es/")
            time.sleep(10)
            self.close_cookies_banner()
            self.close_subscription_popup()

            # Cerrar popups si existen
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, ".dg-close, .popup-close, [class*='close'], .close")
                if close_btn.is_displayed():
                    close_btn.click()
                    time.sleep(1)
            except:
                pass

            self.simulate_human_mouse_movement()
            self.human_like_delay(1, 3)
            
            # Hacer clic en el input de origen para activar el selector
            self.wait_and_click("[data-test-id='ROUTE_ORIGIN_INPUT']")
            if not self.seleccionar_ciudad_por_codigo("UY", origen_code):
                logger.error("❌ No se pudo seleccionar el aeropuerto de origen")
                return []

            # Hacer clic en el input de destino
            self.human_like_delay(3, 5)
            self.wait_and_click("[data-test-id='ROUTE_DESTINATION_INPUT']")
            if not self.seleccionar_ciudad_por_codigo("BR", destino_code):
                logger.error("❌ No se pudo seleccionar el aeropuerto de destino")
                return []

            # Seleccionar las fechas
            time.sleep(15)
            self.seleccionar_fechas(fecha_start, fecha_end)
            self.save_screenshot("fechas_seleccionadas.png")
            time.sleep(2)
            self.human_like_delay(2, 4)
            # Buscar vuelos
            self.wait_and_click("[data-test-id='SUBMIT_SEARCH_BUTTON']")
            logger.info("🔍 Esperando resultados...")
            fechas_ida = ["2026-02-12", "2026-02-14", "2026-02-15"]
            fechas_vuelta = ["2026-02-22", "2026-02-23", "2026-02-24"]
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id*='flight']")))
            return self.extract_flight_results(fecha_start, fecha_end, fechas_ida, fechas_vuelta)
        except Exception as e:
            logger.error(f"❌ Error en búsqueda de vuelos: {e}")
            self.save_screenshot("search_flights_error.png")
            return []

    def extract_flight_results(self, fecha_start, fecha_end, fechas_ida, fechas_vuelta):
        vuelos = []

        for idx in [0, 1]:  # 0: Ida, 1: Vuelta
            tipo = "ida" if idx == 0 else "vuelta"
            try:
                # Verificar que existan resultados
                self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f"[data-test-id='flight-header--j|{idx}']"))
                )

                tarjetas = self.driver.find_elements(By.CSS_SELECTOR, f"[data-test-id^='flight-fee-option--j|{idx}-i|']")
                for tarjeta in tarjetas:
                    try:
                        info = tarjeta.find_element(By.CSS_SELECTOR, f"[data-test-id^='flight-flight-info--j|{idx}-i|']")
                        origen = info.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-flight-info-origin--j|{idx}'] .itinerary-station-name").text.strip()
                        hora_salida = info.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-flight-info-origin--j|{idx}'] .itinerary-flight-time").text.strip()
                        destino = info.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-flight-info-destination--j|{idx}'] .itinerary-station-name").text.strip()
                        hora_llegada = info.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-flight-info-destination--j|{idx}'] .itinerary-flight-time").text.strip()

                        precio_smart = tarjeta.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-smart-fee--j|{idx}-i|0']").get_attribute("data-value")
                        try:
                            precio_club = tarjeta.find_element(By.CSS_SELECTOR, f"[data-test-id='flight-club-fee--j|{idx}-i|0']").get_attribute("data-value")
                        except:
                            precio_club = None

                        vuelos.append({
                            "tipo": tipo,
                            "origen": origen,
                            "destino": destino,
                            "fecha": fecha_start if tipo == "ida" else fecha_end,
                            "hora_salida": hora_salida,
                            "hora_llegada": hora_llegada,
                            "precio_smart": float(precio_smart),
                            "precio_club": float(precio_club) if precio_club else None,
                        })
                    except Exception as e:
                        logger.warning(f"⚠️ Error al extraer tarjeta de vuelo {tipo}: {e}")
            except Exception as e:
                logger.warning(f"⚠️ No se encontraron resultados para {tipo}: {e}")

        try:
            self.save_screenshot(f"antes_calendario_alternativo.png")
            btn_otras_fechas = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test-id='flight-switch-to-calendar']"))
            )
            self.driver.execute_script("arguments[0].click();", btn_otras_fechas)
            logger.info(f"🗓 Calendario alternativo abierto")
            time.sleep(3)
            self.save_screenshot(f"calendario_alternativo_abierto.png")
        
            # Procesar ambos tipos de vuelos en loops separados
            tipos_vuelos = []
            
            # Agregar ida si hay fechas válidas
            if fechas_ida:
                tipos_vuelos.append(("ida", 0, fechas_ida))
            
            # Agregar vuelta si hay fechas válidas
            if fechas_vuelta:
                tipos_vuelos.append(("vuelta", 1, fechas_vuelta))
            
            for tipo_vuelo, journey_idx, fechas_validas in tipos_vuelos:
                logger.info(f"🔄 Procesando vuelos de {tipo_vuelo} (journey_idx: {journey_idx})")
                
                # Si es vuelta, hacer scroll hacia la sección correspondiente
                if tipo_vuelo == "vuelta":
                    try:
                        calendar_section = self.driver.find_element(By.CSS_SELECTOR, "[data-test-id='flight-calendar-journey--j|1']")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", calendar_section)
                        time.sleep(2)
                        logger.info("📍 Scroll realizado hacia sección de vuelta")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo hacer scroll a la sección de vuelta: {e}")
                
                # Selector específico para este tipo de vuelo
                calendario_selector = f"[data-test-id^='flight-calendar-day-content--j|{journey_idx}-c|']"
                logger.info(f"🔍 Buscando elementos con selector: {calendario_selector}")
                
                try:
                    # Esperar a que los elementos estén presentes
                    dias = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, calendario_selector)))
                    logger.info(f"📅 Encontrados {len(dias)} días en calendario alternativo de {tipo_vuelo}")
                except TimeoutException:
                    logger.warning(f"⏰ Timeout esperando elementos de {tipo_vuelo}")
                    continue
                
                logger.info(f"📋 Fechas válidas para {tipo_vuelo}: {fechas_validas}")
                
                vuelos_encontrados = 0
                vuelos_procesados = set()
                
                for dia in dias:
                    try:
                        test_id = dia.get_attribute("data-test-id") or ""
                        precio_attr = dia.get_attribute("data-test-value")
                        
                        # Debug: mostrar información del elemento
                        logger.debug(f"🔍 Procesando elemento: test_id='{test_id}', data-test-value='{precio_attr}'")
                        
                        # Extraer fecha del test-id
                        match = re.search(r"(\d{4}-\d{2}-\d{2})", test_id)
                        if not match:
                            logger.debug(f"⚠️ No se pudo extraer fecha de test_id: {test_id}")
                            continue
        
                        fecha_dia = match.group(1)
                        if fecha_dia not in fechas_validas:
                            logger.debug(f"⚠️ Fecha {fecha_dia} no está en fechas válidas para {tipo_vuelo}")
                            continue
        
                        # Crear clave única para evitar duplicados
                        clave_unica = f"{tipo_vuelo}_{fecha_dia}"
                        if clave_unica in vuelos_procesados:
                            logger.debug(f"⚠️ Vuelo duplicado ignorado: {clave_unica}")
                            continue
                        
                        # Intentar obtener precio del atributo data-test-value primero
                        precio = None
                        if precio_attr:
                            try:
                                precio = float(precio_attr)
                                logger.debug(f"✅ Precio extraído de atributo: {precio}")
                            except ValueError:
                                logger.debug(f"⚠️ No se pudo convertir precio_attr '{precio_attr}' a float")
                        
                        # Si no hay precio en el atributo, extraer del texto
                        if precio is None:
                            try:
                                texto_elemento = dia.text.strip()
                                logger.debug(f"📝 Texto del elemento: '{texto_elemento}'")
                                
                                # Limpiar texto y buscar precio
                                lineas = texto_elemento.split('\n')
                                for linea in lineas:
                                    linea = linea.strip()
                                    if linea.startswith('$'):
                                        # Buscar precio en formato $ XX,XX o $ XXX,XX
                                        precio_match = re.search(r'\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', linea)
                                        if precio_match:
                                            precio_str = precio_match.group(1)
                                            # Manejar formato argentino (130,00 -> 130.00)
                                            if ',' in precio_str and '.' not in precio_str:
                                                precio_str = precio_str.replace(',', '.')
                                            elif ',' in precio_str and '.' in precio_str:
                                                precio_str = precio_str.replace('.', '').replace(',', '.')
                                            
                                            precio = float(precio_str)
                                            logger.debug(f"✅ Precio extraído del texto: {precio}")
                                            break
                                
                                if precio is None:
                                    logger.debug(f"⚠️ No se pudo extraer precio del texto: '{texto_elemento}'")
                            except Exception as e:
                                logger.debug(f"⚠️ Error extrayendo precio del texto: {e}")
        
                        if precio is None:
                            logger.warning(f"⚠️ No se pudo obtener precio para {tipo_vuelo} {fecha_dia}")
                            # Mostrar información del elemento para debug
                            logger.debug(f"    HTML: {dia.get_attribute('outerHTML')[:200]}...")
                            continue
        
                        # Marcar como procesado antes de agregar
                        vuelos_procesados.add(clave_unica)
                        
                        vuelos.append({
                            "tipo": tipo_vuelo,
                            "origen": "Alternativo",
                            "destino": "Alternativo",
                            "fecha": fecha_dia,
                            "hora_salida": None,
                            "hora_llegada": None,
                            "precio_smart": precio,
                            "precio_club": None,
                        })
                        
                        vuelos_encontrados += 1
                        logger.info(f"📆 Agregado desde calendario alternativo: {tipo_vuelo} {fecha_dia} ${precio}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error procesando día alternativo {tipo_vuelo}: {e}")
                        # Agregar información de debug
                        try:
                            logger.debug(f"    Test ID: {dia.get_attribute('data-test-id')}")
                            logger.debug(f"    Texto: {dia.text}")
                            logger.debug(f"    Data-test-value: {dia.get_attribute('data-test-value')}")
                            logger.debug(f"    HTML: {dia.get_attribute('outerHTML')[:200]}...")
                        except:
                            pass
        
                logger.info(f"✅ Total vuelos encontrados en calendario alternativo {tipo_vuelo}: {vuelos_encontrados}")
            
            logger.info(f"🎯 Procesamiento de calendario alternativo completado")
            
        except TimeoutException:
            logger.info(f"ℹ️ Calendario alternativo no visible")
        except Exception as e:
            logger.error(f"❌ Error inesperado al procesar calendario alternativo: {e}")
            import traceback
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            
        logger.info(f"✈️ Se extrajeron {len(vuelos)} vuelos")
        return vuelos


    def send_discord_notification(self, flights, precio_max):
        if not flights:
            logger.info("😞 No hay vuelos para notificar")
            return

        url = os.getenv('DISCORD_WEBHOOK_URL')
        if not url:
            logger.error("❌ No se ha configurado el webhook de Discord")
            return

        embed = {
            "title": "✈️ Vuelos encontrados",
            "description": f"Se encontraron {len(flights)} vuelos desde {flights[0]['origen']} a {flights[0]['destino']}",
            "color": 5814783,
            "fields": []
        }

        for flight in flights:
            if flight['precio_smart'] <= precio_max:
                embed["fields"].append({
                    "name": f"{flight['tipo'].capitalize()} - {flight['origen']} → {flight['destino']} ({flight['fecha']})",
                    "value": f"Hora: {flight['hora_salida']} - {flight['hora_llegada']}\n"
                             f"Precio SMART: ${flight['precio_smart']:.2f}\n"
                             f"Precio CLUB: ${flight['precio_club']:.2f}" if flight['precio_club'] else "",
                    "inline": False
                })

        data = {
            "embeds": [embed]
        }

        try:
            response = requests.post(url, json=data)
            if response.status_code == 204:
                logger.info("✅ Notificación enviada a Discord")
            else:
                logger.error(f"❌ Error al enviar notificación a Discord: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación a Discord: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Driver cerrado")

def main():
    config = {
        "origen_code": os.getenv('ORIGEN_CODE', 'MVD'),
        "origen_name": os.getenv('ORIGEN_NAME', 'Montevideo'),
        "destino_code": os.getenv('DESTINO_CODE', 'RIO'),
        "destino_name": os.getenv('DESTINO_NAME', 'Rio de Janeiro'),
        "fecha_inicio": os.getenv('FECHA_INICIO', '2026-02-13'),
        "fecha_fin": os.getenv('FECHA_FIN', '2026-02-21'),
        "precio_max": int(os.getenv('PRECIO_MAX', '200'))
    }
    scraper = JetSmartScraper()
    # Iterar sobre un grupo de fechas (ejemplo: varias fechas de ida y vuelta)
    
    try:
        all_flights = []
        flights = scraper.search_flights(
            config['origen_code'], config['origen_name'],
            config['destino_code'], config['destino_name'],
            config['fecha_inicio'], config['fecha_fin']
        )
        all_flights.extend(flights)

        if all_flights:
            scraper.send_discord_notification(all_flights, config['precio_max'])
        else:
            logger.info("😞 No se encontraron vuelos")
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        scraper.save_screenshot("main_error.png")
        raise
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
