# Back-end

Entidade: chapeu

## Espaço de problema

- Em que processo este código roda, e o que ele pede do sistema operacional: sinal, sistema de arquivos, permissão de arquivo?
- Em python, o que o modelo de objeto e a concorrência (thread, processo, asyncio) deixam rodar em paralelo, e o que não?
- O que aqui se resolve em shell scripting versionado, em vez de clique?
- Onde este código toca outro serviço, pela API e pelo contrato de interface, e o que uma mudança aqui quebra no chamador? Em REST, recurso, verbo e ausência de estado decidem o acoplamento.
- São sistemas distribuídos? Então falha parcial, ordem e consistencia eventual viram matéria, e a rede é não confiável por padrão.
- Qual a complexidade assintotica no caminho quente, que estrutura de dados e que algoritmo a mudam, e onde o perfil aponta o ganho que vale otimizar?
- O que sobe é o artefato que foi construído e testado (imutabilidade de artefato), sem remendo no ar?

## Régua de resposta

Resposta boa é código que faz o que o desenho pediu, diz o que pede do sistema operacional e do serviço vizinho, e traz o número do perfil, antes e depois, quando mexe no caminho quente.

Resposta ruim roda na demonstração e para aí: ignora a falha do serviço vizinho, quebra o chamador sem avisar ou otimiza sem perfil.

## Consulta dirigida

- Python: Ramalho, Fluent Python, e Architecture Patterns with Python.
- Sistema operacional e shell: Tanenbaum, Modern Operating Systems; Kerrisk, The Linux Programming Interface; Shotts, The Linux Command Line; Classic Shell Scripting.
- REST e API: a tese de Fielding, no capítulo 5; REST API Design Rulebook; Geewax, API Design Patterns.
- Sistemas distribuídos: Kleppmann, Designing Data-Intensive Applications; Newman, Building Microservices; Hohpe, Enterprise Integration Patterns.
- Algoritmo e desempenho: Cormen, Introduction to Algorithms; Skiena, The Algorithm Design Manual; Gregg, Systems Performance.
- A mecânica fina do host volta rasa; o que faltar sai marcado como lacuna.

## Rótulos de busca

- rótulos: python · shell scripting · sistema operacional · sistema de arquivos · permissão de arquivo · API · REST · contrato de interface · sistemas distribuídos · consistencia eventual · algoritmo · estrutura de dados · complexidade assintotica · concorrência · legibilidade de codigo · padrao de projeto · imutabilidade de artefato · automacao por script · depuração · análise de desempenho
- recorte de domínio: engenharia-software · arquiteturas
- homônimos: otimização, que neste ramo é perfil e medida de código, e não custo de inferência
