# Front-end

Entidade: chapeu

## Espaço de problema

- Por que canal a pessoa chega a esta tela, e ela age ali sem aprender uma forma nova?
- Quais são os estados desta tela (vazio, carregando, erro, cheio), e o que falta de estado ou de design token para escrever sem cravar valor?
- Que design system rege a tela, e o componente lê os tokens dele?
- Onde passa o modelo de renderizacao: o que monta no cliente, o que fica no servidor, o que é híbrido, e o que a renderização negociada muda no custo e no que o usuário sente?
- De onde a tela busca o que mostra, pela API ou pelo backend for frontend, e o que fica indefinido se o contrato de dados não vier?
- A separacao de apresentacao mantém a regra de negócio fora da tela?
- A semântica do documento sustenta a acessibilidade digital na marcação, e não pintada no fim?
- É microfront-end? Então a fronteira de composição, o isolamento e o contrato entre fragmentos viram matéria.
- Qual o teste do componente em cada estado, e o de acessibilidade, com teclado, papel e contraste?

## Régua de resposta

Resposta boa é interface que a pessoa usa como usa as outras telas da casa, cobre todos os estados, lê os tokens em vez de cravar valor, é acessível na marcação e pesa o necessário no cliente e no servidor, medido antes e depois.

Resposta ruim pinta só o estado feliz, com cor cravada, sem foco de teclado, com pacote não medido e regra de negócio dentro da tela.

## Consulta dirigida

- Composição e microfront-end: Mezzalira, Building Micro-Frontends; Geers, Micro Frontends in Action.
- Acessibilidade: Inclusive Components e o ARIA Authoring Practices Guide.
- Renderização e contrato com o servidor: as obras de REST e de API servem também ao backend for frontend.
- A mecânica fina do cliente, com laço de eventos e reatividade, volta rasa: o acervo é forte em composição, renderização e acessibilidade.

## Rótulos de busca

- rótulos: modelo de renderizacao · renderização negociada · separacao de apresentacao · semântica do documento · microfront-end · backend for frontend · design system · design token · acessibilidade digital
- recorte de domínio: engenharia-software · produtos-digitais
- homônimos: design, que neste ramo é o sistema de design que o código lê, e não o desenho da jornada · componente, que é o componente de interface, e não o componente de um serviço
