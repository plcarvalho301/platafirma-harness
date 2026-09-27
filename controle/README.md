# controle — plano de controle do harness

Serviço web (`harness-controle`) que responde "o que está acontecendo agora" no
harness: agregador de estado + tela de recepção, `/cadeira/<slug>` e `/feito`.
Construído pelo card #390.

## O que é

Dois processos que só se falam por um arquivo de estado:

- **agregador** (`harness_controle/agregador.py`, systemd `--user` no host —
  `systemd/harness-agregador.service`) — roda os verbos (`fila`, `infra`,
  `conferir`, `tarefas`) em timer e escreve UM JSON de estado. Nunca a tela
  chama verbo em resposta a request.
- **tela** (`harness_controle/web.py`, container `tela` do `compose.yaml`) —
  serve as rotas HTTP e só lê o arquivo de estado, montado somente-leitura.

Roda em dois lugares porque o agregador precisa do host inteiro (`systemctl`,
`docker` CLI, venv com shebang absoluto) e a tela precisa estar na rede do
`oauth2-proxy` (host não é alcançável de dentro do container rootless).

## Como sobe

```
docker compose -f controle/compose.yaml up -d      # tela, porta 127.0.0.1:8091
systemctl --user start harness-agregador.timer      # agregador, no host
```

Variáveis relevantes: `PF_RELEASE_RAIZ`, `PLATAFIRMA_INSTANCIA`,
`AGREGADOR_ESTADO_PATH`, `HARNESS_CONTROLE_PORTA` (ver `compose.yaml`).

## Como se testa

```
cd controle && uv run pytest
```

Três camadas (`tests/`): contrato de verbo (formato + falha, por verbo com
`--json`), unidade do agregador (transformação saída-de-verbo → estado; verbo
morto vira `indisponivel`, nunca zero fake), fumaça HTTP (serviço sobe, rotas
respondem, bloco morto não pinta saudável). Sem teste de navegador, sem e2e,
sem meta de cobertura — suíte verde é aceite.
