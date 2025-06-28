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

    def select_airport(self, input_selector, country_code, city_code, country_name, city_name):
        try:
            # Buscar el input y hacer click en el contenedor padre
            input_elem = self.driver.find_element(By.CSS_SELECTOR, input_selector)
            parent = input_elem.find_element(By.XPATH, "./..")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent)
            parent.click()
            time.sleep(1)
            # Esperar a que la lista de países esté visible
            country_list_selector = "ul[data-test-id='ROUTE_COUNTRY_LIST'] li[data-test-value]"
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, country_list_selector)))
            countries = self.driver.find_elements(By.CSS_SELECTOR, country_list_selector)
            found_country = False
            for c in countries:
                if country_code.upper() == c.get_attribute("data-test-value").upper() or country_name.lower() in c.text.lower():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", c)
                    c.click()
                    found_country = True
                    break
            if not found_country:
                logger.warning(f"⚠️ País no encontrado: {country_name} ({country_code})")
                return False
            time.sleep(1)
            # Esperar a que la lista de ciudades esté visible
            city_list_selector = "ul[data-test-id='ROUTE_CITY_LIST'] li[data-test-id*='ROUTE_CITY_LIST_ITEM']"
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, city_list_selector)))
            cities = self.driver.find_elements(By.CSS_SELECTOR, city_list_selector)
            for city in cities:
                if city_code.upper() == city.get_attribute("data-test-value").upper() or city_name.lower() in city.text.lower():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", city)
                    city.click()
                    logger.info(f"✅ Ciudad seleccionada: {city_name} ({city_code})")
                    return True
            logger.warning(f"⚠️ Ciudad no encontrada: {city_name} ({city_code})")
            return False
        except Exception as e:
            logger.error(f"❌ Error seleccionando aeropuerto {city_name}: {e}")
            self.save_screenshot(f"airport_error_{city_code}.png")
            return False
            
    def select_date(self, date_str):
        try:
            # Click en el input de fecha de ida
            self.wait_and_click("[data-test-id='DATE_DEPARTURE_INPUT']")
            time.sleep(1)
            # Buscar el día en el calendario
            selector = f"button[data-date='{date_str}']"
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            day_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day_btn)
            day_btn.click()
            logger.info(f"✅ Fecha seleccionada: {date_str}")
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando fecha {date_str}: {e}")
            self.save_screenshot(f"date_error_{date_str}.png")
            return False

    def search_flights(self, origen_code, origen_name, destino_code, destino_name, fecha):
        try:
            logger.info(f"🚀 Iniciando búsqueda: {origen_name} → {destino_name} para {fecha}")
            self.driver.get("https://jetsmart.com/uy/es/")
            time.sleep(10)
            # Seleccionar solo vuelo
            vuelo_tab = self.driver.find_element(By.XPATH, "//span[contains(text(),'Vuelo')]/ancestor::label")
            if not "active" in vuelo_tab.get_attribute("class"):
                vuelo_tab.click()
                time.sleep(1)
            # Seleccionar solo ida
            one_way_radio = self.driver.find_element(By.CSS_SELECTOR, "[data-test-id='DATE_ONE_WAY_SELECTOR']")
            if not one_way_radio.is_selected():
                one_way_radio.click()
                time.sleep(1)
            # Seleccionar origen
            if not self.select_airport("[data-test-id='ROUTE_ORIGIN_INPUT']", origen_code[:2], origen_code, origen_name, origen_name):
                logger.error("❌ No se pudo seleccionar el aeropuerto de origen")
                return []
            # Seleccionar destino
            if not self.select_airport("[data-test-id='ROUTE_DESTINATION_INPUT']", destino_code[:2], destino_code, destino_name, destino_name):
                logger.error("❌ No se pudo seleccionar el aeropuerto de destino")
                return []
            # Seleccionar fecha
            if not self.select_date_new(fecha):
                logger.error("❌ No se pudo seleccionar la fecha")
                return []
            # Click en buscar
            self.wait_and_click("[data-test-id='SUBMIT_SEARCH_BUTTON']")
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
        "precio_max": int(os.getenv('PRECIO_MAX', '200'))
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
