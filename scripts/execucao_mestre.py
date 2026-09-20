import os
import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- CONFIGURAÇÕES DE CAMINHOS ---
ARQUIVO_MINERADO = "data/producoes_mineradas.csv"
ARQUIVO_DNA = "data/perfil_institucional.csv"
ARQUIVO_RELATORIO = "Relatorio_Consolidado_SocioInova.pdf"
ID_PASTA_DOUTORADO = "SEU_ID_DA_PASTA_NO_DRIVE" # Troque pelo ID real da sua pasta

def autenticar_drive():
    """Realiza a autenticação via PyDrive2 usando settings.yaml."""
    # Garante que o script procure os arquivos na pasta 'scripts'
    os.chdir(os.path.dirname(os.path.abspath(__file__))) 
    
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth() 
    return GoogleDrive(gauth)

def realizar_upload(drive, caminho_local, nome_no_drive):
    """Função genérica de upload para evitar repetição de código."""
    if os.path.exists(caminho_local):
        try:
            # Cria o arquivo apontando para a pasta do Doutorado
            arquivo = drive.CreateFile({
                'title': nome_no_drive,
                'parents': [{'id': ID_PASTA_DOUTORADO}]
            })
            arquivo.SetContentFile(caminho_local)
            arquivo.Upload()
            print(f"✅ Sincronizado: {nome_no_drive}")
        except Exception as e:
            print(f"❌ Erro ao subir {nome_no_drive}: {e}")
    else:
        print(f"⚠️ Arquivo não encontrado: {caminho_local}")

def consolidar_e_sincronizar():
    print("☁️ Iniciando Sincronização Mestre SocioInova...")
    
    # 1. Autenticação Única
    drive = autenticar_drive()

    # 2. Upload da Base de Artigos (CSV)
    realizar_upload(drive, f"../{ARQUIVO_MINERADO}", "SocioInova_Producoes_Mineradas.csv")

    # 3. Upload do DNA Institucional (CSV)
    realizar_upload(drive, f"../{ARQUIVO_DNA}", "SocioInova_DNA_Institucional.csv")

    # 4. Upload do Relatório Consolidado em PDF (O 'Diário de Bordo')
    data_hoje = datetime.date.today().strftime("%Y-%m-%d")
    nome_pdf_drive = f"Auditoria_Decolonial_{data_hoje}.pdf"
    realizar_upload(drive, f"../{ARQUIVO_RELATORIO}", nome_pdf_drive)

    # 5. Upload do Relatório Metodológico (Markdown)
    realizar_upload(drive, "../relatorio_dificuldades_tecnicas_RAG.md", "SocioInova_Relatorio_Metodologico.md")

    print("\n📦 Todos os ativos da tese estão protegidos no Google Drive!")

if __name__ == "__main__":
    consolidar_e_sincronizar()