@echo off
REM Roda a bateria de evals usando o Python do venv do projeto.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m evals.runner
pause
