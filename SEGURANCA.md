# Guia de Revogação de Credenciais — SocioInova (Fase 1: Mineração e Análise Bibliográfica)

> **IMPORTANTE:** Antes de qualquer ação, verifique as credenciais locais que o app
> precisa para continuar funcionando (elas NÃO estão mais versionadas no
> repositório, mas permanecem no seu disco e são gitignored).

## Contexto

Este repositório **foi público no GitHub** e, historicamente, continha credenciais
reais versionadas. Apesar de o histórico ter sido **reescrito** para removê-las,
**reescrever o histórico NÃO revoga chaves já vazadas** — qualquer pessoa que tenha
baixado o repositório antes da limpeza pode ter copiado estas credenciais.

Portanto, a única solução definitiva é **revogar/rotacionar** as chaves abaixo.

---

## 1. Token de acesso ao Google Drive (o mais urgente)

O repositório continha um **token de acesso ativo** do Google Drive (`ya29.a0ATko...`),
obtido via Google OAuth (escopo `drive`).

### Revogar o acesso
1. Acesse **https://myaccount.google.com/permissions**
2. Encontre o app/projeto **"socia-minera"** (ou qualquer entrada de login da Google que você tenha autorizado para este projeto).
3. Clique em **"Remover acesso"** / **"Revogar"**.

Isso revoga tanto o token de acesso quanto o refresh token, impedindo qualquer uso
futuro com as credenciais vazadas.

### Alternativa via linha de comando (se necessário)
```bash
curl -s -X POST "https://accounts.google.com/o/oauth2/revoke" \
  -d "token=SEU_TOKEN_OU_REFRESH_TOKEN"
```

### Depois de revogar
O app precisará reautorizar o Google Drive. Rode novamente o fluxo de autenticação
local (o `execucao_mestre.py` vai abrir o navegador para gerar um novo
`credentials.json`).

---

## 2. client_secret do Google Cloud (OAuth Client ID)

O `scripts/client_secrets.json` continha o **client_secret** do projeto
`889453605424-fo0anul182v0err89rp3pllisd27ab24.apps.googleusercontent.com`
(de prefixo `GOCSPX-...`).

### Rotacionar
1. Acesse o **Google Cloud Console**: https://console.cloud.google.com
2. Selecione o projeto (ex.: `socia-minera`).
3. Vá em **APIs & Serviços → Credenciais**.
4. Localize o **OAuth 2.0 Client ID** correspondente.
5. **Exclua o cliente antigo** e crie um novo.
6. Baixe o novo `client_secrets.json` e **substitua o arquivo local**.

> Excluir o client ID antigo invalida o segredo antes usado com as credenciais vazadas.

---

## 3. API key do OpenAlex

O `config.json.py` continha a apikey do OpenAlex (`091553141c51cd1385131384dc008f91`).

### Rotacionar
1. Acesse a página de perfil do OpenAlex: https://openalex.org/settings (ou a área de API keys no painel do OpenAlex).
2. **Revogue/descarte a chave antiga** `091553...`.
3. **Gere uma nova chave** de API (premium/de outros usos).
4. Atualize o arquivo local `config.json.py` com a nova chave (o arquivo é gitignored — não versionado):
```json
{
  "apikey": "SUA_NOVA_CHAVE",
  "insttoken": "COLE_SEU_INSTTOKEN_SE_TIVER"
}
```

---

## Resumo das credenciais a rotacionar

| Credencial | Arquivo local | Ação |
| :--- | :--- | :--- |
| Token Google Drive | `scripts/credentials.json` | **Revogar** acesso em myaccount/permissions |
| client_secret Google | `scripts/client_secrets.json` | **Excluir** OAuth Client ID e criar novo |
| API key OpenAlex | `config.json.py` | **Gere** nova chave e descarte a antiga |
| Config PyDrive2 | `scripts/settings.yaml` | Apontará para os novos arquivos (sem segredo) |

---

## Notas gerais

- **Não** commite novamente nenhum destes arquivos. Eles estão no `.gitignore` (seção
  "Segurança / Credenciais").
- Se usar um repositório **privado** no futuro, ainda assim evite versionar
  credenciais — use variáveis de ambiente ou arquivos locais gitignored.
- Após rotacionar as chaves, **valide o app**: rode o minerador e o
  `execucao_mestre.py` para confirmar que autenticação e API continuam funcionando.
