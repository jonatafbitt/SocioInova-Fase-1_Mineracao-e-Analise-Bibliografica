import streamlit as st
import pandas as pd
import os
import ollama
import plotly.express as px
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from fpdf import FPDF
import base64
import json
import os
from pathlib import Path

# Caminho para prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"

def carregar_prompt(nome_arquivo):
    """Carrega um prompt do diretório prompts/."""
    prompt_file = PROMPTS_DIR / nome_arquivo
    if prompt_file.exists():
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""  # Retorna vazio se arquivo não existir

# --- 1. INICIALIZAÇÃO DO ESTADO DE SESSÃO ---
if 'cesto_analises' not in st.session_state:
    st.session_state.cesto_analises = []
if 'analise_persistente' not in st.session_state:
    st.session_state.analise_persistente = ""
if 'ultima_obra' not in st.session_state:
    st.session_state.ultima_obra = ""
if 'tipo_analise' not in st.session_state:
    st.session_state.tipo_analise = ""

# --- 2. CONFIGURAÇÕES DE CAMINHOS ---
PASTA_DATA = "data/producoes_mineradas.csv"
PASTA_PDFS = "meus_pdfs"
DB_DIR = "data/vector_db"
NOME_RELATORIO_LOCAL = "Relatorio_Consolidado_SocIA.pdf"

# --- 3. FUNÇÕES DE SUPORTE (LÓGICA E PDF) ---
def formatar_texto_nome(nome_str):
    """Formata nome de autor, tratando prefixos acadêmicos e casos edge case."""
    if not nome_str or str(nome_str).strip() == "":
        return "Desconhecido"
    
    nome_str = str(nome_str).strip()
    
    # Remover títulos acadêmicos comuns para extração do sobrenome
    prefixos_remover = ['Dr.', 'Prof.', 'Dra.', 'Profa.', 'Mg.', 'Dr. ', 'Prof. ', 'Dra. ', 'Profa. ']
    nome_limpo = nome_str
    for prefixo in prefixos_remover:
        nome_limpo = nome_limpo.replace(prefixo, '').strip()
    
    # Se ficou vazio após remover prefixo, usa original
    if not nome_limpo:
        nome_limpo = nome_str
    
    # Lógica de formatação ABNT
    if ',' in nome_limpo:
        # Já está no formato Sobrenome, Nome
        partes = nome_limpo.split(',', 1)
        sobrenome = partes[0].strip().upper()
        nome = partes[1].strip()
        return f"{sobrenome}, {nome}"
    else:
        # Formato Nome Sobrenome
        partes = nome_limpo.split(' ')
        if len(partes) >= 2:
            sobrenome = partes[-1].upper()
            nome = " ".join(partes[:-1])
            return f"{sobrenome}, {nome}"
        else:
            return nome_limpo.upper()

def formatar_abnt(autores, titulo, ano):
    try:
        if pd.isna(autores) or autores == "":
            autor_formatado = "AUTOR DESCONHECIDO"
        else:
            # Tenta usar o formatador robusto primeiro
            try:
                autor_formatado = formatar_texto_nome(autores)
            except:
                # Fallback para lógica original
                primeiro_autor = str(autores).split(';')[0].strip()
                if ',' in primeiro_autor:
                    autor_formatado = primeiro_autor.upper()
                else:
                    partes = primeiro_autor.split(' ')
                    sobrenome = partes[-1].upper()
                    nome = " ".join(partes[:-1])
                    autor_formatado = f"{sobrenome}, {nome}"
    except Exception as e:
        # Log do erro para debugging
        print(f"[Aviso] Erro no formatador ABNT: {e}")
        autor_formatado = "AUTOR, Nome"
    return f"{autor_formatado}. {titulo}. {ano}."

def gerar_pdf(titulo_obra, conteudo_analise, tipo_analise, referencia_abnt, modelo_ia):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Soc(IA) - Relatorio de Auditoria", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, txt="Referencia Bibliografica (ABNT):", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 8, txt=referencia_abnt.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"Tipo de Analise: {tipo_analise} | IA: {modelo_ia.upper()}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, txt=conteudo_analise.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def gerar_relatorio_consolidado(lista_analises):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, txt="Soc(IA) - Relatorio Consolidado de Pesquisa", ln=True, align='C')
    pdf.ln(10)
    for item in lista_analises:
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt=f"OBRA: {item['obra']}".encode('latin-1', 'replace').decode('latin-1'))
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(0, 7, txt=f"Ref: {item['referencia']}".encode('latin-1', 'replace').decode('latin-1'))
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, txt=f"Analise: {item['tipo']} | IA: {item['modelo'].upper()}", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, txt=item['conteudo'].encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFACE ---
st.set_page_config(page_title="Observatório de Inovação", layout="wide")

# Barra Lateral Consolidada
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2103/2103433.png", width=100)
st.sidebar.title("🔬 Soc(IA) - Gestão")

modelo_ia = st.sidebar.selectbox("Cérebro da IA (LLM):", ["phi3", "llama3", "mistral", "qwen2:1.5b"])

st.sidebar.divider()
if st.sidebar.button("☁️ Sincronizar com Google Drive"):
    st.sidebar.info("Iniciando upload de ativos e relatório...")
    # O script scripts/execucao_mestre.py será chamado
    os.system("python scripts/execucao_mestre.py")
    st.sidebar.success("Sincronização Concluída!")

st.sidebar.divider()
st.sidebar.subheader("📋 Relatório do Dia")
num_itens = len(st.session_state.cesto_analises)
st.sidebar.write(f"Itens no cesto: **{num_itens}**")

if num_itens > 0:
    pdf_total = gerar_relatorio_consolidado(st.session_state.cesto_analises)
    
    # SALVAMENTO AUTOMÁTICO PARA O DRIVE (Aqui está a revisão!)
    with open(NOME_RELATORIO_LOCAL, "wb") as f:
        f.write(pdf_total)
    
    st.sidebar.download_button("📥 Baixar Relatório Consolidado", data=pdf_total, file_name="Relatorio_SocIA.pdf", mime="application/pdf")
    
    if st.sidebar.button("🗑️ Limpar Cesto"):
        st.session_state.cesto_analises = []
        if os.path.exists(NOME_RELATORIO_LOCAL):
            os.remove(NOME_RELATORIO_LOCAL)
        st.rerun()

# Corpo Principal
st.title("🎓 Soc(IA) - Mineração sobre Sociologia da Inovação")
aba_web, aba_local = st.tabs(["🌐 Pesquisa OpenAlex", "📚 Minha Biblioteca (PDFs)"])

# --- ABA 1: WEB ---
with aba_web:
    if not os.path.exists(PASTA_DATA):
        st.error("Base de dados não encontrada. Rode o minerador primeiro.")
    else:
        df = pd.read_csv(PASTA_DATA)
        colunas_possiveis = {
            'ano': ['ano', 'publication_year', 'year'],
            'titulo': ['titulo', 'title', 'display_name'],
            'autores': ['autores', 'authors', 'author_names'],
            'resumo': ['resumo', 'abstract', 'description'],
            'idioma': ['idioma', 'language'],
            'eixo_tematico': ['eixo_tematico', 'eixo', 'tematico', 'eixos']
        }
        col_enc = {k: next((c for c in v if c in df.columns), None) for k, v in colunas_possiveis.items()}
        
        st.subheader("📊 Panorama da Produção")
        g1, g2, g3 = st.columns(3)
        with g1:
            if col_enc['ano']:
                df_ano = df[col_enc['ano']].value_counts().sort_index().reset_index()
                fig_ano = px.bar(df_ano, x=df_ano.columns[0], y=df_ano.columns[1], title="Evolução Temporal")
                st.plotly_chart(fig_ano, use_container_width=True)
        with g2:
            if col_enc['idioma']:
                df_id = df[col_enc['idioma']].value_counts().reset_index()
                df_id.columns = ['Idioma', 'Total']
                mapa_idiomas = {'en': 'Inglês', 'pt': 'Português', 'fr': 'Francês', 'es': 'Espanhol'}
                df_id = df_id[df_id['Idioma'].isin(mapa_idiomas.keys())]
                df_id['Idioma'] = df_id['Idioma'].map(mapa_idiomas)
                fig_id = px.bar(df_id, x='Idioma', y='Total', title="Idiomas", color='Idioma', color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_id, use_container_width=True)
        with g3:
            if os.path.exists("data/perfil_institucional.csv"):
                df_perfil = pd.read_csv("data/perfil_institucional.csv")
                fig_dna = px.bar(df_perfil, x='Frequência', y='Conceito', orientation='h', title="DNA Científico (Top 30)")
                st.plotly_chart(fig_dna, use_container_width=True)

        # Distribuição por eixo temático (se a coluna existir no banco minerado)
        if col_enc['eixo_tematico']:
            def quebrar_eixos(v):
                if pd.isna(v):
                    return []
                return [e.strip() for e in str(v).split(';') if e.strip()]
            lista_eixos = []
            for v in df[col_enc['eixo_tematico']]:
                lista_eixos.extend(quebrar_eixos(v))
            if lista_eixos:
                df_eixos = pd.DataFrame({'Eixo': lista_eixos})['Eixo'].value_counts().reset_index()
                df_eixos.columns = ['Eixo', 'Total']
                rotulos_eixos = {
                    'economia_solidaria': 'Economia Solidária',
                    'tecnologia_social': 'Tecnologia Social',
                    'inovacao_politicas_publicas': 'Inovação em Políticas Públicas',
                    'governanca_inovacao': 'Governança da Inovação',
                    'emancipacao_inovacao': 'Inovação Emancipadora',
                    'inovacao_instituto_publico': 'Inovação em Instituições Públicas',
                    'geral': 'Geral'
                }
                df_eixos['Eixo'] = df_eixos['Eixo'].map(rotulos_eixos).fillna(df_eixos['Eixo'])
                fig_eixos = px.bar(df_eixos, x='Eixo', y='Total', title="Distribuição por Eixo Temático (Lente Sociológica)", color='Eixo')
                st.plotly_chart(fig_eixos, use_container_width=True)

        st.divider()
        
        # Validação de schema robusta
        if not any(col_enc.values()):
            st.error("⚠️ Não foi possível identificar as colunas esperadas no CSV.")
            st.info("Verifique se o arquivo 'data/producoes_mineradas.csv' contém as colunas esperadas (título, autores, ano, idioma, resumo).")
            st.stop()
        
        col_tit = col_enc['titulo'] if col_enc['titulo'] else df.columns[0]
        busca = st.text_input(f"🔍 Filtrar obras por título:")
        df_filtrado = df[df[col_tit].str.contains(busca, case=False, na=False)] if busca else df

        # Filtro por eixo temático (Lente Sociológica da Inovação)
        if col_enc['eixo_tematico']:
            opcoes_eixo = ["Todos"] + sorted(set(
                e for v in df[col_enc['eixo_tematico']] if pd.notna(v)
                for e in str(v).split(';') if e.strip()
            ))
            eixo_sel = st.selectbox("🧭 Filtrar por Eixo Temático (Lente Sociológica):", opcoes_eixo)
            if eixo_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado[col_enc['eixo_tematico']].str.contains(eixo_sel, na=False)]

        col_visiveis = [v for k, v in col_enc.items() if v and k != 'resumo']
        st.dataframe(df_filtrado[col_visiveis], use_container_width=True)

        st.header("🤖 Inteligência Analítica")
        selecao = st.selectbox("Selecione uma obra para análise profunda:", df_filtrado[col_tit].tolist())

        if selecao != st.session_state.ultima_obra:
            st.session_state.analise_persistente = ""
            st.session_state.ultima_obra = selecao

        if selecao:
            art = df_filtrado[df_filtrado[col_tit] == selecao].iloc[0]
            ref_abnt = formatar_abnt(art[col_enc['autores']], art[col_enc['titulo']], art[col_enc['ano']])
            st.code(ref_abnt)
            
            if col_enc['resumo'] and pd.notna(art[col_enc['resumo']]):
                st.markdown("**🧠 Modos de Análise — Lente Sociológica da Inovação:**")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🚀 Fichamento Ágil"):
                        with st.spinner("Analisando..."):
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': f"Fichamento estruturado: {art[col_enc['resumo']]}"}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Fichamento Estruturado"
                    if st.button("🔍 Analisar Tendência"):
                        with st.spinner("Avaliando..."):
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': f"Analise o viés: {art[col_enc['resumo']]}"}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Análise de Tendência"
                with c2:
                    if st.button("🌍 Lente Economia Solidária"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra a seguir pela lente da ECONOMIA SOLIDÁRIA.
Foque em: cooperativismo, autogestão, trabalho associado, relação com a tecnologia social e se a obra dialoga com formas não-capitalistas de produção e inovação.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Economia Solidária"
                    if st.button("📱 Lente Tecnologia Social"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra pela lente da TECNOLOGIA SOCIAL.
Foque em: tecnologias apropriadas, protagonismo comunitário, adequação sociotécnica, soluções para demandas locais e o contraste com a transferência de tecnologia de cima para baixo.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Tecnologia Social"

                c3, c4 = st.columns(2)
                with c3:
                    if st.button("🏛️ Lente Governança da Inovação"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra pela lente da GOVERNANÇA DA INOVAÇÃO.
Foque em: coordenação entre atores (Estado, universidades, sociedade civil), arranjos institucionais de políticas públicas de inovação, participação social e accountability na gestão da inovação.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Governança da Inovação"
                    if st.button("💡 Lente Inovação Emancipadora"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra pela lente das PERSPECTIVAS EMANCIPADORAS DA INOVAÇÃO.
Foque em: autonomia científica e tecnológica, decolonialidade, soberania tecnológica, ruptura com a dependência do Norte Global e protagonismo dos territórios e comunidades locais.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Inovação Emancipadora"
                with c4:
                    if st.button("🎓 Lente Instituições Públicas"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra pela lente da INOVAÇÃO EM INSTITUIÇÕES PÚBLICAS.
Foque em: políticas de inovação na Rede Federal de Educação Profissional, Técnica e Tecnológica, extensão tecnológica, papel dos Institutos Federais no desenvolvimento local e a interface entre ensino, pesquisa e extensão.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Instituições Públicas"
                    if st.button("🏭 Lente Inovação em Políticas Públicas"):
                        with st.spinner("Aplicando lente..."):
                            prompt_lente = f"""Como Sociólogo(a) da Inovação, analise a obra pela lente da INOVAÇÃO EM POLÍTICAS PÚBLICAS.
Foque em: formulação e implementação de políticas de inovação, inovação no setor público, instrumentos de política (financiamento, marcos legais), capacidades estatais e efeitos societais das políticas de inovação.
OBRA: {art[col_enc['resumo']]}"""
                            resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_lente}])
                            st.session_state.analise_persistente = resp['message']['content']
                            st.session_state.tipo_analise = "Lente Inovação em Políticas Públicas"

                if col_enc['eixo_tematico'] and pd.notna(art[col_enc['eixo_tematico']]):
                    st.caption(f"Eixos temáticos associados: {art[col_enc['eixo_tematico']]}")
                elif col_enc['eixo_tematico']:
                    st.caption("Eixos temáticos associados: geral")

                if st.session_state.analise_persistente:
                    st.divider()
                    st.markdown(st.session_state.analise_persistente)
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        pdf_b = gerar_pdf(selecao, st.session_state.analise_persistente, st.session_state.tipo_analise, ref_abnt, modelo_ia)
                        st.download_button("📥 Baixar PDF Individual", data=pdf_b, file_name=f"Analise_{art[col_enc['ano']]}.pdf")
                    with col_d2:
                        if st.button("➕ Adicionar ao Relatório do Dia"):
                            st.session_state.cesto_analises.append({
                                "obra": selecao, "referencia": ref_abnt, "tipo": st.session_state.tipo_analise,
                                "modelo": modelo_ia, "conteudo": st.session_state.analise_persistente
                            })
                            st.toast("Adicionado ao relatório!", icon="✅")

# --- ABA 2: LOCAL (REVISADA E CORRETA) ---
with aba_local:
    st.subheader("📚 Biblioteca Local (PDFs)")

  # --- QUADRO TEÓRICO DE APOIO (Legenda Metodológica) ---
    with st.expander("📚 Matriz Epistemológica: Entenda os Critérios da Auditoria"):
        st.markdown("""
        ### Matriz de Análise: Inovação por Mimetismo vs. Inovação Situada
        Esta matriz orienta a Inteligência Analítica do Soc(IA) na classificação dos trabalhos minerados.
        A análise está aberta a toda a **Rede Federal de Educação Profissional, Científica e Tecnológica**.
        
        | Dimensão Analítica | Inovação por Mimetismo (Dependente) | Inovação Situada (Emancipatória) |
        | :--- | :--- | :--- |
        | **Referencial Geopolítico** | Norte Global (Vale do Silício, Modelos Europeus). | Território Local (Jacobina, Bahia, Contexto Regional). |
        | **Linguagem Predominante** | Eficiência, competitividade, transferência de tecnologia. | Soberania, tecnologias sociais, emancipação, bem comum. |
        | **Papel dos IF's** | Executores de agendas externas e metas mercadológicas. | Protagonistas na solução de demandas sociais locais. |
        | **Vetor de Desenvolvimento** | Top-down (Modelos tecnológicos importados). | Bottom-up (Arranjos produtivos e culturais locais). |
        | **Relação de Poder** | Reprodução de hierarquias de dependência técnica. | Ruptura decolonial e busca por autonomia científica. |
        
        ### Eixos Temáticos da Mineração (Lente Sociológica da Inovação)
        1. **Economia Solidária** — cooperativismo, autogestão, trabalho associado.
        2. **Tecnologia Social** — tecnologias apropriadas e protagonismo comunitário.
        3. **Inovação em Políticas Públicas** — formulação e implementação de políticas de inovação.
        4. **Governança da Inovação** — coordenação entre Estado, academia e sociedade civil.
        5. **Perspectivas Emancipadoras** — decolonialidade, soberania tecnológica e autonomia.
        6. **Inovação em Instituições Públicas** — Rede Federal de Educação e extensão tecnológica.
        
        *Quadro elaborado para fundamentação do capítulo metodológico da tese.*
        """)  
 # --- LISTAGEM PRÉVIA DE ARQUIVOS (NOVIDADE) ---
    if os.path.exists(PASTA_PDFS):
        arquivos_pdf = [f for f in os.listdir(PASTA_PDFS) if f.endswith(".pdf")]
        if arquivos_pdf:
            with st.expander(f"📂 Ver {len(arquivos_pdf)} PDFs detectados na pasta"):
                for a in arquivos_pdf:
                    st.write(f"- {a}")
        else:
            st.warning("Nenhum PDF encontrado na pasta 'meus_pdfs'.")

    # Inicializa variáveis de memória específicas para a Aba Local
    if 'analise_local_persistente' not in st.session_state:
        st.session_state.analise_local_persistente = ""

    arquivos_pdf = [f for f in os.listdir(PASTA_PDFS) if f.endswith(".pdf")] if os.path.exists(PASTA_PDFS) else []
    
    if st.button("🔄 Escanear e Indexar PDFs"):
        if arquivos_pdf:
            with st.spinner("Indexando..."):
                documentos = []
                for arq in arquivos_pdf:
                    loader = PyPDFLoader(os.path.join(PASTA_PDFS, arq))
                    documentos.extend(loader.load())
                splits = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200).split_documents(documentos)
                Chroma.from_documents(documents=splits, embedding=OllamaEmbeddings(model=modelo_ia), persist_directory=DB_DIR)
                st.success("✅ Biblioteca pronta!")
    
    pergunta_local = st.text_input("🧐 Analisar PDFs locais com Lente Decolonial:")
    
    if pergunta_local and os.path.exists(DB_DIR):
        # Só gera uma nova análise se a pergunta mudar
        if st.button("🔍 Executar Auditoria Decolonial"):
            with st.spinner("Realizando Auditoria..."):
                v_db = Chroma(persist_directory=DB_DIR, embedding_function=OllamaEmbeddings(model=modelo_ia))
                docs = v_db.similarity_search(pergunta_local, k=3)
                ctx = "\n\n".join([d.page_content for d in docs])
                
                # Carrega prompt estruturado de arquivos externos
                prompt_base = carregar_prompt("decolonial_pt.txt")
                prompt_decolonial = prompt_base.replace("{ctx}", ctx).replace("{pergunta}", pergunta_local)
                
                resp = ollama.chat(model=modelo_ia, messages=[{'role': 'user', 'content': prompt_decolonial}])
                st.session_state.analise_local_persistente = resp['message']['content']

    # Exibe a análise se ela existir na memória
    if st.session_state.analise_local_persistente:
        st.subheader("🕵️ Resultado da Auditoria Decolonial")
        st.markdown(st.session_state.analise_local_persistente)

        if st.button("➕ Adicionar Auditoria ao Relatório do Dia"):
            st.session_state.cesto_analises.append({
                "obra": "Auditoria de Documentos Locais (IFBA)",
                "referencia": "Biblioteca Interna",
                "tipo": "Auditoria Decolonial",
                "modelo": modelo_ia,
                "conteudo": st.session_state.analise_local_persistente
            })
            st.toast("✅ Auditoria salva no cesto!")