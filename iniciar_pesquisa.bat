@echo off
TITLE Observatorio de Inovacao - Soc(IA) / IFBA-UFBA
CLS

echo ======================================================
echo    SOC(IA) - INICIANDO AMBIENTE DE PESQUISA DOUTORAL
echo ======================================================
echo.

:: 1. Ativa o ambiente virtual
echo [1/3] Ativando Ambiente Virtual (venv)...
call .\venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERRO] Nao foi possivel ativar o venv!
    echo        Verifique se a pasta "venv" existe e tem o Python instalado.
    pause
    exit /b 1
)

:: 2. Executa o Script de Saude do Sistema
echo [2/3] Rodando Diagnostico de Saude...
:: O comando CALL e fundamental aqui para o script nao fechar
call python verificar_sistema.py

:: 3. Oferece o Menu de Opcoes
:menu
echo.
echo ======================================================
echo [3/3] SELECIONE A FERRAMENTA DESEJADA:
echo ======================================================
echo 1. Abrir Dashboard (Visualizacao e IA - Streamlit)
echo 2. Rodar Minerador (OpenAlex)
echo 3. Sincronizar Tudo (Google Drive)
echo 4. Sair
echo ======================================================
set /p op=Escolha uma opcao (1, 2, 3 ou 4) e aperte ENTER:

if "%op%"=="1" goto dashboard
if "%op%"=="2" goto mineracao
if "%op%"=="3" goto sincronizar
if "%op%"=="4" exit
echo Opcao invalida.
goto menu

:dashboard
echo.
echo Iniciando o Dashboard...
call streamlit run app_principal.py
goto menu

:mineracao
echo.
echo Iniciando Coleta de Dados...
call python scripts/minerador_openalex.py
pause
goto menu

:sincronizar
echo.
echo Iniciando Fluxo Mestre de Sincronizacao...
call python scripts/execucao_mestre.py
pause
goto menu
