from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

def carregar_meus_pdfs(pasta_pdfs="meus_pdfs"):
    documentos_totais = []
    
    # Verifica se a pasta existe
    if not os.path.exists(pasta_pdfs):
        os.makedirs(pasta_pdfs)
        print(f"Coloque seus PDFs na pasta: {pasta_pdfs}")
        return []

    for arquivo in os.listdir(pasta_pdfs):
        if arquivo.endswith(".pdf"):
            caminho = os.path.join(pasta_pdfs, arquivo)
            print(f"Lendo: {arquivo}")
            loader = PyPDFLoader(caminho)
            documentos_totais.extend(loader.load())
    
    # Divide o texto em partes para a IA processar melhor
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(documentos_totais)