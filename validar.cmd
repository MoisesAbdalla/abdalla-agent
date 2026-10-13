@echo off
REM Confere o catalogo de servicos. NAO chama a API - custo zero.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" validar.py
pause
