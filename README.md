# Rota Basic

Automacao em Python para atualizar dados operacionais e enviar dashboard no Telegram.

Fluxo principal:
1. Faz login no Connect e baixa o relatorio analitico (`.xlsx`).
2. Faz upload do arquivo no OneDrive via Microsoft Graph.
3. Dispara refresh do dataset no Power BI (opcional).
4. Captura screenshot do dashboard e envia no Telegram.

## Estrutura do Projeto

- `connect_download.py`: baixa relatorio do Connect e envia para OneDrive.
- `powerbi_refresh.py`: dispara e acompanha refresh do dataset no Power BI.
- `send_dash_telegram.py`: captura dashboard com Selenium, recorta imagem e envia no Telegram.
- `telegram_commands.py`: bot Telegram com comandos operacionais (`/rodar`, `/dash`, etc.).
- `run_all.sh`: execucao sequencial simples (dados + dash).
- `setup.sh`: setup rapido em servidor Linux.
- `deploy.sh`: atualizacao e restart do bot.
- `scripts/pbi_device_login.py`: gera `PBI_REFRESH_TOKEN` via Device Code Flow.
- `get_pbi_refresh_token.py`: gera `PBI_REFRESH_TOKEN` via redirect local.

## Requisitos

- Python 3.10+ (recomendado 3.11)
- Google Chrome/Chromium + ChromeDriver compativeis
- Linux para uso em servidor (local tambem funciona com ajustes)
- Credenciais validas para:
  - Connect (email/senha)
  - App no Azure AD (Microsoft Graph + Power BI)
  - Bot Telegram

## Instalacao

### 1) Ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Dependencias de navegador (Ubuntu/Debian)

```bash
sudo apt update -y
sudo apt install -y chromium-browser chromium-chromedriver
```

Se preferir, use o script:

```bash
bash setup.sh
```

## Configuracao de Ambiente (`.env`)

Crie um arquivo `.env` na raiz com os valores abaixo.

### Obrigatorias

```dotenv
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Dashboard Power BI
DASH_URL=

# Connect
EMAIL=
PASSWORD=

# Azure / Microsoft
TENANT_ID=
CLIENT_ID=
CLIENT_SECRET=

# OneDrive
ONEDRIVE_USER=

# Power BI Dataset
PBI_GROUP_ID=
PBI_DATASET_ID=
```

### Opcionais (com padrao)

```dotenv
# Paths / Bot
BASE_DIR=/root/rota-basic
VENV_PY=/root/rota-basic/venv/bin/python
BOT_LOG_FILE=/root/rota-basic/bot_commands.log
POLL_TIMEOUT=50
SLEEP_ON_ERROR=3
ENABLE_PBI_REFRESH=1

# Connect
ONEDRIVE_FOLDER=Rota-Basic/Analitico
ONEDRIVE_FILENAME=analitico_atual.xlsx
DOWNLOAD_TIMEOUT=300
PAGE_LOAD_TIMEOUT=90

# Dash
DASH_PNG=/root/rota-basic/downloads/rota_dash.png
DASH_CAPTION=Rota Inicial - Atualizado
DASH_W=1920
DASH_H=1080
DASH_SCALE=2
DASH_WAIT=35
PBI_ZOOM=1.0
CROP_PADDING=20
CROP_THRESHOLD=240

# Power BI refresh
PBI_AUTH_MODE=client_credentials
PBI_REFRESH_TOKEN=
PBI_WAIT=1
PBI_POLL_SECONDS=10
PBI_TIMEOUT_SECONDS=900

# Token helper (script local)
PBI_REDIRECT_URI=http://localhost:8400
```

## Como Executar

Ative o ambiente:

```bash
source venv/bin/activate
```

### Execucao manual por etapa

```bash
python connect_download.py
python powerbi_refresh.py
python send_dash_telegram.py
```

### Fluxo simples (dados + dash)

```bash
bash run_all.sh
```

## Bot Telegram

Inicie o bot:

```bash
python telegram_commands.py
```

Comandos suportados:

- `/start`: lista comandos.
- `/rodar`: fluxo completo (dados -> powerbi -> dash).
- `/dados`: somente Connect + OneDrive.
- `/powerbi`: somente refresh do Power BI.
- `/dash`: somente captura/envio do dashboard.
- `/status`: mostra ultimas linhas de log.
- `/ping`: verifica saude do bot.

## Deploy (servidor)

Script atual:

```bash
bash deploy.sh
```

Esse script:
1. faz `git pull`
2. instala dependencias
3. mata processo antigo do bot
4. sobe bot em background com `nohup`

## Geração de `PBI_REFRESH_TOKEN` (opcional)

Modo device code (recomendado para ambiente sem navegador no servidor):

```bash
python scripts/pbi_device_login.py
```

Modo redirect local:

```bash
python get_pbi_refresh_token.py
```

## Logs e Diagnostico

- `cron.log`: execucoes agendadas (quando usar `run_all.sh` em cron).
- `bot.log`: saida do processo do bot (via `deploy.sh`).
- `bot_commands.log`: log interno do `telegram_commands.py`.

Erros de Selenium normalmente estao relacionados a:
- incompatibilidade Chrome vs ChromeDriver
- timeout de carregamento da pagina
- seletor alterado no site de origem

## Boas Praticas

- Nao versionar `.env`.
- Nao versionar `venv/` ou `venv_token/`.
- Rotacionar segredos (Telegram/Azure) se houver exposicao.
- Manter `requirements.txt` atualizado e com versoes fixadas para reproducibilidade.
