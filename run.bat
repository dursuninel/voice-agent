@echo off
cd /d "%~dp0"
python -c "from dotenv import load_dotenv; load_dotenv()" 2>nul
python main.py
pause
