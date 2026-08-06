#!/usr/bin/env bash
# criacao = primeiro commit que adicionou o arquivo; ultima = ultimo commit que o tocou
set -u
cd "$HOME/AI"
dump() { # repo path
  local repo="$1" p="$2"
  local cri ult
  cri=$(cd "$repo" && git log --diff-filter=A --follow --format=%aI -- "$p" | tail -1)
  ult=$(cd "$repo" && git log -1 --format=%aI -- "$p")
  printf '%s\t%s\t%s\t%s\n' "$repo" "$p" "${cri:-NA}" "${ult:-NA}"
}
A=platafirma-arquitetura
C=platafirma-conhecimento
for p in ontologia/adr/0062-conceito-nao-estanteia.md ontologia/adr/0063-teia-vizinhanca-por-conceito.md ontologia/adr/0065-medida-de-qualidade-da-faceta-conceito.md ontologia/adr/0057-dominio-platafirma-autorreferente.md ontologia/adr/0059-gestao-organizacional-e-dominio.md ontologia/adr/0069-dominio-declara-rotulo-e-recorte.md ontologia/adr/0061-regimes-de-entrada-no-acervo.md ontologia/adr/0072-endereco-e-a-moradia-da-obra.md ontologia/adr/0073-golden-record-de-obra.md ontologia/adr/0074-nome-de-arquivo-nao-e-chave-nem-indice.md; do dump "$C" "$p"; done
for p in macro-global/capabilities/seguranca/decisions/0004-modelo-abac-com-papel-como-atributo.md macro-global/decisions/0009-vocabulario-de-dominio-unico-por-instancia.md macro-global/decisions/0011-hierarquia-de-dominio-em-campo.md macro-global/decisions/0012-dominio-e-entidade-identificavel.md macro-global/decisions/0005-politica-do-registro-de-decisoes.md macro-global/decisions/0006-adocoes-do-registro-institucional.md macro-global/decisions/0015-forma-da-adr.md macro-global/decisions/0026-camada-de-fronteira.md macro-global/decisions/0025-componente-e-substrato.md macro-global/decisions/0013-busca-semantica-por-gateway.md; do dump "$A" "$p"; done
echo "---SHA---"
(cd "$A" && echo -n "$A "; git rev-parse HEAD)
(cd "$C" && echo -n "$C "; git rev-parse HEAD)
echo "---GREP-TERMOS---"
for t in "arquitetura de software" "arquitetura de dados" "governan.a de dados" "p.s-qu.ntic" "intelig.ncia" "curadoria"; do
  n=$( { (cd "$A" && git ls-files 'macro-global/decisions/*' 'macro-global/capabilities/*/decisions/*' | xargs -r grep -ilE "$t") ; (cd "$C" && git ls-files 'ontologia/adr/*' | xargs -r grep -ilE "$t") ; } | wc -l)
  echo "$t -> arquivos_que_mencionam=$n"
done
