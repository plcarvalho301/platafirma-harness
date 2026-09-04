# caderno — produtização

Aprendizado durável do chapéu; fato, card e estado ficam na mesa e no rastreador.

## Spec de produto é PRD, não racional

- Spec de produto se escreve publicizável e atemporal: presente do indicativo, para quem nunca esteve na conversa. Fora dela: card, ADR, commit, data de decisão, estado de código («hoje 0»), citação do dono, nome de cadeira, marca de tecnologia, bench de terceiro.
- Análise de mercado, concorrente e bench são MRD e ficam em documento de racional (baseline do épico). O PRD descreve o produto; o racional aponta para ele, nunca o contrário (人人都是产品经理 §3.3.1; Adzic, *Specification by Example*, cap. 8; *Cracking the PM Career*: curto, alternativas em apêndice).
- Forma que serviu: o que é · para quem (perfis com nome de papel, ordem de adoção) · por camada: o que entrega, requisitos, o que conta como pronto, o que é do adotante · adoção · fora do produto · glossário.
- Antes de escrever spec, consultar o acervo pelo gênero do documento — a primeira versão saiu sem isso e foi refeita inteira.

## Parecer e card na mesma régua da spec

- Documento que uma pessoa lê corrido não carrega ponteiro de seção nem citação entre aspas: a frase diz a coisa, não o endereço. Ponteiro só onde alguém vai conferir com ferramenta (âncora de contestação, commit, card).
- Card: uma linha por campo (Problema / Resultado / Medida / Fora / Sai quando), sem racional no corpo; o racional vai em comentário ou documento apontado.
- Rollout se escreve como escada: um release por perfil de usuário, na ordem de adoção; cada release lista o que entra, a ordem interna e um gate que acontece com gente de fora. Sem a escada, os goalposts ficam dispersos.

## Armadilhas medidas

- Reduzir «porta humana» à busca da wiki esquece a exposição do acervo — o operador lê o acervo pela tela.
- Design system é entregável do produto (biblioteca publicada que toda tela consome), não «só DS».
- «Entrega não é medida» rebaixa release e distro na fila, mas não os apaga: o que muda é a ordem.
- Pendurar card terminal (descartada) sob feature aberta mata a feature pelo derivado; conferir estado real antes de reparentar — a fila pode estar velha.
