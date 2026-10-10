@echo off
REM Creates the virtual environment, installs dependencies and prepares .env (Windows)
where py >nul 2>nul && (set PY=py -3.12) || (set PY=python)
%PY% --version >nul 2>nul || (set PY=py -3.11)

echo Creating virtual environment in .venv ...
%PY% -m venv .venv || (echo Failed. Install Python 3.11 or 3.12 from python.org and retry. & exit /b 1)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Dependency install failed. & exit /b 1)

if not exist .env (
  copy .env.example .env >nul
  echo Created .env - open it and set GROQ_API_KEY and SECRET_KEY.
)
echo.
echo Setup complete. Next: run  run.bat
