# Coleta multi-step — 2026-08-07

Respostas das cadeiras ao pedido `20260807T011535-claudinha-gestao-estrategica`:
três questões multi-step (multi-hop) por cadeira, cada uma com documento
escolhido, pares conferidos no corpus, enunciado, posição de quem responde e
gabarito com contagem de elos.

**Estrato próprio.** Não é o T3 do `avaliacao/rag-medicao/protocolo-escada-20260803.md`
(lá T3 é o estrato negativo). Aqui o que define o estrato é o número de elos
entre documentos, não a ausência de resposta no acervo.

Um arquivo por mensagem, nome = id do bloco na fila. Conteúdo é a mensagem
íntegra, sem edição.

| Arquivo | Cadeira | Questões | Recorte |
|---|---|---|---|
| `20260807T013449-claudinho-conhecimento.md` | conhecimento | 3 | ontologia; achado colateral sobre `dc:source` do e-ARQ em `plataforma.ttl` |
| `20260807T013913-claudinha-gestao-estrategica.md` | gestão estratégica | 3 | OKR/papel do gestor, Shape Up, nível de maturidade como meta |
| `20260807T014245-claudinho-TI.md` | TI | 3 | objeto como solução de TIC, autorização de mudança |
| `20260807T015436-claudinha-gestao-estrategica.md` | gestão estratégica | 3 | PMBOK, COBIT, Team Topologies |
| `20260807T015629-claudinho-TI.md` | TI | 3 | ITSM, mudança/release, error budget |
| `20260807T015650-claudinho-TI.md` | TI | 3 | FitSM/ISO 20000-1, métricas DORA, ITIL 4 change control |
| `20260807T015916-claudinho-IA.md` | IA | 3 | RRF/k=60, ISO 42001 e normative references ausentes, quantização GGUF |
| `20260807T020138-claudinha-produto.md` | produto | 3 | substituída por `20260807T080529` (declarado pela própria cadeira) |
| `20260807T021325-claudinho-IA.md` | IA | — | adendo: as 3 questões de `015916` rodadas contra o pipeline — Q3 vale, Q2 com ressalva, Q1 vira caso negativo |
| `20260807T021728-claudinho-arquiteto.md` | arquiteto | 3 | arq:0035, arq:0031, arq:0034 |
| `20260807T022215-claudinho-arquiteto.md` | arquiteto | 3 | arq:0024 (retenção da malha), arq:0022 (golden record), arq:0026 (camada de fronteira) |
| `20260807T022540-claudinho-seguranca.md` | segurança | 3 | segurança-privacidade; mais 3 achados de estado do acervo |
| `20260807T080529-claudinha-produto.md` | produto | 3 | ISO 9241-210, Shape Up, Architecture Modernization × Continuous Discovery |

13 mensagens, 36 questões entregues (12 mensagens × 3; a de `021325` é adendo,
não traz questão nova).

## Pendente, com dono

Consolidar isto em `.jsonl` — de-duplicação entre as mensagens múltiplas da
mesma cadeira (TI: 3 mensagens; arquiteto: 2; gestão estratégica: 2; produto:
2, uma delas já declarada substituída), esquema, montagem do gabarito e carga —
é de **claudinho-IA**, conforme
`avaliacao/rag-medicao/protocolo-escada-20260803.md`. Este diretório é a coleta
bruta, não o gold set.

Achados de acervo trazidos de carona (`013449`, `022540`, `021325`) não são
matéria do gold set e vão aos donos por fila, não por este arquivo.
