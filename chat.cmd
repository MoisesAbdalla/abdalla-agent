@echo off
REM Abre o chat com o agente usando o Python do venv do projeto.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" chat.py
pause
