@echo off
REM Starts the API (port 8000) and the Streamlit UI (port 8501) in two windows
call .venv\Scripts\activate.bat
start "Content AI - API" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
start "Content AI - UI" cmd /k "call .venv\Scripts\activate.bat && streamlit run frontend\streamlit_app.py"
echo API: http://localhost:8000/docs   UI: http://localhost:8501
