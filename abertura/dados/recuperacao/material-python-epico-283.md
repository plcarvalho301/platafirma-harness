# regra do épico #283 — não refatore de cabeça

Orientação EXPRESSA para toda sessão do épico #283 (refatoração do código Python do
pipeline de recuperação). O épico é quase todo refatoração de um código grande e ruim;
a recuperação hoje está tóxica em parte porque as sessões afirmam sobre o código e
sobre as normas de cabeça, sem consultar. Esta é a régua que trava isso.

## A regra (dura)

Antes de afirmar, alterar ou refatorar qualquer coisa neste épico, CONSULTE a fonte e
ancore na saída. Responder de cabeça sobre o código ou sobre a norma que rege a
refatoração é o mesmo erro que a régua da contestação (`dono.md`) já proíbe sem âncora
— aqui ele fica nomeado porque é a falha recorrente do épico.

Dois braços, ferramenta distinta em cada. NÃO os confunda: o código-fonte NÃO está no
RAG documental (o RAG indexa o acervo — PDFs, normas, obras —, não os `.py` do repo).

## Braço 1 — o código real, antes de mexer nele

O código do pipeline mora em `platafirma-conhecimento/rag/rag_extractor/`. Leia o
arquivo antes de descrever, criticar ou reescrever qualquer função:

- `rg -n "<símbolo>" platafirma-conhecimento/rag/rag_extractor/` acha a definição.
- `view <arquivo>` no trecho achado — leia o que a função FAZ, não o que você lembra
  que ela faz.
- Refatoração que reescreve uma função sem citar as linhas atuais dela é palpite.
  A citação das linhas velhas é a âncora do diff.

## Braço 2 — a norma/decisão que rege a refatoração

Quando a mudança depende de regra registrada (DMBOK, ADR, decisão de caderno, o
contrato do #2796), consulte o RAG documental on-demand — não cite de memória:

- Busca semântica é sub-ato de `acervo` e `motor` (fichas em
  `acervo listar ferramental --oficio`). `acervo | motor` sem argumento listam os
  sub-atos. Facetas: rode o levantamento de facetas ANTES de filtrar — faceta válida
  e despovoada devolve zero sem erro.
- O que a busca devolver é a âncora da decisão de design. Sem ela, a refatoração está
  seguindo uma norma lembrada, que é como a recuperação ficou tóxica.

## Por que a recuperação ainda é ruim (contexto, não desculpa)

O eixo 1 (#2796 + filhas) é o conserto: 758 de 763 obras têm impressão duplicada
`servindo` competindo no ranking; contrato de obra completa ainda não fecha os 5
degraus. Enquanto isso não fecha, a busca documental DEVOLVE ruído — duplicata e obra
fantasma. Consultar mesmo assim e ancorar é obrigatório: a régua não espera a busca
ficar boa; o eixo 1 é que a torna boa, em paralelo.

## Repertório mínimo para conseguir consultar

Só o que a régua exige para funcionar. Detalhe operacional completo: `caderno.md`.

- **Invocação da CLI que não mente**: `MORADA=nova ~/AI/.venv/bin/python -m
  rag_extractor.cli <sub>`. `rag_extractor` é servido pelo `.venv` raiz — NÃO por
  `.venv-embed`/`.venv-acervo` (medido 26/08: ModuleNotFoundError nesses dois).
- **`MORADA=nova` é obrigatório em toda chamada** — o default `velha` aponta para
  tabela morta (#167); falha em silêncio, não em erro.
- **Dois bancos**: `rag-extractor-pg` (5432, schema `acervo`, sem embedding) e
  `motor-pg` (5433, schema `motor`, vetor particionado d1024/d256). Confundir custa
  diagnóstico errado.
- **Armadilha do clone**: espelho de repo serve SHA velho depois do push — leia o
  clone local, ou `repo_sync`.

## Fronteira

O QUE tem de valer (consultar antes de afirmar; o código é fonte, a norma é fonte) é
conduta desta cadeira para o épico. O COMO o código refatorado fica escrito — estilo,
tipagem, estrutura de erro no toque do CLI — é TI/IA. Esta régua obriga a leitura, não
dita o estilo do diff.
