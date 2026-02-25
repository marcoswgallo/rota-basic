import os
import time
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DASH_URL = os.getenv("DASH_URL")
OUT_PNG = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")

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
    chrome_options.add_argument("--window-size=1600,900")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)

        # espera carregar
        time.sleep(12)

        # tenta "acordar" o layout e garantir render
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Se quiser pegar página inteira:
        # Ajusta altura pelo scrollHeight
        height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(1600, min(int(height), 4000))
        time.sleep(2)

        driver.save_screenshot(out_png)
    finally:
        driver.quit()

def send_telegram_photo(bot_token: str, chat_id: str, png_path: str, caption: str = "") -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(png_path, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f},
            timeout=60,
        )
    if not r.ok:
        raise RuntimeError(f"Falha ao enviar Telegram: {r.status_code} - {r.text}")

def main():
    screenshot_powerbi_view(DASH_URL, OUT_PNG)
    send_telegram_photo(
        BOT_TOKEN,
        CHAT_ID,
        OUT_PNG,
        caption="📊 Rota Inicial (atualizado)",
    )
    print(f"OK: enviado para Telegram. PNG em: {OUT_PNG}")

if __name__ == "__main__":
    main()