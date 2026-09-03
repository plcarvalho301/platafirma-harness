# caderno — Nicole Capivara / inteligência

Durável: continua verdadeiro depois que o assunto morrer. Entrada nova substitui a que
contradiz; o histórico é o git.

## Recorte da cadeira (dono, 03/09/2026)

- Cinco chapéus pela grade da Doutrina ABIN 2023 (§2.1, ramos × elementos): `teoria`,
  `coleta`, `analise`, `contrainteligencia`, `marco`. Disseminação não é chapéu — é
  fase 5–6 da MPC (§5.4) e mora em `analise`.
- `coleta` absorve OSINT inteira ("todas as INT estão aí"); busca é operações, fora.
- A cadeira é o primeiro módulo completo sobre o core: consome a PlataFirma para
  produzir, não a constrói. Inteligência stricto sensu — dado → intel acionável.
- CI ativa: analiso, não executo. Elemento de Operações fora inteiro. CTI é de
  `seguranca`; chega como insumo.
- Interdependência com outros domínios é esperada e incentivada.

## Fontes canônicas da matéria

- Doutrina da Atividade de Inteligência (ABIN, nov/2023), PNI (Decreto 8.793/2016),
  ENINT (Decreto de 15/12/2017) — no Project do dono. **Nenhuma ingerida no acervo**:
  os rótulos da (b) dos chapéus que vêm da Doutrina são órfãos no golden record até a
  ingestão, e `rotas-chapeu.json` não tem `inteligencia` (roteador cai em fallback).
- DIKW da casa = Doutrina §5.2: dado → informação → conhecimento → conhecimento de
  inteligência. MPC = ciclo de análise, 6 fases; TAD = credibilidade (fonte ×
  conteúdo, 3 aspectos cada).
- Clark, *Intelligence Analysis: A Target-Centric Approach*, 7ª ed. — o dono vai
  digitalizar. Até lá, leitura por resenhas: ⚪ hipótese em tudo que cite Clark.
- Segcom/Cepesc = CI preventiva → proteção do conhecimento → camada TIC (§4.1).
  Criptografia de Estado = argumento da caixa-preta (página Tecnologia da ABIN).

## Fronteiras fixadas

- `seguranca` (Leonardo): Doutrina §4.3 — segurança cobre antagonismos e óbices; CI
  só inteligência adversa. Dele: controle, hardening, cripto-engenharia, risco, CTI.
  Meu: adversário, proteção do conhecimento como doutrina, cripto-como-política.
- `osint` (skills `osint`, `modulo-osint-platafirma`): ferramentas de execução da
  coleta; a matéria é de `coleta`. 🟠 relação com a claudinha-osint (a skill
  `platafirma` a descreve como externa e isolada) a acertar pelo dono.
- `direito` (Nuno): lê a norma; `marco` lê o que a norma obriga a acompanhar.
- `arquiteto`/`dados`/`ia`: recebem requisito de produção (metadado §5.2, TAD,
  validação por terceiro) como recorte de inteligência, nunca como desenho.

## Régua de confiança

- Estados da mente (§5.1): certeza / probabilidade / possibilidade / ignorância.
  Possibilidade não vai em produto — volta ao processamento (§5.6). Meu `⚪ hipótese`
  é possibilidade.

## Ingestão: a ponte de arquivo não é minha (medido 03/09)

- O motor do acervo (`acervo ingerir`) vive no host `claudinho`; os arquivos do
  Project do dono vivem no host da fita. `run_command` não vê o Project, e a única
  ponte de conteúdo (`write_file`) me faria retipar 334KB de fonte doutrinária à mão
  — degrada a fonte. Ingestão indexada ainda exige classificação/bancada, matéria de
  `dados`. Então a ingestão inteira é da Olga, não minha.
- `ingerir <raiz> --motor <inst> --apply`: sem `--motor` para no degrau b (não
  indexa); sem classificação, sem faceta no golden record — e é a faceta que
  destrava o roteador.

## Encadeamento em curso (fila, 03/09)

1. Pedido → `dados` (Olga), `20260903T163607-inteligencia`: ingerir Doutrina/PNI/
   ENINT indexadas, domínio inteligencia. **Bloqueia tudo abaixo.**
2. Pedido → `gestao-estrategica` (Carla), `20260903T163626-inteligencia`: rodar
   `recuperacao/gerar_rotas_chapeu.py` para as rotas de `inteligencia`. Depende de (1)
   — antes disso o gerador acusa rótulo órfão. Até lá, `monta_sessao(inteligencia)`
   cai em fallback: a cadeira declara o chapéu na 1ª linha.

## Próximo passo (padrão da casa, dono 03/09)

- Duas rodadas após esta fita: (a) peço corpus e o dono puxa o que tem (Clark 7ª ed.
  digitalizado); (b) lavro conceitos fora e dentro da teia. A MPC interna não é
  publicizável — só o que a Doutrina publica entra.
