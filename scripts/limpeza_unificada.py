"""Limpeza e consolidação unificada das fontes mineradas.

Combina as bases por fonte (OpenAlex, OAI-PMH) em um único CSV padronizado,
aplica deduplicação inter-fonte (por DOI; fallback por título normalizado),
normaliza vocabulário e mantém trilha de auditoria (origem/timestamp/query).
"""

import os
import re
import json
import datetime
import unicodedata
import pandas as pd

DATA = "data"
SAIDAS = ["producoes_mineradas.csv"]

# Colunas obrigatórias do esquema unificado
COLUNAS = [
    "fonte", "id_fonte", "url", "titulo", "ano", "autores", "citacoes",
    "doi", "resumo", "idioma", "conceitos", "veiculo", "eixo_tematico",
    "coleta_timestamp", "query_utilizada",
]

STOPWORDS_INSTITUCIONAIS = [
    "universidade", "tese", "dissertação", "orientador", "banca",
    "relatório anual", "programa de pós-graduação", "exame de qualificação",
]

def _norm(t):
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("ascii").lower()

def _normalizar_titulo(titulo):
    """Título normalizado (sem pontuação/acentos) para dedup por similaridade."""
    t = _norm(titulo)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _extract_doi(texto):
    """Extrai DOI de um campo identifier (ex.: http://hdl.handle.net/... vs doi)."""
    m = re.search(r"10\.\d{4,9}/[^\s\"']+", str(texto))
    return m.group(0).rstrip(".,;") if m else ""

def carregar_fontes():
    """Carrega todos os CSVs de fonte (producoes_*.csv) exceto a base consolidada."""
    frames = []
    if not os.path.exists(DATA):
        os.makedirs(DATA)
    for arquivo in sorted(os.listdir(DATA)):
        if not arquivo.endswith(".csv"):
            continue
        if arquivo in SAIDAS or arquivo == "perfil_institucional.csv":
            continue
        caminho = os.path.join(DATA, arquivo)
        try:
            df = pd.read_csv(caminho)
        except Exception as e:
            print(f"  ⚠️ Não foi possível ler {arquivo}: {e}")
            continue
        if df.empty:
            continue
        frames.append((arquivo, df))
    return frames

def padronizar(df, arquivo):
    """Garante que o DataFrame tenha todas as colunas do esquema unificado."""
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""
    # Converte ano para número quando possível
    if "ano" in df.columns:
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    return df[COLUNAS]

def deduplicar(df):
    """Dedup inter-fonte: por DOI extraído; fallback por título normalizado."""
    df = df.copy()
    df["_norm_titulo"] = df["titulo"].apply(_normalizar_titulo)
    df["_doi_limpo"] = df["doi"].apply(lambda d: _extract_doi(d))

    # 1) Dedup por DOI (quando presente)
    com_doi = df[df["_doi_limpo"] != ""].drop_duplicates(subset="_doi_limpo", keep="first")
    sem_doi = df[df["_doi_limpo"] == ""]

    # 2) Dedup por título normalizado (entre os sem DOI e os não-cobertos)
    vistos = set(com_doi["_norm_titulo"].dropna())
    resto = []
    for _, linha in sem_doi.iterrows():
        chave = linha["_norm_titulo"]
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resto.append(linha)
    sem_doi_df = pd.DataFrame(resto, columns=df.columns)

    resultado = pd.concat([com_doi, sem_doi_df], ignore_index=True)
    resultado = resultado.drop(columns=["_norm_titulo", "_doi_limpo"])
    return resultado

def registrar_auditoria(meta):
    trilha = os.path.join(DATA, "_auditoria_mineracao.json")
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

def executar_limpeza():
    print("🧹 Consolidando fontes mineradas...")
    fontes = carregar_fontes()
    if not fontes:
        print("⚠️ Nenhum CSV de fonte encontrado em data/.")
        return None

    padronizados = []
    for arquivo, df in fontes:
        if "fonte" not in df.columns or df["fonte"].isin(["", "NaN"]).all():
            # fonte não informada: infere do nome do arquivo
            df["fonte"] = arquivo.replace("producoes_", "").replace(".csv", "")
        p = padronizar(df, arquivo)
        print(f"  • {arquivo}: {len(p)} registros")
        padronizados.append(p)

    df_unificado = pd.concat(padronizados, ignore_index=True)
    print(f"  Total bruto (antes da dedup): {len(df_unificado)}")

    df_final = deduplicar(df_unificado)
    df_final = df_final.sort_values(["fonte", "ano"], ascending=[True, False])

    caminho = os.path.join(DATA, "producoes_mineradas.csv")
    df_final.to_csv(caminho, index=False, encoding="utf-8")
    print(f"✅ Base unificada: {len(df_final)} registros únicos em {caminho}")

    registrar_auditoria({
        "tipo": "limpeza_unificada",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_final": int(len(df_final)),
        "por_fonte": df_final["fonte"].value_counts().to_dict(),
        "por_ano": df_final["ano"].value_counts().sort_index().to_dict(),
        "por_idioma": df_final["idioma"].value_counts().to_dict(),
    })
    return df_final

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    executar_limpeza()
