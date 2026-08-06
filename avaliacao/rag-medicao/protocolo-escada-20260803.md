# Protocolo de medição do RAG — escada de goalposts

Origem: mensagem de claudinho-IA para claudinha-gestao-estrategica, 2026-08-03T11:45:52-03:00,
tipo `demanda`. Ref: platafirma-conhecimento/rag (bench/, docs/arquitetura-extrator-rag.md),
schema acervo em rag-extractor-pg. Desenho técnico: claudinho-IA. Sequenciamento e cards:
claudinha-gestao-estrategica.

## O problema

Não sabemos medir a qualidade da nossa busca semântica. Hoje mudança no índice se avalia por
impressão: alguém roda uma pergunta, olha o resultado e acha que melhorou. Isso não é
auditável, não acumula e não sobrevive a troca de sessão.

Ao mesmo tempo estão para acontecer três intervenções grandes e simultâneas no índice — carga
do acervo restante, classificação de domínio/conceito, e descarte de material ruim. Feitas
juntas e sem medição, nenhuma delas fica atribuível: se a busca piorar, não saberemos qual foi.

## O que se propõe

Uma escada de intervenções, uma variável por degrau, com a MESMA bateria de perguntas rodada
antes e depois de cada uma. O que muda entre dois degraus é o efeito daquele degrau, medido,
com teste de significância estatística.

Estado do índice na hora do desenho (03/08, manhã):

```
obras catalogadas ................ 693
com bytes no object storage ...... 625
ingeridas (têm texto no índice) .. 311
alcançáveis pela busca ........... 291   (42% do acervo)
no storage e FORA do índice ...... 314
```

## Pré-condição — o corpus inteiro ingerido

O experimento começa com as obras que faltam dentro do índice. Medir contra 42% do acervo mede
o corpus errado. Estimativa na época: +62 mil trechos sobre 76,5 mil (+81%); banco de 1,6 GB
para ~2,9 GB, sobre 1,5 TB livres. Custo de disco irrelevante, custo de tempo de 1 a 3 horas de
máquina, sem supervisão humana. Trabalho de claudinho-IA, não depende de card.

## G0 — o gabarito ("gold set")

Sem isto nada mais existe, e é o único goalpost que precisa de gente.

Um gold set é um conjunto de perguntas com a resposta certa declarada de antemão: para cada
pergunta, quais trechos do acervo deveriam aparecer no topo. Roda-se a busca, compara-se com o
gabarito, e saem números reprodutíveis (acertou em primeiro? trouxe os certos entre os k
primeiros? ordenou bem?).

O gabarito anterior foi feito pelo Pedro numa fase inicial, cobre o corpus pré-expurgo e não
alcança nenhuma das obras novas. Não serve.

Três estratos:

- **T1, determinístico (~50 perguntas).** Pergunta com identificador exato: "cláusula 6.1.3 da
  ISO 27001", "controle AC-2", "art. 4º da Lei 14.063". A resposta certa é o trecho que contém
  aquele identificador, então o gabarito se rotula sozinho, por código. Sem custo humano —
  claudinho-IA extrai.
- **T2, de domínio (70 perguntas).** Coleta nas cadeiras.
- **T3, negativo (~15 perguntas).** Perguntas que o acervo deliberadamente NÃO responde,
  incluindo armadilhas de vizinhança. Mede se o sistema sabe dizer "não sei" em vez de inventar.
  Sem este estrato, o modo de falha mais perigoso fica invisível.

Tamanho final ~135 perguntas, suficiente para o teste estatístico ter potência. O gabarito é
carimbado com a versão do acervo: obra descartada mais adiante invalida as perguntas dela
explicitamente, nunca em silêncio.

Validação: o Pedro revisa e valida pessoalmente antes de qualquer medição.

**Risco declarado, que a coleta não resolve sozinha:** as gerências do org chart não
correspondem uma a uma aos assuntos do acervo — 11 das 21 gerências não têm contraparte lá. A
coleta tem buraco exatamente onde as duas taxonomias divergem, e nenhuma persona enxerga o
próprio buraco, porque ele é definicional e não de esforço. T1 cobre parcialmente, por ser
sorteado do acervo e não do org chart. Mitigação parcial, declarada.

## G1 — escolha do embedder e da forma de vetorizar

Rodada única, sobre AMOSTRA do corpus (5–10%), antes de embeddar tudo em definitivo. Compara
candidatos de modelo e até três hipóteses de como preparar o texto antes de vetorizar. Vence
quem ganhar com significância estatística; empate mantém o modelo atual, por ser o custo zero.

Por que antes: trocar o modelo depois obriga a refazer todos os vetores. Testar em amostra custa
horas; testar em produção custa a carga inteira de novo.

Trabalho de claudinho-IA, sem card de terceiros. Único ponto de decisão do dono: se o vencedor
for diferente do atual, ele autoriza a troca.

## G2, G3, G4 — os três degraus

| | intervenção | dono | o que se mede |
|---|---|---|---|
| G2 | corpus inteiro, vetor de texto puro, sem filtros | claudinho-IA | linha de base do acervo completo; recalibração do piso de abstenção |
| G3 | classificação de domínio e conceito aplicada | claudinho-conhecimento | a classificação paga o próprio custo? |
| G4 | descarte do material que polui a busca | dono decide, claudinho-IA mede | o descarte melhora ou só encolhe? |

Cada degrau roda a MESMA bateria e compara com o degrau anterior, pareado.

Dois pontos técnicos que afetam sequenciamento:

- **G3 tem dependência dura com claudinho-conhecimento.** Duas frentes de reclassificação em
  curso (405 obras sem espécie declarada; 224 obras em revisão por colaboradora externa). G3 só
  mede depois das duas fecharem — medir no meio mede trabalho pela metade. O passe de
  revetorização de metadado deve ser UM só, no fim das duas.
- **G4 tem uma alternativa que precisa estar na mesa antes de alguém apagar arquivo.** O
  critério de "polui" vira métrica em G3 (concentração: obra que ocupa vários lugares no topo de
  perguntas que não são dela). Havendo o número, existem dois instrumentos: descartar a obra,
  destrutivo e irreversível, ou limitar quantos lugares uma mesma obra pode ocupar no resultado,
  reversível e sem apagar nada. Decisão do dono. O card não deve pressupor o descarte.

## O que o desenho pedia da gestão

1. Cards de coleta para as cadeiras, com as regras no corpo — não como anexo.
2. Card de validação das perguntas, do Pedro, como bloqueador de G2.
3. Sequenciamento de G3 depois das duas frentes de classificação do claudinho-conhecimento.
4. G4 registrado como decisão do dono com duas opções, não como execução de descarte.

Extração de T1, montagem do gabarito, benchmarks, carga e recalibração são de claudinho-IA e
não precisam de card de ninguém, só de posição no roadmap.

## Estado em 03/08 fim do dia — o que já mudou em relação ao desenho acima

- **G1 não acontece.** Decisão do dono: o re-embed que rodou hoje é o definitivo. Fatura
  conhecida: troca futura de modelo custa a carga inteira de novo. Modelo em uso:
  `Qwen/Qwen3-Embedding-0.6B`, backend torch, modo hybrid, rrf_k 60.
- **T2 fechado em 80 perguntas, não 70** — a coleta externa de OSINT entrou como extensão da
  cadeira de claudinho-conhecimento. 40 simples, 40 complexas, validado pelo Pedro.
  Canônico: `gold-set/gold-t2-20260803.jsonl`.
- **A cota de 2 negativas por cadeira caiu**; negativas emergem do casamento. Resultado: 27 de
  80 sem obra (33%), o que já cobre o estrato negativo de sobra e permite T3 encolher.
- **Números do acervo mudaram**: 696 obras catalogadas, 626 no índice (90%), 129.469 chunks,
  14.872 ainda sem vetor.
