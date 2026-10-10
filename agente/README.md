# agente — o arranque de conta do Claude Code

`CLAUDE.md` é o arranque de conta e é byte a byte o `AGENTS.md` do `platafirma-posto`: um texto só
para toda superfície (`abertura/arranque.md`). Não se edita um sem o outro, no mesmo ato. O
`sincroniza.sh` do posto confere a igualdade antes de instalar e para se divergirem; com eles
diferentes, nenhuma instância atualiza.

## Instalação e atualização

- Conta `claudinho`: `instala.sh`. `~/.claude/CLAUDE.md` vira symlink para
  `/opt/platafirma/current/harness/agente/CLAUDE.md`, e `settings.json` é cópia.
- Toda outra instância (conta `megafone`, estações, Windows): `sincroniza.sh` do posto, que copia
  os dois.

Editar o arquivo instalado não dura: muda na fonte e chega pela release ou pelo `sincroniza.sh`.

## Os dois sistemas de arquivos

- **local**: o clone na máquina onde o Code abriu. `Bash`, `Write` e `Edit` nativos valem aqui e só
  aqui.
- **host da plataforma**: uid `claudinho`, release em `/opt/platafirma`, instância em
  `/srv/platafirma/casa`. Só pelo conector `claudinho-mcp`, que vem da conta claude.ai e vale em
  qualquer diretório. É onde vivem contêineres, units, banco e os verbos.

## Por que não `PF_CADEIRA`

Medido (ti, 16/08): `malote` executa no ops-server, cujo ambiente não é o do terminal onde o Code
abriu. Variável exportada ali é ilegível de dentro da sessão; o que atravessa é o slug dito na
abertura.
