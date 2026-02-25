import os
import time
import requests
from dotenv import load_dotenv

# Carrega .env (evita bug em alguns contextos)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

GROUP_ID = os.getenv("PBI_GROUP_ID")
DATASET_ID = os.getenv("PBI_DATASET_ID")

# auth mode: "refresh_token" (delegated) ou "client_credentials" (app permission)
PBI_AUTH_MODE = (os.getenv("PBI_AUTH_MODE", "refresh_token") or "").strip().lower()

PBI_REFRESH_TOKEN = os.getenv("PBI_REFRESH_TOKEN")

PBI_WAIT = (os.getenv("PBI_WAIT", "1") == "1")
PBI_POLL_SECONDS = int(os.getenv("PBI_POLL_SECONDS", "10"))
PBI_TIMEOUT_SECONDS = int(os.getenv("PBI_TIMEOUT_SECONDS", "900"))  # 15 min


def _require_env(name: str, value: str | None):
    if not value:
        raise RuntimeError(f"Defina {name} no .env")


def get_access_token_refresh_token_v1() -> str:
    """
    Troca refresh_token por access_token usando endpoint v1 + resource.
    Isso costuma evitar os 400/invalid_grant do v2 quando scope fica chato.
    """
    _require_env("TENANT_ID", TENANT_ID)
    _require_env("CLIENT_ID", CLIENT_ID)
    _require_env("CLIENT_SECRET", CLIENT_SECRET)
    _require_env("PBI_REFRESH_TOKEN", PBI_REFRESH_TOKEN)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": PBI_REFRESH_TOKEN,
        "resource": "https://analysis.windows.net/powerbi/api",
    }

    r = requests.post(url, data=data, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"⛔ Token endpoint retornou erro:\nSTATUS: {r.status_code}\nBODY: {r.text}")
    return r.json()["access_token"]


def get_access_token_client_credentials_v2() -> str:
    """
    Client Credentials (APLICATIVO) — só funciona se você tiver
    Application Permission no Power BI (não é o seu caso agora).
    """
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
    if r.status_code != 200:
        raise RuntimeError(f"⛔ Token endpoint retornou erro:\nSTATUS: {r.status_code}\nBODY: {r.text}")
    return r.json()["access_token"]


def get_access_token() -> str:
    if PBI_AUTH_MODE == "client_credentials":
        return get_access_token_client_credentials_v2()
    if PBI_AUTH_MODE == "refresh_token":
        return get_access_token_refresh_token_v1()
    raise RuntimeError("PBI_AUTH_MODE inválido. Use refresh_token ou client_credentials.")


def trigger_refresh(token: str) -> None:
    _require_env("PBI_GROUP_ID", GROUP_ID)
    _require_env("PBI_DATASET_ID", DATASET_ID)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    r = requests.post(url, headers=headers, timeout=60)
    if r.status_code not in (200, 202):
        raise RuntimeError(f"⛔ Falha ao disparar refresh:\nSTATUS: {r.status_code}\nBODY: {r.text}")
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
        if r.status_code != 200:
            raise RuntimeError(f"⛔ Falha ao consultar refresh:\nSTATUS: {r.status_code}\nBODY: {r.text}")

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