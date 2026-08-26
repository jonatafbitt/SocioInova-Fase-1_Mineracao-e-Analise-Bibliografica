import requests
import pandas as pd
import os
import time
import asyncio
import aiohttp
from collections import Counter
from tqdm import tqdm

# ======================================================
# CONFIGURAÇÃO DE TERMOS MULTILINGUES (VERSÃO LIMPA)
# ======================================================
cerne = [
    # Inglês (Apertamos o funil: saem as palavras soltas genéricas)
    '"Sociology of Innovation"', '"Innovation Policy"', '"Public Governance"', '"Federal Institute"',
    
    # Português (Mantemos aberto, pois o volume global é menor)
    '"Sociologia da Inovação"', '"Inovação"', '"Políticas Públicas"', '"Governança"', '"Institutos Federais"', '"IFBA"',
    
    # Francês
    '"Sociologie de l\'innovation"', '"Gouvernance"',
    
    # Espanhol
    '"Sociología de la innovación"', '"Gobernanza"',
    
    # Alemão
    '"Innovationssoziologie"'
]

complementos = [
    # Inglês
    '"Social Innovation"', '"Decolonial"', '"Post-colonial"', '"Brazil"',
    
    # Português
    '"Inovação Social"', '"Brasil"', '"Decolonial"', '"Tecnologia Social"',
    
    # Francês
    '"L\'innovation sociale"', '"Décoloniale"', '"Brésil"',
    
    # Espanhol
    '"Innovación Social"'
]

query_cerne = f"({' OR '.join(cerne)})"
query_complementos = f"({' OR '.join(complementos)})"
QUERY_FINAL = f"{query_cerne} AND {query_complementos}"

# Agora configuramos para buscar 2 páginas de 200 resultados
RESULTADOS_POR_PAGINA = 200
TOTAL_PAGINAS = 2 
# ======================================================

def obter_perfil_conceitual_if(institution_id='I165735391', limite=200):
    """
    Mapeia a prevalência de conceitos científicos de um IF (Ex: IFBA)
    focando nas obras MAIS CITADAS (DNA histórico) e conceitos mais granulares.
    """
    url = "https://api.openalex.org/works"
    params = {
        'filter': f'institutions.id:{institution_id}',
        'per_page': limite,
        'select': 'display_name,concepts,publication_year,cited_by_count',
        # MUDANÇA 1: Buscamos o núcleo histórico de impacto (obras mais citadas)
        'sort': 'cited_by_count:desc' 
    }
    
    print(f"🧬 Mapeando DNA científico profundo da instituição (ID: {institution_id})...")
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200: 
            print(f"⚠️ API retornou status {response.status_code}")
            return None

        results = response.json().get('results', [])
        concepts_list = []
        
        for work in results:
            for concept in work.get('concepts', []):
                # MUDANÇA 2: Descemos até o Nível 2 para pegar conceitos mais específicos 
                # como 'Innovation policy' ou 'Public administration'
                if concept.get('level') <= 2:
                    concepts_list.append(concept.get('display_name'))
        
        contagem = Counter(concepts_list)
        return dict(contagem.most_common(15))
    except Exception as e:
        print(f"❌ Erro no mapeamento conceitual: {e}")
        return None
def reconstruir_abstract(inverted_index):
    if not inverted_index:
        return "Resumo não disponível."
    try:
        max_pos = max([pos for positions in inverted_index.values() for pos in positions])
        texto_reconstruido = [None] * (max_pos + 1)
        for palavra, posicoes in inverted_index.items():
            for pos in posicoes:
                texto_reconstruido[pos] = palavra
        return ' '.join([palavra for palavra in texto_reconstruido if palavra is not None])
    except Exception:
        return "Erro ao processar resumo."

def executar_mineracao():
    url = "https://api.openalex.org/works"
    lista_final_obras = []
    
    print(f"🛰️ Iniciando mineração extensiva (Alvo: {RESULTADOS_POR_PAGINA * TOTAL_PAGINAS} artigos)...")

    for pagina in range(1, TOTAL_PAGINAS + 1):
        params = {
            'search': QUERY_FINAL,
            'per_page': RESULTADOS_POR_PAGINA,
            'page': pagina,
            'sort': 'cited_by_count:desc'
        }
        
        print(f"📄 Coletando página {pagina} de {TOTAL_PAGINAS}...")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            results = response.json().get('results', [])
            
            if not results:
                print(f"ℹ️ Fim dos resultados na página {pagina}.")
                break

            for obra in results:
                resumo = reconstruir_abstract(obra.get('abstract_inverted_index'))
                autores_lista = [a.get('author', {}).get('display_name') for a in obra.get('authorships', [])]
                autores_str = ", ".join([a for a in autores_lista if a])

                lista_final_obras.append({
                    'id': obra.get('id'),
                    'titulo': obra.get('display_name'),
                    'ano': obra.get('publication_year'),
                    'autores': autores_str,
                    'citacoes': obra.get('cited_by_count'),
                    'doi': obra.get('doi'),
                    'resumo': resumo,
                    'idioma': obra.get('language')
                })
            
            # Pequena pausa para não sobrecarregar a API
            time.sleep(1)

        except Exception as e:
            print(f"❌ Erro na página {pagina}: {e}")
            break

    if lista_final_obras:
        df = pd.DataFrame(lista_final_obras)
        # Remove duplicatas caso o OpenAlex repita algum ID entre páginas
        df = df.drop_duplicates(subset='id')
        
        caminho_csv = os.path.join('data', 'producoes_mineradas.csv')
        df.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f"✅ SUCESSO: {len(df)} artigos únicos salvos em {caminho_csv}")
        return df
    else:
        print("⚠️ Nenhum dado coletado.")
        return None

async def executar_mineracao_assincrona():
    """Versão assíncrona da mineração OpenAlex usando aiohttp com barra de progresso."""
    url = "https://api.openalex.org/works"
    query_cerne = '("Sociology of Innovation" OR "Innovation Policy" OR "Public Governance" OR "Federal Institute") AND ("Sociology of Innovation" OR "Innovation" OR "Public Governance" OR "Federal Institute" OR "Brazil" OR "IFBA")'
    query_complementos = '("Social Innovation" OR "Decolonial" OR "Post-colonial" OR "Brazil")'
    QUERY_FINAL = f"{query_cerne} AND {query_complementos}"
    
    RESULTADOS_POR_PAGINA = 200
    TOTAL_PAGINAS = 2
    
    print(f"🛰️ Iniciando mineração assíncrona (Alvo: {RESULTADOS_POR_PAGINA * TOTAL_PAGINAS} artigos)...")
    
    todas_obras = []
    
    async with aiohttp.ClientSession() as session:
        # Barra de progresso
        progress_bar = tqdm(total=TOTAL_PAGINAS, desc="Mineração OpenAlex", unit="página")
        
        for pagina in range(1, TOTAL_PAGINAS + 1):
            params = {
                'search': QUERY_FINAL,
                'per_page': RESULTADOS_POR_PAGINA,
                'page': pagina,
                'sort': 'cited_by_count:desc'
            }
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    dados = await response.json()
                    results = dados.get('results', [])
                    
                    for obra in results:
                        resumo = reconstruir_abstract(obra.get('abstract_inverted_index'))
                        autores_lista = [a.get('author', {}).get('display_name') for a in obra.get('authorships', [])]
                        autores_str = ", ".join([a for a in autores_lista if a])
                        
                        todas_obras.append({
                            'id': obra.get('id'),
                            'titulo': obra.get('display_name'),
                            'ano': obra.get('publication_year'),
                            'autores': autores_str,
                            'citacoes': obra.get('cited_by_count'),
                            'doi': obra.get('doi'),
                            'resumo': resumo,
                            'idioma': obra.get('language')
                        })
                    
                    progress_bar.update(1)
                    # Pequena pausa respeitosa para não sobrecarregar a API
                    await asyncio.sleep(0.5)
                else:
                    print(f"⚠️ API retornou status {response.status} na página {pagina}")
                    progress_bar.close()
                    return None
    
    progress_bar.close()
    
    if todas_obras:
        df = pd.DataFrame(todas_obras)
        # Remove duplicatas caso o OpenAlex repita algum ID entre páginas
        df = df.drop_duplicates(subset='id')
        
        caminho_csv = os.path.join('data', 'producoes_mineradas.csv')
        df.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f"✅ SUCESSO: {len(df)} artigos únicos salvos em {caminho_csv}")
        return df
    else:
        print("⚠️ Nenhum dado coletado.")
        return None

def executar_fluxo_completo():
    # 1. Roda a mineração dos artigos
    df_minerado = asyncio.run(executar_mineracao_assincrona())
    
    # 2. Roda a extração do DNA Científico (IFBA)
    perfil_ifba = obter_perfil_conceitual_if('I165735391')
    if perfil_ifba:
        df_perfil = pd.DataFrame(list(perfil_ifba.items()), columns=['Conceito', 'Frequência'])
        df_perfil.to_csv('data/perfil_institucional.csv', index=False)
        print("✅ SUCESSO: Perfil Institucional salvo para o Dashboard.")

    # 3. Gera relatório de status
    if df_minerado is not None:
        print(f"\n=== Relatório de Mineração ===")
        print(f"Total de artigos únicos: {len(df_minerado)}")
        print(f"Anos cobertos: {sorted(df_minerado['ano'].tolist())}")
        print(f"Idiomas: {df_minerado['idioma'].value_counts().to_dict()}")
        print(f"Top 5 autores: {df_minerado['autores'].head().tolist()}")

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    executar_fluxo_completo()