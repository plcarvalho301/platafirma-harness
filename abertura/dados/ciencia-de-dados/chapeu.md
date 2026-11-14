# Ciência de dados

Entidade: chapeu

## Espaço de problema

- Que pergunta a análise responde, e que dado existe para ela?
- Na vista, o resultado sai de receita registrada, que roda de novo do bruto ao resultado com a versão do dado e do código (reprodutibilidade computacional), e a vista montada para uma pergunta só se descarta sem virar conjunto?
- O que o dado diz antes de qualquer modelo (análise exploratória de dados): distribuição, valor estranho, relação entre variáveis; e a pergunta cabe no dado que existe?
- O dado está arrumado, uma observação por linha e uma variável por coluna, ou pede transformação de dados antes da análise?
- Que valor está errado, duplicado ou ausente, e o tratamento de dados ausentes muda o resultado? A limpeza de dados é passo registrado, que roda de novo.
- Que método de aprendizado estatístico responde, prever, agrupar ou explicar, e o modelo simples já basta?
- A avaliação separa treino e teste sem vazamento de dados em avaliação, e o agrupamento fica estável quando a amostra muda?
- Cabe numa máquina só, com pandas e NumPy, ou o volume pede processamento distribuído de dados, com Spark, e a máquina escolhida é a mais barata que resolve?

## Régua de resposta

Resposta boa diz a pergunta, o dado usado com o que se limpou e como, o método, a validação com o número fora da amostra e o que o resultado não diz.

Resposta ruim dá acurácia sem dizer como se validou, gráfico sem pergunta, modelo complexo que ninguém comparou com o simples, ou número que ninguém consegue refazer.

## Consulta dirigida

- Exploração: o Python Data Science Handbook e o Python for Data Analysis trazem a exploração com pandas.
- Forma e limpeza: o Tidy Data dá a forma arrumada. «Dado faltante» volta vazio, e o conceito é tratamento de dados ausentes.
- Modelo: An Introduction to Statistical Learning e The Elements of Statistical Learning são as obras-âncora, e Statistical Modeling: The Two Cultures separa o modelo que explica do modelo que prevê.
- Validação: as mesmas obras-âncora; o vazamento é a falha que faz o número valer só dentro da amostra.
- Motor: os artigos de pandas, NumPy, SciPy e scikit-learn, e o do Spark para o que não cabe numa máquina.
- Gráfico: os artigos de matplotlib e seaborn.
- Reprodução: a busca vai por reprodutibilidade computacional. «Notebook» e «agrupamento» voltam vazios como conceito; para o segundo, a pergunta leva aprendizado estatístico.

## Rótulos de busca

- rótulos: ciência de dados · análise de dados · análise exploratória de dados · transformação de dados · limpeza de dados · tratamento de dados ausentes · aprendizado estatístico · aprendizado de máquina em dados tabulares · vazamento de dados em avaliação · processamento distribuído de dados · visualização de dados · reprodutibilidade computacional · python
- recorte de domínio: sem subdomínio próprio; a busca vai pelo conceito, com o rótulo inteiro
- homônimos: análise, que neste ramo é a conta sobre o dado da casa, e na inteligência é a análise de inteligência
