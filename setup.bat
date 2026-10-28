@echo off
rem SAQR one-time setup: Python 3.12 venv, app deps, Street View (streetlevel without the Mapy.cz-only pyfrpc), CUDA torch.
cd /d "%~dp0"
where uv >nul 2>&1 || (echo uv is not installed. Install it with:  winget install astral-sh.uv   ^(https://docs.astral.sh/uv/^) & goto :err)
uv venv --allow-existing --python 3.12 .venv || goto :err
set VP=.venv\Scripts\python.exe
uv pip install --python %VP% -r requirements.txt || goto :err
uv pip install --python %VP% --no-deps streetlevel==0.12.13 || goto :err
uv pip install --python %VP% torch torchvision --index-url https://download.pytorch.org/whl/cu130 || uv pip install --python %VP% torch torchvision
if not exist .env copy .env.example .env >nul
%VP% -m app.geoint_fetch || goto :err
echo.
echo Done. Run run.bat, then open Settings ^(gear icon^) to add an OpenRouter or Anthropic key.
pause
exit /b 0
:err
echo Setup failed.
pause
exit /b 1
