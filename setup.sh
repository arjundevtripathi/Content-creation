#!/usr/bin/env bash
# Creates the virtual environment, installs dependencies and prepares .env (macOS / Linux)
set -e
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
$PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Created .env - set GROQ_API_KEY and SECRET_KEY."; }
echo "Setup complete. Run: source .venv/bin/activate && uvicorn app.main:app --reload"
