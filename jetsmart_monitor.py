import time
import requests
import json
import os
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

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JetSmartScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.setup_driver()
    
    def setup_driver(self):
        """Configura el driver de Chrome para GitHub Actions"""
        chrome_options = Options()
        
        # Opciones para GitHub Actions
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        # User agent realista
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Deshabilitar notificaciones y popups
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("✅ Driver de Chrome iniciado correctamente")
        except Exception as e:
            logger.error(f"❌ Error al iniciar Chrome: {e}")
            raise

    def wait_and_click(self, selector, by=By.CSS_SELECTOR, timeout=20):
        """Espera a que un elemento sea clickeable y hace click"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(1)
            
            # Intentar click normal primero
            try:
                element.click()
            except ElementClickInterceptedException:
                # Si falla, usar JavaScript
                self.driver.execute_script("arguments[0].click();", element)
            
            logger.info(f"✅ Click exitoso en: {selector}")
            return element
        except Exception as e:
            logger.error(f"❌ Error haciendo click en {selector}: {e}")
            raise

    def select_airport(self, input_selector, airport_code, airport_name):
        """Selecciona un aeropuerto en los campos de origen/destino"""
        try:
            # Click en el campo
            input_field = self.wait_and_click(input_selector)
            time.sleep(2)
            
            # Limpiar y escribir
            input_field.clear()
            input_field.send_keys(airport_name)
            time.sleep(3)
            
            # Buscar en la lista desplegable
            dropdown_options = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid*='airport-option'], .airport-option, .dropdown-item")
            
            for option in dropdown_options:
                if airport_code.upper() in option.text.upper() or airport_name.upper() in option.text.upper():
                    self.driver.execute_script("arguments[0].click();", option)
                    logger.info(f"✅ Aeropuerto seleccionado: {airport_name} ({airport_code})")
                    return True
            
            logger.warning(f"⚠️ No se encontró el aeropuerto: {airport_name} ({airport_code})")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error seleccionando aeropuerto {airport_name}: {e}")
            return False

    def select_date(self, date_str):
        """Selecciona una fecha en el calendario"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Click en selector de fecha
            date_selectors = [
                "[data-testid='departure-date-input']",
                ".date-picker-input",
                "input[placeholder*='fecha']",
                "input[type='date']"
            ]
            
            date_clicked = False
            for selector in date_selectors:
                try:
                    self.wait_and_click(selector)
                    date_clicked = True
                    break
                except:
                    continue
            
            if not date_clicked:
                logger.error("❌ No se pudo abrir el selector de fecha")
                return False
            
            time.sleep(2)
            
            # Buscar el día en el calendario
            day = target_date.day
            month = target_date.month
            year = target_date.year
            
            # Posibles selectores para días del calendario
            day_selectors = [
                f"[data-date='{date_str}']",
                f"[aria-label*='{day}']",
                f".calendar-day[data-day='{day}']",
                f"button[data-day='{day}']",
                f"td[data-day='{day}']:not(.disabled)",
                f".day:not(.disabled):contains('{day}')"
            ]
            
            for selector in day_selectors:
                try:
                    day_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for day_element in day_elements:
                        if str(day) in day_element.text and "disabled" not in day_element.get_attribute("class"):
                            self.driver.execute_script("arguments[0].click();", day_element)
                            logger.info(f"✅ Fecha seleccionada: {date_str}")
                            return True
                except:
                    continue
            
            logger.warning(f"⚠️ No se pudo seleccionar la fecha: {date_str}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error seleccionando fecha {date_str}: {e}")
            return False

    def search_flights(self, origen_code, origen_name, destino_code, destino_name, fecha):
        """Realiza la búsqueda completa de vuelos paso a paso"""
        try:
            logger.info(f"🚀 Iniciando búsqueda: {origen_name} → {destino_name} para {fecha}")
            
            # 1. Ir a la página principal de JetSmart
            self.driver.get("https://jetsmart.com/uy/es/")
            time.sleep(5)
            
            # 2. Cerrar popups/cookies si aparecen
            popup_selectors = [
                ".cookie-accept",
                ".close-popup",
                "[data-testid='accept-cookies']",
                ".modal-close",
                ".btn-accept"
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup.is_displayed():
                        popup.click()
                        time.sleep(1)
                except:
                    continue
            
            # 3. Seleccionar "Solo ida" si hay opción
            try:
                one_way_selectors = [
                    "[data-testid='one-way-radio']",
                    "input[value='one-way']",
                    ".radio-one-way"
                ]
                
                for selector in one_way_selectors:
                    try:
                        one_way = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if not one_way.is_selected():
                            one_way.click()
                            break
                    except:
                        continue
            except:
                pass
            
            # 4. Seleccionar aeropuerto de origen
            origen_selectors = [
                "[data-testid='origin-input']",
                "#origin",
                ".origin-input",
                "input[placeholder*='Origen']",
                "input[placeholder*='origen']"
            ]
            
            origen_selected = False
            for selector in origen_selectors:
                try:
                    if self.select_airport(selector, origen_code, origen_name):
                        origen_selected = True
                        break
                except:
                    continue
            
            if not origen_selected:
                logger.error("❌ No se pudo seleccionar el aeropuerto de origen")
                return []
            
            time.sleep(2)
            
            # 5. Seleccionar aeropuerto de destino
            destino_selectors = [
                "[data-testid='destination-input']",
                "#destination",
                ".destination-input",
                "input[placeholder*='Destino']",
                "input[placeholder*='destino']"
            ]
            
            destino_selected = False
            for selector in destino_selectors:
                try:
                    if self.select_airport(selector, destino_code, destino_name):
                        destino_selected = True
                        break
                except:
                    continue
            
            if not destino_selected:
                logger.error("❌ No se pudo seleccionar el aeropuerto de destino")
                return []
            
            time.sleep(2)
            
            # 6. Seleccionar fecha
            if not self.select_date(fecha):
                logger.error("❌ No se pudo seleccionar la fecha")
                return []
            
            time.sleep(2)
            
            # 7. Buscar vuelos
            search_selectors = [
                "[data-testid='search-button']",
                ".search-button",
                ".btn-search",
                "button[type='submit']",
                ".submit-search"
            ]
            
            search_clicked = False
            for selector in search_selectors:
                try:
                    self.wait_and_click(selector)
                    search_clicked = True
                    break
                except:
                    continue
            
            if not search_clicked:
                logger.error("❌ No se pudo hacer click en buscar")
                return []
            
            logger.info("🔍 Búsqueda iniciada, esperando resultados...")
            
            # 8. Esperar y extraer resultados
            time.sleep(10)  # Esperar a que carguen los resultados
            
            return self.extract_flight_results(origen_code, destino_code, fecha)
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda de vuelos: {e}")
            return []

    def extract_flight_results(self, origen, destino, fecha):
        """Extrae los resultados de vuelos de la página"""
        vuelos = []
        
        try:
            # Esperar a que aparezcan los resultados
            result_selectors = [
                ".flight-result",
                ".flight-option",
                "[data-testid='flight-card']",
                ".flight-card",
                ".flight-item"
            ]
            
            flights_found = False
            for selector in result_selectors:
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    flights_found = True
                    break
                except:
                    continue
            
            if not flights_found:
                logger.warning("⚠️ No se encontraron vuelos o no cargaron los resultados")
                return []
            
            # Extraer información de vuelos
            flight_elements = []
            for selector in result_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    flight_elements = elements
                    break
            
            logger.info(f"📋 Encontrados {len(flight_elements)} elementos de vuelo")
            
            for i, flight_element in enumerate(flight_elements[:10]):  # Máximo 10 vuelos
                try:
                    # Extraer precio
                    precio_selectors = [
                        ".price",
                        ".flight-price",
                        "[data-testid='price']",
                        ".fare-price",
                        ".amount"
                    ]
                    
                    precio = 0
                    precio_text = ""
                    
                    for precio_selector in precio_selectors:
                        try:
                            precio_element = flight_element.find_element(By.CSS_SELECTOR, precio_selector)
                            precio_text = precio_element.text
                            # Limpiar texto del precio
                            precio_clean = precio_text.replace("$", "").replace(".", "").replace(",", "").replace("CLP", "").strip()
                            if precio_clean.isdigit():
                                precio = int(precio_clean)
                                break
                        except:
                            continue
                    
                    # Extraer horarios
                    time_selectors = [
                        ".departure-time",
                        ".flight-time",
                        "[data-testid='departure-time']",
                        ".time"
                    ]
                    
                    hora_salida = "N/A"
                    hora_llegada = "N/A"
                    
                    for time_selector in time_selectors:
                        try:
                            time_elements = flight_element.find_elements(By.CSS_SELECTOR, time_selector)
                            if len(time_elements) >= 2:
                                hora_salida = time_elements[0].text
                                hora_llegada = time_elements[1].text
                                break
                            elif len(time_elements) == 1:
                                hora_salida = time_elements[0].text
                        except:
                            continue
                    
                    if precio > 0:
                        vuelo = {
                            "origen": origen,
                            "destino": destino,
                            "fecha": fecha,
                            "hora_salida": hora_salida,
                            "hora_llegada": hora_llegada,
                            "precio": precio,
                            "precio_texto": precio_text,
                            "url": self.driver.current_url
                        }
                        vuelos.append(vuelo)
                        logger.info(f"✅ Vuelo {i+1}: {origen}→{destino} ${precio:,} ({hora_salida}-{hora_llegada})")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando vuelo {i+1}: {e}")
                    continue
            
            logger.info(f"✅ Extraídos {len(vuelos)} vuelos válidos")
            return vuelos
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo resultados: {e}")
            return []

    def send_discord_notification(self, vuelos, precio_max):
        """Envía notificación a Discord"""
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.error("❌ DISCORD_WEBHOOK_URL no configurado")
            return
        
        vuelos_baratos = [v for v in vuelos if v['precio'] <= precio_max]
        
        if not vuelos_baratos:
            logger.info("ℹ️ No hay vuelos bajo el precio máximo")
            return
        
        try:
            embeds = []
            for vuelo in vuelos_baratos[:5]:  # Máximo 5 vuelos
                embed = {
                    "title": "🛫 Vuelo Económico Encontrado!",
                    "color": 3066993,
                    "fields": [
                        {"name": "Ruta", "value": f"{vuelo['origen']} → {vuelo['destino']}", "inline": True},
                        {"name": "Fecha", "value": vuelo['fecha'], "inline": True},
                        {"name": "Precio", "value": f"${vuelo['precio']:,} CLP", "inline": True},
                        {"name": "Horario", "value": f"{vuelo['hora_salida']} - {vuelo['hora_llegada']}", "inline": True}
                    ],
                    "timestamp": datetime.now().isoformat(),
                    "footer": {"text": "JetSmart Monitor"}
                }
                embeds.append(embed)
            
            payload = {
                "content": f"🎉 Encontrados {len(vuelos_baratos)} vuelo(s) bajo ${precio_max:,} CLP!",
                "embeds": embeds
            }
            
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 204:
                logger.info("✅ Notificación enviada a Discord")
            else:
                logger.error(f"❌ Error enviando a Discord: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {e}")

    def close(self):
        """Cierra el driver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Driver cerrado")

def main():
    """Función principal"""
    # Configuración desde variables de entorno
    config = {
        "origen_code": os.getenv('ORIGEN_CODE', 'SCL'),
        "origen_name": os.getenv('ORIGEN_NAME', 'Santiago'),
        "destino_code": os.getenv('DESTINO_CODE', 'BUE'),
        "destino_name": os.getenv('DESTINO_NAME', 'Buenos Aires'),
        "fecha_inicio": os.getenv('FECHA_INICIO', '2025-07-01'),
        "fecha_fin": os.getenv('FECHA_FIN', '2025-07-31'),
        "precio_max": int(os.getenv('PRECIO_MAX', '80000'))
    }
    
    scraper = JetSmartScraper()
    
    try:
        # Convertir fechas
        fecha_start = datetime.strptime(config['fecha_inicio'], "%Y-%m-%d")
        fecha_end = datetime.strptime(config['fecha_fin'], "%Y-%m-%d")
        
        todos_los_vuelos = []
        
        # Buscar vuelos para cada fecha
        current_date = fecha_start
        while current_date <= fecha_end:
            fecha_str = current_date.strftime("%Y-%m-%d")
            
            vuelos = scraper.search_flights(
                config['origen_code'],
                config['origen_name'],
                config['destino_code'],
                config['destino_name'],
                fecha_str
            )
            
            todos_los_vuelos.extend(vuelos)
            current_date += timedelta(days=1)
            time.sleep(5)  # Pausa entre búsquedas
        
        # Enviar notificación si hay vuelos baratos
        if todos_los_vuelos:
            scraper.send_discord_notification(todos_los_vuelos, config['precio_max'])
        else:
            logger.info("😞 No se encontraron vuelos")
            
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
