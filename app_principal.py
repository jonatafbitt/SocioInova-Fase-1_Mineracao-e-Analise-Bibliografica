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

# Módulo de síntese do estado da arte (pré-processado em scripts/gerar_estado_arte.py)
import sys
scripts_dir = Path(__file__).parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
import sintese_estado_arte as sea
import analisar_termos_pdfs as atp

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
NOME_RELATORIO_LOCAL = "Relatorio_Consolidado_SocioInova.pdf"

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
    pdf.cell(200, 10, txt="SocioInova - Relatorio de Auditoria", ln=True, align='C')
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
    pdf.cell(200, 10, txt="SocioInova - Relatorio Consolidado de Pesquisa", ln=True, align='C')
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
st.sidebar.title("🔬 SocioInova - Gestão")

opcoes_modelo = [
    ("qwen2:1.5b", "qwen2:1.5b — (multilíngue, leve; padrão da síntese)"),
    ("phi3", "phi3 — (rápido, tarefas gerais)"),
    ("llama3", "llama3 — (melhor redação acadêmica)"),
    ("mistral", "mistral — (auditoria de viés teórico)"),
    ("qwen3:1.7b", "qwen3:1.7b — (nova geração, mais capaz que qwen2)"),
    ("qwen3:4b", "qwen3:4b — (mais robusto, exige mais memória)"),
    ("gemma3:4b", "gemma3:4b — (multimodal, contexto maior)"),
    ("phi4-mini", "phi4-mini — (compacto e capaz)"),
]
mapa_modelo = {k: rot for k, rot in opcoes_modelo}
modelo_ia = st.sidebar.selectbox("Cérebro da IA (LLM):", [k for k, _ in opcoes_modelo],
                                 format_func=lambda k: mapa_modelo[k])

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
    
    st.sidebar.download_button("📥 Baixar Relatório Consolidado", data=pdf_total, file_name="Relatorio_SocioInova.pdf", mime="application/pdf")
    
    if st.sidebar.button("🗑️ Limpar Cesto"):
        st.session_state.cesto_analises = []
        if os.path.exists(NOME_RELATORIO_LOCAL):
            os.remove(NOME_RELATORIO_LOCAL)
        st.rerun()

# Corpo Principal
st.title("🎓 SocioInova Fase 1 - Mineração e Análise Bibliográfica")
aba_web, aba_estado, aba_local = st.tabs(["🌐 Pesquisa OpenAlex", "🗺️ Estado da Arte da Inovação", "📚 Minha Biblioteca (PDFs)"])

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
            'eixo_tematico': ['eixo_tematico', 'eixo', 'tematico', 'eixos'],
            'fonte': ['fonte', 'source', 'base']
        }
        col_enc = {k: next((c for c in v if c in df.columns), None) for k, v in colunas_possiveis.items()}

        # --- SELETOR MULTI-FONTE + COBERTURA POR FONTE ---
        if col_enc['fonte']:
            fontes_disponiveis = sorted(df[col_enc['fonte']].dropna().unique())
            nomes_fonte = {
                'OpenAlex': 'OpenAlex',
                'producoes_openalex': 'OpenAlex',
                'openalex': 'OpenAlex',
                'producoes_oai': 'OAI-PMH / Repositórios',
                'Lume_UFRGS': 'Lume UFRGS',
            }
            rotulo_fontes = {f: nomes_fonte.get(str(f), str(f)) for f in fontes_disponiveis}
            fonte_sel = st.selectbox("🗂️ Fonte da base:", ["Todas"] + fontes_disponiveis,
                                     format_func=lambda x: rotulo_fontes.get(str(x), str(x)))
            if fonte_sel != "Todas":
                df = df[df[col_enc['fonte']].astype(str) == str(fonte_sel)]

            with st.expander("📈 Cobertura por Fonte", expanded=False):
                df_cov = df[col_enc['fonte']].value_counts().reset_index()
                df_cov.columns = ['Fonte', 'Total']
                df_cov['Fonte'] = df_cov['Fonte'].map(rotulo_fontes)
                fig_cov = px.bar(df_cov, x='Fonte', y='Total', title="Registros por Fonte",
                                 color='Fonte', color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig_cov, use_container_width=True)
                st.caption("Fonte de origem de cada registro (OpenAlex, OAI-PMH/repositórios etc.).")
        else:
            st.caption("⚠️ Coluna de fonte não detectada na base. Considere rodar a limpeza unificada.")

        # --- FILTRO TEMPORAL (opcional) ---
        if col_enc['ano']:
            anos = sorted(df[col_enc['ano']].dropna().astype(int).unique())
            if len(anos) > 1:
                cmin, cmax = int(anos[0]), int(anos[-1])
                sel_min, sel_max = st.select_slider(
                    "📅 Recorte temporal:",
                    options=anos,
                    value=(cmin, cmax),
                )
                df = df[(df[col_enc['ano']] >= sel_min) & (df[col_enc['ano']] <= sel_max)]

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

# --- ABA 2: ESTADO DA ARTE DA INOVAÇÃO ---
with aba_estado:
    st.subheader("🗺️ Estado da Arte da Inovação")
    st.caption("Leitura de conjunto (macro) do campo a partir do corpus minerado: gramática nacional × internacional e os lugares, usos e sentidos do recorte social, de código aberto e emancipador.")

    INDICES = "data/indices_estado_arte.csv"
    DNA = "data/dna_inovacao.csv"
    COOC = "data/coocorrencia_estado_arte.json"
    SINT = "data/_sintese_estado_arte.json"
    SENT = "data/_sintese_sentidos.txt"

    if not os.path.exists(INDICES) or not os.path.exists(DNA):
        st.warning("Índices do estado da arte não encontrados. Rode: `python scripts/gerar_estado_arte.py`")
        st.stop()

    ind = pd.read_csv(INDICES)
    ind = ind.fillna("")
    ind['ano'] = pd.to_numeric(ind['ano'], errors='coerce')

    # --- Filtros rápidos (não usam IA — instantâneos) ---
    c_f1, c_f2, c_f3 = st.columns(3)
    with c_f1:
        rec_sel = st.multiselect("Recorte geográfico:", ["nacional", "internacional"],
                                 default=["nacional", "internacional"])
    with c_f2:
        anos_disp = sorted(ind['ano'].dropna().astype(int).unique().tolist())
        if len(anos_disp) > 1:
            faixa = st.select_slider("Período:", options=anos_disp,
                                     value=(int(anos_disp[0]), int(anos_disp[-1])))
            ind = ind[(ind['ano'] >= faixa[0]) & (ind['ano'] <= faixa[1])]
    with c_f3:
        cls_sel = st.multiselect("Classe de relevância:", ["nucleo", "contexto"],
                                 default=["nucleo"])
    ind = ind[ind['recorte_geo'].isin(rec_sel)]
    ind = ind[ind['nucleo_contexto'].isin(cls_sel)]

    # --- Métricas-resumo ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Registros no recorte", len(ind))
    m2.metric("Núcleo (lente forte)", int((ind['nucleo_contexto'] == 'nucleo').sum()))
    m3.metric("Recorte social", int(ind['flag_social'].sum()))
    m4.metric("Emancipatório", int(ind['flag_emancipatorio'].sum()))

    # --- 1. SÍNTESE GLOBAL (macro) ---
    st.divider()
    st.markdown("### 1) Síntese Global — a gramática do campo")
    if os.path.exists(SINT):
        with open(SINT, encoding="utf-8") as f:
            cache_sint = json.load(f)
        # pega a primeira entrada do cache (pré-computada)
        payload = next(iter(cache_sint.values()), None)
        if payload and "recortes" in payload:
            rot_geo = {"nacional": "🇧🇷 Nacional", "internacional": "🌎 Internacional"}
            tab_n, tab_i = st.tabs([rot_geo.get("nacional", "Nacional"), rot_geo.get("internacional", "Internacional")])
            with tab_n:
                st.markdown(payload["recortes"].get("nacional", "_indisponível_"))
            with tab_i:
                st.markdown(payload["recortes"].get("internacional", "_indisponível_"))
            st.caption(f"Modelo: {payload.get('modelo')} · gerado em {payload.get('timestamp')} · pré-computado em scripts/gerar_estado_arte.py")
        else:
            st.info("Síntese ainda não gerada. Rode `python scripts/gerar_estado_arte.py`.")
    else:
        st.info("Síntese não encontrada. Rode `python scripts/gerar_estado_arte.py` para gerar o estado da arte automaticamente (pode levar alguns minutos).")

    # --- 2. REDE DE CO-OCORRÊNCIA ---
    st.divider()
    st.markdown("### 2) Rede de Co-ocorrência de Conceitos")
    st.caption("Nós = termos nucleares da gramática do campo; arestas = conceitos que aparecem juntos nos mesmos registros.")
    if os.path.exists(COOC):
        with open(COOC, encoding="utf-8") as f:
            dados_cooc = json.load(f)
        nos = dados_cooc.get("nos", [])
        arestas = dados_cooc.get("arestas", [])
        if nos and arestas:
            import math
            import plotly.graph_objects as go
            df_no = pd.DataFrame(nos)
            df_arest = pd.DataFrame(arestas)
            # Posicionamento circular simples (sem dependência externa)
            n_nodes = len(df_no)
            pos = {}
            for idx, (_, node) in enumerate(df_no.iterrows()):
                ang = 2 * math.pi * idx / n_nodes if n_nodes else 0
                pos[node["id"]] = (math.cos(ang), math.sin(ang))
            edge_trace_x, edge_trace_y, edge_weights = [], [], []
            for _, a in df_arest.iterrows():
                u, v = a["source"], a["target"]
                if u not in pos or v not in pos:
                    continue
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_trace_x += [x0, x1, None]
                edge_trace_y += [y0, y1, None]
                edge_weights.append(float(a.get("weight", 1)))
            node_x, node_y, node_freq, node_labels = [], [], [], []
            for _, node in df_no.iterrows():
                x, y = pos[node["id"]]
                node_x.append(x)
                node_y.append(y)
                node_freq.append(float(node["freq"]))
                node_labels.append(node["label"])
            max_f = max(node_freq) if node_freq else 1
            edge_trace = go.Scatter(x=edge_trace_x, y=edge_trace_y, mode="lines",
                                    line=dict(width=2, color="#888"),
                                    hoverinfo="none")
            node_trace = go.Scatter(x=node_x, y=node_y, mode="markers+text", text=node_labels,
                                    textposition="top center",
                                    marker=dict(size=[20 + (f / max_f) * 60 for f in node_freq],
                                                color="#2255aa", line_width=2, line_color="#fff"),
                                    hovertext=[lbl for lbl in node_labels], hoverinfo="text")
            fig_cooc = go.Figure(data=[edge_trace, node_trace],
                                 layout=go.Layout(title="Co-ocorrência de conceitos", showlegend=False,
                                                  hovermode="closest",
                                                  xaxis=dict(showgrid=False, zeroline=False, visible=False),
                                                  yaxis=dict(showgrid=False, zeroline=False, visible=False),
                                                  margin=dict(l=20, r=20, t=40, b=20)))
            st.plotly_chart(fig_cooc, use_container_width=True)
            with st.expander("🔢 Matriz (top arestas)"):
                df_arest_sorted = df_arest.sort_values("weight", ascending=False).head(20)
                st.dataframe(df_arest_sorted, use_container_width=True)
        else:
            st.info("Matriz de co-ocorrência vazia (recorte pequeno).")
    else:
        st.info("Matriz não encontrada. Rode `python scripts/gerar_estado_arte.py`.")

    # --- 3. MAPA DOS ESPAÇOS PÚBLICOS ---
    st.divider()
    st.markdown("### 3) Mapa dos Espaços Públicos de Inovação")
    st.caption("Quem produz e onde: instituições/veículos de produção e distribuição territorial (UF) das fontes de direito público.")
    # Top instituições detectadas nos resumos + veículos
    coli = ind[ind['instituicoes'] != ""]
    if not coli.empty:
        todas_inst = []
        for vals in coli['instituicoes']:
            todas_inst += [v.strip() for v in str(vals).split(";") if v.strip()]
        df_inst = pd.Series(todas_inst).value_counts().head(15).reset_index()
        df_inst.columns = ['Instituição', 'Registros']
        fig_inst = px.bar(df_inst, x='Registros', y='Instituição', orientation='h',
                          title="Top 15 Instituições citadas nos registros", color='Registros',
                          color_continuous_scale='Blues')
        st.plotly_chart(fig_inst, use_container_width=True)
    else:
        st.caption("Nenhuma instituição detectada nos resumos.")

    # Mapa das UF (a partir das fontes)
    UF_POR_FONTE = {
        "IFBA": "BA", "IFMG": "MG", "CEFETMG": "MG", "IFRS": "RS", "Lume_UFRGS": "RS",
        "IFSC": "SC", "IFAM": "AM", "IFPB": "PB", "IFPE": "PE", "UFOP": "MG",
        "UFCA": "CE", "UFSCar": "SP", "IFRR": "RR", "IFSP": "SP", "IFB": "DF",
        "IFMS": "MS",
    }
    df_br = ind[ind['fonte'].isin(UF_POR_FONTE.keys())].copy()
    df_br['uf'] = df_br['fonte'].map(UF_POR_FONTE)
    if not df_br.empty:
        contagem_uf = df_br['uf'].value_counts().reset_index()
        contagem_uf.columns = ['UF', 'Registros']
        ordem_uf = contagem_uf.sort_values('Registros', ascending=False)['UF'].tolist()
        fig_uf = px.bar(contagem_uf, x='UF', y='Registros', category_orders={'UF': ordem_uf},
                        title='Produção por UF (fontes públicas OAI)',
                        color='Registros', color_continuous_scale='Blues')
        st.plotly_chart(fig_uf, use_container_width=True)
        st.caption("Distribuição por unidade federativa das fontes de direito público (IFs/universidades).")

    # --- 4. ANÁLISE DE SENTIDOS (SEMIÓTICA) ---
    st.divider()
    st.markdown("### 4) Análise de Sentidos — social, código aberto e emancipação")
    st.caption("Leitura semiótica: como o recorte social/aberto/emancipador é usado — performático-mercadológico (mimetismo) vs. emancipatório-situado.")
    k1, k2, k3 = st.columns(3)
    k1.metric("Código aberto", int(ind['flag_codigo_aberto'].sum()))
    k2.metric("Sentido emancipatório (ocorrências)", int(ind['n_sentidos_emancipacao'].sum()))
    k3.metric("Sentido mimetista (ocorrências)", int(ind['n_sentidos_mimetismo'].sum()))
    if os.path.exists(SENT):
        with open(SENT, encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("Síntese de sentidos não encontrada. Rode `python scripts/gerar_estado_arte.py`.")

    # --- DNA Científico do recorte ---
    st.divider()
    st.markdown("### 🧬 DNA Científico do Recorte")
    if os.path.exists(DNA):
        df_dna = pd.read_csv(DNA)
        rotulos_dna = {
            "inovacao": "Inovação", "economia_solidaria": "Economia Solidária",
            "governanca": "Governança", "politicas_publicas": "Políticas Públicas",
            "territorio_desenvolvimento_local": "Território / Desenvolvimento Local",
            "institutos_federais": "Institutos Federais", "patente": "Patente",
            "emancipacao": "Emancipação", "tecnologia_social": "Tecnologia Social",
            "transferencia": "Transferência de Tecnologia", "propriedade_intelectual": "Propriedade Intelectual",
        }
        df_dna['Conceito'] = df_dna['Conceito'].map(lambda x: rotulos_dna.get(str(x), str(x)))
        fig_dna = px.bar(df_dna, x='Frequência', y='Conceito', orientation='h',
                         title="Assinatura conceitual do corpus (termos nucleares)",
                         color='Frequência', color_continuous_scale='Blues')
        st.plotly_chart(fig_dna, use_container_width=True)

    with st.expander("ℹ️ Regenerar o Estado da Arte (IA automática)"):
        st.markdown(
            "A síntese global e a leitura de sentidos são **pré-computadas** (para agilidade) "
            "pelo script abaixo. Processa o corpus em lote com a IA local e pode levar alguns "
            "minutos. Para atualizar, rode no terminal:\n\n"
            "```\npython scripts/gerar_estado_arte.py <modelo>\n```\n"
            "Ex.: `python scripts/gerar_estado_arte.py qwen2:1.5b`")

# --- ABA 3: LOCAL (REVISADA E CORRETA) ---
with aba_local:
    st.subheader("📚 Biblioteca Local (PDFs)")

  # --- QUADRO TEÓRICO DE APOIO (Legenda Metodológica) ---
    with st.expander("📚 Matriz Epistemológica: Entenda os Critérios da Auditoria"):
        st.markdown("""
        ### Matriz de Análise: Inovação por Mimetismo vs. Inovação Situada
        Esta matriz orienta a Inteligência Analítica do SocioInova na classificação dos trabalhos minerados.
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
                # Indexação incremental (com metadados de origem/página) + cache de texto plano
                v_db = Chroma(persist_directory=DB_DIR,
                              embedding_function=OllamaEmbeddings(model="nomic-embed-text"))
                processados = atp.indexar_pdfs(v_db, pasta_pdfs=PASTA_PDFS)
                st.success(f"✅ Biblioteca pronta! {len(processados)} PDF(s) indexado(s).")
        else:
            st.warning("Nenhum PDF encontrado para indexar.")

    # --- ANÁLISE DE TERMOS (Iteração 1): localização literal nos PDFs ---
    st.divider()
    st.markdown("#### 🔎 Localizar Termos nos PDFs")
    with st.expander("ℹ️ Como funciona"):
        st.markdown(
            "Busca **literal** (case-insensitive, ignorando acentos) nos textos dos PDFs "
            "já escaneados. Retorna quantas vezes o termo aparece em cada documento, em quais "
            "páginas e os trechos de contexto. Use campo livre ou selecione um dicionário temático.")

    col_atp_termos, col_atp_dict = st.columns([3, 2])
    with col_atp_termos:
        termos_livres = st.text_input("Termos (separados por vírgula):",
                                      placeholder="ex.: inovação, decolonial, economia solidária")
    with col_atp_dict:
        opcoes_dict = {
            "Nenhum (só campo livre)": None,
            "Eixos nucleares (todos)": sea.TERMOS_NUCLEARES,
            "Mimetismo": sea.TERMOS_MIMETISMO,
            "Emancipatório": sea.TERMOS_EMANCIPA,
            "Código aberto / ciência aberta": sea.TERMOS_CODIGO_ABERTO,
        }
        rotulo_dict = st.selectbox("Ou use um dicionário temático:", list(opcoes_dict.keys()))
    selecionar_todos_dict = st.checkbox("Selecionar todos os termos do dicionário escolhido",
                                        value=False, key="atp_todos_dict")

    termos = [t.strip() for t in termos_livres.split(",") if t.strip()] if termos_livres else []
    dicionario = opcoes_dict.get(rotulo_dict)
    if dicionario:
        if isinstance(dicionario, dict):  # eixos nucleares -> expande valores em uma lista
            termos_dict = [t for lista in dicionario.values() for t in lista]
        else:
            termos_dict = list(dicionario)
        if selecionar_todos_dict:
            termos = list(dict.fromkeys(termos + termos_dict))
        else:
            termos_selecionados = st.multiselect(
                "Escolher termos do dicionário:", termos_dict,
                key="atp_multiselect_dict")
            termos = list(dict.fromkeys(termos + termos_selecionados))

    if st.button("🔍 Localizar Termos", type="primary"):
        if not termos:
            st.warning("Digite termo(s) ou selecione itens do dicionário temático.")
        else:
            with st.spinner("Localizando termos nos PDFs..."):
                resultado = atp.localizar_termos(termos, pasta_pdfs=PASTA_PDFS)

            termos_achados = [t for t in termos if resultado["por_termo"].get(t)]
            if not termos_achados:
                st.warning("Nenhuma ocorrência encontrada para os termos informados.")
            else:
                st.session_state["atp_resultado"] = resultado
                st.session_state["atp_termos"] = termos_achados

    if "atp_resultado" in st.session_state:
        resultado = st.session_state["atp_resultado"]
        termos_achados = st.session_state.get("atp_termos", [])
        tabela = atp.construir_tabela(resultado)

        st.markdown(f"#### Resultado — {len(tabela)} documento(s) com ocorrências")
        st.dataframe(pd.DataFrame(tabela), use_container_width=True)

        # Gráfico: Top PDFs por ocorrências
        if tabela:
            df_plot = pd.DataFrame(tabela)[["PDF", "Ocorrências"]].head(15)
            fig_rank = px.bar(df_plot, x="Ocorrências", y="PDF", orientation="h",
                              title="Top PDFs por ocorrência do(s) termo(s)",
                              color="Ocorrências", color_continuous_scale="Blues")
            fig_rank.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_rank, use_container_width=True)

        # Heatmap termo x documento (quando há 2+ termos)
        if len(termos_achados) >= 2:
            df_heat = pd.DataFrame([
                {**{"PDF": arq}, **{t: info["contagens"].get(t, 0) for t in termos_achados}}
                for arq, info in resultado["por_arquivo"].items()
            ])
            df_heat = df_heat[df_heat[[t for t in termos_achados]].sum(axis=1) > 0]
            if not df_heat.empty:
                fig_heat = px.imshow(df_heat.set_index("PDF"), labels=dict(x="Termo", y="PDF", color="Ocorrências"),
                                     title="Matriz Termo × Documento", color_continuous_scale="YlGnBu")
                st.plotly_chart(fig_heat, use_container_width=True)

        # Trechos de contexto por termo
        for t in termos_achados:
            ocorrencias = resultado["por_termo"].get(t, [])
            with st.expander(f"📄 Termo «{t}» — {len(ocorrencias)} ocorrência(s)"):
                for oc in ocorrencias[:30]:
                    st.markdown(f"**{oc['arquivo']}** — pág. {oc['pagina']}")
                    st.markdown(f"> {oc['trecho']}")
                if len(ocorrencias) > 30:
                    st.caption(f"Mostrando 30 de {len(ocorrencias)} ocorrências.")

        # --- Camada de interpretação por IA (Iteração 2) ---
        st.divider()
        st.markdown("#### 🤖 Interpretação por IA")
        st.caption("O modelo lê os trechos encontrados e sintetiza como o(s) termo(s) são "
                   "mobilizados na biblioteca. Baseia-se apenas na busca literal, sem usar embeddings.")
        if st.button("✨ Gerar interpretação com IA", type="primary"):
            with st.spinner("IA lendo os trechos e sintetizando..."):
                interpretacao = atp.interpretar_com_ia(
                    resultado, termos_achados, modelo=modelo_ia)
                st.session_state["atp_interpretacao"] = interpretacao

        if st.session_state.get("atp_interpretacao"):
            st.markdown(st.session_state["atp_interpretacao"])
            if st.button("➕ Adicionar interpretação ao Relatório do Dia"):
                st.session_state.cesto_analises.append({
                    "obra": "Interpretação IA — Localização de Termos",
                    "referencia": "Biblioteca Interna",
                    "tipo": "Interpretação de Termos (IA)",
                    "modelo": modelo_ia,
                    "conteudo": (
                        f"Termos: {', '.join(termos_achados)}\n\n"
                        f"{st.session_state['atp_interpretacao']}")
                })
                st.toast("✅ Interpretação salva no cesto!")
    
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