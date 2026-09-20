"""Minerador da API OpenAlex — reescrito para eliminar ruído.

Correções em relação à versão anterior:
1. Uso de `filter` + `title_and_abstract.search` com AND estrito por janela de idioma
   (em vez de `search=` amplo que fazia fuzzy disjunctive e puxava biomedicina).
2. `mailto` (polite pool), `select` com campos mínimos e tipos/ano filtrados.
3. Filtro pós-coleta de relevância: só mantém obras com >= N termos do dicionário
   de inovação no título/resumo.
4. Colunas de origem para o esquema unificado multi-fonte (fonte, url, id_fonte,
   conceitos, coleta_timestamp, query_utilizada).
"""

import os
import re
import json
import asyncio
import datetime
import unicodedata
import requests
import pandas as pd
from collections import Counter

MAILTO = "jonata.bittencourt@ifba.edu.br"
RESULTADOS_POR_PAGINA = 100
MAX_PAGINAS = 3
MINIMO_ANOS = 2010

# ======================================================
# DICIONÁRIO DE INOVAÇÃO (para filtro de relevância pós-coleta)
# ======================================================
def _norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").lower()

TERMOS_INOVACAO = [
    # Núcleo sociológico/emancipador
    "innovation", "innovação", "inovacao", "innovación", "innovation sociale",
    "sociology of innovation", "sociologia da inovação", "social innovation",
    "tecnologia social", "social technology", "economia solidária", "solidarity economy",
    "economia solidaria", "decolonial", "emancipatory", "emancipatória",
    # Governança / políticas públicas
    "governança", "governance", "governanza", "públicas", "public policy",
    "public governance", "innovation policy", "políticas de inovação",
    "notice publica", "institutos federais", "federal institute",
    # Instrumentos e marcos
    "transferência de tecnologia", "transfer of technology", "propriedade intelectual",
    "intellectual property", "subven", "marco legal", "lei do bem", "embrapii",
    "frascati", "oslo", "patent", "patente",
    # Temas aplicados
    "indústria 4.0", "industry 4.0", "transição energética", "energy transition",
    "tecnologia apropriada", "appropriate technology", "inclusão social",
]
TERMOS_PESO = {t: _norm(t) for t in TERMOS_INOVACAO}
LIMIAR_RELEVANCIA = 2

# ======================================================
# CONFIGURAÇÃO DE TERMOS MULTILINGUES
# ======================================================
# Janelas de idioma separadas (AND estrito dentro de cada janela)
QUERY_INGLES = (
    '"sociology of innovation" OR "innovation policy" OR "public governance" OR '
    '"public innovation" OR "social technology" OR "social innovation" OR '
    '"innovation governance" OR "emancipatory innovation" OR "critical innovation studies"'
)
QUERY_PORTUGUES = (
    '"sociologia da inovação" OR "inovação" OR "governança" OR "institutos federais" OR '
    '"tecnologia social" OR "economia solidária" OR "inovação pública" OR "inovação social" OR '
    '"perspectivas emancipadoras" OR "inovação emancipatória" OR "políticas de inovação"'
)
QUERY_FRANCES = (
    '"sociologie de l\'innovation" OR "gouvernance de l\'innovation" OR '
    '"innovation publique" OR "innovation sociale" OR "technologie sociale" OR "économie solidaire"'
)
QUERY_ESPANHOL = (
    '"sociología de la innovación" OR "gobernanza de la innovación" OR '
    '"innovación pública" OR "innovación social" OR "tecnología social" OR "economía solidaria"'
)

JANELAS_IDIOMA = {
    "en": QUERY_INGLES,
    "pt": QUERY_PORTUGUES,
    "fr": QUERY_FRANCES,
    "es": QUERY_ESPANHOL,
}

# Complemento obrigatório: recorte institucional/territorial + eixo
COMPLEMENTO = (
    '"Brazil" OR "Rede Federal" OR "Institutos Federais" OR "IFBA" OR '
    '"solidarity economy" OR "technology for social inclusion" OR "emancipatory" OR '
    '"public sector" OR "public institution" OR "decolonial"'
)

# Eixos temáticos para classificação pós-mineração
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

# ======================================================
# HELPERS
# ======================================================
def reconstruir_abstract(inverted_index):
    if not inverted_index:
        return ""
    try:
        max_pos = max(pos for positions in inverted_index.values() for pos in positions)
        texto = [None] * (max_pos + 1)
        for palavra, posicoes in inverted_index.items():
            for pos in posicoes:
                texto[pos] = palavra
        return " ".join(p for p in texto if p is not None)
    except Exception:
        return ""

def extrair_nomes(obra):
    return ", ".join(
        a.get("author", {}).get("display_name", "")
        for a in obra.get("authorships", [])
        if a.get("author", {}).get("display_name")
    )

def extrair_conceitos(obra):
    return ";".join(
        c.get("display_name", "")
        for c in obra.get("concepts", [])
        if c.get("display_name")
    )

def texto_obra(obra):
    return _norm(f"{obra.get('display_name', '')} {reconstruir_abstract(obra.get('abstract_inverted_index'))}")

def passou_filtro_relevancia(obra):
    """Retorna True se a obra contiver pelo menos LIMIAR_RELEVANCIA termos-chave."""
    texto = texto_obra(obra)
    if not texto:
        return False
    hits = sum(1 for _, t in TERMOS_PESO.items() if t in texto)
    return hits >= LIMIAR_RELEVANCIA

def classificar_eixos(texto_obra_str):
    t = _norm(texto_obra_str)
    found = [nome for nome, termos in NORMALIZADO_EIXOS.items() if any(term in t for term in termos)]
    return ";".join(found) if found else "geral"

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
# PERFIL CONCEITUAL DAS INSTITUIÇÕES (DNA científico)
# ======================================================
CONCEITOS_PRIORITARIOS = [
    "innovation", "innovation policy", "public administration", "social innovation",
    "technology assessment", "sociology", "governance", "technology", "economic growth",
    "political economy", "public sector", "management", "entrepreneurship", "tacit knowledge",
    "knowledge economy", "social science", "economic system", "democracy", "welfare",
    "cooperative", "solidarity economy", "social technology", "decolonization",
]

def obter_perfil_conceitual_if(institution_id, limite=200):
    params = {
        "filter": f"institutions.id:{institution_id},publication_year:>={MINIMO_ANOS}",
        "per_page": limite,
        "select": "display_name,concepts,publication_year,cited_by_count",
        "sort": "cited_by_count:desc",
        "mailto": MAILTO,
    }
    try:
        resp = requests.get("https://api.openalex.org/works", params=params, timeout=30)
        if resp.status_code != 200:
            return None
        result = resp.json().get("results", [])
        conceitos = []
        for w in result:
            for c in w.get("concepts", []):
                nome = c.get("display_name", "").lower()
                nivel = c.get("level")
                if nivel <= 3 or any(p in nome for p in CONCEITOS_PRIORITARIOS):
                    conceitos.append(c.get("display_name"))
        return dict(Counter(conceitos).most_common(30))
    except Exception:
        return None

# ======================================================
# COLETA OPENALEX
# ======================================================
def coletar_por_idioma(lang, query, pg_inicio=1, per_page=RESULTADOS_POR_PAGINA):
    """Coleta páginas de uma janela de idioma com filtro estrito de relevância."""
    tipo = "type:article|book-chapter|dissertation|thesis"
    params = {
        "filter": (
            f"title_and_abstract.search:{query},language:{lang},"
            f"{tipo},publication_year:{MINIMO_ANOS}-"
        ),
        "per_page": per_page,
        "mailto": MAILTO,
        "select": ("id,display_name,publication_year,authorships,cited_by_count,doi,"
                   "abstract_inverted_index,language,concepts,primary_location"),
        "sort": "cited_by_count:desc",
    }
    obras = []
    for pagina in range(pg_inicio, MAX_PAGINAS + 1):
        params["page"] = pagina
        try:
            resp = requests.get("https://api.openalex.org/works", params=params, timeout=30)
            if resp.status_code != 200:
                print(f"  ⚠️ HTTP {resp.status_code} ({lang}, página {pagina})")
                break
            results = resp.json().get("results", [])
            if not results:
                break
            obras.extend(results)
        except Exception as e:
            print(f"  ❌ Erro ({lang}, página {pagina}): {e}")
            break
    return obras

def processar_obra(obra, fonte_query):
    url = obra.get("id", "")
    primary = obra.get("primary_location") or {}
    host = (primary.get("source") or {}).get("display_name") or ""
    return {
        "fonte": "OpenAlex",
        "id_fonte": url,
        "url": url,
        "titulo": obra.get("display_name", ""),
        "ano": obra.get("publication_year"),
        "autores": extrair_nomes(obra),
        "citacoes": obra.get("cited_by_count", 0),
        "doi": obra.get("doi", ""),
        "resumo": reconstruir_abstract(obra.get("abstract_inverted_index")),
        "idioma": obra.get("language", ""),
        "conceitos": extrair_conceitos(obra),
        "veiculo": host,
        "eixo_tematico": classificar_eixos(
            f"{obra.get('display_name')} {reconstruir_abstract(obra.get('abstract_inverted_index'))}"
        ),
        "coleta_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "query_utilizada": fonte_query[:120],
    }

def executar_mineracao():
    print("🛰️ Iniciando mineração OpenAlex (filtro de relevância ativo)...")
    todas = {}
    for lang, query in JANELAS_IDIOMA.items():
        print(f"   Buscando idioma '{lang}'...")
        obras_brutas = coletar_por_idioma(lang, query)
        relevantes = [o for o in obras_brutas if passou_filtro_relevancia(o)]
        print(f"      {len(obras_brutas)} coletados -> {len(relevantes)} relevantes")
        for o in relevantes:
            oid = o.get("id")
            if oid and oid not in todas:
                todas[oid] = processar_obra(o, query)

    if not todas:
        print("⚠️ Nenhum dado relevante coletado.")
        return None

    df = pd.DataFrame(todas.values())
    df = df.drop_duplicates(subset="id_fonte")

    caminho = os.path.join("data", "producoes_openalex.csv")
    df.to_csv(caminho, index=False, encoding="utf-8")
    print(f"✅ {len(df)} obras salvas em {caminho}")

    registrar_auditoria({
        "tipo": "openalex",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_final": int(len(df)),
        "idiomas": df["idioma"].value_counts().to_dict(),
        "amostra_eixos": df["eixo_tematico"].value_counts().head(8).to_dict(),
    })
    return df

def executar_perfil_rede():
    ids_institutos = [
        "I165735391",  # IFBA
        "I2059774197",  # IFMG
        "I4210129444",  # IFRN
        "I41187327",    # IFSUL
        "I2803300026",  # IFSC
        "I4210116772",  # IF Goiano
        "I4210129440",  # IFC
        "I4210136515",  # IFES
    ]
    print("🏛️ Mapeando DNA científico da Rede Federal...")
    perfil_rede = {}
    for inst_id in ids_institutos:
        perfil = obter_perfil_conceitual_if(inst_id)
        if perfil:
            for conceito, freq in perfil.items():
                perfil_rede[conceito] = perfil_rede.get(conceito, 0) + freq
    if perfil_rede:
        ordenado = sorted(perfil_rede.items(), key=lambda x: x[1], reverse=True)[:30]
        df = pd.DataFrame(ordenado, columns=["Conceito", "Frequência"])
        df.to_csv("data/perfil_institucional.csv", index=False, encoding="utf-8")
        print("✅ Perfil Institucional (Rede Federal) atualizado.")
    return perfil_rede

def executar_fluxo_completo():
    if not os.path.exists("data"):
        os.makedirs("data")
    df = executar_mineracao()
    executar_perfil_rede()
    if df is not None:
        print("\n=== Relatório de Mineração ===")
        print(f"Total de obras únicas: {len(df)}")
        print(f"Anos: {sorted(df['ano'].dropna().astype(int).unique())[:5]}... "
              f"{int(df['ano'].max())}")
        print(f"Idiomas: {df['idioma'].value_counts().to_dict()}")
        print(f"Eixos (top): {df['eixo_tematico'].value_counts().head(8).to_dict()}")

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    executar_fluxo_completo()
