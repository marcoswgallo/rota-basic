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


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default"
    }

    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def trigger_refresh():
    token = get_access_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    response.raise_for_status()
    print("Refresh disparado com sucesso!")


def wait_for_refresh():
    token = get_access_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes?$top=1"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    print("Aguardando conclusão do refresh...")

    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        status = response.json()["value"][0]["status"]
        print("Status atual:", status)

        if status == "Completed":
            print("Refresh concluído!")
            break

        if status == "Failed":
            raise Exception("Refresh falhou!")

        time.sleep(10)