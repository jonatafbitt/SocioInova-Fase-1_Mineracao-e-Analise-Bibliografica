# SocioInova — Mineração e Análise Bibliográfica

## Documento Metodológico de Divulgação Científica — Funções das Abas, Valores Analíticos e Protocolos de Mineração de Dados Documentais

> **Universo empírico:** produção bibliográfica sobre inovação, com ênfase no social (tecnologia social, economia solidária, governança, emancipação) na Rede Federal de Educação Profissional, Científica e Tecnológica e no cenário nacional/internacional.
>
> **Instrumento:** *SocioInova* (Fase 1 — Mineração e Análise Bibliográfica), dashboard originalmente desenvolvido no âmbito da tese de doutorado "Uma lente sociológica sobre a governança da inovação nos Institutos Federais: interfaces analíticas para uma compreensão do 'social' na inovação pública" (PPGCS–UFBA).

---

## Como ler este documento

Este texto foi redigido para **dois públicos-leitores simultâneos** — cientistas de dados e cientistas sociais — e, por isso, cada seção incorpora duas camadas complementares de leitura:

- 🖥️ **Visão computacional** — detalhamento técnico (APIs, modelos estatísticos, *pipelines*, parâmetros), destinado a quem domina programação e análise de dados.
- 🧭 **Tradução sociológica** — explicação do significado e do valor epistemológico de cada função para a pesquisa social, sem pressupostos técnicos, destinada a quem trabalha com teoria e análise documental.

O leitor pode percorrer o texto de forma contínua ou consultar somente a camada que lhe interessa. Um **glossário duplo** ao final permite a conversão rápida entre os dois vocabulários.

---

## 1. O que é o SocioInova e por que ele existe

O SocioInova é uma **plataforma de pesquisa** que combina mineração de dados bibliográficos, processamento de linguagem natural (PLN) e consulta a modelos de linguagem (LLMs) para transformar um **universo bibliográfico sobre inovação** em um objeto de investigação para as ciências sociais.

Linguisticamente, trata-se de uma **análise documental assistida por computação**: as fontes (artigos, teses, dissertações, relatórios) não são lidas uma a uma, mas *mineradas, agregadas, classificadas e interpretadas em escala*, dentro de protocolos explícitos e auditáveis.

- 🖥️ **Para cientistas de dados:** a ferramenta é uma aplicação **Streamlit** (Python) com arquitetura *Retrieval-Augmented Generation* (RAG). Ela consome **APIs de bases bibliográficas** (OpenAlex, OAI-PMH), organiza os dados em **esquema unificado** (CSV), gera **artefatos derivados** (índices, matrizes de co-ocorrência, contagens de termos) e executa LLMs locais via **Ollama** para síntese e auditoria. Visualizações são geradas com **Plotly**.
- 🧭 **Para cientistas sociais:** a ferramenta é o equivalente digital de uma grande *revisão sistemática de literatura* com três movimentos: (1) *coletar* o que foi publicado sobre inovação; (2) *cartografar* o campo — quem pesquisa, onde, quando, sob quais conceitos; (3) *auditar* criticamente os sentidos — quando "inovação" aparece como palavra-mercado (mimetismo) e quando aparece como prática emancipatória situada no território.

### 1.1. Perguntas de pesquisa que a ferramenta ajuda a responder

| Nível de análise | Pergunta-tipo | Aba que responde |
| :--- | :--- | :--- |
| Macro (campo) | Como evoluiu a produção sobre inovação no tempo, por idioma, por instituição? | Aba 1 (Panorama) |
| Macro (gramática) | Quais conceitos estruturam o campo? O que anda junto (co-ocorrência)? | Aba 2 (DNA, Redes) |
| Meso (espaços) | Quem produz e de onde? Nacional × internacional? | Aba 2 (Espaços Públicos) |
| Meso (sentidos) | O "social", o "código aberto" e a "emancipação" aparecem como retórica ou como prática? | Aba 2 (Análise de Sentidos) |
| Micro (obra) | Que leitura sociológica posso fazer de um texto específico? | Aba 1 (Inteligência Analítica) |
| Micro (documentos locais) | Textos do IFBA, da Rede Federal e da tese usam os mesmos termos? Com que profundidade? | Aba 3 (Biblioteca Local) |

---

## 2. Fundamentos metodológicos

### 2.1. Análise documental digital e cienciometria

A cienciometria estuda a ciência como objeto — medindo quem produz, onde publica, como cita. O SocioInova usa métodos cienciométricos de baixo custo (contagem, distribuição, co-ocorrência) somados a uma lente sociológica qualitativa.

- 🖥️ Técnicas empregadas: contagem de frequências (`value_counts`), séries temporais, `n-gramas` lexicais, normalização Unicode (NFKD), *stopwords* institucionais, matrizes de co-ocorrência e redes de nós/arestas.
- 🧭 Tudo isso responde a perguntas clássicas da sociologia do conhecimento: *quanto campo existe?*, *quem o controla discursivamente?*, *que categorias são hegemônicas e quais são periféricas?*

### 2.2. Mineração de dados textuais (tipo *bulk data mining*)

O repositório contém um catálogo de mais de 1.000 fontes auditáveis (repositórios universitários, FAPs, organismos internacionais, escritórios de patentes, *think tanks* — ver `_fontes auditáveis e os protocolos programáticos para extração em lote (bulk data mining).md`). O código operacionaliza a coleta em três vias:

| Módulo (`scripts/`) | Protocolo | Fonte | Saída |
| :--- | :--- | :--- | :--- |
| `minerador_openalex.py` | API REST (JSON), `filter=title_and_abstract.search`, janelas por idioma (en/pt/fr/es) | OpenAlex (250M+ obras) | `data/producoes_openalex.csv` |
| `minerador_oai.py` | **OAI-PMH** (`ListRecords`, `oai_dc`) | 27+ repositórios DSpace de IFs, universidades federais e o agregador Lume/UFRGS | `data/producoes_oai.csv` |
| `minerador_scopus.py` / `minerador_science_direct.py` | APIs comerciais (pybliometrics / Elsevier) | Scopus, ScienceDirect | `data/producoes_scopus.csv`, `data/producoes_sciencedirect.csv` |
| `limpeza_unificada.py` | Consolidação, **deduplicação** por DOI (fallback: título normalizado) | Todas as acima | `data/producoes_mineradas.csv` (base-mestra) |

- 🖥️ Critérios de relevância: cada registro só ingressa na base se contiver **≥ 2 termos** do dicionário de inovação no título/resumo (filtro pós-coleta), com anos ≥ 2010 e, no caso OAI-PMH, trava de segurança de 4.000 registros brutos por repositório. A deduplicação é feita por DOI extraído por regex (`10\.\d{4,9}/…`) e, por fallback, por título normalizado (sem acentos/pontuação). Toda coleta grava **trilha de auditoria** (`data/_auditoria_mineracao.json`).
- 🧭 Ou seja: não se "baixa tudo que existe" — define-se um *protocolo de inclusão* transparente (equivalente aos critérios de inclusão/exclusão de uma revisão sistemática), aplica-se o mesmo critério a todas as fontes e registra-se cada operação para que a amostra seja **replicável** — condição indispensável de validade científica.

### 2.3. Processamento de Linguagem Natural e LLMs locais

- 🖥️ **Embeddings:** o texto vai para um banco vetorial **ChromaDB** (`data/vector_db`) usando `OllamaEmbeddings(model="nomic-embed-text")`. Os documentos são fatiados em *chunks* de ~2.000 caracteres com sobreposição de 200 (`RecursiveCharacterTextSplitter`), preservando metadados de origem e página. A busca é feita por **similaridade de cosseno** entre o vetor da pergunta e os vetores dos trechos (`similarity_search(..., k=3)`).
- 🧭 **O que isso significa em termos simples:** cada documento é convertido em uma "impressão digital numérica" do seu sentido. Quando se pergunta algo, a máquina localiza os trechos da biblioteca *mais próximos em sentido* (não só em palavra), como um bibliotecário que conhece o conteúdo — não apenas os títulos dos livros.
- 🖥️ **Geração de texto (LLM):** modelos do ecossistema **Ollama** (gratuitos e *open weights*, executados localmente) produzem fichamentos, análises por "lente" sociológica e auditorias decoloniais. Modelos disponíveis no seletor: `qwen2:1.5b` (multilíngue e leve), `phi3`, `llama3` (redação acadêmica), `mistral` (auditoria de viés), `qwen3:1.7b`, `qwen3:4b`, `gemma3:4b`, `phi4-mini`.
- 🧭 **Soberania de dados:** por rodar localmente, documentos institucionais sensíveis (internos ao IFBA, por exemplo) **não saem da máquina**. Em pesquisa com populações e instituições, o controle sobre os dados é uma questão ética e de soberania — a escolha de LLMs locais é uma decisão metodológica, não apenas de infraestrutura.

### 2.4. A matriz epistemológica que orienta as análises

Toda a ferramenta é orientada por um quadro teórico explícito (presente na Aba 3, "Matriz Epistemológica"):

| Dimensão | Inovação por **mimetismo** (dependente) | Inovação **situada** (emancipatória) |
| :--- | :--- | :--- |
| Referencial geopolítico | Norte Global (Vale do Silício, modelos europeus) | Território local (Jacobina, Bahia, contexto regional) |
| Linguagem predominante | Eficiência, competitividade, transferência | Soberania, tecnologias sociais, bem comum |
| Papel dos IFs | Executores de agendas externas | Protagonistas de demandas locais |
| Vetor de desenvolvimento | *Top-down* (modelos importados) | *Bottom-up* (arranjos locais) |
| Relação de poder | Reprodução de dependência técnica | Ruptura decolonial, autonomia científica |

- 🧭 Este quadro é a *lente*: ele não "enviesa" a mineração (a coleta é neutra), mas orienta a *interpretação* — o que é uma escolha teórica declarada, conforme o rigor exige.
- 🖥️ No código, essa lente vira **dicionários semânticos**: `TERMOS_MIMETISMO` (competitividade, mercado, startup, escala, ROI…) e `TERMOS_EMANCIPA` (soberania, autonomia, decolonial, bem comum, autogestão…), usados para contagem de sentidos e para direcionar os *prompts* de interpretação.

---

## 3. Arquitetura e ciclo de vida dos dados

```
 [Coleta]                    [Consolidação]              [Indexação]                 [Análise]                      [Comunicação]
minerador_openalex     ->   limpeza_unificada      ->   ChromaDB (local)        ->  Abas 1/2/3 (Streamlit)   ->   Relatório do Dia
minerador_oai          ->   (dedup, schema único)   ->   pdf_texto_cache.json    ->  Inteligência Analítica   ->   PDF individual
minerador_scopus/scidir->   producoes_mineradas.csv ->      (busca literal)     ->  Estado da Arte           ->   Google Drive
                           + estado da arte (offline)                                    (DNA, redes, sentidos)
```

**Artefatos analíticos gerados offline** (via `python scripts/gerar_estado_arte.py [modelo]`):

| Arquivo (`data/`) | Conteúdo | Para que serve |
| :--- | :--- | :--- |
| `dna_inovacao.csv` | Frequência de 11 eixos-conceito nucleares | "Assinatura conceitual" do corpus |
| `indices_estado_arte.csv` | Registro derivado por obra: recorte geográfico, flags social/aberto/emancipatório, classe núcleo/contexto, instituições detectadas | Base para todos os filtros e métricas da Aba 2 |
| `coocorrencia_estado_arte.json` | Nós e arestas (com pesos) dos termos que aparecem juntos | Rede de co-ocorrência |
| `_sintese_estado_arte.json` | Síntese IA por recorte (nacional/internacional), cacheada por hash | Texto da "gramática do campo" |
| `_sintese_sentidos.txt` | Classificação semiótica (performático × emancipatório) | Análise de sentidos da Aba 2 |
| `pdf_texto_cache.json` | Texto plano de cada página dos PDFs locais | Busca literal (Aba 3) |
| `_auditoria_mineracao.json` | Trilha de todas as operações de coleta/limpeza | Replicabilidade e auditoria |

---

## 4. Barra lateral — Gestão do sistema

A barra lateral concentra controles transversais que valem para todo o aplicativo.

### 4.1. Seletor "Cérebro da IA" (LLM)

- 🖥️ Seleciona o modelo de linguagem usado por *todas* as funções de geração de texto (fichamento, lentes, interpretação de termos, auditoria decolonial). É uma variável do experimento: pode-se repetir a mesma análise com modelos distintos.
- 🧭 **Valor para a pesquisa:** permite o **controle de robustez interpretativa** — se duas "inteligências" diferentes chegam a leituras convergentes, o achado é mais provável de refletir o texto do que o modelo. Na escrita da tese, recomenda-se documentar sempre **qual modelo** produziu cada análise (a ferramenta registra isso no relatório).

### 4.2. "Sincronizar com Google Drive"

- 🖥️ Dispara `scripts/execucao_mestre.py` (pyDrive2), que autentica via OAuth e envia para a pasta do Doutorado: a base unificada (`SocioInova_Producoes_Mineradas.csv`), o DNA institucional (`.csv`), o relatório consolidado do dia (`Auditoria_Decolonial_<data>.pdf`) e o relatório metodológico RAG (`.md`).
- 🧭 **Valor para a pesquisa:** **preservação e rastreabilidade da memória de pesquisa**. O pesquisador que trabalha com documentos originais e bases próprias precisa de redundância (backup) e de um registro datado de cada etapa — um "diário de bordo" automatizado.

### 4.3. "Relatório do Dia" (cesto de análises)

- 🖥️ Mantém em memória de sessão (`st.session_state.cesto_analises`) todos os resultados que o usuário for acumulando em qualquer aba ("Adicionar ao Relatório do Dia"). Ao final, gera um **PDF consolidado** (`gerar_relatorio_consolidado`) com cada obra, sua referência ABNT e a análise produzida.
- 🧭 **Valor para a pesquisa:** funciona como um *instrumento de coleta*: o pesquisador lê, analisa e "arquiva" na ordem desejada, compondo o material empírico bruto que alimentará os capítulos de análise. A referência ABNT já formada poupa retrabalho e reduz erro de citação.

---

## 5. Aba 1 — "🌐 Pesquisa OpenAlex" (universo minerado na web)

Aba de **exploração macro e micro do universo bibliográfico** coletado via OpenAlex e demais fontes da base unificada.

### 5.1. Seletor de fonte e "Cobertura por Fonte"

- 🖥️ Filtra os registros por origem (`OpenAlex`, `OAI-PMH/Repositórios`, `Lume_UFRGS` etc.). O gráfico de cobertura é um `px.bar` com contagem por valor da coluna `fonte`.
- 🧭 **Valor:** permite comparar a contribuição de cada base e isolar vieses — um repositório institucional (OAI) tende a refletir a produção de uma instituição específica; o OpenAlex, a produção mundial indexada. Separar as fontes é controlar a composição da amostra.

### 5.2. Recorte temporal

- 🖥️ `st.select_slider` sobre os anos presentes na base; filtra o DataFrame por intervalo.
- 🧭 **Valor:** operacionaliza a pergunta "como a discussão sobre inovação social cresceu/encolheu no período?". É o eixo diacrônico da análise.

### 5.3. Panorama da Produção (3 painéis)

1. **Evolução Temporal** — barras de publicações por ano;
2. **Idiomas** — distribuição por idioma (en/pt/fr/es), com tradução dos códigos;
3. **DNA Científico (Top 30)** — lido de `data/perfil_institucional.csv`, gerado pelo minerador a partir dos *conceitos* que a OpenAlex atribui à produção de oito IFs da Rede Federal (`executar_perfil_rede`).

- 🖥️ São gráficos `plotly.express.bar`; o DNA usa a triagem de conceitos com `level <= 3` ou pertencentes a uma lista prioritária (innovation, social innovation, solidarity economy…), agregados por `Counter().most_common(30)`.
- 🧭 **Valor sociológico:** o DNA institucional responde "sobre o que a Rede Federal publica de fato?" — importante para contrastar o discurso institucional de inovação com o perfil temático real da produção. É um *mapa das identidades científicas* das instituições.

### 5.4. Distribuição por Eixo Temático

- 🖥️ Lê a coluna `eixo_tematico` (separada por `;`), explode em lista e computa frequências; rótulos legíveis (ex.: `economia_solidaria` → "Economia Solidária").
- 🧭 **Valor:** materializa a **lente sociológica de seis eixos** (Economia Solidária; Tecnologia Social; Inovação em Políticas Públicas; Governança da Inovação; Inovação Emancipadora; Inovação em Instituições Públicas) dando a cada obra um *lugar* no quadro teórico.

### 5.5. Filtros de busca e tabela de obras

- **Filtrar por título** (busca textual *case-insensitive*) e **Filtrar por Eixo Temático** reduzem a base; a tabela exibe colunas selecionadas (título, ano, autores, idioma, eixo, fonte…).
- 🖥️ Implementação: `df[df[col].str.contains(busca, case=False, na=False)]`.
- 🧭 **Valor:** é a "mesa de trabalho" bibliográfica — localização manual de obras para leitura posterior, sem perder a ligação com os metadados estruturados.

### 5.6. Inteligência Analítica (análise profunda por obra)

Ao selecionar uma obra, o sistema gera **a referência ABNT** automaticamente (`formatar_abnt` formata autores no padrão "SOBRENOME, Nome") e oferece **modos de análise** disparados por botões:

| Função | O que faz | Valor metodológico |
| :--- | :--- | :--- |
| 🚀 **Fichamento Ágil** | Resumo estruturado da obra gerado pelo LLM | Comprime a leitura; produz matéria-prima consistente para a revisão de literatura |
| 🔍 **Analisar Tendência** | Avalia o viés do texto (Otimismo Tecnológico × Crítica-Reflexiva) | Detecta o *enquadramento* epistemológico do autor |
| 🌍 **Lente Economia Solidária** | Examina cooperativismo, autogestão, trabalho associado | Mapeia adesão a formas não-capitalistas de produção |
| 📱 **Lente Tecnologia Social** | Examina tecnologias apropriadas, protagonismo comunitário, adequação sociotécnica | Identifica o contraste com transferência *top-down* |
| 🏛️ **Lente Governança da Inovação** | Examina coordenação Estado–universidade–sociedade civil, participação e *accountability* | Opera o conceito central da tese |
| 💡 **Lente Inovação Emancipadora** | Examina decolonialidade, soberania e autonomia científica | Localiza rupturas com a dependência do Norte Global |
| 🎓 **Lente Instituições Públicas** | Examina o papel dos IFs na Rede Federal e a interface ensino-pesquisa-extensão | Ancoragem empírica da tese na Rede Federal |
| 🏭 **Lente Inovação em Políticas Públicas** | Examina formulação/implementação de políticas de inovação, capacidades estatais | Conecta a amostra ao Estado e às políticas |

- 🖥️ Cada lente injeta um *prompt estruturado* que instrui o modelo a atuar como "sociólogo da inovação" e a focar em atributos específicos. O resultado é persistido em `st.session_state` e pode gerar **PDF individual** (FPDF, com referência ABNT) e ser **adicionado ao Relatório do Dia**.
- 🧭 **Valor:** é a ponte entre o dado bibliográfico bruto e a interpretação sociológica — o mesmo texto é lido sob prismas teóricos distintos, permitindo análise comparada de como cada obra se posiciona em cada dimensão do quadro teórico.

> ⚠️ **Boas práticas de pesquisa:** as saídas geradas por LLM são hipóteses de leitura, não dados. Cientistas sociais devem tratar cada fichamento/lente como *proposição a ser verificada na leitura original*; cientistas de dados devem documentar modelo, temperatura e data (a ferramenta regista modelo no relatório) para reprodutibilidade.

---

## 6. Aba 2 — "🗺️ Estado da Arte da Inovação" (leitura de conjunto do campo)

Aba de **análise macro (leitura de conjunto)** do campo a partir do corpus minerado — a "gramática nacional × internacional" e os lugares, usos e sentidos do recorte social, aberto e emancipador.

### 6.1. Filtros rápidos (sem IA)

- **Recorte geográfico** (nacional/internacional) — classificado por proxy do idioma + fonte;
- **Período** — faixa de anos;
- **Classe de relevância** (núcleo/contexto) — ver regras de classificação abaixo.

- 🖥️ A coluna `recorte_geo` resulta de `classificar_recorte_geo(idioma, fonte)`: `pt/por` → nacional; `en/fr/es` → internacional; fallback → nacional. A classe `nucleo_contexto` é definida por heurística: é **núcleo** quem toca eixo central (tecnologia social, economia solidária, emancipação, governança, institutos federais) **OU** tem ≥ 3 termos nucleares **OU** apresenta flag social/aberto; senão, é **contexto**.
- 🧭 **Valor:** "núcleo × contexto" é o equivalente digital da distinção entre literatura *central* e *periférica* do campo; permite ao pesquisador focar a leitura crítica no núcleo e usar o contexto como mapa de horizonte. O recorte nacional × internacional permite comparar a gramática brasileira com a do debate global.

### 6.2. Métricas-resumo

Quatro indicadores instantâneos: **Registros no recorte**, **Núcleo (lente forte)**, **Recorte social** (obras que tocam tecnologia social ou economia solidária) e **Emancipatório** (obras com termos emancipatórios).

- 🧭 **Valor:** um painel de bordo do campo — em poucos segundos o pesquisador sabe "quanto do corpus é social" e "quanto é emancipatório", base para afirmações quantitativas defensáveis.

### 6.3. (1) Síntese Global — a gramática do campo

- 🖥️ Texto **pré-computado** por IA (offline, `gerar_estado_arte.py`), cacheado em `_sintese_estado_arte.json` por hash do recorte+modelo. O processo aplica *chunking* dos resumos (pacotes), síntese parcial por pacote e condensação final em um documento estruturado em: (1) termos-conceito nucleares; (2) enquadramentos dominantes; (3) lugar do social/código aberto/emancipação; (4) lacunas e tensões — separadamente para **nacional** e **internacional**.
- 🧭 **Valor:** produz em texto corrido o "estado da arte" que é esperado em um capítulo de tese — mas gerado de forma sistemática, replicável e atualizável a cada nova coleta. A separação nacional/internacional permite verificar, entre outras, a hipótese de que o debate brasileiro seja mais situado/enraizado que o internacional.

### 6.4. (2) Rede de Co-ocorrência de Conceitos

- 🖥️ Nós = eixos nucleares presentes no registro; arestas = conceitos que aparecem juntos no mesmo texto (peso = nº de co-ocorrências). Visualização em grafo Plotly com posicionamento circular; a expansão "Matriz (top arestas)" lista as 20 arestas mais fortes.
- 🧭 **Valor sociológico:** a co-ocorrência revela *afinidades conceituais do campo* — por exemplo, se "economia solidária" costuma aparecer junto de "tecnologia social", isso sugere um bloco discursivo consolidado; se "inovação" aparece quase sempre sozinha junto de "patente", sugere uma gramática mais mercadológica. É a **estrutura associativa do pensamento** do campo.

### 6.5. (3) Mapa dos Espaços Públicos de Inovação

- **Top 15 Instituições citadas** — detecção por regex (`Instituto Federal|IF|Universidade Federal|UF|CEFET…`) nos títulos/resumos/veículos.
- **Produção por UF** — mapeamento fonte→UF (IFBA→BA, Lume_UFRGS→RS, etc.) com barras por unidade federativa.
- 🧭 **Valor:** responde *"quem produz e de onde"* — espacializa o campo. É a dimensão **territorial** da análise (essencial à hipótese de inovação situada): observar a produção concentrada em certas regiões e a ausência de outras é um dado em si.

### 6.6. (4) Análise de Sentidos — semiótica social/código aberto/emancipação

- 🖥️ Métricas: **Código aberto** (obras com termos como open source, software livre, ciência aberta; `flag_codigo_aberto`), **Sentido emancipatório** e **Sentido mimetista** (contagens de `n_sentidos_emancipacao`/`n_sentidos_mimetismo`). A síntese textual (`_sintese_sentidos.txt`) é gerada por IA com instrução explícita de classificar cada ocorrência como **performático-mercadológico (mimetismo)** ou **emancipatório-situado**.
- 🧭 **Valor:** é o coração da tese. A semiótica aqui é uma *análise de discurso assistida*: a ferramenta não apenas conta palavras, mas instrui a interpretação a distinguir o uso *retórico* da inovação (palavra-mercado) do uso *prático* (inovação ancorada em território, autonomia, bem comum). O pesquisador recebe um mapa dos sentidos acompanhado de exemplos ilustrativos.

### 6.7. DNA Científico do Recorte

- 🖥️ Gráfico de barras com a frequência dos 11 eixos-conceito (de `dna_inovacao.csv`), com rótulos traduzidos.
- 🧭 **Valor:** a "assinatura" do corpus — uma leitura em segundos de quais conceitos estruturam a amostra. Combinado aos filtros, permite comparar o DNA do recorte nacional com o internacional.

### 6.8. Regeneração do Estado da Arte

- 🖥️ Expander que documenta o comando `python scripts/gerar_estado_arte.py <modelo>` (pré-computação em lote, com progresso em `data/_progresso_estado_arte.txt`).
- 🧭 **Valor:** garante **transparência e atualização**: ao rodar o script após cada nova coleta, o estado da arte se reconstrói integralmente com os mesmos critérios — essencial para a reprodutibilidade do capítulo de revisão.

---

## 7. Aba 3 — "📚 Minha Biblioteca (PDFs)" (documentos locais)

Aba de análise dos **documentos em PDF** presentes em `meus_pdfs/` — teses, dissertações, relatórios institucionais (IFBA, Rede Federal), legislação etc. É onde o RAG e a auditoria decolonial atuam.

### 7.1. Matriz Epistemológica (expander)

- 🧭 Apresenta, em linguagem declarada, o quadro teórico Mimetismo × Inovação Situada e os seis eixos temáticos — é a **fundamentação visível** de todas as análises da ferramenta, útil para a escrita do capítulo metodológico.
- 🖥️ Implementação: texto em Markdown estático (sem computação).

### 7.2. Listagem de PDFs detectados

- 🖥️ Varre `meus_pdfs/` por `*.pdf` e lista os arquivos; funciona como prévia do acervo.
- 🧭 **Valor:** inventário visual do corpus local antes de qualquer processamento.

### 7.3. "Escanear e Indexar PDFs"

- 🖥️ Chama `indexar_pdfs` (`scripts/analisar_termos_pdfs.py`): carrega cada PDF com `PyPDFLoader`, atualiza o **cache de texto plano** (`data/pdf_texto_cache.json`), remove IDs antigos do arquivo e reindexa no **ChromaDB** com *chunks* e metadados de origem/página. Indexação **incremental** (reindexa só o que mudou).
- 🧭 **Valor:** é a etapa de "preparação do arquivo" — transforma PDFs em texto pesquisável e em espaço vetorial pesquisável por *sentido*.

### 7.4. "Localizar Termos nos PDFs" (busca literal)

- 🖥️ Busca **literal** (case-insensitive, normalização de acentos via NFKD), feita sobre as páginas em cache. Retorna, por documento: nº de ocorrências, páginas com ocorrência, **densidade** (ocorrências/página) e **trechos de contexto** (janela de ~120–180 caracteres ao redor do termo). Termos podem ser digitados livremente ou escolhidos em **dicionários temáticos** (Eixos nucleares; Mimetismo; Emancipatório; Código aberto), reutilizando o vocabulário de `sintese_estado_arte.py` (sem duplicação de código).
- Visualizações: gráfico "Top PDFs por ocorrência", **heatmap Termo × Documento** (quando ≥ 2 termos) e expansores de contexto por termo.
- 🧭 **Valor sociológico:** é a **análise de frequência e circulação de categorias** nos documentos. O pesquisador pode verificar, por exemplo, se a palavra "empreendedorismo" satura os relatórios da instituição enquanto "tecnologia social" aparece poucas vezes — um dado objetivo sobre os discursos que circulam. A listagem de páginas permite crítica de fontes com **localização verificável** (o trecho citado pode ser conferido no original — requisito de honestidade científica).

### 7.5. "Interpretação por IA"

- 🖥️ `interpretar_com_ia` monta um contexto enxuto (máx. ~6.000 caracteres, até 5 ocorrências/termo) a partir **apenas** dos trechos literais (sem embeddings), detecta a *lente* do termo comparando com os dicionários Mimetismo/Emancipatório e instrui o LLM a sintetizar: sentidos recorrentes, tensões entre documentos e relação com o recorte do projeto (inovação situada × mimetismo). Resultado adicionável ao Relatório do Dia.
- 🧭 **Valor:** converte a contagem fria em *interpretação qualitativa* — mas com uma proteção importante: a base da interpretação são os trechos reais, o que limita o espaço para invenções do modelo ("alucinações") e mantém o controle do pesquisador sobre o material.

### 7.6. "Auditoria Decolonial" (consulta à biblioteca local)

- 🖥️ Usuário formula uma pergunta; o sistema roda `v_db.similarity_search(pergunta, k=3)` (recupera os 3 trechos mais próximos *em sentido*), injeta-os no prompt `prompts/decolonial_pt.txt` (`{ctx}` e `{pergunta}`) e o LLM produz a auditoria seguindo diretrizes fixas: mimetismo × inovação situada; protagonismo dos IFs × metas externas; termos mercadológicos × emancipatórios; economia solidária; tecnologia social; governança; perspectivas emancipadoras; políticas públicas de inovação.
- 🧭 **Valor:** é o dispositivo central de **crítica documental**: em vez de ler cada relatório pedindo por palavra, o pesquisador pergunta um problema analítico ("Há indícios de dependência tecnológica nas parcerias do IFBA?") e o sistema responde apontando trechos. A resposta é hipótese fundamentada em evidência textual recuperável — o pesquisador valida no original. O resultado pode ser arquivado no Relatório do Dia.

> ⚙️ **Complemento do repositório:** `organizador_inteligente.py` organiza PDFs novos por instituição/região/UF, detectando nos metadados das 2 primeiras páginas a autoria institucional (catálogo integral da Rede Federal: IFBA→BA/Nordeste, IFMG→MG/Sudeste etc.) e o ano — automatização do arranjo documental que precede a análise.

---

## 8. Protocolo de uso recomendado (fluxo de pesquisa)

Para que o instrumento produza ciência defensável, sugere-se um fluxo em seis passos:

1. **Coleta auditável** — rodar os mineradores (`minerador_openalex`, `minerador_oai`) e registrar data/query na trilha (`_auditoria_mineracao.json`).
2. **Limpeza** — `limpeza_unificada.py` para deduplicar e padronizar (critérios documentados na saída).
3. **Estado da arte** — `gerar_estado_arte.py <modelo>` para pré-computar DNA, índices, redes e sínteses.
4. **Exploração macro (Aba 2)** — ler DNA, redes e síntese; fixar filtros (recorte, período, núcleo/contexto) e registrar as métricas.
5. **Análise micro (Aba 1)** — selecionar obras do núcleo; aplicar lentes; guardar fichamentos no Relatório do Dia.
6. **Auditoria documental local (Aba 3)** — indexar PDFs, localizar termos, aplicar a Auditoria Decolonial e consolidar o relatório do dia (PDF) → sincronizar ao Drive.

Em cada passo, **documentar**: modelo de LLM usado, filtros aplicados, versão da base e data. Esse metadado é o que permite ao cientista social sustentar a reprodutibilidade e ao cientista de dados auditar o *pipeline*.

---

## 9. Limitações metodológicas e cuidados

> O rigor de uma ferramenta não elimina a responsabilidade de quem a usa. Listamos as fronteiras conhecidas:

1. **LLMs podem errar (alucinação).** Fichamentos, lentes e sínteses são *propostas interpretativas*; toda citação forte deve retornar ao texto original. A ferramenta minimiza o risco ao usar trechos literais na interpretação (Aba 3), mas não o elimina.
2. **Proxies aproximativos.** O "recorte geográfico" usa o idioma como proxy, e o tema da obra deriva do dicionário de termos — ambos heurísticos. Um artigo em português escrito por instituição estrangeira ainda será classificado "nacional".
3. **Cobertura das fontes.** OpenAlex e OAI-PMH capturam o aberto; literatura comercial fechada só entra se minerada via Scopus/ScienceDirect. A ausência de uma obra não é ausência real — é ausência *na base*.
4. **Determinação dos dicionários.** Os termos de mimetismo/emancipação são escolhas teóricas; resultados de sentidos dependem dessa escolha (declarada e editável no código).
5. **Determinismo do limiar.** O critério "≥ 2 termos para entrar na base" é audível, mas afeta a composição da amostra; variações devem ser registradas como decisão metodológica.

---

## 10. Ética, soberania de dados e ciência aberta

- **Soberania:** LLMs e embeddings locais (Ollama) impedem o envio de documentos institucionais a servidores de terceiros — decisão relevante para documentos públicos sensíveis e para a independência do pesquisador (não depende de quota paga de API).
- **Transparência:** trilhas de auditoria (`_auditoria_mineracao.json`, `_progresso_estado_arte.txt`) registram explicitamente cada operação; toda contagem é replicável pelo mesmo código.
- **Ciência aberta:** o código é livre, as fontes são preferencialmente abertas (OpenAlex, OAI-PMH, licenças Creative Commons) e o corpus é trilhável — condições de um pesquisa reproduzível.
- **Crédito e licença:** a ferramenta integra a tese de doutorado de Jonatã França Bittencourt (IFBA–Campus Jacobina / PPGCS–UFBA), licenciada sob CC BY-NC-SA 4.0.

---

## 11. Glossário duplo

### 11.1. Do computacional para o social (para leitores das ciências sociais)

| Termo técnico | Tradução para a pesquisa social |
| :--- | :--- |
| CSV / DataFrame | Tabela de registros (cada linha = uma obra com metadados) |
| Pipeline | Etapas encadeadas do processamento (coletar → limpar → analisar) |
| Deduplicação | Remover registros repetidos de fontes distintas (mesmo artigo em duas bases) |
| Embedding / espaço vetorial | Vetor numérico que representa o "sentido" de um texto; proximidade vetorial ≈ proximidade de sentido |
| Similaridade de cosseno | Métrica de "quão próximos em sentido" estão dois textos |
| Chunk | Fatia de documento (ex.: 1–2 páginas) indexada individualmente |
| RAG | Recuperar trechos do corpus e passá-los ao LLM para responder com base neles |
| LLM / Ollama | Modelo de linguagem gratuito executado na própria máquina (sem nuvem) |
| Top-k (k=3) | Quantos trechos mais próximos são recuperados para montar a resposta |
| DataFrame filtrado / SelectSlider | Filtrar a tabela por intervalo — equivalente a selecionar casos na amostra |
| Matriz de co-ocorrência | Tabela de "quantas vezes dois conceitos aparecem juntos" |
| Núcleo × Contexto | Literatura central do campo × literatura mais periférica |
| Flag (binário) | Marcador 0/1 de presença de uma característica na obra |
| Cache / pré-computação | Resultado carregado de ante-mão para o painel ser rápido e reproduzível |
| FPDF / ABNT | Geração de PDF com citação formatada segundo NBR 6023 |

### 11.2. Do social para o computacional (para leitores das ciências de dados)

| Termo das ciências sociais | Equivalente operacional na ferramenta |
| :--- | :--- |
| Revisão de literatura | Base unificada + filtros da Aba 1 e síntese da Aba 2 |
| Crítica de fontes / citação verificável | Busca literal com página e trecho (Aba 3) |
| Análise de discurso | Lente sociológica (prompts) + análise de sentidos mimetismo/emancipação |
| Herança conceitual do campo | Mapa do DNA científico + co-ocorrência (Aba 2) |
| Categorias analíticas | Dicionários semânticos (eixos, mimetismo, emancipação) |
| Unidade de análise (obra) | Linha do CSV com `id_fonte` único |
| Amostragem (critérios de inclusão) | Filtros de relevância (≥2 termos, ano ≥ 2010, idioma, eixo, núcleo) |
| Viés de seleção | Cobertura por fonte (gráfico) e limites documentados das bases |
| Triangulação | Repetir análises com múltiplos modelos de LLM e múltiplas bases |
| Diário de campo / memória de pesquisa | Relatório do Dia (cesto) + registro de modelo/data + Drive |
| Validade ecológica | Verificação dos mapas/redes contra a leitura dos documentos originais |
| Ética na pesquisa | Soberania dos dados (LLMs locais), licenças, auditoria das trilhas |

---

## 12. Referências e artefatos

- **Código-fonte:** `app_principal.py` (dashboard), `scripts/` (mineradores, limpeza, estado da arte, análise de termos, sincronização), `organizador_inteligente.py`, `config_rag.py`.
- **Vocabulários e matriz teórica:** `prompts/decolonial_pt.txt`; dicionários em `scripts/sintese_estado_arte.py`.
- **Dados derivados:** `data/` (bases unificadas, índices, redes, sínteses, trilhas de auditoria).
- **Documentação associada:** `README.md`; `relatorio_dificuldades_tecnicas_RAG.md`; `_fontes auditáveis e os protocolos programáticos para extração em lote (bulk data mining).md`.
- **Padrões técnicos de referência metodológica:** *Manual de Oslo/Frascati* (OECD), *OpenAlex API docs*, *OAI-PMH* (Open Archives Initiative), *NBR 6023* (ABNT), boas práticas de *fair data* e reprodutibilidade computacional.

---

*Documento metodológico elaborado para fins de divulgação científica e fundamentação do capítulo metodológico da tese. Todas as descrições seguem a implementação corrente do código-fonte do repositório.*