@echo off
rem SAQR: starts the local server and opens the browser once it answers.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run: run setup.bat once.
  pause
  exit /b 1
)
if "%SAQR_PORT%"=="" set SAQR_PORT=8765
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "$u='http://127.0.0.1:%SAQR_PORT%'; for($i=0;$i -lt 120;$i++){ try { Invoke-WebRequest -UseBasicParsing \"$u/api/status\" -TimeoutSec 1 | Out-Null; Start-Process $u; break } catch { Start-Sleep -Milliseconds 500 } }"
echo SAQR is running on http://127.0.0.1:%SAQR_PORT%  (close this window to stop it)
.venv\Scripts\python.exe -m app.server
