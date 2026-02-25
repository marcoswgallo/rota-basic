#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
source venv/bin/activate

echo "=== $(date) INICIO ===" >> cron.log

python connect_download.py >> cron.log 2>&1
python send_dash_telegram.py >> cron.log 2>&1

echo "=== $(date) FIM ===" >> cron.log