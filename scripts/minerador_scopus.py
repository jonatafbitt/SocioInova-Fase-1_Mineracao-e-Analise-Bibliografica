from pybliometrics.scopus import ScopusSearch
import pandas as pd
import os

def minerar_scopus(query="TITLE-ABS-KEY(Sociology AND Innovation)", limite=20):
    print(f"Iniciando busca na Scopus: {query}")
    
    # Executa a busca
    res = ScopusSearch(query, refresh=True)
    
    # Transforma em DataFrame
    df_scopus = pd.DataFrame(res.results)
    
    if not df_scopus.empty:
        # Padronizando colunas para o seu Dashboard
        df_final = pd.DataFrame()
        df_final['titulo'] = df_scopus['title']
        df_final['ano'] = df_scopus['coverDate'].str.slice(0, 4) # Pega só o ano
        df_final['citacoes'] = df_scopus['citedby_count']
        df_final['doi'] = df_scopus['doi']
        df_final['resumo'] = df_scopus['description'] # Na Scopus 'description' costuma ser o abstract
        
        # Salva na sua pasta de dados
        caminho_csv = os.path.join('data', 'producoes_scopus.csv')
        df_final.head(limite).to_csv(caminho_csv, index=False, encoding='utf-8')
        
        print(f"Sucesso! {len(df_final.head(limite))} registros da Scopus salvos.")
        return df_final
    else:
        print("Nenhum resultado encontrado na Scopus.")
        return None

if __name__ == "__main__":
    # Exemplo de busca focada em Institutos Federais e Inovação
    query_tese = 'TITLE-ABS-KEY("Federal Institute" AND "Innovation" AND "Brazil")'
    minerar_scopus(query_tese)