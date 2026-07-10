@echo off
REM Wrapper para o Agendador de Tarefas do Windows.
REM Faz um snapshot consistente do banco e registra a saida em logs\backup.log.
cd /d "%~dp0"
echo [%date% %time%] iniciando backup>> "logs\backup.log"
"venv\Scripts\python.exe" "backup.py">> "logs\backup.log" 2>&1
echo [%date% %time%] fim (exit=%errorlevel%)>> "logs\backup.log"
