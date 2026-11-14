# Engenharia de dados

Entidade: chapeu

## Espaço de problema

- O dado é estado ou evento, e o módulo serve o fato como aconteceu ou a projeção do sistema de origem?
- No módulo, quem cuida do conjunto consegue declarar, guardar, publicar e servir pelo plano de dados, como o data mesh pede, ou cada leitura nova vira um pedido a dados?
- Na estrutura, que estruturação de dados serve a quem consome o conjunto, e a arquitetura de dados põe cada coisa no substrato certo: banco, balde ou repositório?
- No contrato, a mudança de schema a montante avisa quem lê antes de quebrar, e a versão antiga segue servida até o leitor migrar?
- Na linhagem, cada valor chega à fonte com a transformação que o mudou declarada?
- No fichário, a shape gravada vira tabela, migração e carga de ficha sem perder campo, e o dado mestre de cada coisa sai um só, nascido da shape pela materialização e nunca escrito à mão na tabela?
- No log, o fato se grava em ficha que não muda, com o id nascido na origem para a idempotencia de consumo, e a ordem das fichas é a do acontecimento (ordenação causal de eventos)?
- Na derivação, o que acontece está como evento como entidade, separado da coisa que dura, e cada estado diz que evento o inicia, que evento o encerra e o que vale no meio, numa tabela que se refaz das fichas?
- No trânsito, o evento publicado chega a quem o assina, com envelope de campo, tipo e compatibilidade declarados, e a consistencia eventual entre módulos está dita a quem lê?
- Na cópia, tudo o que alguém lê fora da fonte está declarado, com a fonte e o ato que o repõe, e confere com ela?
- No tempo, a medida que cada capacidade instrumenta chega agregada, com a bitemporalidade de quando aconteceu e de quando se soube?

## Régua de resposta

Resposta boa entrega o schema com o conceito por trás, o contrato declarado, a linhagem até a fonte, o evento com a regra que deriva o estado e o efeito da mudança em quem lê.

Resposta ruim é DDL que roda e ninguém sabe o que significa, tabela feita para a conveniência do pipeline, estado gravado por cima do fato, ou leitura entregue à mão que o módulo vai pedir de novo.

## Consulta dirigida

- O módulo que cuida do próprio dado e o serve como produto: Data Mesh, de Dehghani, traz os quatro princípios. «Plataforma de autosserviço» e «governança computacional» voltam vazios como conceito, e a busca vai por data mesh.
- O log como registro e o estado derivado dele: Designing Data-Intensive Applications, de Kleppmann, capítulo 11. «Event sourcing» volta vazio como conceito, e a busca vai por log de eventos.
- O transporte do evento, do produtor a quem assina: Kafka: The Definitive Guide. «Mensageria» volta vazia como conceito, e a busca vai por idempotencia de consumo e consistencia eventual.
- O contrato entre quem gera o dado e quem consome: Driving Data Quality with Data Contracts, de Jones.
- O conjunto e as formas em que ele é entregue: o Padrão DCAT-BR, do Catálogo Nacional de Dados. «Distribuição» e «cópia» voltam vazios como conceito.
- Schema e substrato: a modelagem física mora na prateleira de engenharia de software. «Schema», «normalização» e «partição» voltam vazios como conceito.
- Linhagem: linhagem de dado existe como conceito e ainda não tem obra, e a busca por ele volta rasa.
- Materialização: dado mestre traz «golden record» como variante. A régua da materialização está na Olaria e no schema da casa, e não no acervo.

## Rótulos de busca

- rótulos: data mesh · estruturação de dados · arquitetura de dados · contrato de dado · linhagem de dado · dado mestre · log de eventos · evento como entidade · ordenação causal de eventos · consistencia eventual · idempotencia de consumo · ingestao de dados · bitemporalidade · camada anticorrupcao
- recorte de domínio: engenharia-software · arquiteturas · estudos-ontologias
- homônimos: avaliação, que neste ramo é a medida agregada, e fora dele é a avaliação do motor · evento, que neste ramo é a ficha do que aconteceu na casa, e na produção de inteligência é o evento de mundo
