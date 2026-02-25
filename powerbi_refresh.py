#!/usr/bin/env python3
# powerbi_refresh.py
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

# auth mode: "client_credentials" (Application permissions) ou "refresh_token" (Delegated)
PBI_AUTH_MODE = os.getenv("PBI_AUTH_MODE", "refresh_token").strip().lower()

# usado somente no modo refresh_token
PBI_REFRESH_TOKEN = os.getenv("PBI_REFRESH_TOKEN")

# controle
PBI_WAIT = os.getenv("PBI_WAIT", "1") == "1"  # espera concluir?
PBI_POLL_SECONDS = int(os.getenv("PBI_POLL_SECONDS", "10"))
PBI_TIMEOUT_SECONDS = int(os.getenv("PBI_TIMEOUT_SECONDS", "900"))  # 15 min


def _require_env(name: str, value: str | None):
    if not value:
        raise RuntimeError(f"Defina {name} no .env")


def get_access_token_client_credentials() -> str:
    """
    Application permissions (service principal).
    Requer:
      - Permissões de aplicativo no Entra (Power BI Service) + admin consent
      - Power BI Admin: permitir service principals usar APIs
      - Service principal com acesso ao workspace/dataset
    """
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
    r.raise_for_status()
    return r.json()["access_token"]


def get_access_token_refresh_token() -> str:
    """
    Delegated permissions (refresh_token).
    Observação: para evitar AADSTS9002313/invalid_grant, aqui NÃO enviamos "scope".
    """
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
    }

    r = requests.post(url, data=data, timeout=60)
    r.raise_for_status()
    j = r.json()

    # Se vier um refresh_token novo, você pode salvar no .env depois (opcional):
    # new_rt = j.get("refresh_token")

    return j["access_token"]


def get_access_token() -> str:
    if PBI_AUTH_MODE == "client_credentials":
        return get_access_token_client_credentials()
    if PBI_AUTH_MODE == "refresh_token":
        return get_access_token_refresh_token()
    raise RuntimeError("PBI_AUTH_MODE inválido. Use client_credentials ou refresh_token.")


def trigger_refresh(token: str) -> None:
    _require_env("PBI_GROUP_ID", GROUP_ID)
    _require_env("PBI_DATASET_ID", DATASET_ID)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    r = requests.post(url, headers=headers, timeout=60)
    r.raise_for_status()
    print("✅ Power BI: refresh disparado.")


def wait_for_refresh(token: str) -> None:
    _require_env("PBI_GROUP_ID", GROUP_ID)
    _require_env("PBI_DATASET_ID", DATASET_ID)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes?$top=1"
    headers = {"Authorization": f"Bearer {token}"}

    print("⏳ Power BI: aguardando concluir refresh...")

    t0 = time.time()
    while True:
        if time.time() - t0 > PBI_TIMEOUT_SECONDS:
            raise RuntimeError("⛔ Timeout esperando refresh do Power BI.")

        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        value = r.json().get("value", [])
        if not value:
            print("Status: (sem histórico ainda) aguardando...")
            time.sleep(PBI_POLL_SECONDS)
            continue

        status = value[0].get("status")
        print("Status:", status)

        if status == "Completed":
            print("✅ Power BI: refresh concluído.")
            return
        if status == "Failed":
            raise RuntimeError("⛔ Power BI: refresh falhou.")

        time.sleep(PBI_POLL_SECONDS)


def main():
    token = get_access_token()
    trigger_refresh(token)
    if PBI_WAIT:
        wait_for_refresh(token)


if __name__ == "__main__":
    main()