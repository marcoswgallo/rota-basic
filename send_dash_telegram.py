"""
send_dash_telegram.py
─────────────────────
Captura o dashboard do Power BI via Selenium,
corta automaticamente o espaço em branco com Pillow
e envia para o Telegram.
"""

import os
import time
import requests
import numpy as np
from PIL import Image
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()

# ===== ENV =====
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")
DASH_URL     = os.getenv("DASH_URL")
OUT_PNG      = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")
CAPTION      = os.getenv("DASH_CAPTION", "📊 Rota Inicial - Atualizado")

# ===== CONFIG =====
WINDOW_W          = int(os.getenv("DASH_W", "1920"))
WINDOW_H          = int(os.getenv("DASH_H", "1080"))
SCALE             = float(os.getenv("DASH_SCALE", "2"))
WAIT_SECONDS      = int(os.getenv("DASH_WAIT", "35"))
PBI_ZOOM          = float(os.getenv("PBI_ZOOM", "1.0"))
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "90"))

# Margem extra mantida após o corte (px)
CROP_PADDING = int(os.getenv("CROP_PADDING", "20"))
# Tolerância de cor para considerar "fundo branco/cinza claro" (0-255)
CROP_THRESHOLD = int(os.getenv("CROP_THRESHOLD", "240"))

if not BOT_TOKEN:
    raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")
if not CHAT_ID:
    raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")
if not DASH_URL:
    raise RuntimeError("Defina DASH_URL no .env")

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


# ════════════════════════════════════
# SELENIUM
# ════════════════════════════════════

def build_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={WINDOW_W},{WINDOW_H}")
    opts.add_argument(f"--force-device-scale-factor={SCALE}")
    opts.add_argument("--high-dpi-support=1")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def take_screenshot(url: str, raw_png: str):
    driver = build_driver()
    try:
        print(f"Abrindo dashboard (timeout: {PAGE_LOAD_TIMEOUT}s)...")
        driver.get(url)

        print(f"Aguardando {WAIT_SECONDS}s para renderizar...")
        time.sleep(WAIT_SECONDS)

        if PBI_ZOOM != 1.0:
            driver.execute_script(f"document.body.style.zoom = '{PBI_ZOOM}'")
            time.sleep(2)

        # Ajusta altura para capturar todo o conteúdo
        try:
            total_h = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);"
            )
            if isinstance(total_h, (int, float)) and total_h > WINDOW_H:
                driver.set_window_size(WINDOW_W, int(min(total_h, 4500)))
                time.sleep(1)
        except Exception:
            pass

        # Tenta capturar container principal do PBI
        candidates = [
            (By.CSS_SELECTOR, "div.reportContainer"),
            (By.CSS_SELECTOR, "div.canvasContainer"),
            (By.CSS_SELECTOR, "div[role='main']"),
            (By.TAG_NAME, "body"),
        ]
        target = None
        for by, sel in candidates:
            els = driver.find_elements(by, sel)
            if els:
                target = els[0]
                break

        if target:
            target.screenshot(raw_png)
        else:
            driver.save_screenshot(raw_png)

        print(f"Screenshot salvo: {raw_png}")

    except Exception as e:
        try:
            driver.save_screenshot(raw_png.replace(".png", "_erro.png"))
        except Exception:
            pass
        raise RuntimeError(f"Erro no screenshot: {e}") from e
    finally:
        driver.quit()


# ════════════════════════════════════
# CROP AUTOMÁTICO COM PILLOW
# ════════════════════════════════════

def autocrop(input_png: str, output_png: str):
    """
    Remove bordas com fundo claro (branco/cinza) ao redor do conteúdo.
    Mantém uma margem de CROP_PADDING px para não cortar rente.
    """
    img = Image.open(input_png).convert("RGB")
    arr = np.array(img)

    # Máscara: pixel é "fundo" se todos os canais >= threshold
    bg_mask = np.all(arr >= CROP_THRESHOLD, axis=2)

    # Linhas e colunas que têm pelo menos 1 pixel de conteúdo
    rows_with_content = np.where(~bg_mask.all(axis=1))[0]
    cols_with_content = np.where(~bg_mask.all(axis=0))[0]

    if len(rows_with_content) == 0 or len(cols_with_content) == 0:
        print("⚠️ Autocrop não encontrou conteúdo — usando imagem original.")
        img.save(output_png)
        return

    top    = max(0,          rows_with_content[0]  - CROP_PADDING)
    bottom = min(img.height, rows_with_content[-1] + CROP_PADDING + 1)
    left   = max(0,          cols_with_content[0]  - CROP_PADDING)
    right  = min(img.width,  cols_with_content[-1] + CROP_PADDING + 1)

    cropped = img.crop((left, top, right, bottom))
    cropped.save(output_png)

    orig_w, orig_h   = img.size
    crop_w = right - left
    crop_h = bottom - top
    print(f"✅ Autocrop: {orig_w}x{orig_h} → {crop_w}x{crop_h} px")


# ════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════

def send_telegram_photo(file_path: str, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(file_path, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": f},
            timeout=120,
        )
    if not r.ok:
        raise RuntimeError(f"⛔ Erro Telegram: {r.status_code} - {r.text}")
    print("✅ Imagem enviada para o Telegram.")


# ════════════════════════════════════
# MAIN
# ════════════════════════════════════

def main():
    raw_png    = OUT_PNG.replace(".png", "_raw.png")
    final_png  = OUT_PNG

    # 1) Screenshot
    take_screenshot(DASH_URL, raw_png)

    # 2) Corte automático
    autocrop(raw_png, final_png)

    # 3) Limpa o raw
    try:
        os.remove(raw_png)
    except Exception:
        pass

    # 4) Envia
    send_telegram_photo(final_png, CAPTION)


if __name__ == "__main__":
    main()