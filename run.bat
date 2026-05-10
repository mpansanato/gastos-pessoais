@echo off
chcp 65001 > nul
call venv\Scripts\activate
echo.
echo  Iniciando Gastos Pessoais...
echo  Acesse: https://127.0.0.1:5000
echo  (ignore o aviso de certificado no navegador e clique em "Avancado > Continuar")
echo.
python run.py
pause
