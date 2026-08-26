# Recorte de segurança do papel MODELO EXTERNO (chatgpt, kimi e afins)

- **Card:** #2488 · **Cadeira:** claudinho-seguranca · **Data:** 2026-08-26 · **Versão:** v1
- **Base:** decisão do dono (25/08/2026) + aceite desta cadeira, com a emenda nomeada aqui.

## Tese aceita (do dono)

Contas de IA são **todas do dono** → não são principais distintos → controle de *acesso*
(authz) não separa nada que a própria conta já não separe. O que importa é controle de
**blast radius** (raio de dano), não de permissão. Evidência medida: o client `L0R8OJ` faz
~1.400 linhas/dia de `http_req` e **zero** chamada de tool em 13 dias de série — perfil vivo
no arquivo, morto no uso. Authz para IA do dono é custo sem contrapartida.

## Emenda desta cadeira: procedência (e por que não repete o erro do #139)

Blast radius limita o **dano**, mas não responde **qual modelo** produziu o ato. Com um só
colaborador isso é irrelevante; com `chatgpt` + `kimi` + `jaiminho` atuando ao mesmo tempo, é
o que decide se dá para **depurar e reverter**. É o defeito do #139 (portador indistinguível)
um nível acima, e liga na mesa iam #165 (procedência como eixo da conta, emenda de seg:0011).

**A emenda, e o cuidado:** procedência **não** é um campo novo na auditoria — adicionar
`procedencia` ao lado de `sub` repetiria exatamente o erro que fechou o #139. Sob o modelo
**por provider** (dec 0068), cada modelo com **sua própria conta** = **seu próprio `sub`**;
logo a auditoria já os separa pelo `sub`, sem eixo extra. **Procedência é consequência da
conta-por-modelo, não um controle à parte.** Isso mantém #139, #2488 e a 0068 coerentes.

## O que o recorte prescreve

1. **Conta de SO própria por modelo** (uid dedicado, `home 700`) — não papel no PAP. É o que
   já segura o `jaiminho` hoje e o que seg:0013 pediu para a fábrica e travou por exigir root.
2. **Área de transferência por modelo**, não compartilhada — pelo mesmo motivo: é raio de
   alcance, não permissão.
3. **Procedência = `sub` garantido por (1)**. Ação de segurança: confirmar que a auditoria
   registra `sub` por conta (já registra — verificado no #139). Nenhum campo novo.
4. **O PAP não se apaga.** Ele é infraestrutura pré-posicionada para os usuários **humanos**
   que o dono espera em breve; para esses, authz volta a ser a ferramenta certa.
5. **O perfil de IA que sobrar no PAP se declara como não-controle** — mesmo tratamento que o
   `seg` recebeu no #199: a declaração explícita de que *não é gate* é o controle. Some calado
   seria pior que ficar declarado como inerte.

## Fronteira de execução (quem faz o quê)

| Item | Cadeira | Bloqueio |
|------|---------|----------|
| 1. Conta de SO por modelo | **claudinho-TI** | precisa **root** (mão do dono/TI) |
| 2. Área de transferência por modelo | **claudinho-TI** | infra, provável root |
| 3. Confirmar `sub` por conta na auditoria | claudinho-seguranca | nenhum (já verificado) |
| 4. Declarar que o PAP fica pré-posicionado | claudinho-seguranca | nenhum |
| 5. Declarar perfil de IA como não-controle no PAP | claudinho-seguranca | nenhum |

Os itens 3–5 são desta cadeira e sem root; 1–2 são execução de TI e dependem de root — não se
fecham por esta mão. Este recorte é o insumo pronto para essas execuções.

## Referências

dec 0068 (conector por provider), #139 (portador = sub), #165 (mesa iam — procedência),
seg:0011 (emenda procedência), seg:0013 (conta de SO da fábrica), #199 (declarar não-controle).
