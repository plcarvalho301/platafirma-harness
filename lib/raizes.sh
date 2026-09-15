# raizes.sh — as duas raizes de producao e a bancada declarada (card #3010).
#
# Producao mora em duas raizes e so nelas: a release (codigo imutavel) e a instancia
# (segredos, dados, estado, logs). Todo caminho de producao deriva delas. A bancada
# (onde se escreve codigo) nunca e lida por producao; so os verbos de bancada chamam
# pf_bancada, que falha alto quando a conta nao declarou onde ela fica.
#
# Uso: . "$(dirname "$(readlink -f "$0")")/../lib/raizes.sh"
# As variaveis de ambiente existem para teste apontar tudo para um diretorio temporario.

PF_RELEASE_RAIZ="${PF_RELEASE_RAIZ:-/opt/platafirma}"
PF_RELEASE="${PF_RELEASE:-$PF_RELEASE_RAIZ/current}"
PF_INSTANCIA="${PF_INSTANCIA:-/srv/platafirma/casa}"
PF_ARQUIVO_BANCADA="${PF_ARQUIVO_BANCADA:-$HOME/.config/platafirma/bancada}"

# Imprime a raiz da bancada declarada pela conta; sem declaracao, avisa e devolve 3.
pf_bancada() {
  local b="${PF_BANCADA:-}"
  if [ -z "$b" ] && [ -r "$PF_ARQUIVO_BANCADA" ]; then
    IFS= read -r b < "$PF_ARQUIVO_BANCADA" || true
  fi
  if [ -z "$b" ]; then
    printf 'bancada nao declarada: defina PF_BANCADA ou escreva a raiz em %s\n' "$PF_ARQUIVO_BANCADA" >&2
    return 3
  fi
  printf '%s' "$b"
}
