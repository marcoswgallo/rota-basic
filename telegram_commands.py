import os
import time
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

BASE_DIR = os.getenv("BASE_DIR", "/root/rota-basic")
VENV_PY = os.getenv("VENV_PY", f"{BASE_DIR}/venv/bin/python")

LOG_FILE = os.getenv("BOT_LOG_FILE", f"{BASE_DIR}/bot_commands.log")

POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "50"))
SLEEP_ON_ERROR = int(os.getenv("SLEEP_ON_ERROR", "3"))

# Liga/desliga refresh do Power BI durante /rodar
ENABLE_PBI_REFRESH = os.getenv("ENABLE_PBI_REFRESH", "1") == "1"


def log_line(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def tg_send_message(text: str):
    requests.post(
        f"{API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=60
    )


def tail_log(path: str, lines: int = 30) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.readlines()
        return "".join(data[-lines:])
    except Exception as e:
        return f"(Não consegui ler log: {e})"


def run_script(py_file: str, timeout: int = 1800) -> tuple[int, str]:
    """
    Roda um script python usando o interpretador do venv.
    Retorna (exit_code, output).
    """
    cmd = [VENV_PY, os.path.join(BASE_DIR, py_file)]
    log_line(f"Executando: {' '.join(cmd)}")

    try:
        p = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timeout: {py_file} excedeu {timeout}s"
    except Exception as e:
        return 1, f"Erro ao executar {py_file}: {e}"


def cmd_status():
    # mostra últimas linhas do cron.log se existir, senão do bot log
    cron_log = os.path.join(BASE_DIR, "cron.log")
    if os.path.exists(cron_log):
        text = "📌 Últimas linhas do log:\n\n" + tail_log(cron_log, 35)
    else:
        text = "📌 Últimas linhas do bot log:\n\n" + tail_log(LOG_FILE, 35)

    tg_send_message(text)


def cmd_dash():
    code, out = run_script("send_dash_telegram.py", timeout=900)
    if code == 0:
        tg_send_message("✅ Dash enviado novamente no Telegram.")
    else:
        tg_send_message(f"⛔ Erro ao enviar dash.\n\n{out}")


def cmd_dados():
    code, out = run_script("connect_download.py", timeout=1800)
    if code == 0:
        tg_send_message("✅ Dados atualizados (Connect + OneDrive OK).")
    else:
        tg_send_message(f"⛔ Erro ao atualizar dados.\n\n{out}")


def cmd_powerbi():
    if not ENABLE_PBI_REFRESH:
        tg_send_message("ℹ️ Refresh do Power BI está desabilitado (ENABLE_PBI_REFRESH=0).")
        return

    code, out = run_script("powerbi_refresh.py", timeout=1200)
    if code == 0:
        tg_send_message("✅ Power BI refresh disparado/concluído.")
    else:
        tg_send_message(f"⛔ Erro no refresh do Power BI.\n\n{out}")


def cmd_rodar():
    """
    Processo completo:
    1) Connect download + upload OneDrive
    2) Power BI refresh (opcional)
    3) Screenshot e envio no Telegram
    """
    tg_send_message("🚀 Iniciando rotina completa (/rodar)...")

    # 1) dados
    code, out = run_script("connect_download.py", timeout=1800)
    if code != 0:
        tg_send_message(f"⛔ Falhou no Connect/OneDrive.\n\n{out}")
        return

    # 2) powerbi
    if ENABLE_PBI_REFRESH:
        code, out = run_script("powerbi_refresh.py", timeout=1200)
        if code != 0:
            tg_send_message(f"⚠️ Dados OK, mas falhou Power BI refresh.\nVou tentar enviar o dash mesmo.\n\n{out}")

    # 3) dash
    code, out = run_script("send_dash_telegram.py", timeout=900)
    if code == 0:
        tg_send_message("✅ Rotina concluída! 📊 Rota Atualizada enviada.")
    else:
        tg_send_message(f"⛔ Falhou ao gerar/enviar o dash.\n\n{out}")


def handle_command(text: str):
    t = text.strip().lower()

    if t.startswith("/start"):
        tg_send_message("🤖 Bot Rota Basic ONLINE\n\nComandos:\n/status\n/rodar\n/dados\n/dash\n/powerbi")
        return

    if t.startswith("/status"):
        cmd_status()
        return

    if t.startswith("/rodar"):
        cmd_rodar()
        return

    if t.startswith("/dados"):
        cmd_dados()
        return

    if t.startswith("/dash"):
        cmd_dash()
        return

    if t.startswith("/powerbi"):
        cmd_powerbi()
        return

    tg_send_message("Comando não reconhecido. Use /start para ver a lista.")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no .env")
    if not CHAT_ID:
        raise RuntimeError("Defina TELEGRAM_CHAT_ID no .env")

    log_line("Bot iniciado (polling getUpdates).")
    offset = None

    while True:
        try:
            r = requests.get(
                f"{API}/getUpdates",
                params={"timeout": POLL_TIMEOUT, "offset": offset},
                timeout=POLL_TIMEOUT + 10,
            )
            r.raise_for_status()
            data = r.json()

            if not data.get("ok"):
                time.sleep(SLEEP_ON_ERROR)
                continue

            for upd in data.get("result", []):
                offset = upd["update_id"] + 1

                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue

                chat = msg.get("chat", {})
                chat_id = str(chat.get("id", ""))

                # Segurança: só responde no chat configurado
                if chat_id != str(CHAT_ID):
                    continue

                text = msg.get("text", "")
                if text.startswith("/"):
                    log_line(f"CMD recebido: {text}")
                    handle_command(text)

        except Exception as e:
            log_line(f"ERRO polling: {e}")
            time.sleep(SLEEP_ON_ERROR)


if __name__ == "__main__":
    main()