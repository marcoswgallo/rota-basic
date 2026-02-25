import os
import time
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

load_dotenv()

# ====== ENV ======
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DASH_URL = os.getenv("DASH_URL")

# Caminho do PNG no VPS (padrão ok)
OUT_PNG = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")

# Qualidade / tamanho do print
WINDOW_W = int(os.getenv("DASH_W", "1920"))          # pode mudar pra 2560
WINDOW_H = int(os.getenv("DASH_H", "1080"))          # pode mudar pra 1440
SCALE = float(os.getenv("DASH_SCALE", "2"))          # 2 = bem melhor
WAIT_SECONDS = int(os.getenv("DASH_WAIT", "15"))     # Power BI pode precisar mais

if not BOT_TOKEN:
    raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")
if not CHAT_ID:
    raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")
if not DASH_URL:
    raise RuntimeError("Defina DASH_URL no .env")

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


def screenshot_powerbi_view(url: str, out_png: str) -> None:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Qualidade alta (resolução + “DPI”)
    chrome_options.add_argument(f"--window-size={WINDOW_W},{WINDOW_H}")
    chrome_options.add_argument(f"--force-device-scale-factor={SCALE}")
    chrome_options.add_argument("--high-dpi-support=1")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)

        # Espera render do Power BI
        time.sleep(WAIT_SECONDS)

        # Força reflow/render
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        driver.save_screenshot(out_png)
    finally:
        driver.quit()


def send_telegram_document(bot_token: str, chat_id: str, file_path: str, caption: str = "") -> None:
    """
    Envia como DOCUMENTO (sem compressão do Telegram) => melhor qualidade.
    """
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