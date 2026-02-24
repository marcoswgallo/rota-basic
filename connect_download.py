import os
import time
import shutil
import logging
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

BASE_URL = "https://basic.controlservices.com.br"
LOGIN_URL = f"{BASE_URL}/login"
REL_URL = f"{BASE_URL}/financeiro/relatorio"

DOWNLOAD_DIR = os.path.abspath("./downloads")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("basic_analitico")


def clean_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def wait_download(download_dir: str, timeout=240) -> str:
    end = time.time() + timeout
    while time.time() < end:
        files = os.listdir(download_dir)

        # aguardando downloads parciais
        if any(f.endswith(".crdownload") for f in files):
            time.sleep(1)
            continue

        xlsx = [f for f in files if f.lower().endswith(".xlsx")]
        if xlsx:
            paths = [os.path.join(download_dir, f) for f in xlsx]
            latest = max(paths, key=os.path.getmtime)
            return latest

        time.sleep(1)

    raise TimeoutError("Download do XLSX não apareceu no tempo esperado.")


def mark_excel_checkbox(driver):
    """
    Marca o checkbox 'EXCEL' de forma robusta:
    - tenta achar o input checkbox perto do texto 'EXCEL'
    """
    # tenta pelo label contendo EXCEL
    labels = driver.find_elements(By.XPATH, "//label[contains(translate(., 'excel', 'EXCEL'),'EXCEL')]")
    if labels:
        for lab in labels:
            try:
                # se label estiver ligado a input via 'for'
                for_attr = lab.get_attribute("for")
                if for_attr:
                    cb = driver.find_element(By.ID, for_attr)
                    if not cb.is_selected():
                        driver.execute_script("arguments[0].click();", cb)
                    return
            except Exception:
                pass

    # fallback: qualquer checkbox visível próximo do texto EXCEL
    cb = driver.find_element(
        By.XPATH,
        "//*[contains(translate(., 'excel','EXCEL'),'EXCEL')]/preceding::input[@type='checkbox'][1]"
    )
    if not cb.is_selected():
        driver.execute_script("arguments[0].click();", cb)


def baixar_relatorio_analitico(data_ini: str, data_fim: str) -> str:
    """
    data_ini / data_fim no formato YYYY-MM-DD (ex: 2026-02-24)
    """
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Defina EMAIL e PASSWORD no .env")

    clean_dir(DOWNLOAD_DIR)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("--lang=pt-BR")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        # 1) LOGIN
        log.info("Abrindo login…")
        driver.get(LOGIN_URL)

        email_el = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        pass_el = driver.find_element(By.NAME, "password")

        email_el.clear()
        email_el.send_keys(EMAIL)
        pass_el.clear()
        pass_el.send_keys(PASSWORD)

        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # aguarda home
        wait.until(EC.url_contains("/home"))
        log.info("Login OK.")

        # 2) IR PRA PÁGINA DO RELATÓRIO
        log.info("Abrindo página do relatório…")
        driver.get(REL_URL)

        # 3) MODELO = Relatorio Analitico (select name='tipoRelat')
        log.info("Selecionando modelo: Relatorio Analitico…")
        modelo_el = wait.until(EC.element_to_be_clickable((By.NAME, "tipoRelat")))
        Select(modelo_el).select_by_visible_text("Relatorio Analitico")

        # 4) DATAS
        log.info(f"Preenchendo datas: {data_ini} a {data_fim}…")
        data_ini_el = driver.find_element(By.NAME, "data_ini")
        data_fim_el = driver.find_element(By.NAME, "data_fim")

        # set via JS (evita máscara do input)
        driver.execute_script("arguments[0].value = arguments[1];", data_ini_el, data_ini)
        driver.execute_script("arguments[0].value = arguments[1];", data_fim_el, data_fim)

        # 5) MARCAR EXCEL
        log.info("Marcando opção EXCEL…")
        mark_excel_checkbox(driver)

        # 6) CLICAR BUSCAR
        log.info("Clicando em BUSCAR…")
        buscar_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'BUSCAR')]")))
        buscar_btn.click()

        # 7) ESPERAR DOWNLOAD
        log.info("Aguardando download do XLSX…")
        xlsx_path = wait_download(DOWNLOAD_DIR, timeout=300)
        log.info(f"OK: {xlsx_path}")
        return xlsx_path

    finally:
        driver.quit()


if __name__ == "__main__":
    hoje = datetime.today().strftime("%Y-%m-%d")
    print(baixar_relatorio_analitico(hoje, hoje))