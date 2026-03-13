@echo off
title SocioInova RAG - Inicializacao Rapida
echo [1/3] Verificando Servidor Ollama...
start /min ollama serve

echo [2/3] Ativando Ambiente Virtual Python...
cd /d C:\Users\jonat\analise_ifs
call venv_tese\Scripts\activate

echo [3/3] Iniciando Interface SocioInova RAG...
streamlit run app.py

pause