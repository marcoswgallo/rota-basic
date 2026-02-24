import os
import time
import shutil
import logging
from datetime import datetime
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# =========================
# CONFIG / ENV
# =========================
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

ONEDRIVE_USER = os.getenv("ONEDRIVE_USER")  # e-mail corporativo (UPN)
ONEDRIVE_FOLDER = os.getenv("ONEDRIVE_FOLDER", "Rota-Basic/Analitico")
ONEDRIVE_FILENAME = os.getenv("ONEDRIVE_FILENAME", "analitico_atual.xlsx")

BASE_URL = "https://basic.controlservices.com.br"
LOGIN_URL = f"{BASE_URL}/login"
REL_URL = f"{BASE_URL}/financeiro/relatorio"

DOWNLOAD_DIR = os.path.abspath("./downloads")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("rota-basic")


# =========================
# UTILS
# =========================
def clean_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)

def wait_download(download_dir: str, timeout=300) -> str:
    end = time.time() + timeout
    while time.time() < end:
        files = os.listdir(download_dir)

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
    Marca o checkbox EXCEL de forma robusta (caso o HTML mude um pouco).
    """
    # Tenta achar por label com texto "EXCEL"
    labels = driver.find_elements(By.XPATH, "//label[contains(translate(., 'excel', 'EXCEL'),'EXCEL')]")
    for lab in labels:
        try:
            for_attr = lab.get_attribute("for")
            if for_attr:
                cb = driver.find_element(By.ID, for_attr)
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                return
        except Exception:
            pass

    # Fallback: pega o checkbox antes do texto EXCEL
    cb = driver.find_element(
        By.XPATH,
        "//*[contains(translate(., 'excel','EXCEL'),'EXCEL')]/preceding::input[@type='checkbox'][1]"
    )
    if not cb.is_selected():
        driver.execute_script("arguments[0].click();", cb)


# =========================
# 1) DOWNLOAD DO ANALÍTICO
# =========================
def baixar_relatorio_analitico(data_ini: str, data_fim: str) -> str:
    """
    data_ini / data_fim no formato YYYY-MM-DD
    Retorna caminho do XLSX baixado
    """
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Defina EMAIL e PASSWORD no .env.")

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
        # Login
        log.info("Abrindo login...")
        driver.get(LOGIN_URL)

        email_el = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        pass_el = driver.find_element(By.NAME, "password")

        email_el.clear()
        email_el.send_keys(EMAIL)
        pass_el.clear()
        pass_el.send_keys(PASSWORD)

        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        wait.until(EC.url_contains("/home"))
        log.info("Login OK.")

        # Página do relatório
        log.info("Abrindo página do relatório...")
        driver.get(REL_URL)

        # Seleciona modelo Relatorio Analitico
        log.info("Selecionando modelo: Relatorio Analitico...")
        modelo_el = wait.until(EC.element_to_be_clickable((By.NAME, "tipoRelat")))
        Select(modelo_el).select_by_visible_text("Relatorio Analitico")

        # Preenche datas
        log.info(f"Preenchendo datas: {data_ini} a {data_fim}...")
        data_ini_el = driver.find_element(By.NAME, "data_ini")
        data_fim_el = driver.find_element(By.NAME, "data_fim")
        driver.execute_script("arguments[0].value = arguments[1];", data_ini_el, data_ini)
        driver.execute_script("arguments[0].value = arguments[1];", data_fim_el, data_fim)

        # Marca Excel
        log.info("Marcando opção EXCEL...")
        mark_excel_checkbox(driver)

        # Buscar
        log.info("Clicando em BUSCAR...")
        buscar_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'BUSCAR')]")))
        buscar_btn.click()

        # Download
        log.info("Aguardando download do XLSX...")
        xlsx_path = wait_download(DOWNLOAD_DIR, timeout=300)
        log.info(f"OK: {xlsx_path}")
        return xlsx_path

    finally:
        driver.quit()


# =========================
# 2) AUTH + UPLOAD ONEDRIVE
# =========================
def get_graph_access_token() -> str:
    """
    Client Credentials (app-only) para Microsoft Graph
    """
    if not TENANT_ID or not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("Defina TENANT_ID, CLIENT_ID e CLIENT_SECRET no .env.")

    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }

    r = requests.post(token_url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def ensure_onedrive_folder(token: str, user_upn: str, folder_path: str):
    """
    Garante que a estrutura de pastas exista no OneDrive do usuário.
    Cria pasta a pasta, nível por nível.
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Começa no root
    parent_item_id = None  # root

    parts = [p for p in folder_path.strip("/").split("/") if p.strip()]
    for part in parts:
        part_escaped = part.replace("'", "''")

        if parent_item_id:
            list_url = f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/items/{parent_item_id}/children?$filter=name eq '{part_escaped}'"
        else:
            list_url = f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/root/children?$filter=name eq '{part_escaped}'"

        resp = requests.get(list_url, headers=headers, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("value", [])
        if items:
            parent_item_id = items[0]["id"]
            continue

        # criar pasta
        create_url = (
            f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/items/{parent_item_id}/children"
            if parent_item_id
            else f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/root/children"
        )

        payload = {
            "name": part,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }

        c = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=30)
        c.raise_for_status()
        parent_item_id = c.json()["id"]

def upload_onedrive(local_file_path: str) -> str:
    """
    Faz upload do arquivo para:
      OneDrive do usuário (ONEDRIVE_USER) em ONEDRIVE_FOLDER/ONEDRIVE_FILENAME
    Retorna webUrl do arquivo no OneDrive.
    """
    if not ONEDRIVE_USER:
        raise RuntimeError("Defina ONEDRIVE_USER (email corporativo) no .env.")

    token = get_graph_access_token()

    # garante pasta existir
    ensure_onedrive_folder(token, ONEDRIVE_USER, ONEDRIVE_FOLDER)

    # upload simples (<= ~4MB ok; se for maior, trocamos pra upload session)
    # aqui vamos direto no caminho
    folder_enc = quote(ONEDRIVE_FOLDER.strip("/"))
    filename_enc = quote(ONEDRIVE_FILENAME)

    upload_url = (
        f"https://graph.microsoft.com/v1.0/users/{quote(ONEDRIVE_USER)}/drive/root:"
        f"/{folder_enc}/{filename_enc}:/content"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    with open(local_file_path, "rb") as f:
        r = requests.put(upload_url, headers=headers, data=f, timeout=300)
    r.raise_for_status()

    web_url = r.json().get("webUrl", "")
    log.info("Upload OneDrive OK.")
    if web_url:
        log.info(f"Link: {web_url}")
    return web_url


# =========================
# MAIN
# =========================
def main():
    hoje = datetime.today().strftime("%Y-%m-%d")

    log.info("=== INÍCIO ROTINA ===")
    xlsx_path = baixar_relatorio_analitico(hoje, hoje)
    upload_onedrive(xlsx_path)
    log.info("=== FIM ROTINA ===")

if __name__ == "__main__":
    main()