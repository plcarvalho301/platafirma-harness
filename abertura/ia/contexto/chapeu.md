# Contexto

Entidade: chapeu

## Espaço de problema

- O que já não paga a posição que ocupa na janela? «Cabe, então deixa» ignora o custo de atenção abaixo do teto.
- Por que a janela lê pior quando cresce: a degradação em contexto longo perde o meio, o mecanismo de atencao reparte peso com o ruído, e a codificacao posicional faz o lugar do texto mudar o efeito dele?
- No começo estável, o que fica na frente para o cache de prefixo valer, e o que muda a cada turno e o joga fora?
- Na carga, o que entra sempre e o que entra só quando a tarefa pede? A skill traz o corpo sob demanda, e a pre-carga especulativa gasta janela com o que talvez sirva.
- No texto que o modelo lê, a engenharia de prompt e a restricao de formato mudam o que ele faz, ou só o tamanho? A descricao como interface e o erro legivel por modelo são texto de janela como qualquer outro.
- No papel, a deriva de persona aparece conforme a fita cresce, e até onde a encenação de papel por modelo de linguagem segura?
- Na poda, fica o que a inferência ainda vai usar, e a degradação diferencial sob compressão tira o detalhe antes do resumo?
- Na lousa, o que é memória de trabalho, que morre com a sessão, e o que é memória de agente, que a sessão seguinte precisa achar? A memória episódica guarda o que aconteceu, a memória semântica o que se aprendeu, e a memória prospectiva o que ficou por fazer.
- No transporte de estado entre sessões, o que foi escrito chega à sessão seguinte, e o que não foi escrito se perdeu?
- No que fica guardado, a fossilizacao de memoria já faz a anotação mentir sobre hoje, e a retenção e descarte tem ato ou prazo que a tire?

## Régua de resposta

Resposta boa nomeia a causa da degradação, o critério do que sai e o que se ganha em acerto além do que se ganha em token. Resposta ruim deixa crescer porque cabe, ou trata a lousa como acúmulo. Ganho de acerto de uma poda sem o antes e o depois sai como hipótese.

## Consulta dirigida

- O que pôr na janela e o que tirar: Effective context engineering for AI agents, da Anthropic.
- Como montar o prompt e onde cada parte pega: Prompt Engineering for LLMs, de Berryman e Ziegler.
- A janela como memória curta e a persistência como memória longa: AI Engineering, de Huyen, capítulo 6.
- Os tipos de memória de um agente: Cognitive Architectures for Language Agents separa a de trabalho, a episódica, a semântica e a procedural.
- Paginar a memória para dentro e para fora da janela: MemGPT.
- Escolher o que lembrar por relevância, e não por resumo: Generative Agents.
- O texto de ferramenta que o modelo lê: Writing effective tools for agents.
- A deriva do papel ao longo da conversa: Persona Vectors.
- Menor conjunto de alto sinal e divulgação progressiva ainda não são conceito no tesauro, e a frase de busca leva o termo por inteiro.

## Rótulos de busca

- rótulos: engenharia de contexto · janela de contexto · degradação em contexto longo · mecanismo de atencao · codificacao posicional · cache de prefixo · restricao de formato · degradação diferencial sob compressão · engenharia de prompt · skill · pre-carga especulativa · descricao como interface · erro legivel por modelo · carga cognitiva extranea · deriva de persona · encenação de papel por modelo de linguagem · personalidade situada · deriva de conceito · esquema de conhecimento · memória de agente · memória de trabalho · memória episódica · memória semântica · memória prospectiva · memória humana · memória organizacional · transporte de estado entre sessões · fossilizacao de memoria · retenção e descarte · ciclo de vida do dado · cognição estendida · cognição distribuída · design conversacional · assimetria de contexto · ponto de retomada
- recorte de domínio: ia
- homônimos: contexto, que na arquitetura é o contexto delimitado · memória, que em dados é a guarda da lembrança
