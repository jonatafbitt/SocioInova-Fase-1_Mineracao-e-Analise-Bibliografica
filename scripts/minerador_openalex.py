import requests
import pandas as pd
import os
import time
import asyncio
import aiohttp
from collections import Counter
from tqdm import tqdm

# ======================================================
# CONFIGURAÇÃO DE TERMOS MULTILINGUES (VERSÃO AMPLIADA)
# ======================================================
# Núcleo temático: foca no cruzamento entre inovação e sociologia
cerne = [
    # Inglês (Apertamos o funil: saem as palavras soltas genéricas)
    '"Sociology of Innovation"', '"Innovation Policy"', '"Public Governance"', '"Federal Institute"',
    '"Innovation Governance"', '"Public Innovation"', '"Innovation Technology"', '"Social Technology"',

    # Português (Mantemos aberto, pois o volume global é menor)
    '"Sociologia da Inovação"', '"Inovação"', '"Políticas Públicas"', '"Governança"', '"Institutos Federais"', '"IFBA"',
    '"Governança da Inovação"', '"Tecnologia Social"', '"Economia Solidária"', '"Inovação Pública"',

    # Francês
    '"Sociologie de l\'innovation"', '"Gouvernance"', '"Gouvernance de l\'innovation"', '"Innovation publique"',

    # Espanhol
    '"Sociología de la innovación"', '"Gobernanza"', '"Gobernanza de la innovación"',

    # Alemão
    '"Innovationssoziologie"'
]

# Complementos: adicionam a lente sociológica/emancipadora e o recorte brasileiro
complementos = [
    # Inglês
    '"Social Innovation"', '"Decolonial"', '"Post-colonial"', '"Brazil"', '"Solidarity Economy"',
    '"Emancipatory Innovation"', '"Innovation in Public Policy"', '"Public Innovation Policy"',

    # Português
    '"Inovação Social"', '"Brasil"', '"Decolonial"', '"Tecnologia Social"', '"Economia Solidária"',
    '"Inovação em Políticas Públicas"', '"Perspectivas Emancipadoras"', '"Políticas de Inovação"', '"IFBA"',

    # Francês
    '"L\'innovation sociale"', '"Décoloniale"', '"Brésil"', '"Économie solidaire"', '"Technologie sociale"',

    # Espanhol
    '"Innovación Social"', '"Economía solidaria"', '"Tecnología social"', '"Innovación emancipadora"'
]

# Novos grupos temáticos focados na lente sociológica da inovação
tema_economia_solidaria = [
    # Inglês
    '"Solidarity Economy"', '"Cooperative Economy"', '"Solidarity-based economy"',
    # Português
    '"Economia Solidária"', '"Economia Cooperativa"',
    # Francês
    '"Économie solidaire"', '"Économie sociale et solidaire"',
    # Espanhol
    '"Economía solidaria"'
]

tema_tecnologia_social = [
    # Inglês
    '"Social Technology"', '"Appropriate Technology"', '"Technology for Social Inclusion"',
    # Português
    '"Tecnologia Social"', '"Tecnologia Apropriada"', '"Tecnologia para Inclusão Social"',
    # Francês
    '"Technologie sociale"', '"Technologie appropriée"',
    # Espanhol
    '"Tecnología social"', '"Tecnología apropiada"'
]

tema_inovacao_politicas_publicas = [
    # Inglês
    '"Innovation in Public Policy"', '"Public Innovation Policy"', '"Policy Innovation"',
    # Português
    '"Inovação em Políticas Públicas"', '"Políticas de Inovação"', '"Inovação na Administração Pública"',
    # Francês
    '"Innovation politique publique"', '"Politiques d\'innovation publique"',
    # Espanhol
    '"Innovación en políticas públicas"', '"Políticas de innovación"'
]

tema_governanca_inovacao = [
    # Inglês
    '"Innovation Governance"', '"Governance of Innovation"', '"Innovation Management"',
    # Português
    '"Governança da Inovação"', '"Gestão da Inovação"',
    # Francês
    '"Gouvernance de l\'innovation"', '"Gestion de l\'innovation"',
    # Espanhol
    '"Gobernanza de la innovación"', '"Gestión de la innovación"'
]

tema_emancipacao_inovacao = [
    # Inglês
    '"Emancipatory Innovation"', '"Critical Innovation Studies"', '"Alternative Innovation"',
    # Português
    '"Perspectivas Emancipadoras"', '"Inovação Emancipatória"', '"Estudos Críticos da Inovação"',
    # Francês
    '"Perspectives émancipatrices"', '"Innovation émancipatrice"',
    # Espanhol
    '"Perspectivas emancipadoras"', '"Innovación emancipadora"'
]

tema_inovacao_instituto_publico = [
    # Inglês
    '"Federal Institute"', '"Public Institution Innovation"', '"Innovation in Public Sector"', '"Federal Institute of Education"',
    # Português
    '"Institutos Federais"', '"IFBA"', '"Rede Federal"', '"Instituição Pública de Ensino"', '"Inovação no Setor Público"',
    # Francês
    '"Institut fédéral"', '"Innovation dans le secteur public"',
    # Espanhol
    '"Instituto federal"', '"Innovación en el sector público"'
]

query_cerne = f"({' OR '.join(cerne)})"
query_complementos = f"({' OR '.join(complementos)})"
QUERY_FINAL = f"{query_cerne} AND {query_complementos}"

# Queries temáticas específicas, para mineração focada por eixo temático
QUERY_ECONOMIA_SOLIDARIA = f"({' OR '.join(tema_economia_solidaria)}) AND (innovation OR inovação OR innovación)"
QUERY_TECNOLOGIA_SOCIAL = f"({' OR '.join(tema_tecnologia_social)})"
QUERY_INOVACAO_POLITICAS_PUBLICAS = f"({' OR '.join(tema_inovacao_politicas_publicas)})"
QUERY_GOVERNANCA_INOVACAO = f"({' OR '.join(tema_governanca_inovacao)})"
QUERY_EMANCIPACAO_INOVACAO = f"({' OR '.join(tema_emancipacao_inovacao)})"
QUERY_INOVACAO_INSTITUTO_PUBLICO = f"({' OR '.join(tema_inovacao_instituto_publico)})"

# Dicionário com os eixos temáticos para classificação pós-mineração
EIXOS_TEMATICOS = {
    'economia_solidaria': tema_economia_solidaria,
    'tecnologia_social': tema_tecnologia_social,
    'inovacao_politicas_publicas': tema_inovacao_politicas_publicas,
    'governanca_inovacao': tema_governanca_inovacao,
    'emancipacao_inovacao': tema_emancipacao_inovacao,
    'inovacao_instituto_publico': tema_inovacao_instituto_publico,
}

# Agora configuramos para buscar 2 páginas de 200 resultados
RESULTADOS_POR_PAGINA = 200
TOTAL_PAGINAS = 2 
# ======================================================

def obter_perfil_conceitual_if(institution_id='I165735391', limite=200):
    """
    Mapeia a prevalência de conceitos científicos de um IF (Ex: IFBA)
    focando nas obras MAIS CITADAS (DNA histórico) e conceitos granulares.
    Inclui conceitos de nível 1-3 e prioriza conceitos ligados à inovação.
    """
    url = "https://api.openalex.org/works"
    params = {
        'filter': f'institutions.id:{institution_id}',
        'per_page': limite,
        'select': 'display_name,concepts,publication_year,cited_by_count',
        'sort': 'cited_by_count:desc' 
    }
    
    print(f"🧬 Mapeando DNA científico profundo da instituição (ID: {institution_id})...")

    # Conceitos de interesse prioritário (ligados à inovação e sociologia)
    conceitos_prioritarios = [
        'innovation', 'innovation policy', 'public administration', 'social innovation',
        'technology assessment', 'sociology', 'governance', 'technology', 'economic growth',
        'political economy', 'public sector', 'management', 'entrepreneurship', 'tacit knowledge',
        'knowledge economy', 'social science', 'economic system', 'democracy', 'welfare',
        'cooperative', 'solidarity economy', 'social technology', 'decolonization'
    ]

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200: 
            print(f"⚠️ API retornou status {response.status_code}")
            return None

        results = response.json().get('results', [])
        concepts_list = []
        
        for work in results:
            for concept in work.get('concepts', []):
                nome = concept.get('display_name', '').lower()
                nivel = concept.get('level')
                # Inclui conceitos de nível 1-3, priorizando os ligados à inovação
                if nivel <= 3 or any(p in nome for p in conceitos_prioritarios):
                    concepts_list.append(concept.get('display_name'))
        
        contagem = Counter(concepts_list)
        # Retorna top 30 conceitos
        return dict(contagem.most_common(30))
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

def _normalizar_texto(texto):
    """Remove acentos e coloca em minúsculas para comparação textual robusta."""
    import unicodedata
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii').lower()

def classificar_eixo_tematico(obra):
    """
    Classifica uma obra nos eixos temáticos definidos, com base no título e resumo.
    Retorna uma lista de eixos temáticos associados à obra.
    """
    texto_analise = _normalizar_texto(f"{obra.get('titulo', '')} {obra.get('resumo', '')}")
    eixos_encontrados = []

    for eixo, termos in EIXOS_TEMATICOS.items():
        for termo in termos:
            termo_normalizado = _normalizar_texto(termo.strip('"'))
            if termo_normalizado and termo_normalizado in texto_analise:
                eixos_encontrados.append(eixo)
                break

    return ";".join(eixos_encontrados) if eixos_encontrados else "geral"

async def coletar_pagina_async(session, url, query, pagina):
    """Coleta uma única página da API OpenAlex de forma assíncrona."""
    params = {
        'search': query,
        'per_page': RESULTADOS_POR_PAGINA,
        'page': pagina,
        'sort': 'cited_by_count:desc'
    }

    async with session.get(url, params=params, timeout=30) as response:
        if response.status == 200:
            dados = await response.json()
            return dados.get('results', [])
        print(f"⚠️ API retornou status {response.status} na página {pagina}")
        return None

def processar_obra(obra):
    """Converte uma obra bruta da OpenAlex em um registro estruturado."""
    resumo = reconstruir_abstract(obra.get('abstract_inverted_index'))
    autores_lista = [a.get('author', {}).get('display_name') for a in obra.get('authorships', [])]
    autores_str = ", ".join([a for a in autores_lista if a])

    record = {
        'id': obra.get('id'),
        'titulo': obra.get('display_name'),
        'ano': obra.get('publication_year'),
        'autores': autores_str,
        'citacoes': obra.get('cited_by_count'),
        'doi': obra.get('doi'),
        'resumo': resumo,
        'idioma': obra.get('language')
    }
    record['eixo_tematico'] = classificar_eixo_tematico(record)
    return record

async def executar_mineracao_assincrona():
    """Versão assíncrona da mineração OpenAlex usando aiohttp, percorrendo
    o query principal e as queries temáticas. Classifica cada obra em eixos."""
    url = "https://api.openalex.org/works"
    
    # Combina a query principal com as queries temáticas específicas
    queries = [QUERY_FINAL, QUERY_ECONOMIA_SOLIDARIA, QUERY_TECNOLOGIA_SOCIAL,
               QUERY_INOVACAO_POLITICAS_PUBLICAS, QUERY_GOVERNANCA_INOVACAO,
               QUERY_EMANCIPACAO_INOVACAO, QUERY_INOVACAO_INSTITUTO_PUBLICO]
    
    total_paginas = len(queries) * TOTAL_PAGINAS
    print(f"🛰️ Iniciando mineração assíncrona (Alvo: {len(queries)} queries x {TOTAL_PAGINAS} páginas)...")
    
    todas_obras = []
    ids_ja_vistos = set()
    
    async with aiohttp.ClientSession() as session:
        progress_bar = tqdm(total=total_paginas, desc="Mineração OpenAlex", unit="página")
        
        for query in queries:
            for pagina in range(1, TOTAL_PAGINAS + 1):
                results = await coletar_pagina_async(session, url, query, pagina)
                if results is None:
                    progress_bar.close()
                    break
                
                if not results:
                    progress_bar.update(1)
                    continue
                
                for obra in results:
                    obra_id = obra.get('id')
                    if obra_id and obra_id not in ids_ja_vistos:
                        ids_ja_vistos.add(obra_id)
                        todas_obras.append(processar_obra(obra))
                
                progress_bar.update(1)
                # Pequena pausa respeitosa para não sobrecarregar a API
                await asyncio.sleep(0.5)
            else:
                continue
            break
        
        progress_bar.close()
    
    if todas_obras:
        df = pd.DataFrame(todas_obras)
        df = df.drop_duplicates(subset='id')
        
        caminho_csv = os.path.join('data', 'producoes_mineradas.csv')
        df.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f"✅ SUCESSO: {len(df)} artigos únicos salvos em {caminho_csv}")
        return df
    else:
        print("⚠️ Nenhum dado coletado.")
        return None

def executar_fluxo_completo():
    # 1. Roda a mineração dos artigos (aberta a toda a Rede Federal)
    df_minerado = asyncio.run(executar_mineracao_assincrona())
    
    # 2. Roda a extração do DNA Científico da Rede Federal (IFBA + demais IFs)
    ifba_id = 'I165735391'  # IFBA
    ids_institutos = [
        'I165735391',  # IFBA
        'I2059774197', # IFMG (exemplo)
        'I4210129444', # IFRN (exemplo)
        'I41187327',   # IFSUL (exemplo)
        'I2803300026', # IFSC (exemplo)
        'I4210116772', # IF Goiano (exemplo)
        'I4210129440', # IFC (exemplo)
        'I4210136515', # IFES (exemplo)
    ]

    print(f"🏛️ Mapeando DNA científico da Rede Federal de Educação Profissional e Tecnológica...")
    perfil_rede = {}
    for inst_id in ids_institutos:
        perfil = obter_perfil_conceitual_if(inst_id, limite=200)
        if perfil:
            for conceito, freq in perfil.items():
                perfil_rede[conceito] = perfil_rede.get(conceito, 0) + freq

    if perfil_rede:
        # Classifica em ordem decrescente de frequência
        perfil_ordenado = sorted(perfil_rede.items(), key=lambda x: x[1], reverse=True)[:30]
        df_perfil = pd.DataFrame(perfil_ordenado, columns=['Conceito', 'Frequência'])
        df_perfil.to_csv('data/perfil_institucional.csv', index=False)
        print("✅ SUCESSO: Perfil Institucional (Rede Federal) salvo para o Dashboard.")

    # 3. Gera relatório de status
    if df_minerado is not None:
        print(f"\n=== Relatório de Mineração ===")
        print(f"Total de artigos únicos: {len(df_minerado)}")
        print(f"Anos cobertos: {sorted(df_minerado['ano'].tolist())}")
        print(f"Idiomas: {df_minerado['idioma'].value_counts().to_dict()}")
        if 'eixo_tematico' in df_minerado.columns:
            print(f"Eixos temáticos: {df_minerado['eixo_tematico'].value_counts().head(10).to_dict()}")
        print(f"Top 5 autores: {df_minerado['autores'].head().tolist()}")

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    executar_fluxo_completo()