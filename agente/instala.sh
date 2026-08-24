#!/usr/bin/env bash
# Instala o ambiente do agente na conta claudinho, por symlink.
# Idempotente, sem privilégio. Fonte versionada; destino é o que o Code lê.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="$HOME/.claude"

mkdir -p "$DESTINO"

liga() {
  local origem="$1" alvo="$2"
  if [ -L "$alvo" ]; then
    [ "$(readlink -f "$alvo")" = "$(readlink -f "$origem")" ] && {
      echo "ok (já ligado): $alvo"; return; }
    rm "$alvo"
  elif [ -e "$alvo" ]; then
    mv "$alvo" "$alvo.bak-$(date +%Y%m%dT%H%M%S)"
    echo "arquivo existente movido para .bak: $alvo"
  fi
  ln -s "$origem" "$alvo"
  echo "ligado: $alvo -> $origem"
}

liga "$AQUI/CLAUDE.md" "$DESTINO/CLAUDE.md"
liga "$AQUI/settings.json" "$DESTINO/settings.json"
# Verbo do rastreador: fonte no harness, um so nos dois ambientes.
# A credencial continua sendo a da conta (~/.claude/vikunja.env).
mkdir -p "$HOME/.local/bin"
TAREFAS="$HOME/AI/platafirma-harness/bin/tarefas"
if [ -x "$TAREFAS" ]; then
  liga "$TAREFAS" "$HOME/.local/bin/tarefas"
  if [ -L "$HOME/.local/bin/card" ]; then
    rm "$HOME/.local/bin/card"
    echo "removido (aposentado por tarefas): ~/.local/bin/card"
  fi
else
  echo "aviso: harness ausente em ~/AI/platafirma-harness — sem verbo 'tarefas'."
  echo "       git clone git@github.com:plcarvalho301/platafirma-harness.git ~/AI/platafirma-harness"
fi

# Shims de instancia: para toda INSTANCIA cujo nome != o verbo que serve
# (rastreador->tarefas, keycloak->acesso), materializa um redirecionador que
# avisa e delega. Dirigido pelo acervo, nao por lista fixa: instancia nova no
# golden record ganha shim aqui, sem editar este script. Ver docs/administrativo.md.
GERADOR="$HOME/AI/platafirma-harness/bin/_shims-instancia"
if [ -x "$GERADOR" ]; then
  bash "$GERADOR" || echo "aviso: gerador de shims de instancia falhou (segue sem)"
fi

# Skills — lista explícita, nunca "tudo que houver no harness".
# claudinha-fabrica não carrega `platafirma` (entrega o org chart, que o
# contrato dela nega) nem `osint` (ambiente isolado, outra colaboradora).
SKILLS_DA_FABRICA=()   # vazio até existir skills/fabrica/

HARNESS="$HOME/AI/platafirma-harness/skills"
mkdir -p "$DESTINO/skills"
for nome in ${SKILLS_DA_FABRICA[@]+"${SKILLS_DA_FABRICA[@]}"}; do
  if [ -d "$HARNESS/$nome" ]; then
    liga "$HARNESS/$nome" "$DESTINO/skills/$nome"
  else
    echo "aviso: skill declarada e ausente no harness: $nome"
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
