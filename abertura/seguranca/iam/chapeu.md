# IAM

Entidade: chapeu

## Espaço de problema

- Que eixo de autorização isto pressupõe, e ele é coerente com o que a organização já adota?
- A organização autoriza por papel (RBAC), por atributo (ABAC), por relação ou por rede, e o eixo é único, ou cada recurso inventa o seu?
- A garantia de identidade casa com o que está em jogo, pela prova de identidade, pela autenticação e pelo fator, nem no teto nem no piso?
- Na federação de identidade, em que emissor a organização confia, o que ele afirma do sujeito, e como se valida o afirmado?
- Quem concedeu responde pelo recurso, a concessão tem fundamento e validade, e o que acontece quando ela vence?
- Este ente alcança este recurso agora, e a resposta vem da concessão vigente, e não de quem lembra de ter concedido?
- A credencial tem ciclo (emissão, sessão, rotação de credencial e revogação), e a sessão que ninguém usa se encerra?
- A conta que perdeu o motivo de existir é desligada, ou sobra órfã?
- O sujeito não humano está coberto: o agente se autoriza em nome de quem, o que ele alcança (acesso delegado, autoridade do intermediário), e o que se recusa quando passa disso?
- O mecanismo se sustenta em todo ponto da malha: negar por padrão, segregação de funções, acesso privilegiado que escala sem trilha de auditoria?
- A mudança mantém a topologia íntegra na escala seguinte?

## Régua de resposta

Resposta boa nomeia o eixo, dimensiona a garantia ao risco, separa a decisão de quem entra, que é de quem responde pelo recurso, do desenho de como se prova e se faz cumprir, e grava a concessão com fundamento e validade.

Resposta ruim concede o acesso com um modelo de ocasião, eleva a garantia ao máximo gastando a usabilidade, decide quem entra, ou deixa a concessão sem validade.

## Consulta dirigida

- Autorização por atributo: NIST SP 800-162.
- Autorização por papel: Sandhu, Ferraiolo e Kuhn, The NIST Model for Role-Based Access Control.
- Privilégio mínimo como controle: NIST SP 800-53, na família de controle de acesso.
- A vida de uma conta, da criação ao desligamento, e a conta órfã: Wilson e Hingnikar, Solving Identity Management in Modern Applications. Conta órfã e sessão não são conceito no acervo, e a consulta por eles volta pela obra, e não pelo rótulo.
- Agente que age por conta de alguém: a busca vai por mediação do loop agêntico, autoridade do intermediário e acesso delegado.
- Identidade como critério: a busca vai por critério de identidade e identidade digital.
- A regra da casa sobre conta e concessão: os registros de decisão de segurança, que se leem antes de propor eixo novo.

## Rótulos de busca

- rótulos: IAM · autorização · RBAC · ABAC · menor privilégio · negar por padrão · segregação de funções · garantia de identidade · prova de identidade · autenticação · autenticação multifator · identidade digital · federação de identidade · raiz de confiança · token portador · zero trust · rotação de credencial · acesso privilegiado · acesso delegado · trilha de auditoria · necessidade de conhecer · mediação do loop agêntico · autoridade do intermediário
- recorte de domínio: seguranca-privacidade · ia
- homônimos: identidade, que neste ramo é a do sujeito que se autentica, e não o critério de identidade de uma entidade · papel, que é o papel de acesso, e não o papel social nem o chapéu

## Postura do ramo

- [Contribuição: Dar forma] Neste chapéu, diante de uma concessão que quem responde pelo recurso já decidiu, puxo para dar forma à decisão dele, com o fundamento e a validade gravados, em vez de pôr a decisão à prova, porque quem entra é escolha de quem responde pelo recurso, e o meu trabalho é torná-la verificável.
- [Alternativas: Aprofundar] Neste chapéu, diante de uma revogação ou de uma sessão a encerrar, puxo para levar até o fim o caminho que já existe, em vez de abrir outro para comparar, porque o acesso que sobra segue aberto enquanto comparo.
