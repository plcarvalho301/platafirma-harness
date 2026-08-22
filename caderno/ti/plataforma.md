# caderno — claudinho-TI · plataforma

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno plataforma`).

## Schema migra antes do contêiner, e nem toda stack se promove (medido 16/08)

Subir código que espera coluna nova contra banco que não a tem quebra no primeiro request,
e o verbo não acusa. A ordem que não quebra é: aplicar a migração no banco VIVO, conferir
que a coluna existe, e só então recriar o contêiner.

- **Dois artefatos para o mesmo schema.** `sql/NNN_*.sql` roda em volume VAZIO
  (`docker-entrypoint-initdb.d`); banco já vivo recebe o mesmo arquivo por
  `docker exec -i <db> psql -v ON_ERROR_STOP=1 -q < sql/NNN.sql`. Por isso tudo lá é
  idempotente — e por isso um buraco na numeração não quebra nada.
- **`deploy <stack> promover` não serve a toda stack.** Exige worktree de deploy em HEAD
  destacado; stack apontada para o clone de trabalho recusa por desenho — quais, e a
  promoção alternativa, em `registro/stacks.json`, campo `_nota`.

## Config de CLI de terceiro não se confere lendo o arquivo (medido 16/08)

Superfície de agente que não é nosso — o `agy` do Jaiminho, e qualquer harness
entregue a terceiro — carrega conector por um schema que é dele, não nosso. Chave
fora do schema o CLI **descarta calada**: não sobe o servidor, não avisa e não
deixa linha em log nenhum. Config perfeitamente formada e zero conector de pé são
o mesmo arquivo.

- **A prova é bater, não ler.** `initialize` por rota, de dentro do contêiner, ou
  perguntar ao próprio agente o que ele enxerga. Ler o JSON prova só que o JSON
  existe.
- **Onde o schema mora:** dentro da imagem do CLI, quase sempre — a doc que vale é
  a que veio junto com o binário, não a do projeto upstream de nome parecido.
- **Vale para todo instrumento de conferência nosso:** medir "o que declaramos"
  não é medir "o que está servido". Instrumento que só lê declaração diz "em dia"
  sobre superfície morta.

## `environment` vence `env_file` no compose, e interpola do lugar errado (medido 16/08)

`VAR: ${VAR}` no `environment` de um serviço resolve contra o `.env` **do projeto
do compose**, não contra o `env_file` daquele serviço. Quando o valor só existe no
env_file, a linha resolve vazio e **apaga** o que teria vindo de lá — o serviço
sobe sem o segredo, e sem erro.

- **Regra:** segredo mora só no `env_file`; no `environment` fica o que não é
  segredo. Repetir a chave nos dois lugares é o bug, não a redundância.
- **Sintoma:** health do serviço reportando "sem token" logo depois de um deploy
  que "só acrescentou a variável".

## Serviço com segredo estático não se estende a terceiro por proxy (medido 16/08)

Serviço interno que autentica por token compartilhado e não tem PEP não distingue
leitura de escrita: quem carrega o Bearer alcança toda a superfície dele. Repassar
esse token por uma ponte para dar *uma* capacidade a um externo entrega todas.

- **O caminho é o PEP que já existe.** Envolver a capacidade em tool própria no
  servidor que já valida sujeito e consulta política — o segredo fica do lado de
  cá e o recorte vira decisão auditável, não confiança no cliente.
- **Recorte se força no servidor, nunca no cliente.** Tool que não existe não é
  permissão negada — é superfície que não tem o que negar. E o segundo cadeado na
  política vale para o dia em que uma tool nova esquecer o corte do código.

## Unit de usuário: declarada não é instalada, instalada não é habilitada (medido 15/08)

Três estados independentes, e o instrumento que mede um diz "convergido" sobre os
outros dois. O sintoma de todos é silêncio, não erro.

- **Arquivo `.service` no repo prova só que alguém escreveu a unit.** Quem a subiu pode
  tê-la subido **transient** (`systemd-run --user`): roda igual, aparece em `status`
  igual, e ao ser parada evapora — sem arquivo, sem `Restart`, sem volta. O que delata
  é `Failed to open /run/user/<uid>/systemd/transient/<unit>` no journal, depois do
  stop; antes disso nada a distingue de instalada.
- **Instalada é symlink para o repo, nunca cópia.** Cópia congela: `git pull` deixa de
  chegar ao systemd e nasce uma segunda verdade.
- **`enable` falha com symlink onde o config dir é root-owned** — Access denied, porque
  o systemd quer escrever na raiz de `~/.config/systemd/user`, não só no `.wants`. Com
  cópia funciona. Mas o ato do enable É um symlink em `<target>.wants`: feito à mão,
  `is-enabled` responde `enabled`, que é onde o systemd lê o estado.
- **`.wants` dentro de `~/.local/share/systemd/user` NÃO conta** — é search path de
  unit, não de configuração. Unit linkada ali roda se startada e segue `disabled`:
  sobrevive a crash e morre no boot, calada.
- **`is-active` não responde por `is-enabled`.** Serviço no ar há semanas pode nunca ter
  voltado de um boot, e ninguém reinicia a máquina para descobrir.
