Markdown


# Relatório de Desenvolvimento e Superação de Desafios Técnicos: Sistema RAG de Mineração

**Pesquisador:** Jonatã França Bittencourt  
**Projeto:** Observatório de Sociologia da Inovação - Doutorado UFBA  
**Data:** 09 de Março de 2026  

## 1. Introdução
Este documento descreve as principais barreiras técnicas enfrentadas durante a programação e implementação da arquitetura de Recuperação Aumentada por Geração (RAG) e do minerador multilingue, bem como as soluções aplicadas para garantir a integridade da pesquisa sociológica.

## 2. Compilado de Dificuldades Técnicas

### 2.1. Desafios de Sintaxe e Estrutura de Código (Python/Streamlit)
* **Problema:** Ocorrência recorrente de `SyntaxError` (strings não terminadas) devido à complexidade dos prompts de IA. O Python interrompia a execução porque blocos de texto multilinha não eram fechados corretamente, além de problemas com o apóstrofo em termos franceses (ex: *L'innovation*).
* **Solução:** Implementação de strings formatadas com delimitadores adequados, uso do caractere de escape (`\`) para termos estrangeiros e revisão da indentação rigorosa exigida pelo Streamlit.

### 2.2. Inconstância de Metadados em Bases Acadêmicas (OpenAlex/Pandas)
* **Problema:** Erros de `KeyError` ao tentar exibir dados na tabela. Diferentes versões da API do OpenAlex nomeavam colunas de forma distinta (ex: `authors` vs `author_names`).
* **Solução:** Criação de um algoritmo de **Mapeamento Dinâmico de Colunas**, que busca sinônimos funcionais para garantir que o sistema nunca trave ao ler o arquivo CSV.

### 2.3. Lógica de Busca Booleana e a Evolução do Filtro Epistemológico
* **Problema:** A tentativa inicial de realizar uma mineração multilingue com o operador `AND` entre cinco grupos conceituais estanques resultou em "zero resultados", criando um filtro excessivamente estreito.
* **Solução:** O sistema foi redesenhado para a lógica de **Círculos Concêntricos (Cerne + Complementos)**. O núcleo da busca foi ampliado para incluir não apenas os Institutos Federais, mas categorias essenciais: Governança, Políticas Públicas e Inovação. Termos decoloniais e locais foram posicionados como refinamento.

### 2.4. Escabilidade e Paginação de Dados
* **Problema:** Limitação técnica da API em entregar apenas 200 resultados por requisição, dificultando o alcance de uma base de dados robusta para a análise das Instituições Federais de C&T.
* **Solução:** Implementação de **paginação automática** no script de mineração, permitindo a captura sequencial de múltiplos blocos de 200 resultados com intervalos de segurança (`time.sleep`) para evitar bloqueio de IP.

### 2.5. Opacidade no Processo de Indexação Vetorial (RAG/ChromaDB)
* **Problema:** Dificuldade em visualizar se a IA estava de fato "lendo" os PDFs locais, já que a indexação vetorial é um processo matemático invisível.
* **Solução:** Adição de componentes de transparência na interface, como barras de progresso, contadores de fragmentos (*chunks*) e listagem prévia de arquivos detectados.

### 2.6. Viés Algorítmico e a Calibragem Léxico-Decolonial
* **Problema:** Durante os testes, identificou-se o viés algorítmico de hegemonia linguística. Ao utilizar descritores amplos em inglês (*Innovation*, *Governance*) combinados à ordenação decrescente por citações, a API saturou a amostra com literatura em língua inglesa, empurrando as produções em português, francês e espanhol para fora do extrato principal.
* **Solução:** Aplicação de uma **calibragem léxico-decolonial**. Estreitou-se a sensibilidade dos descritores em inglês (substituindo termos genéricos por *Innovation Policy* e *Public Governance*), preservando a amplitude semântica dos idiomas latinos. Essa assimetria quebrou o monopólio das citações hegemônicas, garantindo um *corpus* final verdadeiramente multilingue e alinhado ao potencial analítico da pesquisa.

## 3. Orquestração de Modelos Locais (Ollama)
Foi necessário gerenciar o equilíbrio entre modelos locais para garantir o sigilo dos dados e a performance da análise:
* **Phi-3:** Escolhido pela velocidade na geração de embeddings (vetores) para a biblioteca local.
* **Llama 3:** Utilizado para a redação final e fichamentos estruturados devido à fluidez de sua linguagem acadêmica.
* **Mistral:** Aplicado em auditorias comparativas de viés teórico (Otimista Tecnológico vs. Crítico-Reflexivo).

## 4. Conclusão Metodológica
A superação destas barreiras demonstra a maturidade técnica da pesquisa. O Observatório de Sociologia da Inovação opera agora sob os princípios da **Soberania Tecnológica** e do **Rigor Algorítmico**, transcendendo a mera coleta de dados para atuar como um instrumento analítico crítico, essencial para uma tese de excelência.
