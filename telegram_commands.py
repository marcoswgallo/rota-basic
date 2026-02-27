import os
import time
import threading
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

ENABLE_PBI_REFRESH = os.getenv("ENABLE_PBI_REFRESH", "1") == "1"

# ─────────────────────────────────────────────
# Controle de tarefa em andamento (evita rodar
# dois comandos pesados ao mesmo tempo)
# ─────────────────────────────────────────────
_running_lock = threading.Lock()
_running_task: str | None = None   # nome da tarefa em andamento


def _set_running(name: str | None):
    global _running_task
    with _running_lock:
        _running_task = name


def _get_running() -> str | None:
    with _running_lock:
        return _running_task


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

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
    try:
        requests.post(
            f"{API}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=30,
        )
    except Exception as e:
        log_line(f"Erro ao enviar mensagem Telegram: {e}")


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
        return 124, f"⏰ Timeout: {py_file} excedeu {timeout}s"
    except Exception as e:
        return 1, f"Erro ao executar {py_file}: {e}"


# ─────────────────────────────────────────────
# Comandos
# ─────────────────────────────────────────────

def cmd_status():
    running = _get_running()
    status_extra = f"\n\n🔄 Tarefa em andamento: {running}" if running else "\n\n💤 Nenhuma tarefa rodando."

    cron_log = os.path.join(BASE_DIR, "cron.log")
    if os.path.exists(cron_log):
        text = "📌 Últimas linhas do log:\n\n" + tail_log(cron_log, 35)
    else:
        text = "📌 Últimas linhas do bot log:\n\n" + tail_log(LOG_FILE, 35)

    tg_send_message(text + status_extra)


def cmd_ping():
    running = _get_running()
    if running:
        tg_send_message(f"🟡 Bot está vivo — processando: {running}")
    else:
        tg_send_message("🟢 Bot respondendo normalmente. Nenhuma tarefa em andamento.")


def _run_dash():
    _set_running("/dash")
    try:
        code, out = run_script("send_dash_telegram.py", timeout=900)
        if code == 0:
            tg_send_message("✅ Dash enviado com sucesso!")
        else:
            tg_send_message(f"⛔ Erro ao enviar dash.\n\n{out[-1000:]}")
    finally:
        _set_running(None)


def _run_dados():
    _set_running("/dados")
    try:
        code, out = run_script("connect_download.py", timeout=1800)
        if code == 0:
            tg_send_message("✅ Dados atualizados (Connect + OneDrive OK).")
        else:
            tg_send_message(f"⛔ Erro ao atualizar dados.\n\n{out[-1000:]}")
    finally:
        _set_running(None)


def _run_powerbi():
    _set_running("/powerbi")
    try:
        if not ENABLE_PBI_REFRESH:
            tg_send_message("ℹ️ Refresh do Power BI está desabilitado (ENABLE_PBI_REFRESH=0).")
            return
        code, out = run_script("powerbi_refresh.py", timeout=1200)
        if code == 0:
            tg_send_message("✅ Power BI refresh concluído.")
        else:
            tg_send_message(f"⛔ Erro no refresh do Power BI.\n\n{out[-1000:]}")
    finally:
        _set_running(None)


def _run_rodar():
    """
    Processo completo:
    1) Connect download + upload OneDrive
    2) Power BI refresh (opcional)
    3) Screenshot e envio no Telegram
    """
    _set_running("/rodar")
    try:
        tg_send_message("🚀 [1/3] Baixando dados do Connect e subindo para OneDrive...")
        code, out = run_script("connect_download.py", timeout=1800)
        if code != 0:
            tg_send_message(f"⛔ Falhou no Connect/OneDrive.\n\n{out[-1000:]}")
            return

        if ENABLE_PBI_REFRESH:
            tg_send_message("🔄 [2/3] Disparando refresh no Power BI...")
            code, out = run_script("powerbi_refresh.py", timeout=1200)
            if code != 0:
                tg_send_message(f"⚠️ Dados OK, mas Power BI falhou. Seguindo para o dash...\n\n{out[-500:]}")
        else:
            tg_send_message("⏭️ [2/3] Power BI refresh desabilitado. Pulando...")

        tg_send_message("📸 [3/3] Capturando e enviando dashboard...")
        code, out = run_script("send_dash_telegram.py", timeout=900)
        if code == 0:
            tg_send_message("✅ Rotina concluída! 📊 Dashboard atualizado enviado.")
        else:
            tg_send_message(f"⛔ Falhou ao gerar/enviar o dash.\n\n{out[-1000:]}")
    finally:
        _set_running(None)


# ─────────────────────────────────────────────
# Dispatcher de comandos
# ─────────────────────────────────────────────

# Comandos pesados que rodam em thread separada
HEAVY_COMMANDS = {
    "/rodar": _run_rodar,
    "/dados": _run_dados,
    "/dash": _run_dash,
    "/powerbi": _run_powerbi,
}


def handle_command(text: str):
    t = text.strip().lower()

    # ── Comandos leves (respondem na hora) ──
    if t.startswith("/start"):
        tg_send_message(
            "🤖 *Bot Rota Basic ONLINE*\n\n"
            "Comandos disponíveis:\n"
            "/rodar — rotina completa\n"
            "/dados — só baixa Connect + OneDrive\n"
            "/dash — só captura e envia dashboard\n"
            "/powerbi — só refresh do Power BI\n"
            "/status — últimas linhas do log\n"
            "/ping — verifica se o bot está vivo"
        )
        return

    if t.startswith("/status"):
        cmd_status()
        return

    if t.startswith("/ping"):
        cmd_ping()
        return

    # ── Comandos pesados (rodam em thread separada) ──
    for cmd, func in HEAVY_COMMANDS.items():
        if t.startswith(cmd):
            running = _get_running()
            if running:
                tg_send_message(
                    f"⚠️ Já existe uma tarefa em andamento: {running}\n"
                    f"Use /ping para checar o status ou aguarde terminar."
                )
                return

            tg_send_message(f"⏳ Comando {cmd} recebido. Iniciando...")
            thread = threading.Thread(target=func, daemon=True, name=cmd)
            thread.start()
            return

    tg_send_message("Comando não reconhecido. Use /start para ver a lista.")


# ─────────────────────────────────────────────
# Loop principal (polling)
# ─────────────────────────────────────────────

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