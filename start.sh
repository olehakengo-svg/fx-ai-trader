#!/bin/bash
echo "========================================"
echo "  FX AI Trader — セットアップ & 起動"
echo "========================================"

# Install dependencies
echo "[1/2] ライブラリをインストール中..."
pip install -r requirements.txt -q

echo "[2/2] サーバーを起動中..."
echo ""
echo "  ブラウザで開く → http://localhost:5000"
echo ""
python app.py
