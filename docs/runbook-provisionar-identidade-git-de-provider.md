# Runbook — provisionar a identidade git de um provider

- **Cadeira:** claudinho-seguranca (iam) · **Origem:** ordem do dono, fita 29/08/2026 · **Card:** #2899
- **Vale para:** todo provider externo (Antigravity/jaiminho hoje; chatgpt, kimi, o próximo).
  Provider-agnóstico por desenho (dec 0068: cada provider = uma conta = um `sub`).

## Para que serve a conta — e para que NÃO serve

A conta bot dá ao provider uma **identidade git própria**, distinta da do dono. É o que ela
entrega, em ordem de importância:

1. **Trilha.** Os pushes saem no nome do provider, não no do dono. Auditoria real.
2. **Blast radius.** Credencial do provider revogável sozinha, sem tocar na do dono.
3. **Escopo do `main` (bônus, não a trava).** Uma identidade NÃO-ADMIN é barrada do `main`
   pela proteção existente; a do dono (admin) passa direto.

O que a conta **não** é: a trava de "publicar em produção". Publicar aqui é ato de **host**
(`docker`/`systemctl`/`deploy`), que o papel `dev` no PAP **já nega**, e **não há CD** (merge
no `main` não faz deploy). A contenção real do provider é **conta de SO segregada + PAP**;
a identidade git é trilha e blast-radius, não o cadeado do prod.

> **Nota de enquadramento (ordem do dono, 29/08):** o gate de PR no `main` **não é controle
> sobre as cadeiras**. Cadeira opera prod com `run_command` — quem tem a mão no host não é
> contido por gate de git. O gate só significa algo para a identidade **não-admin** (o provider).
> Cadeira empurra no `main` direto, por desenho. Não inferir "preciso de PR" a partir da proteção.

## O que NÃO funciona (medido, 29/08/2026)

- **Deploy key read/write em repo de conta pessoal é EQUIVALENTE AO DONO.** Testada duas vezes:
  furou a proteção do `main` sob proteção clássica **e** sob ruleset (`Bypassed rule violations …
  Changes must be made through a pull request`, e empurrou mesmo assim). Não escopa. **Não usar
  para provider.**
- **PAT do dono** é admin — bypassa. Não escopa.
- Só uma **conta não-admin (machine user)** ou um **GitHub App** escopa de verdade, porque só
  eles não têm a autoridade do dono.

## Caminho A — GitHub App  (RECOMENDADO: sem e-mail, sem conta, token curto-vivo)

### O que é um GitHub App, em uma frase
Um "bot" de primeira classe, **dono da sua própria conta** — não é um usuário: não tem login,
e-mail nem 2FA. Tem nome próprio (os commits/PRs saem como `jaiminho-platafirma[bot]`), um conjunto
de **permissões** que você concede (Contents, Pull requests — nunca Administration) e é **instalado**
em repos específicos. Autentica por uma **chave privada** (`.pem`): com ela o container assina e pega
um **token de instalação** que vale ~1h e expira sozinho. Ganho sobre o PAT: nada de conta/e-mail para
gerir, e um token vazado morre em uma hora, não em 90 dias.

### Mão do dono (criar + instalar — web UI, uma vez por provider)
1. **Settings → Developer settings → GitHub Apps → New GitHub App.**
   - *GitHub App name:* `jaiminho-platafirma` (é o que aparece como `[bot]`).
   - *Homepage URL:* qualquer coisa (a URL do repo serve).
   - *Webhook:* **desmarca "Active"** (não usamos).
   - *Permissions → Repository:* **Contents = Read and write**; **Pull requests = Read and write**.
     Nada mais — **sem Administration** (Administration = admin = bypassa a proteção; é o erro a evitar).
   - *Where can this app be installed?:* **Only on this account** → **Create GitHub App**.
2. Na página do App: **Private keys → Generate a private key** → baixa um `.pem`. **Esse é o segredo.**
   Anota o **App ID** (no topo da página).
3. **Install App** → sua conta → **Only select repositories** → os `platafirma-*`. Anota o
   **Installation ID** (aparece na URL: `.../installations/<ID>`).
4. Me passa **App ID + Installation ID**; o `.pem` vai para o cofre do container (mão do TI), nunca fila/git.

### Mão da segurança (eu faço)
5. Confiro a instalação: repos certos, permissões certas, **sem** Administration.
6. **Verifico executando** (a régua que pegou a deploy key): gero um token de instalação da chave,
   empurro branch `card-*` (tem que PASSAR), empurro `main` (tem que BARRAR — App não é bypass actor),
   abro PR (tem que PASSAR). Se o `main` passar, ponho o App fora de qualquer bypass e re-testo.
7. Registro no inventário: App ID, onde vive a chave, prazo de rotação da chave.

### Mão do TI (container)
8. `.pem` + App ID + Installation ID no cofre do container (uid do provider). O tooling mint o token:
   - JWT curto (~10 min) assinado com o `.pem` (autentica como o App) →
   - `POST /app/installations/<installation_id>/access_tokens` → token de ~1h →
   - `git remote` HTTPS com `x-access-token:<token>@github.com/...`. Re-minta quando expirar.
   Bibliotecas prontas fazem os três passos: `ghinstallation` (Go), `PyJWT`+`requests` ou `ghapi` (Python).

### Revogar
- Desinstala o App do repo (**Settings → Installed GitHub Apps → uninstall**), **ou** rotaciona/deleta
  a chave privada na página do App. Os tokens de instalação vivos morrem sozinhos em ~1h.

---

## Caminho B — machine user (fallback; N contas para gerir)

### Mão do dono (signup e segredo — não automatizável por mim)

1. Cria um usuário GitHub novo para o provider (ex.: `jaiminho-platafirma`), com um e-mail que
   você controle (um alias `+jaiminho` do seu serve). 2FA ligado, recovery no cofre.
2. Logado como esse usuário, gera um **fine-grained PAT**:
   - **Resource owner:** você (`plcarvalho301`).
   - **Repositories:** só os `platafirma-*` que o provider toca.
   - **Permissions:** *Contents* = Read and write; *Pull requests* = Read and write.
     **Nada** de *Administration* (Administration = admin = bypassa; é o erro a evitar).
   - **Expiração:** 90 dias. Rotação é ato de estado — entra no calendário.
3. Me passa o **username** do bot. O **PAT** vai para o cofre do container do provider (mão do TI),
   nunca para a fila, git ou compose.

### Mão da segurança (eu faço, quando me passar o username)

4. Convido o bot como colaborador **não-admin** (role `push`) nos `platafirma-*`:
   ```
   gh api -X PUT repos/plcarvalho301/<repo>/collaborators/<bot-username> -f permission=push
   ```
5. **Verifico o escopo executando, não por config** (a régua que pegou a deploy key):
   - bot empurra branch `card-*` → tem de PASSAR;
   - bot empurra `main` → tem de ser BARRADO (não é admin, a proteção pega);
   - bot abre PR → tem de PASSAR.
   Se o `main` passar, o provisionamento falhou — paro e conserto antes de liberar.
6. Registro no inventário de credencial: onde vive, prazo de rotação, como revogar.

### Mão do TI (container)

7. Injeta o PAT no container do provider (uid próprio), `git remote` HTTPS com o PAT. O provider
   clona e empurra com a identidade dele — **nunca** com o token do dono.

## Revogar (saída do provider, ou incidente)

```
gh api -X DELETE repos/plcarvalho301/<repo>/collaborators/<bot-username>   # tira o acesso
```
Depois: revoga o PAT na conta do bot. `acesso orfaos` não pode achar o sujeito depois — se achar,
sobrou credencial.
