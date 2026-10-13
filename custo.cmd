@echo off
REM Mede o custo real de uma conversa de venda e projeta o gasto mensal.
cd /d "%~dp0"
echo.
echo  ATENCAO: este script NAO e um relatorio - ele EXECUTA uma conversa
echo  real de 4 turnos contra a API para medir. Custa cerca de US$ 0,02.
echo.
choice /C SN /M "Rodar a medicao agora"
if errorlevel 2 goto :fim
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" custo.py
:fim
pause
