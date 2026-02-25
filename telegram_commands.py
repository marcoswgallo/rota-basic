import os
import time
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "cron.log")

RUN_ALL = os.path.join(BASE_DIR, "run_all.sh")
RUN_CONNECT = os.path.join(BASE_DIR, "connect_download.py")
RUN_DASH = os.path.join(BASE_DIR, "send_dash_telegram.py")
VENV_PYTHON = os.path.join(BASE_DIR, "venv/bin/python")

if not BOT_TOKEN:
    raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")

if not CHAT_ID:
    raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ===============================
# Funções Telegram
# ===============================

def send_message(text: str):
    requests.post(
        f"{API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=30,
    )


def get_updates(offset=None):
    params = {"timeout": 50}
    if offset:
        params["offset"] = offset

    r = requests.get(f"{API}/getUpdates", params=params, timeout=60)
    return r.json()


# ===============================
# Utilidades
# ===============================

def tail_log(lines=30):
    if not os.path.exists(LOG_FILE):
        return "Sem log ainda."

    with open(LOG_FILE, "r") as f:
        content = f.readlines()

    return "".join(content[-lines:])[-3500:]


def run_command(command):
    process = subprocess.Popen(
        command,
        shell=True,
        cwd=BASE_DIR,
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process.wait()


def is_authorized(chat_id):
    return str(chat_id) == str(CHAT_ID)


# ===============================
# Loop principal
# ===============================

def main():
    print("Bot iniciado...")
    send_message("🤖 Bot Rota Basic ONLINE\n\nComandos disponíveis:\n/status\n/rodar\n/dados\n/dash")

    offset = None

    while True:
        try:
            data = get_updates(offset)

            if not data.get("ok"):
                time.sleep(3)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "").strip()

                if not is_authorized(chat_id):
                    continue

                # ===========================
                # COMANDOS
                # ===========================

                if text == "/status":
                    send_message("📌 Últimas linhas do log:\n\n" + tail_log(35))

                elif text == "/rodar":
                    send_message("🚀 Executando fluxo completo...")
                    code = run_command(RUN_ALL)
                    send_message(f"✅ Finalizado. Código: {code}\n\n" + tail_log(25))

                elif text == "/dados":
                    send_message("⬇️ Atualizando apenas dados (Connect)...")
                    code = run_command(f"{VENV_PYTHON} {RUN_CONNECT}")
                    send_message(f"✅ Finalizado. Código: {code}\n\n" + tail_log(25))

                elif text == "/dash":
                    send_message("📸 Gerando apenas print do dashboard...")
                    code = run_command(f"{VENV_PYTHON} {RUN_DASH}")
                    send_message(f"✅ Finalizado. Código: {code}\n\n" + tail_log(20))

        except Exception as e:
            try:
                send_message(f"⚠️ Erro no bot: {e}")
            except:
                pass

            time.sleep(5)


if __name__ == "__main__":
    main()