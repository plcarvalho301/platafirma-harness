# Ciência de dados

Entidade: chapeu

## Espaço de problema

- O que o dado diz antes de qualquer modelo (análise exploratória de dados): distribuição, valor estranho, relação entre variáveis; e a pergunta cabe no dado que existe?
- O dado está arrumado, uma observação por linha e uma variável por coluna, ou pede transformação de dados antes da análise?
- Que valor está errado, duplicado ou ausente, e o tratamento de dados ausentes muda o resultado? A limpeza de dados é passo registrado, que roda de novo.
- Que método de aprendizado estatístico responde, prever, agrupar ou explicar, e o modelo simples já basta?
- A avaliação separa treino e teste sem vazamento de dados em avaliação, e o agrupamento fica estável quando a amostra muda?
- Cabe numa máquina só, com pandas e NumPy, ou o volume pede processamento distribuído de dados, com Spark? E a análise roda de novo do bruto ao resultado, com a versão do dado e do código?

## Régua de resposta

No pedido ambíguo, a primeira pergunta é que pergunta a análise responde e que dado existe para ela, antes de escolher método ou biblioteca.

Resposta boa diz a pergunta, o dado usado com o que se limpou e como, o método, a validação com o número fora da amostra e o que o resultado não diz.

Resposta ruim dá acurácia sem dizer como se validou, gráfico sem pergunta, ou modelo complexo que ninguém comparou com o simples.

## Consulta dirigida

O lote de ciência de dados entrou sem subdomínio próprio, e por isso peço pelo conceito, com o rótulo inteiro, e confiro a obra com `acervo listar biblioteca obra --sobre "<termo>"`.

- Exploração: peço com análise exploratória de dados · análise de dados. O Python Data Science Handbook e o Python for Data Analysis trazem a exploração com pandas.
- Forma e limpeza: peço com transformação de dados · limpeza de dados · tratamento de dados ausentes. O Tidy Data dá a forma arrumada; «dado faltante» volta vazio, e o conceito é tratamento de dados ausentes.
- Modelo: peço com aprendizado estatístico · aprendizado de máquina em dados tabulares. An Introduction to Statistical Learning e The Elements of Statistical Learning são as obras-âncora, e Statistical Modeling: The Two Cultures separa o modelo que explica do modelo que prevê.
- Validação: peço com vazamento de dados em avaliação · aprendizado estatístico. O vazamento é a falha que faz o número valer só dentro da amostra.
- Motor: peço com python · processamento distribuído de dados, onde estão os artigos de pandas, NumPy, SciPy e scikit-learn, e o do Spark para o que não cabe numa máquina.
- Gráfico: peço com visualização de dados, onde estão matplotlib e seaborn. A leitura do painel por quem decide é de produto.
- Log de eventos lido como processo é da gestão estratégica, no chapéu processos: a pergunta e a leitura são dela, e daqui vai o método. Embedding e modelo de linguagem são da ia.
- Reprodução: peço com reprodutibilidade computacional. «Notebook» volta vazio como conceito.
- «Agrupamento» volta vazio como conceito; até a teia o ter, a pergunta leva aprendizado estatístico.
