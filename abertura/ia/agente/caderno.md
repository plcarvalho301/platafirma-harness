## conhecimento curado
- Sub-agente não responde ao dono: não carrega conduta nem tem dono. Recebe o recorte de cadeira e chapéu que a tarefa pede, medido, e age na sessão do orquestrador (preferência do dono, 27/09).
- Sub-agente e bot são planos distintos que compõem: o arquivo do especialista diz quem faz (instrução, tools, modelo); o bot diz quando roda, dono e vivo/caído. Fundir põe agenda num especialista que a sessão comum não usa.
- Modelo do sub-agente se escolhe por papel, não pela sessão: orquestrador caro planeja e confere, fan-out barato executa; a conferência do achado fica com modelo diferente do que gerou (juiz-modelo).
- Vocabulário: turno = um prompt, uma saída (`claude -p`); giro = cada chamada de tool dentro do turno. O `--max-turns` do Claude Code conta giros (dono, 28/09).
- Guia de estudo de multiagente (perguntas 1-8 da aula #3155) na wiki: IA/agentes/multiagente-guia-de-estudo (28/09).

## conhecimento curado (28/09, #3155)
- Duas formas de multiagente no Claude Code, e a diferença é onde mora o estado compartilhado: sub-agente é orquestração (hub; volta só o resumo; o lead sintetiza); agent team é coreografia (task list com dependências + mailbox; teammates se falam e se auto-atribuem). Times: experimental, lead fixo, sem aninhar, plan approval automático (doc oficial 28/09).
- Fan-out vale quando o trabalho é paralelizável, excede uma janela ou toca muitas tools; não vale quando os agentes precisam do mesmo contexto ou há muita dependência (a maior parte do código). Custo: ~15x os tokens de um chat (Anthropic, multi-agent research system).
- Ordem do modelo do sub-agente (v2.1.251+): parâmetro da chamada > model do arquivo > CLAUDE_CODE_SUBAGENT_MODEL > sessão; FORCE=1 iguala todos. Antes de 2.1.251 a variável vinha primeiro.
