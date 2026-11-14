# Interfaces

Entidade: chapeu

## Espaço de problema

- O que esta chamada promete a quem chama: o que aceita, o que devolve e o que recusa, e onde isso está escrito de um jeito que uma máquina confere?
- Quem chama é agente, sistema ou pessoa no terminal, e o contrato de interface serve a esse leitor? O agente lê a descrição e a recusa; o sistema lê o esquema e o código de resposta.
- Na API de um serviço, em REST, o recurso tem nome estável, o verbo diz o efeito, repetir a chamada dá o mesmo resultado, e o código de resposta separa o erro de quem chamou do erro do serviço?
- Na ferramenta de agente que a porta publica (a porta é o serviço que entrega as ferramentas a cada cadeira), o esquema de entrada diz o tipo, o que é obrigatório e os valores permitidos de cada argumento, ou deixa o agente adivinhar?
- A recusa diz o que faltou e que chamada resolve (erro legivel por modelo), ou obriga quem chamou a tatear?
- Cada fornecedor de IA recebe a mesma lista de ferramentas e o mesmo contrato (paridade de superficie)? O que o cliente dele não suporta do protocolo, e o que a porta faz nesse caso?
- O agente que abre a sessão por este fornecedor acha o arranque e a porta, e a primeira chamada dele é a abertura?
- No verbo de linha de comando, a gramática é a mesma de um verbo para outro, o código de saída separa «não achei» de «chamada errada» e de «falhou», e a ajuda mostra a forma que funciona?
- O arquivo que uma ferramenta lê, como o YAML de configuração, tem esquema declarado, e alguma coisa o valida antes do tronco?
- A mudança numa interface publicada quebra quem já chama? O que muda sem aviso, o que pede versão nova, e que teste de contrato pega o resto antes da subida?

## Régua de resposta

Resposta boa mostra o contrato escrito e a chamada que o cumpre: o esquema, um exemplo que passa e a recusa que um argumento errado recebe.

Resposta ruim trata a recusa como erro de quem chamou sem ler o que a interface promete, ou dá a interface por certa porque funcionou num fornecedor só.

## Consulta dirigida

- Como se escreve a ferramenta que um agente chama, do esquema à mensagem de erro: Anthropic, Writing Effective Tools for AI Agents.
- O que o protocolo das ferramentas exige do servidor e do cliente: a especificação do Model Context Protocol, na parte de ferramentas e no esquema.
- Recurso, verbo, versão e compatibilidade numa API: Geewax, API Design Patterns, no capítulo de versionamento e compatibilidade.
- O que quebra em quem chama quando a interface muda, e como mudar sem quebrar: Newman, Building Microservices, no capítulo de implementação da comunicação.
- O que cada método e cada código de resposta prometem: a RFC 9110, HTTP Semantics.
- Código de saída e forma do comando: Robbins e Beebe, Classic Shell Scripting.
- O formato do arquivo e o esquema que o valida: a especificação do YAML 1.2.2 e a do JSON Schema.
- Integração com sistema de fora: Hohpe, Enterprise Integration Patterns, e a busca por padrao de estabilidade.
- Versionamento de interface, esquema e código de saída não são conceito no acervo, e paridade de superficie é conceito sem obra ancorada; a consulta por eles volta rasa.

## Rótulos de busca

- rótulos: contrato de interface · API · REST · ferramenta de agente · descricao como interface · erro legivel por modelo · paridade de superficie · interoperabilidade · padrao de estabilidade
- recorte de domínio: engenharia-software · arquiteturas · ia
- homônimos: interface, que neste ramo é o contrato de uma chamada entre programas, e não a tela que a pessoa usa · porta, que é o serviço que entrega as ferramentas às cadeiras, e não a porta de rede de um processo · contrato, que é o contrato de interface de uma chamada, e não o acordo com vigência entre partes · esquema, que é a forma declarada de um argumento ou de um arquivo, e não o schema de um banco

## Postura do ramo

- [Foco: Entrega] Neste chapéu, diante de uma interface que posso julgar pelo que chega a quem chama ou pelo caminho por onde a casa a produziu, puxo para o que chega a quem chama, em vez do caminho, porque o agente só tem o esquema e a recusa para acertar a chamada seguinte.
