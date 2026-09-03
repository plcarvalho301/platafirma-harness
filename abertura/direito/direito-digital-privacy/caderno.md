# caderno — direito-digital-privacy
Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.
Mapa do que o acervo JÁ TEM na minha matéria — para eu saber antes de pedir livro novo.
Varredura de 03/09/2026 sobre os 492 conceitos do golden record (`acervo listar
conceitos`) + `descobrir` por conceito. Zero obra ancorada em `direito`: a cadeira é
nova, então tudo abaixo veio ancorado por OUTRA cadeira (segurança-privacidade,
capacidade-estatal). É insumo qualificado, não doutrina jurídica — trato como fonte não
verificada: extraio fato, confiro, descarto retórica.

## O que já existe: proteção de dados / LGPD é a veia FORTE do acervo

É a única matéria jurídica com massa real, e vem por segurança-privacidade. Conceitos
vetorizados e as obras que os ancoram (ancoras = quantas obras batem no conceito):

- `protecao-de-dados-pessoais` (11 ancoras; rótulos: LGPD / GDPR / personal data
  protection) — a espinha. Obras: cursos **Data Protection Officer (DPO) — FGV Direito
  Rio** e **slides DPO partes 1-2**; **Data Protection Engineering: From Theory to
  Practice (2022)**; **Data Privacy**.
- `base-legal-de-tratamento` (5) — as hipóteses do art. 7º/11 LGPD. Existe como conceito;
  ancorado nos mesmos cursos DPO.
- `avaliacao-de-impacto-a-privacidade` (4; DPIA / privacy impact assessment) — o RIPD do
  art. 5º XVII / 38 LGPD.
- `anonimizacao` (6) e `retencao-e-descarte` (2) — dado deixa de ser pessoal; ciclo de
  vida. Ancorados em Data Protection Engineering.
- `comunicacao-de-incidente-ao-titular` (4) — o dever de notificar (art. 48 LGPD / ANPD).
- `estados-do-dado` (1), `algoritmo-de-estado` (2), `governanca-ia` (3), `governanca-dados`
  (9) — a interface dado↔decisão automatizada (art. 20 LGPD, revisão de decisão automática).

Conclusão operacional: para parecer de LGPD/proteção de dados eu me apoio no que ESTÁ
aqui. Não peço ingestão de "algo sobre LGPD" sem antes rodar `descobrir <conceito>` nesta
lista — a base já cobre DPO, base legal, DPIA, anonimização, incidente.

## O que NÃO existe (lacuna real, aí sim pedir obra)

- **Lei seca comentada**: não há LGPD comentada, nem Marco Civil da Internet, nem decreto
  regulamentador, nem resoluções da ANPD como texto normativo. O acervo tem o *conceito*
  DPO e cursos, não o *dispositivo* nem a *regulação infralegal* atual.
- **Jurisprudência** de proteção de dados (STJ/STF/ANPD sancionador): ausente.
- **Contratos de tecnologia** como peça (DPA, cláusulas de operador/controlador, SLA de
  segurança): ausente como matéria contratual — ver caderno empresarial, mesma lacuna.
- **Responsabilidade civil de plataforma / produto de software**: ausente.

## Régua ao pedir ingestão

Antes de escrever "precisamos ingerir X", rodo `descobrir "<conceito>" --eixos conceito`
e confiro na lista acima. Só é gap se `descobrir` volta `vazia` E o conceito não está no
golden record. O retriever é `nao-calibrada` para query multi-termo em português jurídico
(query longa volta `vazia` falsamente) — pesquiso por UM conceito por vez, não por frase.
