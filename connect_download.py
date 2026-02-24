from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time, os, shutil
from datetime import datetime

# ─── CONFIGURAÇÕES ───────────────────────────────────────────
URL_LOGIN     = "https://basic.controlservices.com.br/login"
URL_RELATORIO = "https://basic.controlservices.com.br/financeiro/relatorio"
EMAIL         = "gallo@redeclaro.com.br"
SENHA         = "Basic@159753"
DOWNLOAD_DIR  = "/opt/rota_basic/downloads"
DESTINO_FINAL = "/opt/rota_basic/rota_atual.xlsx"
# ─────────────────────────────────────────────────────────────

def rodar():
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando...")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    for f in os.listdir(DOWNLOAD_DIR):
        os.remove(os.path.join(DOWNLOAD_DIR, f))

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
    wait = WebDriverWait(driver, 30)

    try:
        # LOGIN
        print("  → Login...")
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SENHA)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
        time.sleep(4)
        print(f"  → Logado: {driver.current_url}")

        # NAVEGAR PARA RELATÓRIOS
        print("  → Abrindo relatórios...")
        driver.get(URL_RELATORIO)
        time.sleep(3)

        # MODELO = Relatório Analítico (value=2)
        wait.until(EC.presence_of_element_located((By.NAME, "tipoRelat")))
        Select(driver.find_element(By.NAME, "tipoRelat")).select_by_value("2")
        print("  → Modelo selecionado: Relatório Analítico")

        # DATA = HOJE
        hoje = datetime.now().strftime("%Y-%m-%d")
        for campo in driver.find_elements(By.CSS_SELECTOR, "input[type='date']"):
            driver.execute_script(f"arguments[0].value = '{hoje}';", campo)
        print(f"  → Data definida: {hoje}")

        # CLICAR EM BUSCAR
        print("  → Clicando Buscar...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary"))).click()
        print("  → Buscar clicado! Aguardando download...")

        # AGUARDAR DOWNLOAD (até 2 minutos)
        for i in range(60):
            arqs = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith((".xlsx", ".xls"))]
            if arqs:
                time.sleep(2)
                shutil.copy2(os.path.join(DOWNLOAD_DIR, arqs[0]), DESTINO_FINAL)
                print(f"  ✅ Download concluído! Salvo em: {DESTINO_FINAL}")
                break
            time.sleep(2)
        else:
            print("  ❌ Timeout: arquivo não baixado em 2 minutos.")

    except Exception as e:
        print(f"  ❌ Erro: {e}")
        print(f"  → URL atual: {driver.current_url}")

    finally:
        driver.quit()
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Finalizado.")

if __name__ == "__main__":
    rodar()