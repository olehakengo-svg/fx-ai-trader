@echo off
echo ========================================
echo   FX AI Trader — セットアップ & 起動
echo ========================================

echo [1/2] ライブラリをインストール中...
pip install -r requirements.txt

echo [2/2] サーバーを起動中...
echo.
echo   ブラウザで開く: http://localhost:5000
echo.
python app.py
pause
