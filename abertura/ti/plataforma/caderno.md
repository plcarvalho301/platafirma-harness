# caderno — plataforma (ti)

## Conhecimento curado

- Promover código de uma unit de usuário (systemd --user) NÃO basta com `release promover`: ele materializa `current` e recria containers de STACK, mas não recarrega units de usuário. O systemd exige `systemctl --user daemon-reload` quando o `.service` mudou no disco, e `infra restart` não o faz — reexecuta o ExecStart mas o systemd mantém a definição velha em memória. Sintoma: unit segue no código antigo após promover + restart pela porta; o journal não registra start novo. Prova é medir o efeito, não confiar no "reiniciada: active" do verbo. Cura hoje é ato no host (fora da porta): `sudo -u <conta> XDG_RUNTIME_DIR=/run/user/$(id -u <conta>) systemctl --user daemon-reload && ...restart <unit>`. Mesma classe do pf-porta-watch que não reinicia a porta após promover.

- Sonda de leitura que passa por `sessao abrir` cunha chave viva no msg-mem como efeito colateral — leitura com escrita escondida. Prova de disponibilidade de montagem deve usar leitura pura (`expediente montar --sem-acervo`), nunca `sessao abrir`/`monta-sessao`. Padrão a imitar: sondas infra_estado/conferir_* do agregador não cunham nada.

- Stack de código (harness) e código servido pela PORTA sobem por caminhos diferentes: stack por `deploy promover` (recria container), verbo servido pela porta pela promoção do harness + reinício da porta. Mudança em bin/<verbo> só chega ao que a sessão executa quando o harness é promovido; até lá a porta serve o código velho, mesmo com o PR já em main. Não confundir "mergeado em main" com "servido".

- Um mecanismo dormente (gancho no-op guardado "caso precise") que já provou levar a deriva é dívida, não conveniência: mantê-lo deixa disponível o desvio que causou o problema. O pre_build (andaime da wiki, #3075) era isso — removido quando nenhuma stack o usava. Régua: gancho que só existe para um caso já eliminado sai junto com o caso.

- O que um contêiner de stack sobe de fato é a lista `compose` do registro (`acervo stack ver --json`) mais a sobreposição da instância, não o compose do repositório sozinho. Em 30/09 quase afirmei a rag-api sem GPU: a GPU vem do compose.gpu que está na lista do registro. Dispositivo, limite e rede de um contêiner se leem ali antes de afirmar.
