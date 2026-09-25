# Norma e prompt: a mesma pergunta

Redigir norma e instruir modelo respondem à mesma pergunta: quanto detalhe dar a um
executor cuja capacidade se conhece mal. Esta nota diz por que a skill está escrita
como está e registra a ponte para quem pesquisa legimática (redação normativa com e
para sistemas). As obras citadas estão no acervo, salvo onde marcado.

A ponte é analogia, não identidade. Modelo não tem compromisso nem resistência (eixo 4
do quadro), e a sua «fiscalização» é avaliação automatizada, não controle externo. O
que se transfere é o raciocínio sobre densidade, não o regime jurídico.

## O que a literatura de IA diz, lido pela régua do guia

| Achado | Obra | Leitura pelo guia |
|---|---|---|
| A instrução a agente vive entre dois erros: lógica rígida e frágil, escrita como sequência de condições, e orientação geral demais, que supõe contexto compartilhado que o modelo não tem. | Anthropic, Effective context engineering for AI agents (2025) | É o par regra detalhada contra padrão sem julgador. O primeiro quebra no caso não previsto; o segundo não dá contra o que conferir. |
| Explicar o porquê rende mais que empilhar «DEVE» em maiúsculas; a descrição da skill precisa ser insistente, porque o modelo tende a não acioná-la. | skill-creator (Anthropic) | O porquê é a motivação (LINDB, art. 20) dirigida a executor que julga: com a razão, ele aplica o padrão ao caso que o texto não previu. |
| Skill é pasta com arquivo raiz curto que aponta recursos carregados sob demanda (divulgação progressiva), como guia de integração de um recém-chegado. | Anthropic, Equipping agents for the real world with Agent Skills (2025) | É a norma por função com o detalhe em anexo ou ato inferior. |
| Divulgação progressiva mudou o comportamento do agente (recursos distintos consultados por trajetória de 1,18 para 3,85) e deu 17 acertos a mais em 410 tentativas pareadas (+4,1%). Ajudou quando o recurso guiava implementar, conferir ou reparar; ajudou menos quando o sucesso dependia de convenção exata de saída, limiar numérico ou cadeia longa de geração. | arXiv 2606.11543 (SkillJuror, 2026); um só modelo e um só banco de tarefas | O que é regra exata fica no corpo; o que é apoio vai ao anexo. Por isso as colunas da matriz e os critérios de aceite estão no SKILL.md, e o estado da arte está em `reference/`. |
| O harness embute premissas sobre o que o modelo não consegue fazer, e elas envelhecem quando o modelo melhora; dicas de prompt de modelos antigos ficaram obsoletas. | Anthropic, Scaling Managed Agents (snapshot de 01/08/2026); Huyen, AI Engineering (2024) | É a trajetória da tese A (Schäfer): com mais capacidade no executor, a regra cede ao padrão. Instrução a modelo precisa de regime de revisão, como a norma. |
| Exemplos no prompt puxam a saída para o próprio molde e podem ensinar padrão espúrio; seguir a forma de documento que o modelo viu no treino dá saída mais previsível. | Berryman e Ziegler, Prompt Engineering for LLMs (2024) | Exemplo copiado é mimetismo em escala de prompt; por isso `exemplos.md` avisa que é ilustração. E a minuta segue a forma canônica (LC 95, Decreto 12.002), que o modelo conhece. |
| Sem raciocínio antes, a resposta do modelo é palpite e a explicação vem depois como racionalização; listar as regras aplicáveis antes de agir melhora a conformidade. | Berryman e Ziegler (cadeia de raciocínio); Anthropic, The «think» tool (snapshot de 01/08/2026) | A matriz por dispositivo força a análise antes da redação. Sem ela, a minuta sai primeiro e a fundamentação é montada depois, que é o vício da norma escrita para blindar quem assina. |

## Como a skill aplica isso a si mesma

- Gate, colunas e critérios em regra, no arquivo raiz: são convenção exata, e é onde a
  divulgação progressiva ajuda menos.
- Quadro e leitores em padrão com a razão ao lado: são juízo, e o executor (você) tem
  capacidade de julgar.
- Estado da arte, exemplos e esta nota em `reference/`: apoio, carregado quando
  preciso.
- Um verificador explícito (critérios, relatados item a item): pela condição de Huber e
  McCarty, detalhe sem fiscalização rende menos em executor que falha.

## Para a pesquisa

Hipótese, não testada: a tipologia de tarefa que decide a densidade da norma decide
também a densidade da instrução a modelo, e a norma que vai virar código ou prompt é o
caso-limite onde as duas literaturas se encontram. Duas perguntas que a ponte abre:

1. Se o executor-modelo ganha capacidade a cada versão, a instrução escrita como regra
   hoje vira carga inútil amanhã. Quem revisa, e com que gatilho?
2. A OCDE (2020, Cracking the Code, fora do acervo) trata da regra escrita para pessoas
   e máquinas ao mesmo tempo. Ler antes de afirmar o que ela resolve.
