# controle

Pasta do harness com o plano de controle: o agregador roda os verbos em laço e grava um JSON de
estado; a tela (`/`, `/cadeira/<slug>`, `/feito`) só lê esse arquivo. A tela é o contêiner da stack
`harness-controle`; o agregador é a unit `harness-agregador` (`systemd --user`) no host.

Por que existe: Plano de controle do harness, especificação de tela — `acervo ler casa spec plano-de-controle-harness`.

## Como sobe

Pré-requisitos: as redes externas `plataforma-wiki_default` e `motor_malha` de pé (stacks de
conhecimento e do motor), e a imagem `platafirma/ui:0.1.0` disponível, de onde o build copia o front.

```
release promover platafirma-harness <sha>
infra build harness-controle
infra up harness-controle -d
/opt/platafirma/current/harness/deploy-harness/instalar
```

`instalar` liga e inicia a unit do agregador (`controle/systemd/harness-agregador.service`).
Subiu quando `infra ps harness-controle` mostra `harness-controle-tela-1` «Up» em
`127.0.0.1:8091`, e `infra estado harness-agregador` mostra a unit ativa. A tela sem o agregador
sobe, mas pinta todo bloco como indisponível.

Armadilha: a unit do agregador não recarrega numa promoção. Depois de promover código que a toca,
`infra restart harness-agregador`; se o restart avisar «changed on disk», falta `daemon-reload`.

## Como se testa

```
teste rodar harness-controle --portao
```

Roda só os arquivos listados em `tests/VERDES`, o mesmo portão do `hooks/pre-push`. Passou quando
sai `suite VERDE` e exit 0. Sem `--portao` roda `tests/` inteiro, que tem arquivos fora do portão.
De fora da casa, o equivalente é `uv sync --locked --group dev` e `uv run pytest $(grep -v '^#' tests/VERDES)`
a partir desta pasta, como faz `.github/workflows/controle-tests.yml`.
