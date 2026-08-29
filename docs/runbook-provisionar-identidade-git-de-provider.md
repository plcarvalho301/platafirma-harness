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

## Passos — machine user (repetível por provider)

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

## Alternativa: GitHub App (mais limpo para provider permanente)

Um App instalado nos repos com *Contents* + *Pull requests* write dá **tokens de instalação
curtos-vivos** (sem senha nem 2FA de conta para gerir, rotação automática). Setup também é mão do
dono (criar + instalar o App), mas a operação depois é menos frágil. Recomendado quando o provider
deixa de ser experimento e vira permanente.
