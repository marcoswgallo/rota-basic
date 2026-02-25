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

# auth mode: "client_credentials" (app permission) ou "refresh_token" (delegated)
PBI_AUTH_MODE = os.getenv("PBI_AUTH_MODE", "refresh_token").strip().lower()

# usado somente no modo refresh_token
PBI_REFRESH_TOKEN = os.getenv("PBI_REFRESH_TOKEN")

# controle
PBI_WAIT = os.getenv("PBI_WAIT", "1") == "1"   # espera concluir?
PBI_POLL_SECONDS = int(os.getenv("PBI_POLL_SECONDS", "10"))
PBI_TIMEOUT_SECONDS = int(os.getenv("PBI_TIMEOUT_SECONDS", "900"))  # 15 min


def _require_env(name: str, value: str | None):
    if not value:
        raise RuntimeError(f"Defina {name} no .env")


def get_access_token_client_credentials() -> str:
    _require_env("TENANT_ID", TENANT_ID)
    _require_env("CLIENT_ID", CLIENT_ID)
    _require_env("CLIENT_SECRET", CLIENT_SECRET)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }

    r = requests.post(url, data=data, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def get_access_token_refresh_token() -> str:
    _require_env("TENANT_ID", TENANT_ID)
    _require_env("CLIENT_ID", CLIENT_ID)
    _require_env("CLIENT_SECRET", CLIENT_SECRET)
    _require_env("PBI_REFRESH_TOKEN", PBI_REFRESH_TOKEN)

    # OBS: isso aqui pressupõe que o refresh_token foi gerado com scopes do Power BI + offline_access
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": PBI_REFRESH_TOKEN,
        "scope": "https://analysis.windows.net/powerbi/api/.default offline_access",
    }

    r = requests.post(url, data=data, timeout=60)
    r.raise_for_status()
    j = r.json()

    # se vier refresh_token novo, você pode atualizar no .env depois (opcional)
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
        status = r.json()["value"][0]["status"]

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