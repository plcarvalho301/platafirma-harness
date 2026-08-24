# ferramental — TI/observabilidade (L2)

Sinal antes do incidente: log, métrica, saúde de serviço.

- `infra sinal` — o painel de saúde consolidado.
- `infra logs|saude` — log e healthcheck por serviço.
- `lnav` — leitura de log estruturado.
- `sar` · `df -h` · `du -sh` · `ncdu` — CPU/IO, disco, ocupação.
- `nvitop` — GPU (a inferência mora no host).

## Ambiente
- `export PF_CADEIRA=TI` antes de `infra`.

## Armadilhas de uso
- Consumidor de JSONL de log deve pular linha inválida com parse tolerante e contar as
  puladas — nunca abortar no `jq` cru.
