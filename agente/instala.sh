#!/usr/bin/env bash
# Instala o ambiente do agente na conta claudinho, a partir da RELEASE no ar.
# Idempotente, sem privilégio. Fonte: /opt/platafirma/current/harness/agente;
# destino é o que o Code lê (~/.claude).
#
# ambiente: PF_RELEASE_RAIZ (default /opt/platafirma), PLATAFIRMA_RELEASE (default
#           $PF_RELEASE_RAIZ/current). Só para teste apontar outra árvore.
#
# Por que da release e nunca do clone: o que o Code lê em toda sessão é produção. Ligado
# a um clone de bancada, apagar a bancada tira o arranque da conta — e o clone muda de
# branch debaixo de sessão viva.
#   ~/.claude/CLAUDE.md     -> symlink para a release (ro, atravessa promoção por `current`)
#   ~/.claude/settings.json -> CÓPIA gerida aqui: o Code grava nele, e /opt é r-x
set -euo pipefail

. "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/raizes.sh"

FONTE="$PLATAFIRMA_RELEASE/harness/agente"
DESTINO="$HOME/.claude"

if [ ! -f "$FONTE/CLAUDE.md" ] || [ ! -f "$FONTE/settings.json" ]; then
  echo "release ausente em $FONTE — instalar o agente exige a release promovida (release promover)." >&2
  exit 3
fi

mkdir -p "$DESTINO"

liga() {
  local origem="$1" alvo="$2"
  if [ -L "$alvo" ]; then
    [ "$(readlink "$alvo")" = "$origem" ] && {
      echo "ok (já ligado): $alvo"; return; }
    rm "$alvo"
  elif [ -e "$alvo" ]; then
    mv "$alvo" "$alvo.bak-$(date +%Y%m%dT%H%M%S)"
    echo "arquivo existente movido para .bak: $alvo"
  fi
  ln -s "$origem" "$alvo"
  echo "ligado: $alvo -> $origem"
}

# Cópia gerida: igual à fonte, nada a fazer; diferente (ou symlink antigo), guarda o
# anterior em .bak e copia — o que o Code gravou ali não some sem rastro.
copia() {
  local origem="$1" alvo="$2"
  if [ -f "$alvo" ] && [ ! -L "$alvo" ] && cmp -s "$origem" "$alvo"; then
    echo "ok (cópia igual à release): $alvo"; return
  fi
  if [ -L "$alvo" ]; then
    rm "$alvo"
  elif [ -e "$alvo" ]; then
    mv "$alvo" "$alvo.bak-$(date +%Y%m%dT%H%M%S)"
    echo "anterior movido para .bak: $alvo"
  fi
  install -m 0644 "$origem" "$alvo"
  echo "copiado: $origem -> $alvo"
}

liga "$FONTE/CLAUDE.md" "$DESTINO/CLAUDE.md"
copia "$FONTE/settings.json" "$DESTINO/settings.json"

# Verbos: o PATH da release (/opt/platafirma/current/harness/bin) cobre `tarefas` e os
# demais. Este instalador não grava em ~/.local/bin (desenho #3010 §5): sobra de
# instalação anterior ali sai na fase de host, não aqui.

# Shims de instancia: para toda INSTANCIA cujo nome != o verbo que serve
# (rastreador->tarefas, keycloak->acesso), materializa um redirecionador que
# avisa e delega, em $PLATAFIRMA_INSTANCIA/var/shims (estado da instância, nunca ~/.local/bin).
# Dirigido pelo acervo, nao por lista fixa: instancia nova no golden record ganha shim
# aqui, sem editar este script.
GERADOR="$PLATAFIRMA_RELEASE/harness/bin/_shims-instancia"
if [ -x "$GERADOR" ]; then
  bash "$GERADOR" || echo "aviso: gerador de shims de instancia falhou (segue sem)"
fi

# Skills — lista explícita, nunca "tudo que houver no harness".
# claudinha-fabrica não carrega `platafirma` (entrega o org chart, que o
# contrato dela nega) nem `osint` (ambiente isolado, outra colaboradora).
SKILLS_DA_FABRICA=()   # vazio até existir skills/fabrica/

SKILLS="$PLATAFIRMA_RELEASE/harness/skills"
mkdir -p "$DESTINO/skills"
for nome in ${SKILLS_DA_FABRICA[@]+"${SKILLS_DA_FABRICA[@]}"}; do
  if [ -d "$SKILLS/$nome" ]; then
    liga "$SKILLS/$nome" "$DESTINO/skills/$nome"
  else
    echo "aviso: skill declarada e ausente na release: $nome"
  fi
done

# Symlink de skill não declarada é sobra de instalação anterior: remove.
for l in "$DESTINO"/skills/*; do
  [ -L "$l" ] || continue
  nome="$(basename "$l")"
  case " ${SKILLS_DA_FABRICA[*]-} " in *" $nome "*) continue;; esac
  rm "$l"; echo "removido (não declarado): $l"
done

echo
echo "conferir:  ls -l ~/.claude/CLAUDE.md ~/.claude/skills/"
