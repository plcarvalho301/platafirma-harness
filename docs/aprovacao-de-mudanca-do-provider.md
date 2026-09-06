# Aprovação de mudança do provider — o App abre, o operador aprova

Uma conta de provider (ex. `jaiminho-fabrica`) muda código **propondo, não empurrando**.
Ela abre Pull Request pela identidade do seu **GitHub App**; a mudança só chega a
produção quando o **operador do host aprova o merge**. Autor e aprovador são
identidades distintas **por construção** — é esse o controle, não um efeito colateral.

Este documento é a mecânica da linha do card #3003 ("mudança em produção só chega por
PR/esteira que um operador do host aprova"). Antes dele o modelo vivia só no código e na
cabeça de quem o escreveu, e a leitura errada era fácil: ver a conta humana abrindo PRs
na fase de bootstrap e concluir que "o gate está quebrado por auto-aprovação". Não está.

## Os dois papéis, e por que são contas diferentes

- **Provider (autor).** Opera por um **GitHub App próprio**. O App é quem clona, comita
  e abre PR — os PRs saem como `app/<provider>` (ex. `app/jaiminho-platafirma`), nunca
  como uma pessoa. A **chave privada do App (`.pem`) vive só no host**, em cofre 600
  (`~/AI/var/secrets/<provider>-app/app.pem`); o braço recebe apenas um **token de
  instalação de ~1h**, entregue no volume da conta — nunca a chave. `APP_ID` e
  `INSTALL_ID` são do App, não segredo. Ref: `bin/jaiminho-git-token-refresh.sh`
  (cards #2899, #3012).
- **Operador do host (aprovador).** A conta humana do dono (`plcarvalho301`), operada
  pela TI (claudinho) **em nome do dono**. É quem revisa e aprova o PR do provider.
  Aprovar merge de provider é o ato de autoridade que a TI exerce por delegação.

Como as duas identidades são distintas, o GitHub aceita a aprovação: o operador
aprovando o PR de um App **não é auto-aprovação**. O que o GitHub recusa — e nunca foi o
modelo — é a **mesma conta** abrir e aprovar. Se um PR sair pela conta do operador
(bootstrap, trabalho na mão), a aprovação por review fica bloqueada e o merge só entra
por exceção registrada (`--admin`).

## O fluxo, ponta a ponta

1. O provider, na sua conta (uid próprio), clona/ramifica/comita no clone local e abre
   PR pela credencial do **App** (verbo `abrir-PR`, story #3004).
2. A esteira roda os checks no PR.
3. O **operador** (TI em nome do dono) revisa e aprova.
4. Merge em `main`; a esteira promove a produção.

Nenhuma etapa deixa o provider escrever direto em `main`: **write direto é vetado, o PR
é a única porta** (default de superfície nova, #3003: read all / write direta vetada /
PR).

## Bootstrap × regime

Enquanto os Apps de cada provider não abrem 100% dos PRs, parte do trabalho sai pela
conta do operador (na mão). Nessa fase, o merge entra por `--admin` — **exceção do
operador, registrada no relato**. No regime, todo PR de provider sai pelo App e entra
por aprovação, **sem `--admin`**. `--admin` sobre PR de provider em regime é desvio, não
atalho.

## Duas camadas de controle, que coexistem

- **Na mudança de código:** o gate de PR deste documento — o operador aprova o merge.
- **Em runtime:** o **PEP no endpoint** (#3006) decide, a cada chamada, o que o provider
  alcança agora. Grão e autorização são de segurança (Leonardo).

O PEP decide a chamada; o operador decide o merge. Uma não substitui a outra.

## Onde este modelo encosta

- **#3003** — superfície de provider: a linha do aprovador é esta mecânica.
- **#3004** — verbos-por-API: `abrir-PR` é o verbo que o provider usa; abre como o App.
- **#3006** — PEP no endpoint: a camada de runtime.
- **#2924** — identidade federada por conta-provider (segurança): o App é a identidade
  federada de cada provider no GitHub.
