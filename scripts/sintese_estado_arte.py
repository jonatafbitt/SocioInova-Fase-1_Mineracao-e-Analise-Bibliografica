"""Síntese do Estado da Arte da Inovação — camada analítica sobre o corpus minerado.

Constrói, a partir da base unificada (data/producoes_mineradas.csv), um conjunto de
artefatos que permitem ao dashboard ler o *campo da inovação* em escala de conjunto
(estado da arte), revelando a gramática da inovação (nacional x internacional) e os
lugares, usos e sentidos do recorte social, de código aberto e das pautas emancipadoras.

Entregas (gravadas em data/):
  * dna_inovacao.csv          -> assinatura conceitual (termos nucleares) do corpus
  * indices_estado_arte.csv   -> registro derivado: recorte_geo, flags social/aberto/
                                 emancipatorio, nucleo/contexto, instituicoes
  * coocorrencia_estado_arte.json -> matriz de co-ocorrencia de termos-conceito
  * _sintese_estado_arte.json     -> cache da síntese IA (por hash do recorte+modelo)

Pode ser executado em linha de comando (mongrel) ou importado pelo dashboard.
"""

import os
import re
import json
import unicodedata
import hashlib
import datetime
import pandas as pd

import ollama  # IA local

PASTA_DATA = "data"
BASE = os.path.join(PASTA_DATA, "producoes_mineradas.csv")
ARQ_DNA = os.path.join(PASTA_DATA, "dna_inovacao.csv")
ARQ_INDICES = os.path.join(PASTA_DATA, "indices_estado_arte.csv")
ARQ_COOCORRENCIA = os.path.join(PASTA_DATA, "coocorrencia_estado_arte.json")
ARQ_SINTESE = os.path.join(PASTA_DATA, "_sintese_estado_arte.json")

# --- Normalização ---
def _norm(t):
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("ascii").lower()

# ============================================================
# DICIONÁRIOS SEMÂNTICOS (gramática do campo)
# ============================================================
# Termos nucleares da inovação (para DNA + detecção de sentidos)
TERMOS_NUCLEARES = {
    "inovacao": ["innovation", "inovação", "inovacao", "innovación", "innovation"],
    "governanca": ["governança", "governance", "governanza", "gouvernance"],
    "tecnologia_social": ["tecnologia social", "social technology", "technologie sociale", "tecnología social"],
    "economia_solidaria": ["economia solidária", "solidarity economy", "économie solidaire", "economía solidaria", "cooperativ", "autogestão", "autogestion"],
    "politicas_publicas": ["políticas públicas", "políticas de inovação", "innovation policy", "public policy", "politique publique", "políticas publicas"],
    "emancipacao": ["emancipatóri", "emancipator", "emancipación", "decolonial", "soberania tecnológica", "autonomia", "liberation", "libertação"],
    "institutos_federais": ["institutos federais", "federal institute", "rede federal", "instituts fédéraux", "institutos federales"],
    "transferencia": ["transferência de tecnologia", "transfer of technology", "transfert de technologie", "transferencia de tecnología"],
    "propriedade_intelectual": ["propriedade intelectual", "intellectual property", "propriété intellectuelle", "propiedad intelectual"],
    "patente": ["patente", "patent", "brevet"],
    "territorio_desenvolvimento_local": ["desenvolvimento local", "local development", "développement local", "desarrollo local", "território", "territoire", "territorio"],
}
NORMALIZADO_NUCLEARES = {k: [_norm(t) for t in v] for k, v in TERMOS_NUCLEARES.items()}

# Código aberto / ciência aberta
TERMOS_CODIGO_ABERTO = [
    "open source", "código aberto", "codigo aberto", "software livre", "free software",
    "software libre", "logiciel libre", "open innovation", "open science", "ciência aberta",
    "ciencia aberta", "science ouverte", "creative commons", "licença aberta", "licenÃ§a aberta",
    "licencia abierta", "floss", "open hardware", "open access", "acesso aberto",
]
TERMOS_CODIGO_ABERTO = [_norm(t) for t in TERMOS_CODIGO_ABERTO]

# Sentidos (semiótica): vocabulário indicativo de mimetismo vs situada
TERMOS_MIMETISMO = [
    "competitividade", "competitiveness", "eficiência", "eficiência", "productivity",
    "produtividade", "mercado", "market", "startup", "unicorn", "vale do silício",
    "silicon valley", "disrupt", "escala", "escalável", "retorno", "roi", "absent",
    "dependência tecnológica", "transferência de tecnologia de cima para baixo",
]
TERMOS_EMANCIPA = [
    "soberania", "sovereignty", "autonomia", "autonomie", "decolonial", "emancipação",
    "emancipación", "bem comum", "common good", "bien commun", "economia solidária",
    "cooperativ", "autogestão", "autogestion", "protagonismo comunitário", "justiça social",
    "inclusão social", "participação social", "participación social",
]

# ============================================================
# DETECÇÃO LÉXICA
# ============================================================
def _contar_termos(texto_norm, lista_termos):
    return sum(1 for t in lista_termos if t in texto_norm)

def detectar_falanges(resumo, titulo):
    """Retorna dict com contagens de termos por eixo nuclear."""
    texto = _norm(f"{titulo} {resumo}")
    contagens = {}
    for nome, termos in NORMALIZADO_NUCLEARES.items():
        contagens[nome] = _contar_termos(texto, termos)
    return contagens

def detectar_codigo_aberto(resumo, titulo):
    texto = _norm(f"{titulo} {resumo}")
    return _contar_termos(texto, TERMOS_CODIGO_ABERTO)

def detectar_sentidos(resumo, titulo):
    """Retorna (n_mimetismo, n_emancipacao)."""
    texto = _norm(f"{titulo} {resumo}")
    m = _contar_termos(texto, [_norm(t) for t in TERMOS_MIMETISMO])
    e = _contar_termos(texto, [_norm(t) for t in TERMOS_EMANCIPA])
    return m, e

# ============================================================
# INSTITUIÇÕES / "LUGARES" DOS ESPAÇOS PÚBLICOS DE INOVAÇÃO
# ============================================================
PADRAO_INST = re.compile(
    r"\b(?:Instituto Federal|IF|Universidade Federal|UF|Centro Federal|CEFET)"
    r"[A-ZÁ-Úa-zá-ú0-9\-\. ]{3,40}\b",
    re.IGNORECASE,
)

def extrair_instituicoes(resumo, titulo, veiculo):
    texto = f"{titulo} {resumo} {veiculo}"
    nomes = set(PADRAO_INST.findall(texto))
    nomes = {re.sub(r"\s{2,}", " ", n).strip() for n in nomes}
    return ";".join(sorted(nomes))

def classificar_recorte_geo(idioma, fonte):
    """nacional x internacional a partir do idioma (proxy) + fonte."""
    idi = _norm(str(idioma or ""))
    if idi in ("pt", "por", "pt_br", "português", "portugues", "português brasil"):
        return "nacional"
    if idi in ("en", "fr", "es"):
        return "internacional"
    # fallback: fonte OAI brasileira conta como nacional
    return "nacional"

def classificar_nucleo_contexto(contagens, n_termos_totais, flag_social, flag_aberto):
    """Núcleo = toca eixo central OU tem >=3 termos nucleares OU indício social/aberto."""
    eixos_centrais = ["tecnologia_social", "economia_solidaria", "emancipacao",
                      "governanca", "institutos_federais"]
    if any(contagens.get(e, 0) > 0 for e in eixos_centrais):
        return "nucleo"
    if n_termos_totais >= 3:
        return "nucleo"
    if flag_social or flag_aberto:
        return "nucleo"
    return "contexto"

# ============================================================
# PRÉ-PROCESSAMENTO PRINCIPAL
# ============================================================
def preparar_indices():
    """Lê a base unificada e gera o dataframe de índices derivados + DNA."""
    df = pd.read_csv(BASE, encoding="utf-8")
    df = df.fillna("")

    rows = []
    contagens_totais = {}
    for _, r in df.iterrows():
        resumo = str(r.get("resumo", ""))
        titulo = str(r.get("titulo", ""))
        falanges = detectar_falanges(resumo, titulo)
        n_total = sum(falanges.values())
        for k, v in falanges.items():
            contagens_totais[k] = contagens_totais.get(k, 0) + v

        flag_aberto = detectar_codigo_aberto(resumo, titulo)
        n_mim, n_ema = detectar_sentidos(resumo, titulo)
        flag_social = (falanges.get("tecnologia_social", 0) + falanges.get("economia_solidaria", 0)) > 0

        reg = {
            "fonte": r.get("fonte", ""),
            "id_fonte": r.get("id_fonte", ""),
            "titulo": titulo,
            "ano": r.get("ano", ""),
            "idioma": r.get("idioma", ""),
            "autores": r.get("autores", ""),
            "veiculo": r.get("veiculo", ""),
            "eixo_tematico": r.get("eixo_tematico", ""),
            "resumo": resumo,
            "recorte_geo": classificar_recorte_geo(r.get("idioma", ""), r.get("fonte", "")),
            "n_termos_nucleares": n_total,
            "flag_codigo_aberto": int(flag_aberto > 0),
            "flag_social": int(flag_social),
            "flag_emancipatorio": int(n_ema > 0),
            "n_sentidos_mimetismo": n_mim,
            "n_sentidos_emancipacao": n_ema,
            "nucleo_contexto": classificar_nucleo_contexto(falanges, n_total, flag_social, flag_aberto),
            "instituicoes": extrair_instituicoes(resumo, titulo, str(r.get("veiculo", ""))),
        }
        rows.append(reg)

    ind = pd.DataFrame(rows)
    ind.to_csv(ARQ_INDICES, index=False, encoding="utf-8")

    # DNA Científico do recorte (termos nucleares, normalizados por nome)
    dna = pd.DataFrame(sorted(contagens_totais.items(), key=lambda x: x[1], reverse=True),
                       columns=["Conceito", "Frequência"])
    dna.to_csv(ARQ_DNA, index=False, encoding="utf-8")

    return ind

# ============================================================
# MATRIZ DE CO-OCORRÊNCIA
# ============================================================
def construir_coocorrencia(ind=None):
    if ind is None:
        ind = pd.read_csv(ARQ_INDICES, encoding="utf-8")
        ind = ind.fillna("")
    # nós = eixos nucleares presentes no registro (via contagem no resumo re-detectado)
    chaves = sorted(NORMALIZADO_NUCLEARES.keys())
    # Re-detectamos por registro
    presenca = {k: [] for k in chaves}
    for _, r in ind.iterrows():
        falanges = detectar_falanges(str(r.get("resumo", "")), str(r.get("titulo", "")))
        ativos = [k for k in chaves if falanges.get(k, 0) > 0]
        for a in ativos:
            presenca[a].append(set(ativos))

    cooc = {}
    for a in chaves:
        cooc[a] = {}
    for a in chaves:
        for conjunto in presenca[a]:
            for b in conjunto:
                if a != b:
                    cooc[a][b] = cooc[a].get(b, 0) + 1

    # converte nested dict para lista de arestas
    arestas = []
    nos = []
    vistos = set()
    for a in chaves:
        total_a = sum(cooc[a].values())
        if total_a > 0:
            nos.append({"id": a, "label": a, "freq": total_a})
        for b, peso in cooc[a].items():
            aresta = tuple(sorted([a, b]))
            if aresta in vistos:
                continue
            vistos.add(aresta)
            arestas.append({"source": a, "target": b, "weight": peso})

    dados = {"nos": nos, "arestas": arestas}
    with open(ARQ_COOCORRENCIA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return dados

# ============================================================
# SÍNTESE IA (chunking + condensação em camadas)
# ============================================================
def _hash_recorte(ind, modelo):
    """Hash estável do recorte + modelo para caching."""
    selec = ind[["titulo", "resumo", "recorte_geo", "nucleo_contexto"]]
    blob = selec.to_csv(index=False)
    return hashlib.md5(f"{blob}|{modelo}".encode("utf-8")).hexdigest()

def _chunk_textos(textos, max_chars):
    """Agrupa textos em pacotes respeitando limite de caracteres."""
    pacotes = []
    atual = []
    soma = 0
    for t in textos:
        if t and soma + len(t) > max_chars and atual:
            pacotes.append("\n".join(atual))
            atual = []
            soma = 0
        atual.append(t)
        soma += len(t)
    if atual:
        pacotes.append("\n".join(atual))
    return pacotes

def _resumir_parcial(textos, modelo):
    """Gera síntese parcial de um pacote de resumos (trunca para agilidade)."""
    truncados = [str(t)[:600] for t in textos if t]
    corpo = "\n".join(f"- {t}" for t in truncados)[:14000]
    prompt = (
        "Você é um sociólogo da inovação. A partir dos resumos abaixo (recorte de um "
        "corpus maior), identifique os elementos-chave do estado da arte: termos-conceito "
        "centrais, enquadramentos dominantes (inovação por mimetismo vs. inovação situada), "
        "e a presença de pautas sociais, de código aberto e emancipadoras. Seja objetivo.\n\n"
        f"RESUMOS:\n{corpo}\n\nSÍNTESE PARCIAL:"
    )
    try:
        resp = ollama.chat(model=modelo, messages=[{"role": "user", "content": prompt}],
                           options={"num_ctx": 8192})
        return resp["message"]["content"]
    except Exception as e:
        return f"[erro na síntese parcial: {e}]"

def gerar_sintese(ind, modelo, forcar=False):
    """Gera (ou recupera do cache) o documento de estado da arte nacional+internacional."""
    os.makedirs(PASTA_DATA, exist_ok=True)
    hash_rec = _hash_recorte(ind, modelo)

    cache = {}
    if os.path.exists(ARQ_SINTESE):
        try:
            with open(ARQ_SINTESE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    if not forcar and hash_rec in cache:
        return cache[hash_rec], True  # (conteúdo, do_cache)

    # prioriza núcleo, depois contexto
    ind_sorted = ind.sort_values(by="nucleo_contexto", ascending=False,
                                 key=lambda s: s.map({"nucleo": 1, "contexto": 0}))
    geo = {"nacional": [], "internacional": []}
    for _, r in ind_sorted.iterrows():
        txt = str(r.get("resumo", "")).strip()
        if not txt:
            continue
        geo[r.get("recorte_geo", "nacional")].append(txt)

    documento = {}
    for chave, textos in geo.items():
        pacotes = _chunk_textos(textos, 38000)
        parciais = []
        for i, pacote in enumerate(pacotes):
            parciais.append(_resumir_parcial(pacote.split("\n"), modelo))
        # condensação
        corpo = "\n\n".join(parciais)
        prompt_final = (
            "Componha o ESTADO DA ARTE da inovação a partir das sínteses parciais abaixo, "
            "com foco na gramática do campo e nos lugares, usos e sentidos do recorte "
            "social, de código aberto e das pautas emancipadoras nos espaços públicos de "
            "inovação. Estruture em: (1) termos-conceito nucleares; (2) enquadramentos "
            "dominantes; (3) lugar do social/código aberto/emancipação; (4) lacunas e "
            "tensões. Texto acadêmico, conciso.\n\n"
            f"SÍNTESES PARCIAIS:\n{corpo}"
        )
        try:
            resp = ollama.chat(model=modelo, messages=[{"role": "user", "content": prompt_final}],
                               options={"num_ctx": 8192})
            documento[chave] = resp["message"]["content"]
        except Exception as e:
            documento[chave] = f"[erro na síntese final: {e}]"

    payload = {
        "hash": hash_rec,
        "modelo": modelo,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "recortes": documento,
    }
    cache[hash_rec] = payload
    with open(ARQ_SINTESE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    return payload, False

# ============================================================
# SÍNTESE DE SENTIDOS (semiótica)
# ============================================================
def gerar_sintese_sentidos(ind, modelo):
    """Classifica globalmente o uso de social/código aberto/emancipação."""
    nucleo = ind[ind["nucleo_contexto"] == "nucleo"]
    textos = [f"- {str(r.get('titulo',''))} | {str(r.get('resumo',''))[:600]}" for _, r in nucleo.iterrows()][:40]
    corpo = "\n".join(textos)[:14000]
    prompt = (
        "Sob a lente da sociologia da inovação, analise como o recorte 'social', o "
        "'código aberto' e as 'pautas emancipadoras' aparecem nas obras abaixo. Classifique "
        "cada presença como (a) PERFORMÁTICO-MERCADOLÓGICO (mimetismo: uso de termos como "
        "retórica sem compromisso emancipatório) ou (b) EMANCIPATÓRIO-SITUADO (uso ligado a "
        "autonomia, bem comum, território). Depois, uma síntese da distribuição de sentidos "
        "e 3 exemplos ilustrativos.\n\n"
        f"OBRAS:\n{corpo}"
    )
    try:
        resp = ollama.chat(model=modelo, messages=[{"role": "user", "content": prompt}],
                           options={"num_ctx": 8192})
        return resp["message"]["content"]
    except Exception as e:
        return f"[erro na síntese de sentidos: {e}]"

# ============================================================
# ENTRYPOINT
# ============================================================
def executar_tudo():
    print("🧭 Preparando índices do estado da arte...")
    ind = preparar_indices()
    print(f"   {len(ind)} registros indexados; DNA salvo em {ARQ_DNA}")
    construir_coocorrencia(ind)
    print(f"   Matriz de co-ocorrência salva em {ARQ_COOCORRENCIA}")
    return ind

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    executar_tudo()
