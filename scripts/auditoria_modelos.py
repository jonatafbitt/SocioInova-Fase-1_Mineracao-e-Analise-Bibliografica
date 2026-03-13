import ollama
from fpdf import FPDF
import pandas as pd
import os

def consultar_modelo(modelo, prompt):
    try:
        response = ollama.chat(model=modelo, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Erro no modelo {modelo}: {e}"

def gerar_pdf_auditoria(titulo_artigo, resumo_texto):
    modelos = ["llama3", "mistral"]
    prompt = f"""
    Como um especialista em Sociologia da Inovação, analise este resumo:
    Título: {titulo_artigo}
    Resumo: {resumo_texto}
    
    Identifique os principais conceitos de GOVERNANÇA presentes no texto.
    """

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Auditoria: Sociologia da Inovacao", ln=True, align='C')
    pdf.ln(10)

    # Informações do Artigo
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"Artigo: {titulo_artigo[:80]}...", ln=True)
    pdf.ln(5)

    for mod in modelos:
        print(f"Consultando {mod}...")
        resposta = consultar_modelo(mod, prompt)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, f"Analise do Modelo: {mod.upper()}", ln=True, fill=True)
        
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, resposta)
        pdf.ln(5)

    if not os.path.exists('relatorios'):
        os.makedirs('relatorios')
        
    caminho_pdf = os.path.join('relatorios', 'auditoria_governanca.pdf')
    pdf.output(caminho_pdf)
    return caminho_pdf

if __name__ == "__main__":
    # Carrega o último arquivo minerado para teste
    caminho_csv = os.path.join('data', 'producoes_mineradas.csv')
    if os.path.exists(caminho_csv):
        df = pd.read_csv(caminho_csv)
        artigo = df.iloc[0] # Pega o primeiro artigo para o teste
        print("Iniciando auditoria comparativa...")
        relatorio = gerar_pdf_auditoria(artigo['titulo'], artigo['resumo'])
        print(f"Relatorio gerado com sucesso em: {relatorio}")
    else:
        print("Erro: CSV de dados nao encontrado em /data")