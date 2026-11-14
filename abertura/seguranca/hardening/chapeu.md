# Hardening

Entidade: chapeu

## Espaço de problema

- O que este componente acrescenta à superfície de ataque?
- O ativo consta do inventário de ativos que a operação mantém? Só se endurece o que se sabe que existe.
- O que, do que roda, pode ser explorado: porta aberta, serviço desnecessário, permissão larga, valor de fábrica?
- Há quanto tempo a vulnerabilidade conhecida está aberta (janela de exposição), e a mais explorável fecha primeiro?
- O que roda e não foi escrito aqui (dependência, biblioteca, imagem de base), e a transparência de composição o torna visível?
- O componente já nasce apertado, pela segurança por concepção, com imagem mínima e negação por padrão?
- A configuração que se endureceu é a que a operação tem no ar (procedencia do que esta no ar)?
- O teste de intrusão confirma o que se supõe?

## Régua de resposta

Resposta boa parte do que a operação tem no ar, nomeia o que o componente acrescenta de atacável, prioriza o mais explorável e o mais antigo aberto, e trata dependência de terceiro como superfície própria.

Resposta ruim endurece o componente óbvio e deixa a dependência vulnerável correndo, ou toma «não fomos atacados» por sinal de endurecido.

## Consulta dirigida

- Correção de vulnerabilidade como manutenção preventiva: NIST SP 800-40.
- Endurecimento na construção: NIST SP 800-218, o quadro de desenvolvimento seguro de software.
- Código de terceiro: Software Supply Chain Security.
- Configuração segura por sistema: os CIS Benchmarks.
- O que a casa barra no gate: os registros de decisão de segurança.

## Rótulos de busca

- rótulos: hardening · superfície de ataque · inventário de ativos · valor de fábrica · gestão de vulnerabilidades · janela de exposição · teste de intrusão · segurança por concepção · cadeia de suprimentos de software · transparência de composição · dependencia exogena · procedencia do que esta no ar · gestão de configuração · engenharia social · exercício adversarial
- recorte de domínio: seguranca-privacidade · engenharia-software
- homônimos: superfície, que neste ramo é a superfície de ataque, e não a superfície de acesso ao produto · inventário, que é o inventário de ativos, e não o inventário de dados
