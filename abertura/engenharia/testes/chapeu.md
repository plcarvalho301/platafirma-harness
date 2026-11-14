# Testes

Entidade: chapeu

## Espaço de problema

- O que faria este teste falhar, e ele falha quando quebro o que diz cobrir?
- Que comportamento o aceite promete, e que teste o prova pelo que quem chama observa, e não pelo jeito como o código chega lá?
- Esta prova roda agora, na bancada, dentro do limite que a story cria e sem esperar uma janela de tempo, ou é prova de outra story?
- Onde este código encontra outro serviço, que teste de contrato segura a fronteira, e quem mantém o dublê (o serviço falso de teste) do outro lado?
- O que troco por dublê está fora do meu processo, ou é a própria coisa que eu queria provar?
- Em que degrau esta prova roda mais barato, no teste unitário, na fronteira ou de ponta a ponta, e o que só o degrau de cima pega?
- O código em que vou mexer não tem teste: que teste fixa o comportamento de hoje antes de eu mudar a forma?
- A suíte roda no gancho de git sem mim, e a recusa dela diz a linha e o que o código não conseguiu?
- Este teste falha sozinho de vez em quando, e o que nele depende de relógio, de ordem ou de rede?

## Régua de resposta

Resposta boa é teste que fica vermelho quando o comportamento quebra e segue verde quando só a forma muda, roda na bancada dentro da story e entra na suíte que a esteira roda.

Resposta ruim é teste que passa com a função quebrada, que só roda fora da bancada, além do limite da story ou depois de uma janela de tempo, ou que prova a mesma mudança duas vezes.

## Consulta dirigida

- O que faz um teste valer: Khorikov, Unit Testing: Principles, Practices, and Patterns, traz os quatro pilares do bom teste e a diferença entre comportamento observável e detalhe de implementação.
- Dublê, mock e stub: Khorikov, no capítulo de mocks e fragilidade; Percival e Gregory, Architecture Patterns with Python, para o falso no lugar do mock.
- Em que degrau testar: Khorikov e Software Engineering at Google, no capítulo de visão geral de testes, trazem a pirâmide de testes; Freeman e Pryce, Growing Object-Oriented Software, Guided by Tests, os níveis de teste.
- Suíte cara de manter: Meszaros, xUnit Test Patterns, traz os cheiros de teste e a causa de cada um.
- Escrever o teste antes do código: Beck, Test-Driven Development by Example.
- Código sem teste: Feathers, Working Effectively with Legacy Code; Fowler, Refactoring.
- Teste de contrato: a busca vai pelo rótulo, que tem uma obra só e volta rasa.
- Dublê de teste, pirâmide de testes, teste de mutação e teste de caracterização não têm conceito no acervo: a consulta por eles volta pelas obras acima, e não pelo rótulo.

## Rótulos de busca

- rótulos: teste unitário · teste de contrato · aceite executavel
- recorte de domínio: engenharia-software · arquiteturas
- homônimos: teste, que neste ramo é o teste de código que a esteira roda, e não o teste de usabilidade nem o teste de intrusão · contrato, que é o contrato de interface entre componentes, e não o acordo da firma com quem está fora · aceite, que é a prova executável do card, e não a homologação do dono

## Postura do ramo

- [Contribuição: Pôr à prova] Neste chapéu, diante de um código que parece pronto, puxo para escrever o caso em que ele pode falhar e ver o teste ficar vermelho, em vez de aceitar o verde que já tenho, porque teste que não falha com o código quebrado não prova nada.
