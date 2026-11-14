# Esteira

Entidade: chapeu

## Espaço de problema

- O que prova que isto pode subir, e o que prova que subiu?
- O gate barra ou passa sem interpretar, com a suíte da engenharia verde e cenário verificável para o atributo de qualidade não funcional, ou é carimbo que pede julgamento e deixa passar o que se quis deixar?
- Do código verde ao que roda, a imutabilidade de artefato e a paridade entre ambientes garantem que o artefato testado é o que sobe, rastreável até o commit?
- Contra que registro autoritativo de configuracao se confere que subiu, e onde a deriva de configuracao afastou o estado real do estado desejado reconciliado, sem ninguém mandar?
- O que sobe junto com esta mudança sem ter sido pedido (implantabilidade independente), e que tamanho de lote esconde o que quebrou?
- Pela habilitação de mudança, esta é mudanca padrao, reversível e já aprovada, ou precisa de gate, e a volta leva a um estado conhecido e provado?

## Régua de resposta

Resposta boa diz o que o gate barra, se ele é determinístico, e contra que registro a subida se confere: sobe com a suíte verde, o atributo não funcional sem cenário trava aqui, e o que roda bate com tal registro.

Resposta ruim aceita carimbo por prova, solta sem gate, ou dá a subida por feita sem ter consultado o runtime.

## Consulta dirigida

- O efeito medido do trilho: os relatórios Accelerate State of DevOps e o livro Accelerate trazem as métricas de entrega e o que as move.
- A regra do trilho: a busca vai por esteira de implantação, trunk-based development e habilitação de mudança.
- Preparo do artefato: a busca vai por imutabilidade de artefato e paridade entre ambientes.
- O que o gate prova: a busca vai por garantia de qualidade de software e cenario de atributo de qualidade.
- Registro de configuração e deriva: Morris, Infrastructure as Code, traz o registro de configuração e os padrões em volta dele; Wang, Patterns and Practices for Infrastructure as Code, traz como se expressa a mudança de infraestrutura.
- Como se volta atrás: a busca vai por tempo de restauracao e mudanca padrao.
- Deriva de configuracao e registro autoritativo de configuracao têm obra fina, e reversibilidade de mudanca é conceito sem obra ancorada. A consulta por eles volta rasa.

## Rótulos de busca

- rótulos: esteira de implantação · garantia de qualidade de software · trunk-based development · habilitação de mudança · paridade entre ambientes · imutabilidade de artefato · tamanho de lote · frequencia de implantacao · tempo de espera · taxa de falha de mudanca · procedencia do que esta no ar · registro autoritativo de configuracao · deriva de configuracao · estado desejado reconciliado · implantabilidade independente · mudanca padrao · reversibilidade de mudanca · tempo de restauracao · gestão de configuração · injeção de segredo em implantação · feature toggle
- recorte de domínio: engenharia-software · arquiteturas
- homônimos: esteira, que neste ramo é o trilho do commit ao que está no ar, e não o pipeline do acervo · gate, que é o portão automático da subida, e não a aprovação do dono · release, que é o que está no ar e a volta dele, e não a nota de versão · procedência, que é a do artefato em produção, e não a proveniência de uma asserção
