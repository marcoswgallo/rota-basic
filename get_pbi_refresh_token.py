import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# pode ser http://localhost:8400 também, mas precisa bater com o que você cadastrou no Azure
REDIRECT_URI = os.getenv("PBI_REDIRECT_URI", "http://localhost:8400")
PORT = int(REDIRECT_URI.split(":")[-1])

AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

SCOPES = [
    "offline_access",
    "https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All",
]

def main():
    import http.server
    import socketserver

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "prompt": "consent",
    }
    url = AUTH_URL + "?" + urlencode(params)

    print("\n1) Abra este link no navegador e faça login:\n")
    print(url)
    print("\n2) Depois do login, o navegador vai redirecionar e a gente vai capturar o CODE automaticamente.\n")

    code_holder = {"code": None}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            code_holder["code"] = qs.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK! Pode voltar pro terminal.")
            return

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.handle_request()

    code = code_holder["code"]
    if not code:
        raise RuntimeError("Nao consegui capturar o code. Veja se o redirect_uri esta correto no Azure.")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
    }

    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    token = r.json()

    print("\n✅ Refresh token gerado!\n")
    print("PBI_REFRESH_TOKEN=" + token.get("refresh_token", ""))
    print("\nCole isso no .env do servidor.\n")

if __name__ == "__main__":
    main()