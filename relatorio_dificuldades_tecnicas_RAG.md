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

---

## 5. Arquitetura Expandida de Mineração (Implementação Planejada a partir do Catálogo de Fontes)

A partir do catálogo *"Fontes Auditáveis e Protocolos Programáticos para Extração em Lote (Bulk Data Mining)"* — que mapeia mais de 1.000 fontes primárias e secundárias em 10 macrocategorias — o pipeline de mineração foi **reestruturado de single-fonte (OpenAlex) para multi-fonte**, com separação rigorosa entre **coleta por fonte** e **consolidação** da base.

### 5.1. Arquitetura em Três Estágios

| Estágio | Script | Responsabilidade |
| :--- | :--- | :--- |
| **Coleta por fonte** | `scripts/minerador_openalex.py` | OpenAlex (works) com filtro estrito de relevância |
| **Coleta por fonte** | `scripts/minerador_oai.py` | Harvester OAI-PMH (Oasisbr/DSpace/SciELO) |
| **Consolidação** | `scripts/limpeza_unificada.py` | Merge, dedup inter-fonte, normalização e trilha de auditoria |

Cada script de coleta grava em um arquivo **de fonte** (`data/producoes_openalex.csv`, `data/producoes_oai.csv`), e o estágio de consolidação produz a **base unificada** (`data/producoes_mineradas.csv`). Isso elimina o conflito anterior (a coleta gravava sobre a base consolidada) e permite reprocessar qualquer fonte sem perder as demais.

### 5.2. Correção da Qualidade (Eliminação do Ruído Biomédico)

A versão anterior usava `search=` amplo no OpenAlex, cujo *matching fuzzy disjuntivo* (agravado pelo termo `"Brazil"`) saturava a amostra com literatura biomédica (Global Burden of Disease, neurociência, microbiologia). Medidas adotadas no novo `minerador_openalex.py`:

- **Query estruturada por janela de idioma**: `title_and_abstract.search` com `language:{en|pt|fr|es}` separadas, em vez de uma única query OR global.
- **Filtros de tipo e ano**: `type:article|book-chapter|dissertation|thesis` e `publication_year:2010-`.
- **Filtro pós-coleta de relevância**: só são retidas obras com **≥2 termos do dicionário de inovação** no título/resumo (inovação, governança, tecnologia social, economia solidária, patente, etc.), eliminando os falsos-positivos biomédicos.
- **`mailto` (polite pool)** e `select` com campos mínimos, minimizando custo e sobrecarga.
- **Rastreabilidade**: colunas `fonte`, `id_fonte`, `url`, `conceitos`, `coleta_timestamp` e `query_utilizada` em cada registro (auditabilidade/replicabilidade para a tese).

### 5.3. Harvester OAI-PMH

O `minerador_oai.py` implementa o protocolo **OAI-PMH** via `sickle` para extração em lote de repositórios institucionais (DSpace), alinhado às macrocategorias 1 e 2 do catálogo:

- **Resiliência a anti-bot**: alguns agregadores nacionais (ex.: Oasisbr) estão atrás de *challenge* Cloudflare (JS) e não respondem ao acesso programático simples — o harvester tenta cada endpoint, registra o status e **ignora graciosamente** os bloqueados, sem interromper o pipeline.
- **Filtro por comunidade/coleção** (`set` do DSpace), permitindo mirar áreas relevantes (ex.: Ciências Sociais Aplicadas).
- **Filtro de relevância e ano** reutilizados do dicionário de inovação.
- **Endpoints validados**: Lume UFRGS (funcional); o catálogo de endpoints pode ser ampliado editando `FONTES_OAI`.

### 5.4. Consolidação e Trilha de Auditoria

O `limpeza_unificada.py`:
- Padroniza todos os CSVs de fonte para **um esquema unificado** de colunas.
- **Deduplica por DOI** (com fallback por título normalizado sem acentos/pontuação).
- Grava um **registro de auditoria** (`data/_auditoria_mineracao.json`) com timestamp, total, volume por fonte/ano/idioma — pré-requisito metodológico de replicabilidade.

### 5.5. Dashboard Multi-Fonte

O `app_principal.py` (Aba 1) ganhou:
- **Seletor de fonte** (Todas / OpenAlex / Lume UFRGS / etc.).
- **Gráfico de cobertura por fonte**.
- **Recorte temporal** (`select_slider` de anos).
- Rótulos legíveis das fontes na tabela e nos gráficos.

### 5.6. Barreiras Técnicas Identificadas (e impacto no planejamento)

| Barreira | Observação | Tratamento |
| :--- | :--- | :--- |
| Cloudflare/JS challenge em agregadores nacionais (Oasisbr, BDTD) | Bloqueio programático de acesso direto | Harvester resiliente registra `erro` e segue para endpoints abertos; alternativa futura: *render* headless ou dump agregado |
| Timeout em alguns endpoints OAI (SciELO) | Conectividade/bot-protection | Tratamento por endpoint, retry implícito, sem quebra do pipeline |
| Encoding cp1252 no console Windows | Emojis/BOM nos prints podiam quebrar execução | `sys.stdout.reconfigure(encoding="utf-8")` nos entrypoints |

### 5.7. Próximas Fases (Roteiro)

1. **Ampliar `FONTES_OAI`** com mais DSpace de IFs/Universidades (validar endpoint individualmente) e SciELO quando disponível.
2. **CORDIS (UE)** e **Zenodo** via REST (macrocategorias 5 e 2) para literatura cinzenta de inovação.
3. **Patentes (fase 2)**: WIPO PATENTSCOPE / EPO OPS para vocabulário de inovação *hard science*.
4. **NLP avançado**: n-gramas, NER (instrumentos/instituições) e matriz de coocorrência no dashboard.

