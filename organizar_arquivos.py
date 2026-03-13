import os
import shutil
import re

# --- CONFIGURAÇÃO ---
PASTA_ENTRADA = "C:/Users/jonat/analise_ifs/novos_pdfs"  # Onde você coloca os arquivos brutos
PASTA_DESTINO = "C:/Users/jonat/analise_ifs/documentos_inovação"

# Exemplo de lista para renomeio (Dicionário: "parte_do_nome_original": "Instituição")
# Isso ajuda o script a saber para qual pasta mover o arquivo
MAPA_INSTITUICOES = {
    "ifba": "IFBA",
    "ifbaiano": "IFBAIANO",
    "sertao": "IFSERTAO",
    "brasil": "BRASIL",
    "federal": "BRASIL"
}

def organizar_e_renomear():
    if not os.path.exists(PASTA_ENTRADA):
        print(f"Erro: A pasta {PASTA_ENTRADA} não existe.")
        return

    for arquivo in os.listdir(PASTA_ENTRADA):
        if arquivo.endswith(".pdf"):
            caminho_completo = os.path.join(PASTA_ENTRADA, arquivo)
            
            # 1. Extrair Ano (procura 4 dígitos)
            ano_match = re.search(r'20[0-2][0-9]', arquivo)
            ano = ano_match.group(0) if ano_match else "0000"
            
            # 2. Identificar Instituição e UF (Lógica simplificada)
            inst_selecionada = "OUTROS"
            uf = "XX"
            regiao = "OUTROS"
            
            for chave, nome_limpo in MAPA_INSTITUICOES.items():
                if chave.lower() in arquivo.lower():
                    inst_selecionada = nome_limpo
                    # Define UF e Região baseado na instituição (Exemplos)
                    if nome_limpo in ["IFBA", "IFBAIANO"]: uf, regiao = "BA", "NORDESTE"
                    elif nome_limpo == "IFSERTAO": uf, regiao = "PE", "NORDESTE"
                    elif nome_limpo == "BRASIL": uf, regiao = "BR", "BRASIL"
                    break
            
            # 3. Limpar nome da Resolução (Pega o que vem após o ano ou termos comuns)
            # Remove extensões e caracteres estranhos para o novo padrão
            nome_limpo_res = arquivo.replace(".pdf", "").replace(ano, "").strip("- ")
            
            novo_nome = f"{ano} - {inst_selecionada} - {nome_limpo_res}.pdf"
            
            # 4. Criar estrutura de pastas se não existir
            if inst_selecionada == "BRASIL":
                caminho_final = os.path.join(PASTA_DESTINO, "BRASIL")
            else:
                caminho_final = os.path.join(PASTA_DESTINO, regiao, uf, inst_selecionada)
            
            os.makedirs(caminho_final, exist_ok=True)
            
            # 5. Mover e Renomear
            shutil.move(caminho_completo, os.path.join(caminho_final, novo_nome))
            print(f"Sucesso: {arquivo} -> {novo_nome}")

if __name__ == "__main__":
    organizar_e_renomear()