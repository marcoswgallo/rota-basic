"""
send_dash_telegram.py
─────────────────────
Exporta uma página do relatório Power BI como PNG via API oficial
e envia para o Telegram — sem Selenium, sem Chrome.

Variáveis obrigatórias no .env:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  PBI_GROUP_ID       (Workspace ID)
  PBI_REPORT_ID      (Report ID)

  + autenticação (igual ao powerbi_refresh.py):
  TENANT_ID, CLIENT_ID, CLIENT_SECRET
  PBI_AUTH_MODE      (client_credentials ou refresh_token)
  PBI_REFRESH_TOKEN  (só se PBI_AUTH_MODE=refresh_token)

Variáveis opcionais:
  PBI_REPORT_PAGE    (nome da página, ex: "ReportSection1" — deixe vazio para página ativa)
  PBI_EXPORT_TIMEOUT (segundos máx aguardando export, padrão 120)
  PBI_POLL_SECONDS   (intervalo de polling, padrão 5)
  DASH_PNG           (caminho local para salvar o PNG)
  DASH_CAPTION       (legenda no Telegram)
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ───
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# ─── Power BI ───
TENANT_ID         = os.getenv("TENANT_ID")
CLIENT_ID         = os.getenv("CLIENT_ID")
CLIENT_SECRET     = os.getenv("CLIENT_SECRET")
PBI_AUTH_MODE     = os.getenv("PBI_AUTH_MODE", "client_credentials").strip().lower()
PBI_REFRESH_TOKEN = os.getenv("PBI_REFRESH_TOKEN")

GROUP_ID          = os.getenv("PBI_GROUP_ID")
REPORT_ID         = os.getenv("PBI_REPORT_ID")
REPORT_PAGE       = os.getenv("PBI_REPORT_PAGE", "")   # vazio = página ativa

EXPORT_TIMEOUT    = int(os.getenv("PBI_EXPORT_TIMEOUT", "120"))
POLL_SECONDS      = int(os.getenv("PBI_POLL_SECONDS", "5"))

# ─── Saída ───
OUT_PNG = os.getenv("DASH_PNG", "/root/rota-basic/downloads/rota_dash.png")
CAPTION = os.getenv("DASH_CAPTION", "📊 Rota Inicial - Atualizado")

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


# ════════════════════════════════════════
# AUTH
# ════════════════════════════════════════

def _require(name: str, value):
    if not value:
        raise RuntimeError(f"Defina {name} no .env")


def get_access_token() -> str:
    _require("TENANT_ID", TENANT_ID)
    _require("CLIENT_ID", CLIENT_ID)
    _require("CLIENT_SECRET", CLIENT_SECRET)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    scope = "https://analysis.windows.net/powerbi/api/.default"

    if PBI_AUTH_MODE == "refresh_token":
        _require("PBI_REFRESH_TOKEN", PBI_REFRESH_TOKEN)
        data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": PBI_REFRESH_TOKEN,
            "scope": scope,
        }
    else:
        data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": scope,
        }

    r = requests.post(url, data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"⛔ Erro ao obter token:\n{r.status_code} - {r.text}")
    return r.json()["access_token"]


# ════════════════════════════════════════
# EXPORT PNG via API do Power BI
# ════════════════════════════════════════

def export_report_png(token: str) -> bytes:
    """
    Usa a API exportTo do Power BI para gerar um PNG do relatório.
    Faz polling até o export ficar pronto e retorna os bytes da imagem.
    """
    _require("PBI_GROUP_ID", GROUP_ID)
    _require("PBI_REPORT_ID", REPORT_ID)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    base_url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/reports/{REPORT_ID}"

    # ── Monta o body do export ──
    body = {"format": "PNG"}

    if REPORT_PAGE:
        body["powerBIReportConfiguration"] = {
            "pages": [{"pageName": REPORT_PAGE}]
        }

    # ── 1) Dispara o export ──
    print(f"Disparando export PNG do relatório {REPORT_ID}...")
    r = requests.post(f"{base_url}/ExportTo", headers=headers, json=body, timeout=60)

    if r.status_code not in (200, 202):
        raise RuntimeError(f"⛔ Falha ao iniciar export:\n{r.status_code} - {r.text}")

    export_id = r.json().get("id")
    if not export_id:
        raise RuntimeError("⛔ API não retornou export ID.")

    print(f"Export iniciado. ID: {export_id}")

    # ── 2) Polling até ficar pronto ──
    status_url = f"{base_url}/exports/{export_id}"
    t0 = time.time()

    while True:
        elapsed = time.time() - t0
        if elapsed > EXPORT_TIMEOUT:
            raise TimeoutError(f"⛔ Timeout de {EXPORT_TIMEOUT}s aguardando export.")

        time.sleep(POLL_SECONDS)

        sr = requests.get(status_url, headers=headers, timeout=30)
        if sr.status_code != 200:
            raise RuntimeError(f"⛔ Erro ao consultar status:\n{sr.status_code} - {sr.text}")

        status_data = sr.json()
        status  = status_data.get("status", "")
        percent = status_data.get("percentComplete", 0)

        print(f"Status: {status} — {percent}% ({int(elapsed)}s)")

        if status == "Succeeded":
            break
        if status == "Failed":
            raise RuntimeError(f"⛔ Export falhou:\n{status_data}")

    # ── 3) Baixa o arquivo ──
    print("Export concluído! Baixando PNG...")
    file_url = f"{base_url}/exports/{export_id}/file"
    fr = requests.get(file_url, headers=headers, timeout=60)

    if fr.status_code != 200:
        raise RuntimeError(f"⛔ Erro ao baixar arquivo:\n{fr.status_code} - {fr.text}")

    print(f"PNG baixado ({len(fr.content) / 1024:.1f} KB).")
    return fr.content


# ════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════

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


# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════

def main():
    _require("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    _require("TELEGRAM_CHAT_ID", CHAT_ID)

    token = get_access_token()
    png_bytes = export_report_png(token)

    with open(OUT_PNG, "wb") as f:
        f.write(png_bytes)
    print(f"PNG salvo em: {OUT_PNG}")

    send_telegram_photo(OUT_PNG, CAPTION)


if __name__ == "__main__":
    main()