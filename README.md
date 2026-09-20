🔬 SocioInova Fase 1: Mineração e Análise Bibliográfica

Este repositório contém o código-fonte do SocioInova (Fase 1: Mineração e Análise Bibliográfica), uma ferramenta de pesquisa desenvolvida como parte da tese de doutorado: "UMA LENTE SOCIOLÓGICA SOBRE A GOVERNANÇA DA INOVAÇÃO NOS INSTITUTOS FEDERAIS: INTERFACES ANALÍTICAS PARA UMA COMPREENSÃO DO “SOCIAL” NA INOVAÇÃO PÚBLICA".
A ferramenta utiliza Processamento de Linguagem Natural (PLN) e arquitetura RAG (Retrieval-Augmented Generation) para realizar auditorias sociológicas e decoloniais em produções científicas e documentos institucionais.

🚀 Funcionalidades Principais

🌐 Aba 1: Pesquisa Web (OpenAlex)
Mineração de Dados: Integração com a API OpenAlex para extração de produções sobre Sociologia da Inovação.
Análise Cienciométrica: Visualização de DNA Científico, evolução temporal e distribuição por idiomas.
Inteligência Analítica: Geração de fichamentos estruturados e análise de tendências epistemológicas (Otimismo Tecnológico vs. Crítica-Reflexiva).
Exportação: Geração de relatórios individuais em PDF com referências automáticas no padrão ABNT (NBR 6023).

📚 Aba 2: Auditoria Decolonial (Biblioteca Local)
Arquitetura RAG: Indexação local de documentos em PDF utilizando ChromaDB.
Lente Decolonial: Prompt estruturado para identificar mimetismo tecnológico e relações de poder entre o IFBA e agências de fomento.
Soberania de Dados: Todo o processamento dos documentos sensíveis é feito localmente via Ollama.

☁️ Sincronização Mestra
Backup Estratégico: Sincronização automática de bases mineradas e relatórios consolidados para o Google Drive.
Relatório do Dia: Função de "cesto de análises" que consolida todas as investigações diárias em um único documento de auditoria.

🛠️ Requisitos Técnicos
Modelos de Linguagem (LLMs) via Ollama
Para o pleno funcionamento, certifique-se de ter instalado os seguintes modelos:
qwen2:1.5b: Modelo principal para análises multilingues e baixo consumo de memória.
llama3: Modelo de suporte para extração de dados estruturados.
nomic-embed-text: Modelo dedicado para geração de embeddings vetoriais.
Bibliotecas Python
Instale as dependências necessárias:

Bash


pip install streamlit pandas ollama plotly langchain-community langchain-text-splitters chromadb fpdf pydrive2 pypdf


📁 Estrutura do Repositório

Plaintext


├── app_principal.py          # Dashboard em Streamlit (Interface)
├── scripts/
│   └── execucao_mestre.py    # Script de sincronização e upload para Drive
│   └── settings.yaml         # Configurações da PyDrive2
│   └── client_secrets.json   # Credenciais do Google Cloud (não versionado)
├── data/
│   ├── producoes_mineradas.csv
│   └── vector_db/            # Banco de dados vetorial do ChromaDB
├── meus_pdfs/                # Pasta local para os documentos da tese
└── Relatorio_Consolidado_SocioInova.pdf  # Arquivo gerado para sincronização


🧪 Metodologia e IA Responsável
Este software foi projetado sob a ótica da Soberania Tecnológica. O uso de modelos de código aberto locais garante que documentos institucionais do IFBA não sejam enviados para servidores de terceiros durante o processo de qualificação e análise de dados.
O Prompt Decolonial utilizado na ferramenta foca em:
Identificação de Inovação Situada vs. Mimetismo.
Análise de protagonismo acadêmico nas Instituições Federais.
Tensão entre termos mercadológicos e emancipatórios.
👤 Autor
Jonatã França Bittencourt
Professor do IFBA - Campus Jacobina
Doutorando em Ciências Sociais (PPGCS - UFBA)

Este trabalho está licenciado sob a Licença Creative Commons Atribuição-NãoComercial-CompartilhaIgual 4.0 Internacional (CC BY-NC-SA 4.0).
