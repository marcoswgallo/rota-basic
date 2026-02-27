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

ONEDRIVE_USER = os.getenv("ONEDRIVE_USER")
ONEDRIVE_FOLDER = os.getenv("ONEDRIVE_FOLDER", "Rota-Basic/Analitico")
ONEDRIVE_FILENAME = os.getenv("ONEDRIVE_FILENAME", "analitico_atual.xlsx")

BASE_URL = "https://basic.controlservices.com.br"
LOGIN_URL = f"{BASE_URL}/login"
REL_URL = f"{BASE_URL}/financeiro/relatorio"

DOWNLOAD_DIR = os.path.abspath("./downloads")

# Timeouts configuráveis via .env
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))

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
    """
    Aguarda o download do XLSX com log de progresso a cada 30s.
    Lança TimeoutError se não aparecer no prazo.
    """
    end = time.time() + timeout
    last_log = time.time()

    while time.time() < end:
        files = os.listdir(download_dir)

        if any(f.endswith(".crdownload") for f in files):
            if time.time() - last_log >= 30:
                log.info("Download em progresso (.crdownload detectado)...")
                last_log = time.time()
            time.sleep(1)
            continue

        xlsx = [f for f in files if f.lower().endswith(".xlsx")]
        if xlsx:
            paths = [os.path.join(download_dir, f) for f in xlsx]
            latest = max(paths, key=os.path.getmtime)
            return latest

        time.sleep(1)

    raise TimeoutError(
        f"Download do XLSX não apareceu em {timeout}s. "
        "Verifique se o relatório gerou corretamente no Connect."
    )


def mark_excel_checkbox(driver):
    """
    Marca o checkbox EXCEL de forma robusta.
    """
    labels = driver.find_elements(
        By.XPATH,
        "//label[contains(translate(., 'excel', 'EXCEL'),'EXCEL')]"
    )
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

    # Fallback
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
    Retorna caminho do XLSX baixado.
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

    # ─── CORREÇÃO: timeout na abertura de páginas ───
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)

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

        log.info("Selecionando modelo: Relatorio Analitico...")
        modelo_el = wait.until(EC.element_to_be_clickable((By.NAME, "tipoRelat")))
        Select(modelo_el).select_by_visible_text("Relatorio Analitico")

        log.info(f"Preenchendo datas: {data_ini} a {data_fim}...")
        data_ini_el = driver.find_element(By.NAME, "data_ini")
        data_fim_el = driver.find_element(By.NAME, "data_fim")
        driver.execute_script("arguments[0].value = arguments[1];", data_ini_el, data_ini)
        driver.execute_script("arguments[0].value = arguments[1];", data_fim_el, data_fim)

        log.info("Marcando opção EXCEL...")
        mark_excel_checkbox(driver)

        log.info("Clicando em BUSCAR...")
        buscar_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'BUSCAR')]")))
        buscar_btn.click()

        log.info(f"Aguardando download do XLSX (timeout: {DOWNLOAD_TIMEOUT}s)...")
        xlsx_path = wait_download(DOWNLOAD_DIR, timeout=DOWNLOAD_TIMEOUT)
        log.info(f"Download OK: {xlsx_path}")
        return xlsx_path

    except TimeoutError:
        # Screenshot para diagnóstico
        try:
            diag_path = os.path.join(DOWNLOAD_DIR, "erro_timeout.png")
            driver.save_screenshot(diag_path)
            log.error(f"Timeout! Screenshot salvo em: {diag_path}")
        except Exception:
            pass
        raise

    except Exception as e:
        # Screenshot para diagnóstico
        try:
            diag_path = os.path.join(DOWNLOAD_DIR, "erro_geral.png")
            driver.save_screenshot(diag_path)
            log.error(f"Erro inesperado! Screenshot salvo em: {diag_path}")
        except Exception:
            pass
        raise RuntimeError(f"Erro no download do relatório: {e}") from e

    finally:
        driver.quit()


# =========================
# 2) AUTH + UPLOAD ONEDRIVE
# =========================
def get_graph_access_token() -> str:
    """
    Client Credentials (app-only) para Microsoft Graph.
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
    """
    headers = {"Authorization": f"Bearer {token}"}
    parent_item_id = None

    parts = [p for p in folder_path.strip("/").split("/") if p.strip()]
    for part in parts:
        part_escaped = part.replace("'", "''")

        if parent_item_id:
            list_url = (
                f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/items/"
                f"{parent_item_id}/children?$filter=name eq '{part_escaped}'"
            )
        else:
            list_url = (
                f"https://graph.microsoft.com/v1.0/users/{quote(user_upn)}/drive/root/"
                f"children?$filter=name eq '{part_escaped}'"
            )

        resp = requests.get(list_url, headers=headers, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("value", [])
        if items:
            parent_item_id = items[0]["id"]
            continue

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

        c = requests.post(
            create_url,
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        c.raise_for_status()
        parent_item_id = c.json()["id"]


def upload_onedrive(local_file_path: str) -> str:
    """
    Faz upload para OneDrive via Microsoft Graph.
    Retorna webUrl do arquivo.
    """
    if not ONEDRIVE_USER:
        raise RuntimeError("Defina ONEDRIVE_USER (email corporativo) no .env.")

    token = get_graph_access_token()
    ensure_onedrive_folder(token, ONEDRIVE_USER, ONEDRIVE_FOLDER)

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