import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

GROUP_ID = os.getenv("PBI_GROUP_ID")
DATASET_ID = os.getenv("PBI_DATASET_ID")

PBI_AUTH_MODE = os.getenv("PBI_AUTH_MODE", "client_credentials").strip().lower()
PBI_REFRESH_TOKEN = os.getenv("PBI_REFRESH_TOKEN")

PBI_WAIT = os.getenv("PBI_WAIT", "1") == "1"
PBI_POLL_SECONDS = int(os.getenv("PBI_POLL_SECONDS", "10"))
PBI_TIMEOUT_SECONDS = int(os.getenv("PBI_TIMEOUT_SECONDS", "900"))

# Status finais conhecidos do Power BI
STATUS_FINAL_OK = {"Completed"}
STATUS_FINAL_ERRO = {"Failed", "Cancelled", "Disabled"}
# Se chegar nestes status, não adianta esperar mais
STATUS_FINAL_TODOS = STATUS_FINAL_OK | STATUS_FINAL_ERRO


# -------------------------
# Helpers
# -------------------------

def _require_env(name: str, value):
    if not value:
        raise RuntimeError(f"Defina {name} no .env")


# -------------------------
# TOKEN
# -------------------------

def get_access_token_client_credentials() -> str:
    _require_env("TENANT_ID", TENANT_ID)
    _require_env("CLIENT_ID", CLIENT_ID)
    _require_env("CLIENT_SECRET", CLIENT_SECRET)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }

    r = requests.post(url, data=data, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(
            f"⛔ Token endpoint retornou erro:\nSTATUS: {r.status_code}\nBODY: {r.text}"
        )
    return r.json()["access_token"]


def get_access_token_refresh_token() -> str:
    _require_env("TENANT_ID", TENANT_ID)
    _require_env("CLIENT_ID", CLIENT_ID)
    _require_env("CLIENT_SECRET", CLIENT_SECRET)
    _require_env("PBI_REFRESH_TOKEN", PBI_REFRESH_TOKEN)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": PBI_REFRESH_TOKEN,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }

    r = requests.post(url, data=data, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(
            f"⛔ Token endpoint retornou erro:\nSTATUS: {r.status_code}\nBODY: {r.text}"
        )
    return r.json()["access_token"]


def get_access_token() -> str:
    if PBI_AUTH_MODE == "client_credentials":
        return get_access_token_client_credentials()
    if PBI_AUTH_MODE == "refresh_token":
        return get_access_token_refresh_token()
    raise RuntimeError(f"PBI_AUTH_MODE inválido: '{PBI_AUTH_MODE}'. Use 'client_credentials' ou 'refresh_token'.")


# -------------------------
# TRIGGER REFRESH
# -------------------------

def trigger_refresh(token: str) -> None:
    _require_env("PBI_GROUP_ID", GROUP_ID)
    _require_env("PBI_DATASET_ID", DATASET_ID)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        r = requests.post(url, headers=headers, timeout=60)

        if r.status_code in (200, 202):
            print("✅ Power BI: refresh disparado.")
            return

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 120
            print(f"⚠️ Rate limit (429). Aguardando {wait_seconds}s... ({attempt}/{max_attempts})")
            time.sleep(wait_seconds)
            continue

        raise RuntimeError(
            f"⛔ Falha ao disparar refresh:\nSTATUS: {r.status_code}\nBODY: {r.text}"
        )

    raise RuntimeError("⛔ Muitas tentativas (429). Tente novamente mais tarde.")


# -------------------------
# WAIT STATUS
# -------------------------

def wait_for_refresh(token: str) -> None:
    _require_env("PBI_GROUP_ID", GROUP_ID)
    _require_env("PBI_DATASET_ID", DATASET_ID)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes?$top=1"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"⏳ Power BI: aguardando refresh concluir (timeout: {PBI_TIMEOUT_SECONDS}s)...")

    t0 = time.time()
    consecutive_unknown = 0  # conta status desconhecidos consecutivos

    while True:
        elapsed = time.time() - t0

        if elapsed > PBI_TIMEOUT_SECONDS:
            raise RuntimeError(
                f"⛔ Timeout após {PBI_TIMEOUT_SECONDS}s esperando refresh do Power BI."
            )

        r = requests.get(url, headers=headers, timeout=60)

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 30
            print(f"⚠️ Rate limit (429) ao consultar status. Aguardando {wait_seconds}s...")
            time.sleep(wait_seconds)
            continue

        if r.status_code != 200:
            raise RuntimeError(
                f"⛔ Falha ao consultar refresh:\nSTATUS: {r.status_code}\nBODY: {r.text}"
            )

        items = r.json().get("value", [])

        if not items:
            print("⚠️ Sem histórico ainda. Aguardando...")
            time.sleep(PBI_POLL_SECONDS)
            continue

        status = items[0].get("status", "Unknown")
        print(f"Status: {status} ({int(elapsed)}s decorridos)")

        # ─── CORREÇÃO: status de sucesso ───
        if status == "Completed":
            print("✅ Power BI: refresh concluído com sucesso.")
            return

        # ─── CORREÇÃO: status de erro definitivo ───
        if status in STATUS_FINAL_ERRO:
            error_info = items[0].get("serviceExceptionJson", "")
            raise RuntimeError(
                f"⛔ Power BI: refresh terminou com status '{status}'.\n{error_info}"
            )

        # ─── CORREÇÃO: status desconhecido — não trava para sempre ───
        if status not in ("Unknown", "InProgress"):
            consecutive_unknown += 1
            print(f"⚠️ Status inesperado '{status}' ({consecutive_unknown}x consecutivo).")
            if consecutive_unknown >= 5:
                raise RuntimeError(
                    f"⛔ Status inesperado '{status}' por 5 ciclos consecutivos. Abortando."
                )
        else:
            consecutive_unknown = 0  # reset ao ver status conhecido

        time.sleep(PBI_POLL_SECONDS)


# -------------------------
# MAIN
# -------------------------

def main():
    token = get_access_token()
    trigger_refresh(token)

    if PBI_WAIT:
        wait_for_refresh(token)


if __name__ == "__main__":
    main()