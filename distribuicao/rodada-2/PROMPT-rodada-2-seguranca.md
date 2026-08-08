# Rodada 2 — prompt de proposta de conceitos: claudinho-seguranca

Variante única para `claudinho-seguranca`. As outras seis cadeiras usam
`PROMPT-rodada-2.md` sem alteração.

Motivo do desvio: o lote é 178 obras contra 63 da segunda maior cadeira, e o
vocabulário de segurança é majoritariamente canônico — a régua já está lavrada
em norma, e derivá-la não exige o mesmo trabalho de abdução.

---

**Rodada 2 da distribuição do acervo. Você é `claudinho-seguranca`. Proponha os
conceitos que as obras do seu lote sustentam.**

**Seu lote:** 174 obras em
`distribuicao/rodada-1/reivindicacoes/claudinho-seguranca.csv` (excluídas as que
foram a conflito) + 4 obras de `distribuicao/rodada-1/conflitos.csv` em que você
foi reivindicante e perdeu — o conceito destas é seu.

**Sem teto de 10.** O teto das outras cadeiras existe para forçar seleção onde a
régua é difícil de derivar. No seu lote não é: proponha quantos conceitos o
lastro sustentar. Continua valendo ≥2 obras-âncora por conceito.

**Conceito não tem dono.** Você propõe régua, não posse. Não existe campo de
domínio na entrada: o conceito existe sozinho, individuado pela definição, e é o
domínio que declara pertencimento do lado dele.

## Os dois baldes, e a ordem entre eles

Separe seus candidatos em dois, **antes** de escrever qualquer régua.

**Balde A — canônico.** Termo cuja régua já está lavrada em norma ou framework
(IAM, ABAC, gestão de vulnerabilidades, segregação de funções, os controles de
ISO/IEC 27001, NIST, CIS). Aqui não há abdução a fazer, e fingir que há produz
definição pior que a da norma.

- Uma consulta `rag_search` por conceito, **com o código exato** quando existir
  ("cláusula 5.15", "AC-2", "anexo A"): o retorno vem com `codigo_exato: true` e
  crava a formulação da fonte.
- A `definicao` articula o mecanismo na sua redação, não copia a norma; mas a
  norma é a âncora, e `estatuto` é `instituido` ou `doutrinario` conforme a
  fonte vincule ou não.
- Não passe cada um destes pelos sete testes. Passe pelos testes 1, 5 e 7
  (mecanismo, parônimo, varredura) e siga.

**Balde B — transversal.** Termo cuja régua decide **fora** da segurança:
*security by design*, *privacy by design*, superfície de ataque de um sistema
que outra cadeira constrói, modelagem de ameaça aplicada a produto. É a régua
que uma cadeira não-segurança vai consumir no momento em que estiver prestes a
errar, e ela decide caso que quem escreveu a norma não tinha no horizonte.

- **Comece por estes**, com a sessão fresca. Sequência completa: leitura no RAG
  (`colecao="firma"`, `texto="secao"`, duas consultas por obra em ângulos
  diferentes), extração do mecanismo, e os sete testes inteiros.
- É aqui que o teste 3 (transposição) decide: se a régua só funciona dentro da
  segurança, ela é do balde A e foi rotulada errado.
- Estes são poucos e valem mais que o resto do lote somado.

**As 4 obras que você perdeu na arbitragem** entram sempre pelo balde B, mesmo
parecendo canônicas: você não as leu com o olho de dono, e é justamente por isso
que o conceito delas ficou com você.

## Amostragem do balde A — declarada, não silenciosa

Você não vai consultar 178 obras. Regra:

- Toda obra usada como **âncora** de um conceito é consultada no RAG. Sem
  exceção — âncora não lida não é âncora.
- O resto do lote entra por amostra: relate no fim quantas obras você consultou
  e quantas ficou sem abrir. Lote não coberto é dado da próxima rodada, não
  falha desta.
- Obra que não retorna em nenhuma consulta: marque **não recuperável**, não use
  como âncora, reporte.

## Varredura, que no seu caso é o passo mais caro

`distribuicao/rodada-2/conceitos-existentes.csv` tem 205 entradas, e **50 delas
já vêm de obras do domínio `seguranca-privacidade`** — a maior concentração do
acervo. A chance de você propor duplicata com rótulo diferente é a mais alta de
todas as cadeiras.

Rótulo diferente que decide a mesma coisa é a mesma entrada. Discordando da
régua existente, use o campo `substitui` com o motivo — nunca entrada nova em
paralelo.

## Entrega

`distribuicao/rodada-2/propostas/claudinho-seguranca.md`, um bloco por conceito,
**balde B primeiro**:

```
## <slug>
balde: A | B
rotulo: <nome legível>
natureza: fenomeno | processo | disposicao | modelo
estatuto: natural | doutrinario | instituido
definicao: <a régua: o mecanismo, em uma a três frases>
obras-ancora: <obra_id>, <obra_id>   # ≥2, UUID literal do CSV
caso-falseador: <o caso que mostraria a régua errada>
pai-proposto: <slug do conceito mais amplo, ou vazio>
substitui: <slug existente, ou vazio>
```

`pai-proposto` só quando a régua do pai decide todo caso que a do filho decide.

`git pull --rebase`, commit e push só do seu arquivo.

**Resposta na conversa, no máximo:** quantos conceitos em cada balde; quantas
obras consultou e quantas ficaram fora; as não recuperáveis; e o conceito do
balde B que você acha que outra cadeira vai discordar — com a linha de defesa.

**Não faça agora:** escrever em `acervo.conceito`, criar ou editar página de
wiki, criar subdomínio, declarar relação com conceito de outra cadeira.
