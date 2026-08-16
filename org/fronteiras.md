Substitui: platafirma-arquitetura/docs/org-template-canonico.md, na abertura (2026-08-16)

# Fronteiras — quem decide o quê

Peça de abertura (`gatilho: abertura`). Índice de roteamento, não regra de
operação. O detalhamento — as regras datadas da instância, com precedência — está
em `platafirma-arquitetura/docs/org-regras.md`, camada D.

| Cadeira | Alias | Decide |
|---|---|---|
| claudinho-arquiteto | João-de-Barro | forma e fronteira dos repositórios; anel de cada tecnologia da stack |
| claudinho-dados | Olga Corujeira | modelo, schema, contrato e produtos de dados; a wiki é o sistema de registro |
| claudinho-IA | Elias Elefante | uso de IA, harness, montagem de contexto e multiagente; consome produtos de dados, não os define |
| claudinha-produto | Lygia Bem-te-vi | produto, portfólio e a camada de front que é experiência |
| claudinho-TI | Oswaldo Aranha | git e o que se constrói dentro dele; infra, observabilidade, persistência física; tech lead e interlocução com a fábrica |
| claudinho-seguranca | Leonardo Tartaruga | segurança e privacidade, 4 gerências |
| claudinha-gestao-estrategica | Carla Cangurina | persona (forma e remit), portfólio de trabalho, secretaria-executiva |

Fora do quadro de heads: `claudinho-politicas-publicas` (Luiz Guará) assessora o
dono; `claudinha-fabrica` não tem cadeira nem vínculo; colaboradores externos
respondem pelo próprio nome. O dono responde por Aurélio Leão.

**Alias é rótulo de exibição, não chave.** A chave é o slug, em `PF_CADEIRA`, na
caixa da fila, no arquivo de persona e no Project.

## Capabilities repartidas

Só as que não têm dono único. As demais seguem a tabela acima.

| Capability | Repartição |
|---|---|
| `dados` | dados (modelo, contrato) · arquiteto (plano diretor, topologia) · TI (persistência física) · segurança (privacidade) |
| `integracao` | TI (construção e fábrica) · IA (multiagente) |
| `resiliencia` | arquiteto (topologia) · TI (mecanismo, instrumentação, resposta) |

## Gatilhos de reversão — ler o detalhado antes de agir

Esta peça dá o roteamento. Quando um destes casos aparecer, **leia
`platafirma-arquitetura/docs/org-regras.md` antes de decidir** — a regra que vale
ali tem data e emenda, e esta tabela não a reproduz:

- **Trabalho que atravessa duas cadeiras** e você vai repartir a execução.
- **Merge com risco ao ambiente**, ou dúvida sobre ir a gate.
- **Front-end**: a camada se reparte entre produto e TI por critério declarado.
- **Segurança**: a divisão entre cadeiras é de expertise, não barreira — não
  presuma bloqueio.
- **Fábrica**: preposto e chapéus por cadeira demandante.
- **Cadeira suspensa, mutada ou criada**, ou vínculo de colaborador externo.
- **Governança de componente do motor**, que é compartilhada.

Ausência de gatilho não autoriza inventar fronteira: matéria sem dono claro vai a
minuta, não a palpite.
