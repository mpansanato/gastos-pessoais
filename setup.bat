@echo off
chcp 65001 > nul
echo.
echo  ============================================
echo    Configuracao Inicial - Gastos Pessoais
echo  ============================================
echo.

:: Verificar Python
python --version > nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado.
    echo  Instale Python 3.10+ em https://python.org
    echo  Marque "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo  Python encontrado: %%v

echo.
echo  [1/5] Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo  [ERRO] Falha ao criar ambiente virtual.
    pause
    exit /b 1
)
echo        OK

echo  [2/5] Instalando dependencias (aguarde)...
call venv\Scripts\activate
pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo  [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo        OK

echo  [3/5] Gerando chave secreta...
python -c "import secrets; open('.env','w').write('SECRET_KEY=' + secrets.token_hex(32) + '\n'); print('       OK')"

echo  [4/5] Gerando certificado SSL local (valido 10 anos)...
python generate_cert.py
if errorlevel 1 (
    echo  [ERRO] Falha ao gerar certificado.
    pause
    exit /b 1
)

echo  [5/5] Criando usuario administrador...
echo.
python create_admin.py
if errorlevel 1 (
    echo  [ERRO] Falha ao criar usuario.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    Configuracao concluida com sucesso!
echo.
echo    Execute run.bat para iniciar o sistema.
echo  ============================================
echo.
pause
