@echo off
REM Painel: agendamentos, escalacoes e leads. NAO chama a API - custo zero.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" painel.py
pause
