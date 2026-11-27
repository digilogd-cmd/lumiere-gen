@echo off
chcp 65001 >nul
rem LUMIERE GEN System - 대시보드 켜기(이미 켜져 있으면 브라우저만 엽니다)
cd /d "%~dp0"
powershell -NoProfile -Command "try{(Invoke-WebRequest http://localhost:8431/api/projects -UseBasicParsing -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}"
if errorlevel 1 (
  where python >nul 2>nul && (start "" /min python dashboard\server.py) || (start "" /min py -3 dashboard\server.py)
  timeout /t 4 /nobreak >nul
)
start "" http://localhost:8431/
