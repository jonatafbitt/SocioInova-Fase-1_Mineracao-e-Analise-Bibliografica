"""Análise de termos na biblioteca local de PDFs (busca literal + contagem + interpretação IA).

Fornece:
  * indexar_pdfs(...)          -> indexa a pasta de PDFs no Chroma com metadados de origem/página
                                   e grava um cache de texto plano por PDF (para busca literal exata);
  * localizar_termos(...)      -> busca literal case-insensitive (com normalização de acentos) e
                                   retorna, por documento, ocorrências, páginas e trechos de contexto;
  * construir_tabela(...)      -> helpers de visualização usados pelo dashboard;
  * interpretar_com_ia(...)    -> camada qualitativa (Ollama) que lê os trechos e sintetiza como
                                   os termos são mobilizados na biblioteca.

Reutiliza os dicionários semânticos e a normalização de scripts/sintese_estado_arte.py (sea),
sem duplicar o vocabulário.
"""

import os
import json
import unicodedata

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Normalização padrão usada no restante do app (acentos -> ascii minusculo)
def _norm(t):
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("ascii").lower()


# Cache de texto plano: {nome_arquivo: {"paginas": [texto_pag0, ...], "total_paginas": n}}
CACHE_PATH = os.path.join("data", "pdf_texto_cache.json")


def _carregar_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _salvar_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def indexar_pdfs(v_db, pasta_pdfs="meus_pdfs", modelo_emb="nomic-embed-text", chunk_size=2000,
                 chunk_overlap=200):
    """Indexa os PDFs da pasta de forma incremental (com metadados de origem/página)
    e atualiza o cache de texto plano.

    Retorna a lista de nomes de arquivos processados.
    """
    if not os.path.exists(pasta_pdfs):
        return []

    arquivos = [f for f in os.listdir(pasta_pdfs) if f.lower().endswith(".pdf")]
    cache = _carregar_cache()
    processados = []

    for arq in arquivos:
        caminho = os.path.join(pasta_pdfs, arq)
        loader = PyPDFLoader(caminho)
        paginas = loader.load()

        # Atualiza cache de texto plano (para busca literal + localização de página)
        novo_cache = {
            "paginas": [p.page_content for p in paginas],
            "total_paginas": len(paginas),
        }
        cache[arq] = novo_cache

        # Remove ids antigos deste arquivo (reindexação incremental)
        try:
            ids_existentes = v_db._collection.get(where={"source": arq})["ids"]
            if ids_existentes:
                v_db._collection.delete(ids=ids_existentes)
        except Exception:
            pass

        # Divide em chunks preservando a página de origem
        splits = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        ).split_documents(paginas)

        textos, metadatas, ids = [], [], []
        for i, ch in enumerate(splits):
            pagina = ch.metadata.get("page_label") or str(ch.metadata.get("page", ""))
            textos.append(ch.page_content)
            metadatas.append({"source": arq, "pagina": pagina, "chunk": i})
            ids.append(f"{arq}::{i}")

        if textos:
            v_db.add_texts(texts=textos, metadatas=metadatas, ids=ids)
        processados.append(arq)

    _salvar_cache(cache)
    return processados


def _normalizar_para_busca(texto):
    """Versão normalizada (case + acentos) para busca. Precalculada por página."""
    return _norm(texto)


def _ocorrencias_normalizadas(texto_norm, termo_norm):
    """Lista de índices de início de cada ocorrência no texto normalizado."""
    idxs = []
    start = 0
    while True:
        i = texto_norm.find(termo_norm, start)
        if i == -1:
            break
        idxs.append(i)
        start = i + len(termo_norm)
    return idxs


def _extrair_trecho_original(original, ini_norm, fim_norm, max_ini=120, max_fim=180):
    """Extrai janela de contexto do texto ORIGINAL a partir de índices normalizados.

    Percorre o original em paralelo (contando apenas caracteres que sobrevivem à
    normalização) até atingir a posição normalizada desejada, preservando os
    caracteres originais (com acentos e pontuação).
    """
    lim_inf = max(0, ini_norm - max_ini)
    lim_sup = fim_norm + max_fim

    start_orig = None
    end_orig = None
    cum_norm = 0
    for oi, ch in enumerate(original):
        nf = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
        if not nf:
            continue
        if start_orig is None and cum_norm >= lim_inf:
            start_orig = oi
        if start_orig is not None and cum_norm > lim_sup:
            end_orig = oi
            break
        cum_norm += 1

    if start_orig is None:
        start_orig = 0
    if end_orig is None:
        end_orig = len(original)
    return original[start_orig:end_orig].replace("\n", " ").strip()


def localizar_termos(termos, pasta_pdfs="meus_pdfs", incluir_variacao_acento=True):
    """Busca literal (case-insensitive, sem sensibilidade a acentos) dos termos no
    cache de texto plano dos PDFs.

    termos: lista de strings (ex.: ["inovação", "decolonial"]).

    Retorna dict:
        por_termo: {termo: [ {arquivo, pagina, trecho, indice} ... ] }
        por_arquivo: {arquivo: {termo: n_ocorrencias, paginas: set, total_paginas}}
    """
    cache = _carregar_cache()
    if not cache:
        # Fallback: tenta indexar/recriar cache a partir da pasta diretamente
        cache = _indexar_cache_da_pasta(pasta_pdfs)

    # A busca é feita em texto normalizado; acentos são removidos na comparação.
    termos_norm = []
    for t in termos:
        t = t.strip()
        if not t:
            continue
        tn = _norm(t)
        termos_norm.append((t, tn))

    por_termo = {t: [] for t, _ in termos_norm}
    por_arquivo = {}

    for arq, info in cache.items():
        paginas = info.get("paginas", [])
        total_paginas = info.get("total_paginas", len(paginas))
        if not paginas:
            continue

        # Pré-normaliza as páginas uma única vez (rápido, evita repetição)
        paginas_norm = [_normalizar_para_busca(p) for p in paginas]
        # window de contexto fixa
        MAX_INI = 120
        MAX_FIM = 180

        paginas_arquivo = set()
        contagens = {t: 0 for t, _ in termos_norm}

        for pag_idx, (texto_orig, texto_norm) in enumerate(zip(paginas, paginas_norm)):
            pag_rotulo = str(pag_idx + 1)
            for termo, tn in termos_norm:
                ocorr = _ocorrencias_normalizadas(texto_norm, tn)
                if not ocorr:
                    continue
                n = len(ocorr)
                contagens[termo] += n
                paginas_arquivo.add(pag_rotulo)
                for i in ocorr:
                    trecho = _extrair_trecho_original(
                        texto_orig, i, i + len(tn), max_ini=MAX_INI, max_fim=MAX_FIM)
                    por_termo[termo].append({
                        "arquivo": arq,
                        "pagina": pag_rotulo,
                        "trecho": trecho,
                        "indice": i,
                    })

        por_arquivo[arq] = {
            "contagens": contagens,
            "paginas": sorted(paginas_arquivo),
            "total_paginas": total_paginas,
        }

    return {"por_termo": por_termo, "por_arquivo": por_arquivo}


def _indexar_cache_da_pasta(pasta_pdfs):
    """Recria o cache de texto plano a partir dos PDFs da pasta (fallback)."""
    cache = {}
    if not os.path.exists(pasta_pdfs):
        return cache
    for arq in os.listdir(pasta_pdfs):
        if not arq.lower().endswith(".pdf"):
            continue
        try:
            paginas = PyPDFLoader(os.path.join(pasta_pdfs, arq)).load()
            cache[arq] = {
                "paginas": [p.page_content for p in paginas],
                "total_paginas": len(paginas),
            }
        except Exception:
            continue
    _salvar_cache(cache)
    return cache


def construir_tabela(resultado):
    """Converte o resultado de localizar_termos em uma lista de linhas (dict) para dataframe/tabela."""
    linhas = []
    por_arquivo = resultado["por_arquivo"]
    termos = list(resultado["por_termo"].keys())

    for arq, info in por_arquivo.items():
        linha = {
            "PDF": arq,
            "Ocorrências": sum(info["contagens"].values()),
            "Páginas": len(info["paginas"]),
            "Lista de Páginas": ", ".join(info["paginas"]) if info["paginas"] else "—",
            "Densidade (ocorr/pág)": round(
                sum(info["contagens"].values()) / info["total_paginas"], 2
            ) if info["total_paginas"] else 0,
        }
        for t in termos:
            linha[t] = info["contagens"].get(t, 0)
        if linha["Ocorrências"] > 0:
            linhas.append(linha)

    linhas.sort(key=lambda r: r["Ocorrências"], reverse=True)
    return linhas


def _montar_contexto_para_ia(resultado, termos, max_por_termo=5, max_total_chars=6000):
    """Prepara um contexto enxuto (por termo e por documento) para a interpretação por IA."""
    blocos = []
    total = 0
    for t in termos:
        ocorrencias = resultado["por_termo"].get(t, [])
        if not ocorrencias:
            continue
        blocos.append(f"### Termo: «{t}» ({len(ocorrencias)} ocorrência(s))")
        c = 0
        for oc in ocorrencias:
            trecho = oc["trecho"]
            bloco = f"- [{oc['arquivo']} | pág. {oc['pagina']}] {trecho}"
            if total + len(bloco) > max_total_chars and blocos:
                blocos.append(f"_... (contexto truncado para caber no limite de {max_total_chars} caracteres)_")
                return "\n".join(blocos)
            blocos.append(bloco)
            total += len(bloco)
            c += 1
            if c >= max_por_termo:
                blocos.append(f"_... (mostrando {max_por_termo} de {len(ocorrencias)} ocorrências)_")
                break
    return "\n".join(blocos)


def _definir_lente(termos):
    """Classifica os termos conforme os dicionários semânticos (mimetismo x emancipatório)
    para orientar a lente da IA. Reutiliza os vocabulários de sintese_estado_arte."""
    try:
        import sintese_estado_arte as sea
    except Exception:
        return "neutral"
    nrm = _norm
    t_norm = [nrm(t) for t in termos]
    mim = sum(1 for t in t_norm if any(nrm(tm) == t or nrm(tm) in t for tm in sea.TERMOS_MIMETISMO))
    ema = sum(1 for t in t_norm if any(nrm(tm) == t or nrm(tm) in t for tm in sea.TERMOS_EMANCIPA))
    if ema > mim:
        return "emancipatorio"
    if mim > ema:
        return "mimetismo"
    return "neutral"


def interpretar_com_ia(resultado, termos, modelo="qwen2:1.5b", max_por_termo=5):
    """Gera uma síntese qualitativa (por IA) sobre como os termos são mobilizados na biblioteca.

    Usa exclusivamente os trechos (busca literal) — sem depender de embeddings.

    Retorna a string com o texto gerado pela IA local (ollama).
    """
    import ollama

    contexto = _montar_contexto_para_ia(resultado, termos, max_por_termo=max_por_termo)
    if not contexto.strip():
        return "Nenhum trecho disponível para interpretação."

    lente = _definir_lente(termos)

    desc_lente = {
        "emancipatorio": (
            "Analise como os termos apontam para uma perspectiva EMANCIPATÓRIA/situada: "
            "soberania, autonomia, tecnologias sociais, participação social, decolonialidade."),
        "mimetismo": (
            "Analise como os termos apontam para uma perspectiva de METÁFORA MERCADOLÓGICA/"
            "mimetismo: competitividade, eficiência, mercado, transferência de tecnologia."),
        "neutral": "Analise os sentidos e usos dos termos de forma equilibrada, sem viés.",
    }

    prompt = f"""Você é um analista de Sociologia da Inovação. Recebeu trechos da biblioteca
local (PDFs) onde aparecem os seguintes termos: {', '.join(termos)}.

{desc_lente[lente]}

Síntese pedida: como os termos são mobilizados nos documentos? Identifique:
1) Sentidos e ênfases recorrentes.
2) Tensões eventuais entre os documentos (diferenças de enquadramento).
3) Relação com o recorte do projeto: inovação situada vs. por mimetismo na Rede Federal.

Baseie-se APENAS nos trechos fornecidos. Seja conciso (máx. ~250 palavras).

CONTEXTO (trechos):
{contexto}
"""
    try:
        resp = ollama.chat(model=modelo, messages=[{'role': 'user', 'content': prompt}])
        return resp['message']['content']
    except Exception as e:
        return f"Erro ao chamar a IA ({modelo}): {e}"
