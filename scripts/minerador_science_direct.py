import pandas as pd
import os
import json
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

def minerar_science_direct(query='"Sociology of Innovation" AND "Governance"', limite=25):
    # 1. Carregar chaves do config.json
    with open('config.json') as f:
        config = json.load(f)
    
    client = ElsClient(config['091553141c51cd1385131384dc008f91'])
    if config.get('insttoken'):
        client.inst_token = config['insttoken']

    print(f"Iniciando busca na ScienceDirect: {query}")
    
    # 2. Executar a busca
    doc_srch = ElsSearch(query, 'sciencedirect')
    doc_srch.execute(client, get_all=False)
    
    if doc_srch.results:
        # 3. Processar e Padronizar
        lista_final = []
        for doc in doc_srch.results:
            # ScienceDirect usa nomes de campos levemente diferentes
            lista_final.append({
                'titulo': doc.get('dc:title'),
                'ano': doc.get('webapp:publication-date', '0000')[:4],
                'citacoes': doc.get('citedby-count', 0),
                'doi': doc.get('prism:doi'),
                'resumo': doc.get('dc:description', 'Resumo não disponível via API.')
            })
        
        df = pd.DataFrame(lista_final)
        
        # Salvar na pasta data
        caminho_csv = os.path.join('data', 'producoes_sciencedirect.csv')
        df.to_csv(caminho_csv, index=False, encoding='utf-8')
        
        print(f"Sucesso! {len(df)} artigos da ScienceDirect salvos.")
        return df
    else:
        print("Nenhum resultado encontrado.")
        return None

if __name__ == "__main__":
    # Query focada no seu tema
    termo_busca = '"Sociology of Innovation" AND "Federal Institute"'
    minerar_science_direct(termo_busca)