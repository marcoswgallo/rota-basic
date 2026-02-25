#!/usr/bin/env bash
set -e

echo "🚀 Iniciando deploy..."

cd /root/rota-basic

echo "📥 Atualizando código do Git..."
git pull origin main

echo "🐍 Ativando venv..."
source venv/bin/activate

echo "📦 Instalando dependências..."
pip install -r requirements.txt

echo "🛑 Parando bot antigo (se existir)..."
pkill -f telegram_commands.py || true

echo "🤖 Iniciando bot..."
nohup python3 telegram_commands.py >> bot.log 2>&1 &

echo "✅ Deploy finalizado com sucesso!"