# caderno — construcao (chapéu de TI)

## Lições (conhecimento curado)

- Validar PR da fábrica é medir, não confiar no relato: ler o diff inteiro, e onde o card cita commit-por-passo, conferir com `repo git show <sha> --stat` que o commit muda o que diz mudar. Nesta rodada o relato e o card afirmavam que o passo 2 mexia na régua da porta; medido, a régua já estava em main e o commit do passo 2 só adicionava teste. O engano teria passado se eu tivesse validado pela descrição.
- Aceite que só se mede pós-deploy (métrica sobre 24h de ops log) não bloqueia o merge — declarar como pendência de medição, não como verde. Distinguir do aceite que roda agora (suíte de contrato).
- Gate de outra cadeira que vem com correção de fato: conferir a correção contra a fonte antes de aceitar, e devolver âncora onde ela erra. O de-acordo do Leonardo trouxe um fato certo (régua já no ar) e um errado (cobertura ausente) — o teste da régua estava no PR, ele lera a versão de main do arquivo. Aceitar o certo e refutar o errado, os dois com âncora.