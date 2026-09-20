"""Harvester OAI-PMH (Oasisbr / DSpace / SciELO) — extração em lote via protocolo OAI.

Permite minerar repositórios institucionais brasileiros que exponham OAI-PMH
(universidades, IFs, SciELO). É resiliente: tenta cada endpoint e ignora os que
estiverem bloqueados por anti-bot (Cloudflare) ou indisponíveis, registrando isso
na trilha de auditoria.

Saída: data/producoes_oai.csv (esquema unificado, mesmo do OpenAlex) somado à
base data/producoes_mineradas.csv ao final.
"""

import os
import re
import json
import datetime
import unicodedata
import pandas as pd
from sickle import Sickle

# ======================================================
# CATÁLOGO DE ENDPOINTS OAI-PMH
# ======================================================
# Cada entrada filtra por comunidade/coleção relevante (`set`, quando conhecida)
# ou varre o repositório inteiro (sem `set`) confiando no filtro de relevância
# + trava de segurança (MAX_REGISTROS_BRUTOS) para limitar o trabalho.
# Endpoints validados via Verb=Identify/ListSets (2026-09).
FONTES_OAI = [
    # --- Rede Federal de Educação Profissional e Tecnológica (IFs) ---
    {"fonte": "IFBA", "endpoint": "https://repositorio.ifba.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal da Bahia"},
    {"fonte": "IFGoiano", "endpoint": "https://repositorio.ifgoiano.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal Goiano"},
    {"fonte": "IFMG", "endpoint": "https://repositorio.ifmg.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Minas Gerais"},
    {"fonte": "IFES", "endpoint": "https://repositorio.ifes.edu.br/server/oai/request",
     "set": "col_123456789_7548", "descricao": "IFES - Agência de Inovação do Ifes"},
    {"fonte": "IFTO", "endpoint": "https://repositorio.ifto.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal do Tocantins"},
    {"fonte": "IFRS", "endpoint": "https://repositorio.ifrs.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal do Rio Grande do Sul"},
    {"fonte": "IFAL", "endpoint": "https://repositorio.ifal.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Alagoas"},
    {"fonte": "IFAM", "endpoint": "https://repositorio.ifam.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal do Amazonas"},
    {"fonte": "IFAC", "endpoint": "https://repositorio.ifac.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal do Acre"},
    {"fonte": "IFRO", "endpoint": "https://repositorio.ifro.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Rondônia"},
    {"fonte": "IFPB", "endpoint": "https://repositorio.ifpb.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal da Paraíba"},
    {"fonte": "IFSP", "endpoint": "https://repositorio.ifsp.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de São Paulo"},
    {"fonte": "IFSC", "endpoint": "https://repositorio.ifsc.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Santa Catarina"},
    {"fonte": "IFMS", "endpoint": "https://repositorio.ifms.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Mato Grosso do Sul"},
    {"fonte": "IFB", "endpoint": "https://repositorio.ifb.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Brasília"},
    {"fonte": "IFCE", "endpoint": "https://repositorio.ifce.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal do Ceará"},
    {"fonte": "IFPE", "endpoint": "https://repositorio.ifpe.edu.br/oai/request",
     "set": "", "descricao": "Instituto Federal de Pernambuco"},
    {"fonte": "IFRR", "endpoint": "https://repositorio.ifrr.edu.br/server/oai/request",
     "set": "", "descricao": "Instituto Federal de Roraima"},
    {"fonte": "CEFETMG", "endpoint": "https://repositorio.cefetmg.br/server/oai/request",
     "set": "", "descricao": "Centro Federal de Educação Tecnológica de Minas Gerais"},
    # --- Universidades públicas ---
    {"fonte": "Lume_UFRGS", "endpoint": "https://lume.ufrgs.br/oai/request",
     "set": "com_10183_9", "descricao": "UFRGS Lume - Ciências Sociais Aplicadas",
     "limite": 60},
    {"fonte": "UFSM", "endpoint": "https://repositorio.ufsm.br/oai/request",
     "set": "com_1_9", "descricao": "UFSM Manancial - Centro de Ciências Sociais e Humanas (CCSH)"},
    {"fonte": "UFU", "endpoint": "https://repositorio.ufu.br/oai/request",
     "set": "col_123456789_38896", "descricao": "UFU - Seminário Diário de Ideias: inovação e criatividade na educação"},
    {"fonte": "UFSCar", "endpoint": "https://repositorio.ufscar.br/server/oai/request",
     "set": "", "descricao": "UFSCar Repositório Institucional"},
    {"fonte": "UFOP", "endpoint": "https://repositorio.ufop.br/server/oai/request",
     "set": "", "descricao": "UFOP Repositório Institucional"},
    {"fonte": "UFCA", "endpoint": "https://repositorio.ufca.edu.br/server/oai/request",
     "set": "", "descricao": "UFCA Repositório Institucional"},
    {"fonte": "UNIFESP", "endpoint": "https://repositorio.unifesp.br/oai/request",
     "set": "", "descricao": "UNIFESP Repositório Institucional"},
]

# ======================================================
# DICIONÁRIO DE INOVAÇÃO (reutilizado p/ filtro de relevância)
# ======================================================
def _norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").lower()

TERMOS_INOVACAO = [
    "innovation", "innovação", "inovacao", "innovación", "social innovation",
    "tecnologia social", "social technology", "economia solidária", "economia solidaria",
    "economie solidaire", "economía solidaria", "solidarity economy",
    "sociologia da inovação", "sociology of innovation", "decolonial", "emancipatory",
    "governança", "governance", "governanza", "innovation policy", "políticas de inovação",
    "institutos federais", "federal institute", "transferência de tecnologia",
    "transfer of technology", "propriedade intelectual", "intellectual property",
    "subven", "marco legal", "lei do bem", "embrapii", "patent", "patente",
    "indústria 4.0", "industry 4.0", "transição energética", "energy transition",
    "tecnologia apropriada", "appropriate technology", "inclusão social",
    "inovação social", "innovação pública", "public innovation", "policy innovation",
    "empreendedorismo", "entrepreneurship", "competitividade", "startup",
    "incubadora", "incubator", "parque tecnológico", "science park",
]
LIMIAR_RELEVANCIA = 2
MINIMO_ANOS = 2010

# Eixos temáticos (reutilizados do OpenAlex p/ consistência)
EIXOS = {
    "economia_solidaria": ["solidarity economy", "economia solidária", "economia solidaria",
                           "economie solidaire", "economía solidaria", "cooperative", "cooperativ"],
    "tecnologia_social": ["social technology", "tecnologia social", "technologie sociale",
                          "tecnología social", "appropriate technology", "tecnologia apropriada",
                          "technology for social inclusion"],
    "inovacao_politicas_publicas": ["innovation in public policy", "innovation policy",
                                    "public innovation policy", "políticas de inovação",
                                    "políticas publicas", "inovação em políticas públicas",
                                    "policy innovation"],
    "governanca_inovacao": ["innovation governance", "governance of innovation",
                            "governança da inovação", "gouvernance de l'innovation",
                            "gobernanza de la innovación", "innovation management"],
    "emancipacao_inovacao": ["emancipatory innovation", "critical innovation studies",
                             "decolonial", "perspectivas emancipadoras", "inovação emancipatória",
                             "soberania tecnológica", "alternative innovation"],
    "inovacao_instituto_publico": ["federal institute", "institutos federais", "ifba",
                                   "rede federal", "public institution innovation",
                                   "inovação no setor público", "public sector innovation"],
}
NORMALIZADO_EIXOS = {k: [_norm(t) for t in v] for k, v in EIXOS.items()}

# Palavras institucionais que não agregam semântica (stopwords do corpus)
STOPWORDS_INSTITUCIONAIS = [
    "universidade", "universidade", "tese", "dissertação", "orientador", "banca",
    "relatório anual", "programa de pós-graduação", "exame de qualificação",
]

# ======================================================
# HELPERS
# ======================================================
def _texto_registro(md, titulo, resumo):
    subs = " ".join(md.get("subject", [])) or ""
    desc = " ".join(md.get("description", [])) or ""
    return _norm(f"{titulo} {resumo} {desc} {subs}")

def passou_filtro_relevancia(titulo, md_texto):
    texto = _texto_registro(md_texto, titulo, "")
    if not texto:
        return False
    texto_norm = _norm(texto)
    hits = sum(1 for t in TERMOS_INOVACAO if _norm(t) in texto_norm)
    return hits >= LIMIAR_RELEVANCIA

def classificar_eixos(titulo, md_texto):
    t = _texto_registro(md_texto, titulo, "")
    found = [nome for nome, termos in NORMALIZADO_EIXOS.items() if any(term in t for term in termos)]
    return ";".join(found) if found else "geral"

def _pri(lista):
    if isinstance(lista, list) and lista:
        return str(lista[0])
    return str(lista) if lista else ""

def limpar_ano(ano_str):
    m = re.search(r"(20\d{2}|19\d{2})", str(ano_str or ""))
    return int(m.group(1)) if m else None

def registrar_auditoria(meta):
    trilha = os.path.join("data", "_auditoria_mineracao.json")
    registro = []
    if os.path.exists(trilha):
        try:
            with open(trilha, "r", encoding="utf-8") as f:
                registro = json.load(f)
        except Exception:
            registro = []
    registro.append(meta)
    with open(trilha, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

# ======================================================
# HARVESTER
# ======================================================
def coletar_repositorio(meta_fonte, limite=300):
    """Coleta registros de um repositório OAI-PMH. Retorna (df, status_dict)."""
    fonte = meta_fonte["fonte"]
    endpoint = meta_fonte["endpoint"]
    set_spec = meta_fonte.get("set") or ""
    limite = int(meta_fonte.get("limite", limite))  # limite específico da fonte, se houver
    resultados = []
    status = {"fonte": fonte, "endpoint": endpoint, "status": "ok", "detalhe": ""}

    MAX_REGISTROS_BRUTOS = 4000  # trava de segurança para não varrer repositórios inteiros
    erro_msg = ""
    try:
        cliente = Sickle(endpoint, timeout=40)
        kwargs = {"metadataPrefix": "oai_dc"}
        if set_spec:
            kwargs["set"] = set_spec

        recs = cliente.ListRecords(**kwargs, ignore_deleted=True)
        bruto = 0
        for registro in recs:
            bruto += 1
            if bruto > MAX_REGISTROS_BRUTOS:
                erro_msg = f"Limite bruto atingido ({MAX_REGISTROS_BRUTOS}) antes de coletar {limite} relevantes"
                break
            md = registro.metadata or {}
            titulo = _pri(md.get("title"))
            if not titulo:
                continue
            ano_record = limpar_ano(_pri(md.get("date")))
            if ano_record is not None and ano_record < MINIMO_ANOS:
                continue
            if not passou_filtro_relevancia(titulo, md):
                continue

            resultados.append({
                "fonte": fonte,
                "id_fonte": registro.header.identifier,
                "url": "",
                "titulo": titulo,
                "ano": limpar_ano(_pri(md.get("date"))),
                "autores": _pri(md.get("creator")),
                "citacoes": 0,
                "doi": _pri(md.get("identifier", [])).strip() if md.get("identifier") else "",
                "resumo": _pri(md.get("description")),
                "idioma": _pri(md.get("language")),
                "conceitos": ";".join(md.get("subject", [])),
                "veiculo": fonte,
                "eixo_tematico": classificar_eixos(titulo, md),
                "coleta_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                "query_utilizada": f"OAI-PMH {endpoint} set={set_spec}",
            })
            if len(resultados) >= limite:
                break
    except Exception as e:
        # Preserva o que já foi coletado (resiliência a timeout/instabilidade)
        if resultados:
            status["status"] = "parcial"
            status["detalhe"] = f"{len(resultados)} relevantes (interrompido: {type(e).__name__}: {e})"
        else:
            status["status"] = "erro"
            status["detalhe"] = f"{type(e).__name__}: {e}"
            return None, status
    else:
        status["status"] = "ok"
        status["detalhe"] = f"{len(resultados)} registros relevantes" + (f" ({erro_msg})" if erro_msg else "")

    df = pd.DataFrame(resultados) if resultados else pd.DataFrame()
    return df, status

def executar_mineracao(limite_por_fonte=300):
    print("🌐 Iniciando mineração via OAI-PMH (Oasisbr/DSpace/SciELO)...")
    todos = []
    for meta in FONTES_OAI:
        print(f"   [{meta['fonte']}] {meta['endpoint']}")
        df, status = coletar_repositorio(meta, limite=limite_por_fonte)
        registrar_auditoria({
            "tipo": "oai",
            **status,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        if df is not None and not df.empty:
            print(f"      ✅ {len(df)} relevantes")
            todos.append(df)
        else:
            print(f"      ⚠️ {status['detalhe']}")

    if not todos:
        print("⚠️ Nenhum dado OAI coletado (endpoints bloqueados/indisponíveis).")
        return None

    df_final = pd.concat(todos, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["fonte", "id_fonte"])

    caminho = os.path.join("data", "producoes_oai.csv")
    df_final.to_csv(caminho, index=False, encoding="utf-8")
    print(f"✅ {len(df_final)} registros OAI salvos em {caminho}")

    registrar_auditoria({
        "tipo": "oai_merge",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_final": int(len(df_final)),
        "por_fonte": df_final["fonte"].value_counts().to_dict(),
    })
    return df_final

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not os.path.exists("data"):
        os.makedirs("data")
    executar_mineracao()
