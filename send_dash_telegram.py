import os
import time
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()

# ===== ENV =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DASH_URL = os.getenv("DASH_URL")
OUT_PNG = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")

# ===== CONFIG DE QUALIDADE =====
WINDOW_W = int(os.getenv("DASH_W", "2560"))
WINDOW_H = int(os.getenv("DASH_H", "1440"))
SCALE = float(os.getenv("DASH_SCALE", "3"))
WAIT_SECONDS = int(os.getenv("DASH_WAIT", "30"))
PBI_ZOOM = float(os.getenv("PBI_ZOOM", "1.5"))

# ===== TIMEOUTS =====
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "90"))   # segundos para abrir a URL
SCREENSHOT_TIMEOUT = int(os.getenv("SCREENSHOT_TIMEOUT", "120")) # segundos máximos no driver

if not BOT_TOKEN:
    raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")
if not CHAT_ID:
    raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")
if not DASH_URL:
    raise RuntimeError("Defina DASH_URL no .env")

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


# ===== DRIVER =====
def build_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size={WINDOW_W},{WINDOW_H}")
    chrome_options.add_argument(f"--force-device-scale-factor={SCALE}")
    chrome_options.add_argument("--high-dpi-support=1")

    driver = webdriver.Chrome(options=chrome_options)

    # ─── CORREÇÃO: timeout para carregamento de página ───
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


# ===== SCREENSHOT =====
def screenshot_powerbi_view(url: str, out_png: str):
    driver = build_driver()
    t0 = time.time()

    try:
        print(f"Abrindo URL do dashboard (timeout: {PAGE_LOAD_TIMEOUT}s)...")
        driver.get(url)

        # aguarda Power BI carregar
        print(f"Aguardando {WAIT_SECONDS}s para o Power BI renderizar...")
        time.sleep(WAIT_SECONDS)

        # força zoom na página
        driver.execute_script(f"document.body.style.zoom = '{PBI_ZOOM}'")
        time.sleep(3)

        # ajusta altura dinamicamente
        try:
            total_height = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);"
            )
            if isinstance(total_height, (int, float)):
                driver.set_window_size(WINDOW_W, int(min(total_height, 4500)))
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ Não consegui ajustar altura da janela: {e}")

        # verifica timeout total antes de tirar screenshot
        elapsed = time.time() - t0
        remaining = SCREENSHOT_TIMEOUT - elapsed
        if remaining <= 0:
            raise TimeoutError(f"Timeout total de {SCREENSHOT_TIMEOUT}s atingido antes do screenshot.")

        # tenta capturar container principal
        candidates = [
            (By.CSS_SELECTOR, "div.reportContainer"),
            (By.CSS_SELECTOR, "div.canvasContainer"),
            (By.CSS_SELECTOR, "div[role='main']"),
            (By.TAG_NAME, "body"),
        ]

        target = None
        for by, sel in candidates:
            elements = driver.find_elements(by, sel)
            if elements:
                target = elements[0]
                break

        if target:
            target.screenshot(out_png)
            print(f"✅ Screenshot do elemento salvo: {out_png}")
        else:
            driver.save_screenshot(out_png)
            print(f"✅ Screenshot da página salvo: {out_png}")

    except Exception as e:
        # Tenta salvar screenshot de diagnóstico
        try:
            diag_path = out_png.replace(".png", "_erro.png")
            driver.save_screenshot(diag_path)
            print(f"⚠️ Erro! Screenshot de diagnóstico salvo em: {diag_path}")
        except Exception:
            pass
        raise RuntimeError(f"Erro ao capturar dashboard: {e}") from e

    finally:
        driver.quit()


# ===== TELEGRAM =====
def send_telegram_photo(bot_token: str, chat_id: str, file_path: str, caption: str = ""):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    with open(file_path, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f},
            timeout=120,
        )

    if not r.ok:
        raise RuntimeError(f"Erro Telegram: {r.status_code} - {r.text}")


# ===== MAIN =====
def main():
    screenshot_powerbi_view(DASH_URL, OUT_PNG)
    send_telegram_photo(
        BOT_TOKEN,
        CHAT_ID,
        OUT_PNG,
        caption="📊 Rota Inicial - Atualizado",
    )
    print("OK: Screenshot enviado para Telegram.")


if __name__ == "__main__":
    main()