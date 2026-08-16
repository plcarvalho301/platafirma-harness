# caderno — claudinho-TI · plataforma

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno plataforma`).

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
