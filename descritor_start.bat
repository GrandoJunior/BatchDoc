@echo off
chcp 850 >nul
setlocal EnableDelayedExpansion

:: Identifica a origem (mesmo se for caminho UNC)
set "ORIGIN_DIR=%~dp0"
set "TARGET_DIR=%LOCALAPPDATA%\DescritorIADocumentos"

echo Iniciando processo de autoinstala‡Æo do Descritor IA de Documentos...

:: Verifica se ja existe e copia a estrutura
if not exist "%TARGET_DIR%" (
    echo Copiando arquivos para o ambiente seguro em %LOCALAPPDATA%...
    robocopy "%ORIGIN_DIR:~0,-1%" "%TARGET_DIR%" /E /XD ".git" ".venv" "__pycache__" /NJH /NJS /NDL /NC /NS /NP >nul
) else (
    echo Sincronizando arquivos atualizados...
    robocopy "%ORIGIN_DIR:~0,-1%" "%TARGET_DIR%" /E /XD ".git" ".venv" "__pycache__" /NJH /NJS /NDL /NC /NS /NP >nul
)

cd /d "%TARGET_DIR%"

:: Verifica se a venv existe, se nao, cria
if not exist ".venv" (
    echo Criando ambiente virtual Python...
    python -m venv .venv
)

:: Instala dependencias silenciosamente
echo Instalando/Verificando dependencias...
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt -q

:: Executa a aplicacao CLI repassando todos os argumentos
echo.
echo =======================================================
echo Iniciando Descritor IA de Documentos...
echo =======================================================
python -m src.presentation.cli "%~1" %2 %3 %4 %5 %6 %7 %8 %9

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO FATAL] A aplicacao foi encerrada devido a uma falha interna ou de comunicacao com a rede UNC.
    echo Codigo de Saida: %ERRORLEVEL%
)

endlocal
exit /b %ERRORLEVEL%
