import os
import sys
import subprocess
import shutil

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def check_step(desc, condition, fix_hint):
    if condition:
        print(f"✅ {desc}")
        return True
    else:
        print(f"❌ {desc}")
        print(f"   👉 Dica: {fix_hint}")
        return False

def verificar_saude():
    print("="*50)
    print("🔍 DIAGNÓSTICO DO OBSERVATÓRIO DE INOVAÇÃO")
    print("="*50)
    
    tudo_ok = True

    # 1. Verificar Ambiente Virtual (venv)
    is_venv = sys.prefix != sys.base_prefix
    tudo_ok &= check_step("Ambiente Virtual Ativo", is_venv, "Rode '.\\venv\\Scripts\\activate' no terminal.")

    # 2. Verificar Pastas Essenciais
    pastas = ['data', 'scripts', 'meus_pdfs', 'relatorios']
    for p in pastas:
        tudo_ok &= check_step(f"Pasta '{p}' existente", os.path.exists(p), f"Crie a pasta '{p}' manualmente.")

    # 3. Verificar Scripts Críticos
    scripts = ['scripts/minerador_openalex.py', 'scripts/minerador_oai.py', 'scripts/limpeza_unificada.py', 'scripts/auditoria_modelos.py', 'app_principal.py']
    for s in scripts:
        tudo_ok &= check_step(f"Arquivo '{s}' íntegro", os.path.exists(s), "Recupere o código do histórico do chat.")

    # 4. Verificar Ollama e Modelos (VERSÃO FINAL ALINHADA)
    import socket
    def porta_aberta(ip, porta):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((ip, porta))
            s.close()
            return True
        except:
            return False

    servico_rodando = porta_aberta("127.0.0.1", 11434)
    check_step("Serviço Ollama (Porta 11434) Ativo", servico_rodando, "Abra o Ollama no Windows.")

    if servico_rodando:
        try:
            import ollama
            modelos = ollama.list()
            model_names = []
            # Loop corrigido e alinhado
            for m in modelos.get('models', []):
                name = m.get('model') or m.get('name')
                if name:
                    model_names.append(name)
            
            for m_req in ['llama3:latest', 'mistral:latest', 'phi3:latest']:
                check = any(m_req in str(m) for m in model_names)
                tudo_ok &= check_step(f"Modelo IA '{m_req}' pronto", check, f"Rode 'ollama pull {m_req.split(':')[0]}'")
        except Exception as e:
            print(f"⚠️ Erro de API: {e}")
            tudo_ok = False
    else:
        tudo_ok = False

    # 5. Verificar Bases de Dados
    csv_path = 'data/producoes_mineradas.csv'
    tudo_ok &= check_step("Base de Dados (CSV) Gerada", os.path.exists(csv_path), "Rode o minerador OpenAlex para começar.")

    # 6. Verificar Bibliotecas de Mineração (OAI-PMH)
    try:
        import sickle
        tudo_ok &= check_step("Biblioteca 'sickle' (OAI-PMH) instalada", True, "pip install sickle")
    except ImportError:
        tudo_ok &= check_step("Biblioteca 'sickle' (OAI-PMH) instalada", False, "pip install sickle")

    print("="*50)
    if tudo_ok:
        print("🚀 STATUS: PRONTO PARA PESQUISA! Tudo configurado corretamente.")
    else:
        print("⚠️ STATUS: PENDÊNCIAS ENCONTRADAS. Resolva as dicas acima.")
    print("="*50)

if __name__ == "__main__":
    verificar_saude()