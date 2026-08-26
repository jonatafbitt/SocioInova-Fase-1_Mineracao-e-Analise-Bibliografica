from langchain_ollama import ChatOllama, OllamaEmbeddings
import subprocess


def obter_modelos_ollama():
    """Lista modelos disponíveis no Ollama, com fallback para defaults."""
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            linhas = result.stdout.strip().split("\n")[1:]  # Pular header
            modelos = []
            for linha in linhas:
                partes = linha.split()
                if partes:
                    modelo_nome = partes[0].split(":")[0] if ":" in partes[0] else partes[0]
                    modelos.append(modelo_nome)
            return modelos if modelos else ["llama3", "phi3", "mistral"]
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    # Fallback para defaults conhecidos
    return ["llama3", "phi3", "mistral", "qwen2:1.5b"]


def testar_conexao_llm(modelo="llama3"):
    """Testa conexão com modelo LLM, retorna True se OK."""
    try:
        llm = ChatOllama(model=modelo, temperature=0)
        response = llm.invoke("Teste de conexão")
        return True
    except Exception:
        return False


def carregar_llm_com_fallback(modelos_preferenciais=None):
    """Carrega LLM com fallback automático entre modelos."""
    if modelos_preferenciais is None:
        modelos_preferenciais = ["llama3", "phi3", "mistral", "qwen2:1.5b"]
    
    for modelo in modelos_preferenciais:
        if testar_conexao_llm(modelo):
            print(f"Conexão com LLM: OK! (Usando modelo: {modelo})")
            return ChatOllama(model=modelo, temperature=0)
    
    # Se nenhum modelo funcionar, tenta llama3 como último recurso
    print("Aviso: Nenhum modelo configurado funcionando. Tentando llama3 como último recurso...")
    try:
        return ChatOllama(model="llama3", temperature=0)
    except Exception as e:
        print(f"Erro crítico: Não foi possível conectar em nenhum modelo: {e}")
        return None


llm = carregar_llm_com_fallback()
try:
    response = llm.invoke("O que é uma política de inovação?")
    print("Conexão com LLM: OK!")
except Exception as e:
    print(f"Erro no LLM: {e}")


embeddings = OllamaEmbeddings(model="nomic-embed-text")
try:
    vector = embeddings.embed_query("Inovação tecnológica")
    print(f"Conexão com Embeddings: OK! (Vetor gerado com {len(vector)} dimensões)")
except Exception as e:
    print(f"Erro nos Embeddings: {e}")





