@echo off
rem SAQR one-time setup. torch is the CPU index unless nvidia-smi sees a GPU, then cu130.
rem Same rule as scripts/setup.sh. ADR-014.
cd /d "%~dp0"
where uv >nul 2>&1 || (echo uv is not installed. Install it with:  winget install astral-sh.uv   ^(https://docs.astral.sh/uv/^) & goto :err)
uv venv --allow-existing --python 3.12 .venv || goto :err
set VP=.venv\Scripts\python.exe
uv pip install --python %VP% -r requirements.txt || goto :err
uv pip install --python %VP% --no-deps streetlevel==0.12.13 || goto :err
set TORCH_INDEX=https://download.pytorch.org/whl/cpu
nvidia-smi -L >nul 2>&1
if not errorlevel 1 set TORCH_INDEX=https://download.pytorch.org/whl/cu130
echo torch index: %TORCH_INDEX%
uv pip install --python %VP% torch torchvision --index-url %TORCH_INDEX% || goto :err
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
