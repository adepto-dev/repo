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

    def seleccionar_ciudad_por_codigo(self, codigo_pais, codigo_ciudad):
        # Espera y selecciona el país correcto
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

    def seleccionar_fecha_calendario(self, fecha_salida: str, fecha_regreso: str):
        # Abrir el calendario (asume que ya está visible desde el paso anterior)
        # Formato esperado: 'YYYY-MM-DD'

        def esperar_elemento(locator):
            return WebDriverWait(self, 10).until(EC.presence_of_element_located(locator))

        def avanzar_mes_hasta(fecha_objetivo):
            while True:
                contenedor_mes = esperar_elemento((By.CSS_SELECTOR, "[data-test-id='DATE_MONTH_NAME']"))
                valor_mes = contenedor_mes.get_attribute("data-test-value")
                if valor_mes == fecha_objetivo.strftime('%Y-%m'):
                    break
                btn_forward = self.find_element(By.CSS_SELECTOR, "[data-test-id='DATE_MOVE_FORWARD']")
                btn_forward.click()
                time.sleep(0.8)  # Dar tiempo a que actualice

        def seleccionar_dia(fecha_str):
            dia = datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            xpath = f"//*[@data-test-id='DATE_DATE' and @data-test-value='{dia}']"
            WebDriverWait(self, 10).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()

        try: 
            fecha_inicio_dt = datetime.strptime(fecha_salida, "%Y-%m-%d")
            fecha_regreso_dt = datetime.strptime(fecha_regreso, "%Y-%m-%d")

            avanzar_mes_hasta(fecha_inicio_dt)
            seleccionar_dia(fecha_salida)

            avanzar_mes_hasta(fecha_regreso_dt)
            seleccionar_dia(fecha_regreso)
        except Exception as e:
            logger.error(f"❌ Error seleccionando fechas: {e}")
            self.save_screenshot("date_selection_error.png")
            return False

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
            logger.info(f"🚀 Iniciando búsqueda: {origen_name} → {destino_name} para {fecha_start+fecha_end}")
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

            # Hacer clic en el input de origen para activar el selector
            self.wait_and_click("[data-test-id='ROUTE_ORIGIN_INPUT']")
            if not self.seleccionar_ciudad_por_codigo(origen_code):
                logger.error("❌ No se pudo seleccionar el aeropuerto de origen")
                return []

            # Hacer clic en el input de destino
            self.wait_and_click("[data-test-id='ROUTE_DESTINATION_INPUT']")
            if not self.seleccionar_ciudad_por_codigo(destino_code):
                logger.error("❌ No se pudo seleccionar el aeropuerto de destino")
                return []

            # Seleccionar la fecha (solo ida)
            self.wait_and_click("[data-test-id='DATE_ONE_WAY_SELECTOR']")
            if not self.seleccionar_fecha_calendario(fecha_start, fecha_end):
                logger.error("❌ No se pudo seleccionar la fecha")
                return []

            # Buscar vuelos
            self.wait_and_click("[data-test-id='SUBMIT_SEARCH_BUTTON']")
            logger.info("🔍 Esperando resultados...")
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id*='flight']")))
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
        "destino_code": os.getenv('DESTINO_CODE', 'RIO'),
        "destino_name": os.getenv('DESTINO_NAME', 'Rio de Janeiro'),
        "fecha_inicio": os.getenv('FECHA_INICIO', '2026-02-13'),
        "fecha_fin": os.getenv('FECHA_FIN', '2026-02-21'),
        "precio_max": int(os.getenv('PRECIO_MAX', '200'))
    }
    scraper = JetSmartScraper()
    try:
        fecha_start = datetime.strptime(config['fecha_inicio'], "%Y-%m-%d")
        fecha_end = datetime.strptime(config['fecha_fin'], "%Y-%m-%d")
        all_flights = []
        flights = scraper.search_flights(
            config['origen_code'], config['origen_name'],
            config['destino_code'], config['destino_name'],
            fecha_start,
            fecha_end
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
