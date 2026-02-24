#!/bin/bash

echo "🔄 Atualizando sistema..."
sudo apt update -y

echo "🐍 Instalando Python e dependências..."
sudo apt install -y python3 python3-venv python3-pip

echo "🌐 Instalando Chromium..."
sudo apt install -y chromium-browser chromium-chromedriver

echo "📁 Criando ambiente virtual..."
python3 -m venv venv

echo "⚡ Ativando venv e instalando libs..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "📂 Criando pasta downloads..."
mkdir -p downloads

echo "✅ Setup concluído!"