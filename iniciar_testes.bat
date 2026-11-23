@echo off
cd /d "%~dp0"
set CVJDATA_DEMO=1
".venv\Scripts\python.exe" -m streamlit run pages/2_Fechamento.py --server.port 8502
