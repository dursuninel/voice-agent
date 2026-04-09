@echo off
echo === Sesli Ajan Kurulum ===

python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi. https://python.org adresinden kurun.
    pause
    exit /b
)

if not exist ".env" (
    copy .env.example .env
    echo.
    echo .env dosyasi olusturuldu.
)

echo.
echo --- API Anahtarlari ---
echo.
echo 1. GEMINI API anahtari icin: https://aistudio.google.com
echo 2. GROQ API anahtari icin:   https://console.groq.com
echo.

set /p GEMINI_KEY="GEMINI_API_KEY girin: "
set /p GROQ_KEY="GROQ_API_KEY girin: "

powershell -Command "(Get-Content .env) -replace 'GEMINI_API_KEY=.*', 'GEMINI_API_KEY=%GEMINI_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace 'GROQ_API_KEY=.*', 'GROQ_API_KEY=%GROQ_KEY%' | Set-Content .env"

echo.
echo .env guncellendi.

echo Bagimliliklar kuruluyor...
pip install -r requirements.txt

echo Playwright tarayici kuruluyor...
playwright install chromium

echo.
echo Kurulum tamamlandi! Calistirmak icin: python main.py
pause
