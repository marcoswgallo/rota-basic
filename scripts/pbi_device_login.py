# scripts/pbi_device_login.py
import os, json
import msal
from dotenv import load_dotenv

load_dotenv()  # vai ler seu .env local (não o da VPS)

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")

if not TENANT_ID or not CLIENT_ID:
    raise SystemExit("Defina TENANT_ID e CLIENT_ID no .env local para gerar o token.")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = [
    "https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All",
    "offline_access",
]

app = msal.PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY)

flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    raise SystemExit("Falhou iniciar device flow: " + str(flow))

print(flow["message"])  # mostra o link + código
result = app.acquire_token_by_device_flow(flow)

print("\n=== COPIE O REFRESH TOKEN ABAIXO ===\n")
print(result.get("refresh_token", "NÃO VEIO refresh_token (verifique permissões/consent)"))
print("\n=== FIM ===\n")