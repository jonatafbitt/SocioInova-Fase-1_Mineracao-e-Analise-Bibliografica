import os
import shutil
import re
from pypdf import PdfReader

# --- CONFIGURAÇÃO ---
PASTA_ENTRADA = "C:/Users/jonat/analise_ifs/novos_pdfs"
PASTA_DESTINO = "C:/Users/jonat/analise_ifs/documentos_inovação"

# --- MAPEAMENTO INTEGRAL DA REDE FEDERAL ---
MAPA_CONTEUDO = {
    # NACIONAL
    "BRASIL": {"termos": ["MINISTÉRIO DA EDUCAÇÃO", "PRESIDÊNCIA DA REPÚBLICA", "DECRETO FEDERAL", "LEI FEDERAL"], "uf": "BR", "regiao": "BRASIL"},
    
    # NORDESTE
    "IFBA": {"termos": ["INSTITUTO FEDERAL DA BAHIA", "IFBA"], "uf": "BA", "regiao": "NORDESTE"},
    "IFBAIANO": {"termos": ["INSTITUTO FEDERAL BAIANO", "IF BAIANO"], "uf": "BA", "regiao": "NORDESTE"},
    "IFAL": {"termos": ["INSTITUTO FEDERAL DE ALAGOAS", "IFAL"], "uf": "AL", "regiao": "NORDESTE"},
    "IFCE": {"termos": ["INSTITUTO FEDERAL DO CEARÁ", "IFCE"], "uf": "CE", "regiao": "NORDESTE"},
    "IFMA": {"termos": ["INSTITUTO FEDERAL DO MARANHÃO", "IFMA"], "uf": "MA", "regiao": "NORDESTE"},
    "IFPB": {"termos": ["INSTITUTO FEDERAL DA PARAÍBA", "IFPB"], "uf": "PB", "regiao": "NORDESTE"},
    "IFPE": {"termos": ["INSTITUTO FEDERAL DE PERNAMBUCO", "IFPE"], "uf": "PE", "regiao": "NORDESTE"},
    "IFSERTÃOPE": {"termos": ["INSTITUTO FEDERAL DO SERTÃO PERNAMBUCANO", "IF SERTÃO", "IF SERTAO"], "uf": "PE", "regiao": "NORDESTE"},
    "IFPI": {"termos": ["INSTITUTO FEDERAL DO PIAUÍ", "IFPI"], "uf": "PI", "regiao": "NORDESTE"},
    "IFRN": {"termos": ["INSTITUTO FEDERAL DO RIO GRANDE DO NORTE", "IFRN"], "uf": "RN", "regiao": "NORDESTE"},
    "IFS": {"termos": ["INSTITUTO FEDERAL DE SERGIPE", "IFS"], "uf": "SE", "regiao": "NORDESTE"},

    # NORTE
    "IFAC": {"termos": ["INSTITUTO FEDERAL DO ACRE", "IFAC"], "uf": "AC", "regiao": "NORTE"},
    "IFAP": {"termos": ["INSTITUTO FEDERAL DO AMAPÁ", "IFAP"], "uf": "AP", "regiao": "NORTE"},
    "IFAM": {"termos": ["INSTITUTO FEDERAL DO AMAZONAS", "IFAM"], "uf": "AM", "regiao": "NORTE"},
    "IFPA": {"termos": ["INSTITUTO FEDERAL DO PARÁ", "IFPA"], "uf": "PA", "regiao": "NORTE"},
    "IFRO": {"termos": ["INSTITUTO FEDERAL DE RONDÔNIA", "IFRO"], "uf": "RO", "regiao": "NORTE"},
    "IFRR": {"termos": ["INSTITUTO FEDERAL DE RORAIMA", "IFRR"], "uf": "RR", "regiao": "NORTE"},
    "IFTO": {"termos": ["INSTITUTO FEDERAL DO TOCANTINS", "IFTO"], "uf": "TO", "regiao": "NORTE"},

    # SUDESTE
    "IFES": {"termos": ["INSTITUTO FEDERAL DO ESPÍRITO SANTO", "IFES"], "uf": "ES", "regiao": "SUDESTE"},
    "IFMG": {"termos": ["INSTITUTO FEDERAL DE MINAS GERAIS", "IFMG"], "uf": "MG", "regiao": "SUDESTE"},
    "IFNMG": {"termos": ["INSTITUTO FEDERAL DO NORTE DE MINAS", "IFNMG"], "uf": "MG", "regiao": "SUDESTE"},
    "IFSUDESTEMG": {"termos": ["FEDERAL DO SUDESTE DE MINAS", "IFSUDESTEMG"], "uf": "MG", "regiao": "SUDESTE"},
    "IFSULDEMINAS": {"termos": ["FEDERAL DO SUL DE MINAS", "IFSULDEMINAS"], "uf": "MG", "regiao": "SUDESTE"},
    "IFTM": {"termos": ["INSTITUTO FEDERAL DO TRIÂNGULO MINEIRO", "IFTM"], "uf": "MG", "regiao": "SUDESTE"},
    "CEFET-MG": {"termos": ["CEFET-MG", "CENTRO FEDERAL DE EDUCAÇÃO TECNOLÓGICA DE MINAS GERAIS"], "uf": "MG", "regiao": "SUDESTE"},
    "IFRJ": {"termos": ["INSTITUTO FEDERAL DO RIO DE JANEIRO", "IFRJ"], "uf": "RJ", "regiao": "SUDESTE"},
    "IFFLUMINENSE": {"termos": ["INSTITUTO FEDERAL FLUMINENSE", "IFFLUMINENSE"], "uf": "RJ", "regiao": "SUDESTE"},
    "CEFET-RJ": {"termos": ["CEFET-RJ", "CENTRO FEDERAL DE EDUCAÇÃO TECNOLÓGICA CELSO SUCKOW"], "uf": "RJ", "regiao": "SUDESTE"},
    "PEDROII": {"termos": ["COLÉGIO PEDRO II", "PEDRO II"], "uf": "RJ", "regiao": "SUDESTE"},
    "IFSP": {"termos": ["INSTITUTO FEDERAL DE SÃO PAULO", "IFSP"], "uf": "SP", "regiao": "SUDESTE"},

    # SUL
    "IFPR": {"termos": ["INSTITUTO FEDERAL DO PARANÁ", "IFPR"], "uf": "PR", "regiao": "SUL"},
    "UTFPR": {"termos": ["UNIVERSIDADE TECNOLÓGICA FEDERAL DO PARANÁ", "UTFPR"], "uf": "PR", "regiao": "SUL"},
    "IFRS": {"termos": ["INSTITUTO FEDERAL DO RIO GRANDE DO SUL", "IFRS"], "uf": "RS", "regiao": "SUL"},
    "IFSUL": {"termos": ["FEDERAL SUL-RIO-GRANDENSE", "IFSUL"], "uf": "RS", "regiao": "SUL"},
    "IFFARROUPILHA": {"termos": ["INSTITUTO FEDERAL FARROUPILHA", "IFFAR"], "uf": "RS", "regiao": "SUL"},
    "IFSC": {"termos": ["INSTITUTO FEDERAL DE SANTA CATARINA", "IFSC"], "uf": "SC", "regiao": "SUL"},
    "IFC": {"termos": ["INSTITUTO FEDERAL CATARINENSE", "IFC"], "uf": "SC", "regiao": "SUL"},

    # CENTRO-OESTE
    "IFB": {"termos": ["INSTITUTO FEDERAL DE BRASÍLIA", "IFB"], "uf": "DF", "regiao": "CENTRO-OESTE"},
    "IFG": {"termos": ["INSTITUTO FEDERAL DE GOIÁS", "IFG"], "uf": "GO", "regiao": "CENTRO-OESTE"},
    "IFGOIANO": {"termos": ["INSTITUTO FEDERAL GOIANO", "IF GOIANO"], "uf": "GO", "regiao": "CENTRO-OESTE"},
    "IFMT": {"termos": ["INSTITUTO FEDERAL DO MATO GROSSO", "IFMT"], "uf": "MT", "regiao": "CENTRO-OESTE"},
    "IFMS": {"termos": ["INSTITUTO FEDERAL DE MATO GROSSO DO SUL", "IFMS"], "uf": "MS", "regiao": "CENTRO-OESTE"}
}

def extrair_metadados_do_pdf(caminho_pdf):
    texto_inicio = ""
    try:
        reader = PdfReader(caminho_pdf)
        for i in range(min(2, len(reader.pages))):
            page_text = reader.pages[i].extract_text()
            if page_text:
                texto_inicio += page_text.upper()
    except Exception as e:
        print(f"Erro ao ler {caminho_pdf}: {e}")
    
    inst_detectada = "OUTROS"
    uf, regiao = "XX", "OUTROS"
    
    for inst, info in MAPA_CONTEUDO.items():
        if any(termo in texto_inicio for termo in info["termos"]):
            inst_detectada = inst
            uf = info["uf"]
            regiao = info["regiao"]
            break
            
    ano_match = re.search(r'20[0-2][0-9]', texto_inicio)
    ano = ano_match.group(0) if ano_match else "0000"
    
    return inst_detectada, uf, regiao, ano

def organizar_inteligente():
    if not os.path.exists(PASTA_ENTRADA): 
        os.makedirs(PASTA_ENTRADA)
        return

    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith(".pdf")]
    
    for arquivo in arquivos:
        caminho_original = os.path.join(PASTA_ENTRADA, arquivo)
        inst, uf, regiao, ano = extrair_metadados_do_pdf(caminho_original)
        
        if ano == "0000":
            ano_match = re.search(r'20[0-2][0-9]', arquivo)
            ano = ano_match.group(0) if ano_match else "0000"

        nome_limpo = arquivo.replace(".pdf", "").replace(".PDF", "").strip()
        nome_limpo = nome_limpo.replace(ano, "").replace(inst, "").strip("- ")
        
        novo_nome = f"{ano} - {inst} - {nome_limpo}.pdf"
        
        if inst == "BRASIL":
            caminho_final = os.path.join(PASTA_DESTINO, "BRASIL")
        else:
            caminho_final = os.path.join(PASTA_DESTINO, regiao, uf, inst)
        
        os.makedirs(caminho_final, exist_ok=True)
        
        try:
            shutil.move(caminho_original, os.path.join(caminho_final, novo_nome))
            print(f"✅ Processado: {inst} ({uf}) | {novo_nome}")
        except Exception as e:
            print(f"❌ Erro ao mover {arquivo}: {e}")

if __name__ == "__main__":
    print("Iniciando Organização Inteligente...")
    organizar_inteligente()
    print("Processo concluído.")