#!/usr/bin/env bash
# uso.sh — mapa (N1), forma de ato (N2) e erro gracioso para os verbos em bash.
# capacidade: construcao
# dono: claudinho-TI
# card: #3016 (feature #3015 — todo verbo com --help e erro de verbo gracioso)
#
# NADA aqui duplica texto de verbo: a fonte e o CABECALHO DO PROPRIO VERBO, lido
# do arquivo em tempo de chamada. O verbo declara, esta lib renderiza.
#
#   # ato: mover <id> <estado> — move o card de estado
#   #   <id>          numero do card
#   #   --forcar      pula a checagem de transicao
#   #   stdin: nao
#   #   ex: tarefas mover 3016 em-execucao
#   # exit: 0 ok · 1 falha declarada · 2 uso
#
# Bloco de ato = a linha `# ato:` mais as linhas de detalhe CONTIGUAS que comecam
# com `#` + DOIS espacos. Qualquer outra linha de comentario fecha o bloco — por
# isso um `#` pelado separa os blocos das tabelas de prosa do cabecalho.
#
# Regua de forma (card #3016):
#   N1  `<verbo>` sem ato, `--help`, `--ajuda`, `-h`  -> uma linha por ato + tabela
#       `exit:`, em STDOUT, exit 0.
#   N2  `<verbo> <ato> --help`                        -> sinopse + detalhe (uma linha
#       cada) + exit + um exemplo, em STDOUT, exit 0.
#   erro -> linha 1 `erro: <o que faltou>`, depois `corrija:` com a N2 do ato, o
#       mapa (ato desconhecido) ou o conjunto valido; em STDERR, exit 2.
#
# O que o verbo faz, em tres pontos de solda:
#   1. `. "$(dirname "$(readlink -f "$0")")/../lib/uso.sh"` logo apos o cabecalho;
#   2. `uso_intercepta "$@"` ANTES de qualquer posicional (para que `tarefas criar
#      --help` mostre a forma e NAO crie card);
#   3. `uso() { uso_mapa >&2; exit 2; }` — os call sites antigos de `uso` seguem
#      valendo, e caem no caminho de ERRO (stderr, exit 2), nao no de ajuda.

# Fonte = o arquivo do verbo que nos carregou; nome = como ele foi invocado (o
# symlink servido, que e o nome que a cadeira digita: `fila`, nao `fila_streams.py`).
# Sub-ato de despachante (arq:0040 — `bin/_minuta/escrever`) declara USO_FONTE e
# USO_VERBO ANTES do source, e renderiza o cabecalho do verbo PAI: a forma de
# `minuta escrever` mora no cabecalho de `minuta`, uma vez so.
_USO_FONTE="${USO_FONTE:-$(readlink -f "$0" 2>/dev/null || printf '%s' "$0")}"
_USO_VERBO="${USO_VERBO:-$(basename "$0")}"
_USO_VERBO="${_USO_VERBO%.py}"
_USO_VERBO="${_USO_VERBO%.sh}"

# --- leitura do cabecalho ----------------------------------------------------

# Valor de uma chave do cabecalho (`# <chave>: <valor>`), primeira ocorrencia.
uso_chave() { sed -n "s/^# $1:[[:space:]]*//p" "$_USO_FONTE" 2>/dev/null | head -1; }

# Linha de proposito: a linha 2 do arquivo, `# <verbo> — <o que faz>`.
uso_proposito() { sed -n '2{s/^#[[:space:]]*//;p;}' "$_USO_FONTE" 2>/dev/null; }

# Tabela de exit: do cabecalho, com o default da casa quando o verbo nao declara.
uso_exit() {
  local e; e="$(uso_chave exit)"
  printf '%s\n' "${e:-0 ok · 1 falha declarada · 2 uso}"
}

# Blocos crus, um registro por linha: "A<TAB><sinopse> — <resumo>" ou "D<TAB><detalhe>".
_uso_blocos() {
  awk '
    /^#!/                 { next }
    /^# ato:/             { linha = $0; sub(/^# ato:[[:space:]]*/, "", linha)
                            print "A\t" linha; dentro = 1; next }
    dentro && /^#  [^ ]/  { linha = $0; sub(/^#[[:space:]]+/, "", linha)
                            print "D\t" linha; next }
    dentro && /^#  /      { linha = $0; sub(/^#[[:space:]]+/, "", linha)
                            print "D\t" linha; next }
    /^#/                  { dentro = 0; next }
    !/^#/                 { exit }
  ' "$_USO_FONTE" 2>/dev/null
}

# Nomes dos atos declarados, um por linha. Usado pelo gate do `conferir`.
#
# Duas fontes, nesta ordem: os blocos `# ato:` (que tambem carregam a forma) e, na
# falta deles, a lista `# atos:` que TODO verbo ja declara. A segunda nao da forma
# por ato, mas da o conjunto valido — e conjunto valido e o que separa a recusa
# graciosa do exit 2 mudo. Entrada que nao e nome de ato (`ato=<stack>`, `nenhum`,
# frase com espaco) fica de fora: verbo de alvo livre nao tem conjunto a conferir.
uso_atos() {
  local blocos
  # `# ato: <inst> buscar ...` (verbo de alvo livre) nao declara ato chamado `<inst>`:
  # o placeholder e do CHAMADOR. Fica no mapa, fora do conjunto que se confere.
  blocos="$(_uso_blocos | awk -F'\t' '$1 == "A" { split($2, p, /[ \t]/); if (p[1] ~ /^[A-Za-z]/) print p[1] }')"
  if [ -n "$blocos" ]; then
    printf '%s\n' "$blocos"
    return 0
  fi
  uso_chave atos \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | grep -Ex '[A-Za-z][A-Za-z0-9_-]*' \
    | grep -vx 'nenhum' \
    || true
}

# Alias de ato, declarado no cabecalho como `# alias: ver = ler`. O alias e aceito
# na chamada e mostra a forma do ato de DESTINO — sem virar linha propria no mapa,
# que descreveria duas vezes o mesmo ato.
uso_alias() {
  sed -n "s/^# alias:[[:space:]]*//p" "$_USO_FONTE" 2>/dev/null \
    | awk -F= -v a="${1:-}" '
        { gsub(/[ \t]/, "", $1); gsub(/[ \t]/, "", $2)
          if ($1 == a) { print $2; exit } }'
}

uso_tem_ato() {
  [ -n "${1:-}" ] || return 1
  uso_atos | grep -qxF -- "$1" && return 0
  [ -n "$(uso_alias "$1")" ]
}

# --- N1: o mapa --------------------------------------------------------------

# Uma linha por ato (sinopse alinhada + resumo) + a tabela de exit. STDOUT.
# Verbo que ainda nao declarou `# ato:` cai no cabecalho velho (`# atos:`), que e
# menos, mas e honesto — nunca uma tela vazia.
uso_mapa() {
  local prop atos
  prop="$(uso_proposito)"
  [ -n "$prop" ] && printf '%s\n\n' "$prop"
  printf 'uso: %s <ato> [args]\n\n' "$_USO_VERBO"
  if [ -z "$(_uso_blocos)" ]; then
    # Sem bloco `# ato:`: o conjunto vem de `# atos:`, e o mapa diz os NOMES. Menos
    # que a forma, mais que nada — e nunca uma tela vazia.
    uso_atos | sed 's/^/  /'
  else
    _uso_blocos | awk -F'\t' -v verbo="$_USO_VERBO" '
      $1 != "A" { next }
      {
        linha = $2
        i = index(linha, " — ")
        if (i > 0) { forma = substr(linha, 1, i - 1); res = substr(linha, i + 4) }
        else       { forma = linha; res = "" }
        sub(/^[ \t]+/, "", res)   # o travessao e multibyte: index() do mawk conta bytes
        if (res == "") printf "  %s\n", forma
        else if (length(forma) <= 40) printf "  %-40s %s\n", forma, res
        else printf "  %s\n  %-40s %s\n", forma, "", res
      }'
  fi
  printf '\nexit: %s\n' "$(uso_exit)"
  printf 'a forma de um ato: %s <ato> --help\n' "$_USO_VERBO"
}

# --- N2: a forma de um ato ---------------------------------------------------

# Sinopse + detalhe (uma linha cada) + exit. STDOUT. Ato sem bloco declarado cai
# no mapa, que e a resposta honesta para "este ato nao declarou forma".
uso_ato() {
  local alvo="${1:-}" destino
  uso_tem_ato "$alvo" || { uso_mapa; return 0; }
  destino="$(uso_alias "$alvo")"
  [ -n "$destino" ] && alvo="$destino"
  _uso_blocos | awk -F'\t' -v verbo="$_USO_VERBO" -v alvo="$alvo" '
    $1 == "A" {
      linha = $2
      split(linha, p, /[ \t]/)
      casou = (p[1] == alvo)
      if (!casou) next
      i = index(linha, " — ")
      if (i > 0) { forma = substr(linha, 1, i - 1); res = substr(linha, i + 4) }
      else       { forma = linha; res = "" }
      sub(/^[ \t]+/, "", res)   # o travessao e multibyte: index() do mawk conta bytes
      printf "uso: %s %s\n", verbo, forma
      if (res != "") printf "  %s\n", res
      print ""
      next
    }
    $1 == "D" && casou { printf "  %s\n", $2 }
  '
  printf '\nexit: %s\n' "$(uso_exit)"
}

# --- erro gracioso -----------------------------------------------------------

# uso_erro "<o que faltou>" [<ato> | --mapa | --conjunto "<valores validos>"]
# Linha 1 sempre `erro: ...`; depois `corrija:` com a forma do ato, o conjunto
# valido, ou o mapa. STDERR, exit 2 — o exit de USO da casa.
uso_erro() {
  local msg="${1:-uso invalido}" modo="${2:---mapa}" extra="${3:-}"
  printf 'erro: %s\n' "$msg" >&2
  printf 'corrija:\n' >&2
  case "$modo" in
    --mapa|"")   uso_mapa | sed 's/^./  &/' >&2 ;;
    --conjunto)  printf '  valores validos: %s\n' "$extra" >&2
                 printf '  o mapa inteiro: %s --help\n' "$_USO_VERBO" >&2 ;;
    *)           if uso_tem_ato "$modo"; then
                   uso_ato "$modo" | sed 's/^./  &/' >&2
                 else
                   uso_mapa | sed 's/^./  &/' >&2
                 fi ;;
  esac
  exit 2
}

# Ato desconhecido: o mapa e a correcao, e o conjunto valido sai na linha do erro.
uso_erro_ato() {
  local ato="${1:-}" validos
  validos="$(uso_atos | paste -sd, - | sed 's/,/, /g')"
  [ -n "$validos" ] || validos="$(uso_chave atos)"
  printf 'erro: ato desconhecido: %s\n' "'${ato}'" >&2
  printf 'corrija:\n' >&2
  printf '  atos de %s: %s\n' "$_USO_VERBO" "$validos" >&2
  printf '  a forma de um ato: %s <ato> --help\n' "$_USO_VERBO" >&2
  exit 2
}

# --- interceptador -----------------------------------------------------------

# Chamado ANTES de qualquer posicional. Nunca erra: pedido de ajuda que nao casa
# com ato declarado cai no mapa, exit 0.
#   USO_SEM_ATO=passa  -> verbo cujo "sem ato" e chamada valida (sinal, deploy,
#                         motor, descobrir, situacao) nao tem o vazio sequestrado.
uso_intercepta() {
  case "${1:-}" in
    -h|--help|--ajuda|ajuda) uso_mapa; exit 0 ;;
    "") case "${USO_SEM_ATO:-mapa}" in
          mapa) uso_mapa; exit 0 ;;
          *) return 0 ;;
        esac ;;
  esac
  case "${2:-}" in
    -h|--help|--ajuda)
      if uso_tem_ato "$1"; then uso_ato "$1"; else uso_mapa; fi
      exit 0 ;;
  esac
  # Ato desconhecido morre AQUI, e nao no `*)` de cada despacho: a recusa e a mesma
  # em toda a casa, e verbo nenhum precisa lembrar de escreve-la.
  #   USO_ATO_LIVRE=1 -> o primeiro argumento nao e ato de conjunto fechado, e sim
  #                      alvo do chamador (deploy <stack>, motor <instancia>,
  #                      descobrir <assunto>, situacao <obra>, ingerir <pasta>).
  if [ -z "${USO_ATO_LIVRE:-}" ] && [ -n "$(uso_atos)" ] && ! uso_tem_ato "$1"; then
    uso_erro_ato "$1"
  fi
  return 0
}

# --- argumento obrigatorio ---------------------------------------------------

# Passo 2 do card: erro de bash NAO vaza. A causa media era `${1:?uso: ...}`, que
# imprime `bin/tarefas: line 761: 1: uso:` — endereco do interpretador, nao do
# chamador. A cura e na FONTE, nao num filtro de stderr: `exec 2> >(sed ...)` faz
# a saida de erro depender de um processo assincrono que o exit do verbo pode
# cortar no meio, e erro perdido e pior que erro feio.
#
#   uso_arg "${1:-}" "<id>" ler      # falta -> erro: falta <id> + a forma de `ler`
#
# GUARDA, nao filtro: nao ecoa valor nenhum, e por isso se usa como COMANDO, nunca
# dentro de `$( )`. Em substituicao o `exit 2` mataria so o subshell, o verbo seguiria
# com a string vazia e o erro sairia duas vezes — medido ao ligar o `repo`.
uso_arg() {
  [ -n "${1:-}" ] || uso_erro "falta ${2:-<arg>}" "${3:---mapa}"
}

# Mesma coisa para flag que exige valor: `uso_flag "${2:-}" -m commitar`.
uso_flag() {
  case "${1:-}" in
    ""|-*) uso_erro "a flag ${2:---flag} exige um valor" "${3:---mapa}" ;;
  esac
}
