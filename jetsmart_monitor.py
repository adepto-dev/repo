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
import shutil
from selenium.webdriver.chrome.service import Service

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
        chrome_options.add_argument("--user-agent=Mozilla/5.0")

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

    def select_airport(self, input_selector, airport_code, airport_name):
        try:
            input_field = self.wait_and_click(input_selector)
            time.sleep(1)
            input_field.clear()
            input_field.send_keys(airport_name)
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-test-id*='airport-option'], .airport-option, .dropdown-item"))
            )
            time.sleep(1)
            dropdown_options = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-id*='airport-option'], .airport-option, .dropdown-item")
            for option in dropdown_options:
                if airport_code.upper() in option.text.upper() or airport_name.upper() in option.text.upper():
                    self.driver.execute_script("arguments[0].click();", option)
                    logger.info(f"✅ Aeropuerto seleccionado: {airport_name} ({airport_code})")
                    return True
            logger.warning(f"⚠️ No se encontró el aeropuerto: {airport_name} ({airport_code})")
            return False
        except Exception as e:
            logger.error(f"❌ Error seleccionando aeropuerto {airport_name}: {e}")
            logger.debug(self.driver.page_source)
            self.save_screenshot(f"airport_error_{airport_code}.png")
            return False

    def select_date(self, date_str):
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            day = target_date.day
            month = target_date.month
            year = target_date.year
            self.wait_and_click("[data-test-id='departure-date-input']")
            time.sleep(1)
            for _ in range(12):
                calendar_header = self.driver.find_element(By.CSS_SELECTOR, ".calendar-title, .month-year")
                if calendar_header:
                    text = calendar_header.text.lower()
                    if str(year) in text and target_date.strftime("%B").lower()[:3] in text:
                        break
                next_button = self.driver.find_element(By.CSS_SELECTOR, ".next-month, [aria-label='Siguiente mes']")
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(0.5)
            selector = f"[data-date='{date_str}'], td[data-day='{day}']:not(.disabled), button[data-day='{day}']"
            days = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for d in days:
                if d.is_displayed():
                    self.driver.execute_script("arguments[0].click();", d)
                    logger.info(f"✅ Fecha seleccionada: {date_str}")
                    return True
            logger.warning(f"⚠️ No se pudo seleccionar la fecha: {date_str}")
            return False
        except Exception as e:
            logger.error(f"❌ Error seleccionando fecha {date_str}: {e}")
            self.save_screenshot(f"date_error_{date_str}.png")
            return False

    def search_flights(self, origen_code, origen_name, destino_code, destino_name, fecha):
        try:
            logger.info(f"🚀 Iniciando búsqueda: {origen_name} → {destino_name} para {fecha}")
            self.driver.get("https://jetsmart.com/uy/es/")
            time.sleep(25)
            # Listar todos los iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            logger.info(f"🧩 Número de iframes encontrados: {len(iframes)}")
            for idx, iframe in enumerate(iframes):
                try:
                    logger.info(f"🧪 Intentando entrar al iframe #{idx}")
                    self.driver.switch_to.frame(iframe)
                    if self.driver.find_elements(By.CSS_SELECTOR, "[data-test-id='origin-input']"):
                        logger.info(f"✅ Selector encontrado dentro del iframe #{idx}")
                    self.driver.switch_to.default_content()
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo acceder al iframe #{idx}: {e}")
            self.driver.execute_script("document.querySelectorAll('.modal, .popup, .overlay').forEach(e => e.remove());")
            for selector in [".cookie-accept", ".close-popup", "[data-test-id='accept-cookies']", ".modal-close", ".btn-accept"]:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup.is_displayed():
                        popup.click()
                        time.sleep(1)
                except:
                    continue
            for selector in ["[data-test-id='one-way-radio']", "input[value='one-way']", ".radio-one-way"]:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if not btn.is_selected():
                        btn.click()
                        break
                except:
                    continue
            if not any(self.select_airport(s, origen_code, origen_name) for s in ["[data-test-id='origin-input']", "#origin", ".origin-input", "input[placeholder*='Origen']"]):
                logger.error("❌ No se pudo seleccionar el aeropuerto de origen")
                return []
            if not any(self.select_airport(s, destino_code, destino_name) for s in ["[data-test-id='destination-input']", "#destination", ".destination-input", "input[placeholder*='Destino']"]):
                logger.error("❌ No se pudo seleccionar el aeropuerto de destino")
                return []
            if not self.select_date(fecha):
                logger.error("❌ No se pudo seleccionar la fecha")
                return []
            if not any(self.wait_and_click(s) for s in ["[data-test-id='search-button']", ".search-button", "button[type='submit']"]):
                logger.error("❌ No se pudo hacer click en buscar")
                return []
            logger.info("🔍 Esperando resultados...")
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".flight-result, .flight-option, [data-test-id='flight-card'], .flight-card")))
            return self.extract_flight_results(origen_code, destino_code, fecha)
        except Exception as e:
            logger.error(f"❌ Error en búsqueda de vuelos: {e}")
            self.save_screenshot("search_flights_error.png")
            return []

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Driver cerrado")

def main():
    config = {
        "origen_code": os.getenv('ORIGEN_CODE', 'MVD'),
        "origen_name": os.getenv('ORIGEN_NAME', 'Montevideo'),
        "destino_code": os.getenv('DESTINO_CODE', 'Rio'),
        "destino_name": os.getenv('DESTINO_NAME', 'Rio de Janeiro'),
        "fecha_inicio": os.getenv('FECHA_INICIO', '2026-02-13'),
        "fecha_fin": os.getenv('FECHA_FIN', '2026-02-21'),
        "precio_max": int(os.getenv('PRECIO_MAX', '160'))
    }
    scraper = JetSmartScraper()
    try:
        fecha_start = datetime.strptime(config['fecha_inicio'], "%Y-%m-%d")
        fecha_end = datetime.strptime(config['fecha_fin'], "%Y-%m-%d")
        current_date = fecha_start
        all_flights = []
        while current_date <= fecha_end:
            fecha_str = current_date.strftime("%Y-%m-%d")
            flights = scraper.search_flights(
                config['origen_code'], config['origen_name'],
                config['destino_code'], config['destino_name'],
                fecha_str
            )
            all_flights.extend(flights)
            current_date += timedelta(days=1)
            time.sleep(5)
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
