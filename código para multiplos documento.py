Python


import os
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA

# --- CONFIGURAÇÃO ---
CAMINHO_PASTA = "./documentos_inovacao"
DB_DIR = "./vetores_politicas"

def processar_biblioteca_inovacao():
    # 1. Carregar todos os PDFs da pasta
    print(f"Carregando documentos de: {C:\Users\jonat\analise_ifs\documentos_inovação}...")
    # O glob="**/*.pdf" busca PDFs inclusive em subpastas
    loader = DirectoryLoader(C:\Users\jonat\analise_ifs\documentos_inovação, glob="**/*.pdf", loader_cls=PyPDFLoader)
    documentos = loader.load()
    print(f"Total de páginas carregadas: {len(documentos)}")

    # 2. Fragmentação (Chunking) 
    # Importante: O metadado 'source' (nome do arquivo) é preservado aqui
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\nArt.", "\n§", "\n\n", "\n", " "]
    )
    chunks = text_splitter.split_documents(documentos)
    print(f"Documentos divididos em {len(chunks)} fragmentos.")

    # 3. Embeddings Locais (Ollama)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # 4. Criar ou Atualizar Banco de Vetores
    print("Indexando documentos no banco de dados local...")
    vectorstore = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    return vectorstore

def realizar_pergunta(vectorstore, pergunta):
    llm = ChatOllama(model="llama3", temperature=0)
    
    # Configuramos o retriever para buscar nos documentos
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True # Para sabermos de qual arquivo veio a resposta
    )
    
    resultado = qa_chain.invoke({"query": pergunta})
    
    print(f"\nRESPOSTA:\n{resultado['result']}")
    print("\nFONTES UTILIZADAS:")
    # Exibe quais arquivos foram usados para gerar essa resposta
    fontes = set([doc.metadata['source'] for doc in resultado['source_documents']])
    for fonte in fontes:
        print(f"- {os.path.basename(fonte)}")

# --- EXECUÇÃO ---
# 1. Processa a pasta uma única vez
meu_banco_vetores = processar_biblioteca_inovacao()

# 2. Faz perguntas para a "IA Jurídica"
pergunta_usuario = "Compare o que a Lei X e o Decreto Y dizem sobre incentivos fiscais."
realizar_pergunta(meu_banco_vetores, pergunta_usuario)