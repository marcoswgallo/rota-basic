import os
import time
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DASH_URL = os.getenv("DASH_URL")
OUT_PNG = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")

# qualidade
WINDOW_W = int(os.getenv("DASH_W", "2560"))
WINDOW_H = int(os.getenv("DASH_H", "1440"))
SCALE = float(os.getenv("DASH_SCALE", "2.5"))     # sobe pra 3 se quiser
WAIT_SECONDS = int(os.getenv("DASH_WAIT", "20"))

# zoom do Power BI dentro do iframe (1.0=100%, 1.25=125%, 1.5=150%)
PBI_ZOOM = float(os.getenv("PBI_ZOOM", "1.25"))

if not BOT_TOKEN:
    raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")
if not CHAT_ID:
    raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")
if not DASH_URL:
    raise RuntimeError("Defina DASH_URL no .env")

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


def build_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    chrome_options.add_argument(f"--window-size={WINDOW_W},{WINDOW_H}")
    chrome_options.add_argument(f"--force-device-scale-factor={SCALE}")
    chrome_options.add_argument("--high-dpi-support=1")
    return webdriver.Chrome(options=chrome_options)


def screenshot_powerbi_view(url: str, out_png: str) -> None:
    driver = build_driver()
    wait = WebDriverWait(driver, 60)

    try:
        driver.get(url)

        # aguarda carregar a página base
        time.sleep(WAIT_SECONDS)

        # tenta achar iframe do Power BI e entrar nele
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)

        # força zoom dentro do iframe (isso costuma corrigir o 78%)
        # (quando o browser está em 100% mas o report renderiza menor)
        driver.execute_script(f"document.body.style.zoom = '{PBI_ZOOM}';")
        time.sleep(3)

        # tenta encontrar a área principal do report e tirar screenshot só dela
        # (seletores variam; esses 2 cobrem a maioria dos embeds)
        candidates = [
            (By.CSS_SELECTOR, "visual-container, .visualContainer"),
            (By.CSS_SELECTOR, ".report, .reportContainer, .canvasContainer, .pv-visualContainer"),
            (By.CSS_SELECTOR, "body"),
        ]

        target = None
        for by, sel in candidates:
            els = driver.find_elements(by, sel)
            if els:
                target = els[0]
                break

        if target:
            target.screenshot(out_png)
        else:
            driver.save_screenshot(out_png)

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def send_telegram_document(bot_token: str, chat_id: str, file_path: str, caption: str = "") -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(file_path, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": f},
            timeout=120,
        )
    if not r.ok:
        raise RuntimeError(f"Falha ao enviar Telegram: {r.status_code} - {r.text}")


def main():
    screenshot_powerbi_view(DASH_URL, OUT_PNG)
    send_telegram_document(
        BOT_TOKEN,
        CHAT_ID,
        OUT_PNG,
        caption="📊 Rota Inicial (atualizado)",
    )
    print(f"OK: enviado para Telegram. PNG em: {OUT_PNG}")


if __name__ == "__main__":
    main()