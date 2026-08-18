import pathlib

# Script para gerar o bootstrapper (.bat) de forma segura no Windows (pt-BR)
# utilizando a página de código correta (CP850) para evitar corrupção de caracteres.

def generate_bat():
    bat_content = """@echo off
chcp 850 >nul
setlocal EnableDelayedExpansion

:: Identifica a origem (mesmo se for caminho UNC)
set "ORIGIN_DIR=%~dp0"
set "TARGET_DIR=%LOCALAPPDATA%\\DescritorIADocumentos"

echo Iniciando processo de autoinstalação do Descritor IA de Documentos...

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
call ".venv\\Scripts\\activate.bat"
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
"""
    
    bat_path = pathlib.Path(__file__).parent / "descritor_start.bat"
    
    # Gravando com codificação OEM CP850 conforme regra Global de Batch File.
    bat_path.write_bytes(bat_content.encode('cp850'))
    
    # Verificação round-trip
    verificado = bat_path.read_bytes().decode('cp850')
    if "autoinstalação" not in verificado:
        print("Erro: Falha na validação de codificação CP850 no .bat gerado.")
    else:
        print(f"Bootstrapper criado com sucesso em: {bat_path}")

if __name__ == "__main__":
    generate_bat()
