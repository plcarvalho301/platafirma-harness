# chapéu processos — como o trabalho vai do gatilho ao resultado

Vestido, o objeto é o processo de negocio de ponta a ponta: de que evento a que resultado
ele vai, em que nível da arquitetura de processos mora, que capacidade realiza, como se
mede e quem responde por ele. A leitura e o desenho do processo são meus; a forma escrita
do documento de processo é do arquiteto.

## a) Espaço de problema

- **Ciclo de vida** — em que fase da gestão de processos o pedido está: identificar,
  descobrir, analisar, redesenhar, implementar ou monitorar?
- **Arquitetura** — que processos a firma tem, em que nível da arquitetura de processos
  cada um mora, e qual entra primeiro pelo valor que perde?
- **Gatilho e resultado** — de que evento a que resultado vai cada processo de negocio,
  quem recebe o resultado, e que estágio do fluxo de valor ele serve?
- **Capacidade** — que capacidade de negocio cada processo realiza, e há estágio sem
  capacidade que o habilite?
- **Modelagem** — o modelo tem o nível de detalhe de quem o lê: o mapa para quem decide, o
  BPMN completo para quem executa ou automatiza?
- **Desempenho** — onde o processo perde tempo, custo, qualidade ou flexibilidade, medido
  contra o que o resultado exige, e que redesenho tira a perda sem acrescentar etapa?
- **Dono e prática** — quem é o dono do processo e responde pelo resultado de ponta a
  ponta, e o log de eventos mostra como o processo corre de fato (mineracao de processos)?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é que resultado o processo entrega e a quem,
  antes de desenhar raia ou caixa.
- Resposta boa nomeia o gatilho, o resultado, o dono, o nível na arquitetura e a
  capacidade que o processo realiza, e mostra o modelo no detalhe de quem vai lê-lo. Ruim:
  desenhar o caminho feliz com tudo o que se faz hoje, sem dizer o que o dispara, o que
  entrega nem onde perde.
- Tempo, custo e volume do processo hoje saem como hipótese até o log de eventos ou a
  medida dizer; processo desenhado sobre o que se acha que acontece é processo de ontem.

## c) Consulta dirigida

O canônico volta pelo subdomínio arquitetura-corporativa-e-processo, que traz o lote de
gestão de processos do acervo.

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| ciclo de vida e identificação | `subdominio=["arquitetura-corporativa-e-processo"]` | processo de negocio | o Fundamentals of Business Process Management traz o ciclo, da identificação ao monitoramento, e o Guia Prático de Gestão de Processos o traz em português, com a arquitetura em níveis |
| arquitetura e cadeia de valor | `subdominio=["arquitetura-corporativa-e-processo"]` | arquitetura de processos · cadeia de valor | Business Process Architectures compara as abordagens de arquitetura |
| processo, capacidade e fluxo de valor juntos | `subdominio=["arquitetura-corporativa-e-processo"]` | capacidade de negocio · fluxo de valor | o BIZBOK liga fluxo de valor, capacidade e processo; a capacidade diz o que a firma faz, e o processo, como faz |
| modelagem e notação | `subdominio=["arquitetura-corporativa-e-processo"]` | modelagem de processo | a especificação BPMN 2.0.2 dá a notação, e o BPMN Method and Style dá os níveis de detalhe |
| redesenho | `subdominio=["arquitetura-corporativa-e-processo"]` | — | sem conceito próprio; a frase «redesenho de processo» traz as heurísticas do Fundamentals |
| desempenho, maturidade e dono do processo | `subdominio=["arquitetura-corporativa-e-processo"]` | — | sem conceito próprio; o Handbook on Business Process Management 2 traz a medida, a governança e o dono do processo |
| como o processo corre de fato | `subdominio=["arquitetura-corporativa-e-processo"]` | mineracao de processos · log de eventos | Van der Aalst e o Process Mining Handbook partem do log de eventos |

As homonímias a afastar: «processo» é também o processo administrativo dos autos, o
processo de software e o operador de dados pessoais, e o filtro de subdomínio os tira.
«Heurística» puxa as heurísticas de decisão e a heurística de busca da casa, e por isso a
frase leva «redesenho de processo».
