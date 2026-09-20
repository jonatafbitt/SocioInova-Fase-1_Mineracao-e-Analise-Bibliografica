"""Pré-computação do Estado da Arte da Inovação (batch, com progresso).

Gera, a partir da base consolidada, os artefatos analíticos do estado da arte:
  * data/dna_inovacao.csv
  * data/indices_estado_arte.csv
  * data/coocorrencia_estado_arte.json
  * data/_sintese_estado_arte.json   (síntese IA nacional + internacional)
  * data/_sintese_sentidos.txt       (síntese semiótica de sentidos)

Roda em background com progresso gravado em data/_progresso_estado_arte.txt.
O dashboard apenas lê esses artefatos (agilidade). Uso:
    python scripts/gerar_estado_arte.py [modelo]
"""

import os
import sys
import time
import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import sintese_estado_arte as sea

ARQ_PROGRESSO = os.path.join("data", "_progresso_estado_arte.txt")
ARQ_SENTIDOS = os.path.join("data", "_sintese_sentidos.txt")

def _prog(msg):
    with open(ARQ_PROGRESSO, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    print(msg, flush=True)

def main():
    modelo = sys.argv[1] if len(sys.argv) > 1 else "qwen2:1.5b"
    os.makedirs("data", exist_ok=True)
    # zera progresso anterior
    open(ARQ_PROGRESSO, "w", encoding="utf-8").close()

    _prog("Iniciando pré-computação do Estado da Arte...")
    _prog(f"Modelo: {modelo}")

    _prog("1/3 Preparando índices...")
    ind = sea.preparar_indices()
    _prog(f"   {len(ind)} registros indexados; DNA salvo.")

    _prog("2/3 Construindo matriz de co-ocorrência...")
    sea.construir_coocorrencia(ind)
    _prog("   Co-ocorrência salva.")

    _prog("3/3 Gerando síntese do estado da arte (pode levar alguns minutos)...")
    t0 = time.time()
    payload, do_cache = sea.gerar_sintese(ind, modelo, forcar=True)
    _prog(f"   Síntese concluída em {round(time.time()-t0,1)}s ({'cache' if do_cache else 'nova'}).")

    _prog("Bônus: síntese de sentidos (semiótica)...")
    sentidos = sea.gerar_sintese_sentidos(ind, modelo)
    with open(ARQ_SENTIDOS, "w", encoding="utf-8") as f:
        f.write(sentidos)
    _prog("   Síntese de sentidos salva.")

    _prog("✅ Pré-computação concluída. Recortes: "
          + ", ".join(payload["recortes"].keys()))

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
