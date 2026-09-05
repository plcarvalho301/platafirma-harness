# molde — runbook

Família `padrao-tecnico`. Régua fina: `docs/styleguide-moldes-por-tipo.md` §4 (fonte).

Distintivo: executável passo a passo por quem não o escreveu, sob condição adversa.
Não explica o porquê — manda fazer. Se o leitor precisa da teoria para executar, o
runbook falhou. É o tipo mais próximo da conduta do dono (memória curta, decide na
tela, começa pelo que dá).

Estratos, na ordem:

1. **Gatilho/sintoma** — o que o leitor observa que o traz aqui (alarme, mensagem de
   erro, sintoma); no que se observa, não na causa raiz. Indexado pelo **sintoma**,
   não pelo nome do procedimento — é a primeira coisa que confirma «é este o runbook».
2. **Pré-requisitos** — acesso, credencial, ferramenta e estado do sistema que os
   passos exigem, e o que conferir antes de tocar; checklist verificável, sem prosa.
   Inclui o que **não** fazer se um pré-requisito falta.
3. **Passos executáveis** — sequência numerada, um passo por item, comando ou ação
   literal e colável, o menor caminho que resolve; imperativa, com o resultado
   esperado de cada passo. **Executável sem interpretar**: variável some por valor
   concreto ou por instrução de onde obtê-lo; ramificação («se X, vá a Y») explícita.
   Herda a régua de lista do núcleo.
4. **Verificação/rollback** — como confirmar que resolveu e como desfazer se piorou;
   sinal concreto de sucesso, passo de volta. Passo destrutivo sem rollback vai
   marcado como irreversível.
