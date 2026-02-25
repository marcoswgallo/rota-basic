#!/usr/bin/env python3
"""
Gera um refresh_token do Power BI via Device Code Flow (OAuth2 v2.0)
e imprime na tela para você colar no .env da VPS como PBI_REFRESH_TOKEN.

Requisitos no .env LOCAL (na raiz do projeto):
TENANT_ID=...
CLIENT_ID=...
"""

import os
import time
import requests
from dotenv import load_dotenv


def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Defina {name} no seu .env local (na raiz do projeto).")
    return v.strip()


def main() -> None:
    load_dotenv()

    tenant_id = require_env("TENANT_ID")
    client_id = require_env("CLIENT_ID")

    # precisa de offline_access para vir refresh_token
    scope = "offline_access https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All"

    device_code_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    # 1) pede o device code
    dc_resp = requests.post(
        device_code_url,
        data={"client_id": client_id, "scope": scope},
        timeout=60,
    )
    dc_resp.raise_for_status()
    dc = dc_resp.json()

    print("\n=== AUTH DEVICE CODE ===")
    print(dc.get("message") or "Abra a URL e digite o código:")
    if dc.get("verification_uri") and dc.get("user_code"):
        print(f"URL : {dc['verification_uri']}")
        print(f"CODE: {dc['user_code']}")
    print("========================\n")

    device_code = dc["device_code"]
    interval = int(dc.get("interval", 5))
    expires_in = int(dc.get("expires_in", 900))

    # 2) fica consultando até você autorizar
    t0 = time.time()
    while True:
        if time.time() - t0 > expires_in:
            raise SystemExit("⛔ Tempo esgotado. Rode de novo e autorize mais rápido.")

        tok_resp = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code,
            },
            timeout=60,
        )

        if tok_resp.status_code == 200:
            tokens = tok_resp.json()
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                raise SystemExit("⛔ Não veio refresh_token. Verifique se o scope incluiu offline_access.")

            print("✅ Autorizado! COPIE o refresh_token abaixo e cole no .env da VPS como PBI_REFRESH_TOKEN:\n")
            print(refresh_token)
            print("\n✅ Fim.")
            return

        err = tok_resp.json()
        code = err.get("error")

        if code == "authorization_pending":
            time.sleep(interval)
            continue
        if code == "slow_down":
            interval += 5
            time.sleep(interval)
            continue

        raise SystemExit(f"⛔ Falha ao obter token: {tok_resp.status_code} {err}")


if __name__ == "__main__":
    main()