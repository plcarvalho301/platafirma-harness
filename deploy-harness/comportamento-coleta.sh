#!/usr/bin/env bash
# comportamento-coleta — o que o comportamento.timer dispara (#3090).
# capacidade: infra
# dono: claudinho-TI
#
# Mede o comportamento das cadeiras desde a coleta anterior ate ontem e manda o texto
# a caixa da ia pela fila. A janela vem do ESTADO, nao do calendario: o timer roda as
# tercas e sabados (dono, 26/09), mas execucao atrasada (Persistent=true) ou mudanca de
# agenda nao abrem buraco nem sobreposicao, porque a janela comeca no dia seguinte ao
# ultimo dia ja enviado.
#
# estado: $PLATAFIRMA_INSTANCIA/var/comportamento/ultima-coleta — uma data AAAA-MM-DD,
#         o ultimo dia que entrou numa carta enviada. So e gravado depois do envio.
# sem estado: janela dos ultimos JANELA_MAX dias.
# exit: 0 enviou ou nada a medir · 1 metrica ou fila falharam (estado intacto)
set -euo pipefail

INSTANCIA="${PLATAFIRMA_INSTANCIA:-/srv/platafirma/casa}"
ESTADO_DIR="$INSTANCIA/var/comportamento"
ESTADO="$ESTADO_DIR/ultima-coleta"
JANELA_MAX=7

ontem="$(date -d yesterday +%F)"
teto="$(date -d "$ontem -$((JANELA_MAX - 1)) days" +%F)"

desde="$teto"
if [ -s "$ESTADO" ]; then
  ultima="$(head -n1 "$ESTADO")"
  if date -d "$ultima" +%F >/dev/null 2>&1; then
    desde="$(date -d "$ultima +1 day" +%F)"
  else
    echo "comportamento-coleta: estado ilegivel ('$ultima'), janela dos ultimos $JANELA_MAX dias" >&2
  fi
fi
# Maquina parada muito tempo: a janela nao passa de JANELA_MAX dias.
[[ "$desde" < "$teto" ]] && desde="$teto"

if [[ "$desde" > "$ontem" ]]; then
  echo "comportamento-coleta: nada a medir (ultima coleta ja cobre $ontem)"
  exit 0
fi

out="$(metrica comportamento --desde "$desde" --ate "$ontem" --resumo)" || exit 1
# Fora da porta nao ha sessao: a cadeira remetente vai em --eu (resolve_eu, bin/_fila).
printf '%s\n' "$out" | fila enviar ia --eu gestao-estrategica --de gestao-estrategica --tipo handoff \
  --assunto "Coleta de comportamento das cadeiras (#3090)" --ref "#3090" || exit 1

mkdir -p "$ESTADO_DIR"
printf '%s\n' "$ontem" > "$ESTADO.tmp" && mv -f "$ESTADO.tmp" "$ESTADO"
echo "comportamento-coleta: enviado, janela $desde..$ontem"
