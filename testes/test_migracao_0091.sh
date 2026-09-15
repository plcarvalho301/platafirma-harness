#!/usr/bin/env bash
# Migracao 0091 (acervo.stack sem a pasta de trabalho da conta, card #3010), aplicada de verdade:
#   1. Postgres DESCARTAVEL local (initdb num tmp, so socket unix, sem TCP, sem docker);
#   2. schema do acervo pelo 0076c real + as 12 linhas MEDIDAS em 15/09/2026
#      (testes/test_migracao_0091_linhas_medidas.json, sem valor de segredo) + as 4 ligacoes medidas;
#   3. aceites embutidos: linha que o bin/deploy recusaria aborta a migracao INTEIRA (transacional);
#   4. ensaio do dono (commit trocado por rollback) nao grava nada;
#   5. aplicada como o `migrar` aplica (psql -1, ON_ERROR_STOP), duas vezes: mesmo resultado;
#   6. o resultado, stack a stack, e exatamente o contrato do bin/deploy da main; campos que nao
#      sao caminho (papel, critico, repo, profiles, via/quem/janela/estado) ficam os medidos;
#   7. o bin/deploy REAL le essa topologia (serializada pelo `acervo stack ver --json` real) numa
#      release e instancia falsas num tmp, com docker stub: config/segredos/rotas/acessos das 12
#      stacks sem exit 3, projeto compose preservado, sobreposicao so pelo verbo;
#   8. banco novo (sem linha nenhuma) sai com as 12 stacks e as 4 ligacoes.
#
# Validacao no banco real (dono, antes do `migrar aplicar rag`), sem gravar:
#   sed 's/^commit;$/rollback;/' /opt/platafirma/current/harness/sessao/migracao/0091_acervo_stack_release_instancia.sql \
#     | DOCKER_HOST=unix:///run/user/1001/docker.sock docker exec -i rag-extractor-pg \
#         psql -U rag -d rag_extractor -v ON_ERROR_STOP=1 -P pager=off -f -
#   = BEGIN; aplicar; aceites; SELECT de prova (12 linhas); ROLLBACK. Nenhum ERROR esperado.
#
# Ambiente: PLATAFIRMA_PG_BIN (diretorio com initdb/pg_ctl/psql; default pg_config --bindir, senao
# o maior /usr/lib/postgresql/*/bin). Sem Postgres local o teste FALHA: verde sem banco nao prova nada.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MIG="$REPO_ROOT/sessao/migracao/0091_acervo_stack_release_instancia.sql"
DDL="$REPO_ROOT/sessao/migracao/0076c_acervo_stack.sql"
FIXTURE="$SCRIPT_DIR/test_migracao_0091_linhas_medidas.json"
STACK_PY="$REPO_ROOT/bin/_acervo/stack"
DEPLOY="$REPO_ROOT/bin/deploy"

falha() { echo "FALHA: $*" >&2; exit 1; }
pulado() { echo "PULADO: $*"; }

PG_BIN="${PLATAFIRMA_PG_BIN:-}"
if [ -z "$PG_BIN" ]; then
  PG_BIN="$(pg_config --bindir 2>/dev/null || true)"
  [ -x "$PG_BIN/initdb" ] || PG_BIN="$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1 || true)"
fi
[ -n "$PG_BIN" ] && [ -x "$PG_BIN/initdb" ] && [ -x "$PG_BIN/pg_ctl" ] && [ -x "$PG_BIN/psql" ] \
  || falha "sem Postgres local (initdb/pg_ctl/psql); aponte PLATAFIRMA_PG_BIN"
command -v jq >/dev/null || falha "jq ausente (dependencia do bin/deploy)"
command -v python3 >/dev/null || falha "python3 ausente"
python3 -c 'import yaml' 2>/dev/null || falha "python3 sem yaml (o bin/deploy le name: do compose com ele)"

TMP_DIR="$(mktemp -d /tmp/pf-migracao-0091.XXXXXX)"
PGDATA_T="$TMP_DIR/pg"; SOCK="$TMP_DIR/sock"
parar_pg() { [ -f "$PGDATA_T/postmaster.pid" ] && "$PG_BIN/pg_ctl" -D "$PGDATA_T" -m immediate stop >/dev/null 2>&1 || true; }
trap 'parar_pg; chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

PSQL() { "$PG_BIN/psql" -X -h "$SOCK" -U teste "$@"; }
# A pasta de trabalho da conta, na FORMA EXATA das linhas medidas (til + barra + nome; conferido
# campo a campo contra o SELECT so-leitura de 15/09/2026: zero diferencas). Montada em tempo de
# execucao: nenhum literal dela neste repo.
PASTA="$(python3 -c 'print("~/" + "A" + "I")')"
SQL_TEM_PASTA="select count(*) from acervo.stack where concat_ws(' ',compose,rotas::text,segredos::text,reversao::text,gate::text,nota) ~ ('/'||'AI([/[:space:]\"]|\$)')"
retrato() { PSQL -d "$1" -tA -c "select coalesce(md5(string_agg(row_to_json(s)::text, E'\n' order by slug)),'vazia') from acervo.stack s"; }
aplicar() { PSQL -d "$1" -v ON_ERROR_STOP=1 -1 -P pager=off -f - < "$MIG"; }   # como o bin/migrar

echo "=== migracao 0091: Postgres descartavel + linhas medidas + bin/deploy ==="

mkdir -p "$SOCK"
"$PG_BIN/initdb" -D "$PGDATA_T" -A trust -U teste -E UTF8 --locale=C --no-sync >"$TMP_DIR/initdb.log" 2>&1 \
  || falha "initdb: $(tail -5 "$TMP_DIR/initdb.log")"
"$PG_BIN/pg_ctl" -D "$PGDATA_T" -l "$TMP_DIR/pg.log" -w \
  -o "-k $SOCK -c listen_addresses='' -p 5432 -F" start >/dev/null \
  || falha "pg_ctl start: $(tail -5 "$TMP_DIR/pg.log")"

# ------------------------------------------------------------------------------------------------
PY="$TMP_DIR/aux.py"
cat > "$PY" <<'PYEOF'
import importlib.machinery, importlib.util, io, json, os, subprocess, sys
from contextlib import redirect_stdout

OPT, SRV = "/opt/platafirma", "/srv/platafirma/casa"
CF = SRV + "/deploy/core/cloudflared.yml"
GATE_CORE = OPT + "/current/core/docker-compose.yml"
TUNEL = SRV + "/segredos/core/cloudflared/01452d04-7dd9-40ea-be5a-f8bcaa7bed8f.json"
R = OPT + "/current"
S = SRV + "/segredos"

# O contrato do bin/deploy (main) aplicado as 12 linhas medidas: compose so a base, na release da
# propria familia; rotas/gate sob a instancia ou a release; segredos no cofre da stack (+ cofre
# matrix do chat, credencial do tunel e env do ops-server no core); projeto = name: da base medido
# nos conteineres vivos em 15/09/2026.
ESPERADO = {
  "acervo-api":      dict(projeto="acervo-api",      compose=[R+"/conhecimento/acervo-api/docker-compose.yml"], rotas=None, gate=None, segredos=[S+"/acervo-api/"]),
  "chat":            dict(projeto="chat",            compose=[R+"/harness/chat/docker-compose.yml"], rotas=CF, gate=None,
                          segredos=[S+"/chat/", S+"/matrix/oidc-client-secret", S+"/matrix/signing.key", S+"/matrix/segredos.yaml", S+"/matrix/registration.yaml"]),
  "conhecimento":    dict(projeto="plataforma-wiki", compose=[R+"/conhecimento/docker-compose.yml", R+"/conhecimento/docker-compose.override.yml"], rotas=None, gate=None, segredos=[S+"/conhecimento/"]),
  "core":            dict(projeto="platafirma-core", compose=[R+"/core/docker-compose.yml"], rotas=CF, gate=None,
                          segredos=[S+"/core/", TUNEL, S+"/ops/systemd.env"]),
  "harness-controle": dict(projeto="harness-controle", compose=[R+"/harness/controle/compose.yaml"], rotas=None, gate=None, segredos=[]),
  "harness-sessao":  dict(projeto="harness-sessao",  compose=[R+"/harness/sessao/compose.yaml"], rotas=None, gate=None, segredos=[S+"/harness-sessao/"]),
  "jaiminho":        dict(projeto="jaiminho",        compose=[R+"/harness/jaiminho/docker-compose.yml"], rotas=None, gate=None, segredos=[S+"/jaiminho/"]),
  "motor":           dict(projeto="motor",           compose=[R+"/motor/docker-compose.yml"], rotas=None, gate=None, segredos=[S+"/motor/"]),
  "rag":             dict(projeto="edm",             compose=[R+"/conhecimento/rag/docker-compose.yml", R+"/conhecimento/rag/docker-compose.gpu.yml"], rotas=None, gate=None, segredos=[S+"/rag/"]),
  "rastreador":      dict(projeto="rastreador",      compose=[R+"/rastreador/docker-compose.yml"], rotas=CF, gate=GATE_CORE, segredos=[S+"/rastreador/"]),
  "rastreador-tela": dict(projeto="rastreador-tela", compose=[R+"/ui/app/rastreador/docker-compose.yml"], rotas=CF, gate=GATE_CORE, segredos=[]),
  "searxng":         dict(projeto="searxng",         compose=[R+"/core/deploy/searxng/docker-compose.yml"], rotas=None, gate=None, segredos=[S+"/searxng/"]),
}
LIGACOES = [("keycloak", "core"), ("matrix", "chat"), ("rastreador", "rastreador"), ("rastreador", "rastreador-tela")]


def lit_txt(v):
    return "null" if v is None else "'" + str(v).replace("'", "''") + "'"


def lit_jsonb(v):
    return "null" if v is None else "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def fixture(caminho, pasta):
    bruto = open(caminho, encoding="utf-8").read().replace("@PASTA_DE_TRABALHO@", pasta)
    return json.loads(bruto)["linhas"]


def cmd_carga(caminho, pasta):
    linhas = fixture(caminho, pasta)
    print("begin;")
    print("insert into acervo.ferramental_instancia (slug) values ('keycloak'),('matrix'),('rastreador'),('ollama');")
    for l in linhas:
        print("insert into acervo.stack (slug,papel,critico,repo,compose,rotas,segredos,reversao,gate,profiles,nota) values (%s);" % ",".join([
            lit_txt(l["slug"]), lit_txt(l["papel"]), "true" if l["critico"] else "false", lit_txt(l["repo"]),
            lit_txt(l["compose"]), lit_jsonb(l["rotas"]), lit_jsonb(l["segredos"]), lit_jsonb(l["reversao"]),
            lit_jsonb(l["gate"]), lit_jsonb(l["profiles"]), lit_txt(l["nota"])]))
    for i, s in LIGACOES:
        print("insert into acervo.instancia_roda_em_stack select i.id, s.id from acervo.ferramental_instancia i, "
              "acervo.stack s where i.slug=%s and s.slug=%s;" % (lit_txt(i), lit_txt(s)))
    print("commit;")


def cmd_topo(stack_py, psql, sock, banco, saida):
    # A serializacao e a do verbo real (`acervo stack ver --json`); so o transporte do psql muda
    # (socket local em vez de docker exec).
    loader = importlib.machinery.SourceFileLoader("acervo_stack", stack_py)
    spec = importlib.util.spec_from_loader("acervo_stack", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)

    def _psql(sql, stdin=None):
        return subprocess.run([psql, "-X", "-h", sock, "-U", "teste", "-d", banco, "-v", "ON_ERROR_STOP=1",
                               "-tAF|", "-c", sql], capture_output=True, text=True, check=True).stdout
    mod._psql = _psql
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.cmd_ver(True)
    arr = json.loads(buf.getvalue())
    json.dump({"stacks": {s["slug"]: s for s in arr}}, open(saida, "w"), ensure_ascii=False, indent=1)


def como_lista(v):
    return [] if v is None else (v if isinstance(v, list) else [v])


def cmd_confere(caminho, pasta, topo):
    med = {l["slug"]: l for l in fixture(caminho, pasta)}
    st = json.load(open(topo))["stacks"]
    erros = []
    if sorted(st) != sorted(ESPERADO):
        erros.append("stacks: %s != %s" % (sorted(st), sorted(ESPERADO)))
    for slug, esp in ESPERADO.items():
        s = st.get(slug)
        if s is None:
            continue
        for campo in ("compose", "rotas", "gate", "segredos"):
            got = como_lista(s[campo]) if campo == "compose" else s[campo]
            if got != esp[campo]:
                erros.append("%s.%s: %r != %r" % (slug, campo, got, esp[campo]))
        # serializacao do `acervo stack`: compose de um arquivo e string, de varios e lista JSON
        if len(esp["compose"]) == 1 and not isinstance(s["compose"], str):
            erros.append("%s.compose devia ser string: %r" % (slug, s["compose"]))
        m = med[slug]
        for campo in ("papel", "critico", "repo", "profiles"):
            if s[campo] != m[campo]:
                erros.append("%s.%s mudou: %r -> %r" % (slug, campo, m[campo], s[campo]))
        for k in ("via", "quem", "janela_min", "estado"):
            if (s["reversao"] or {}).get(k) != (m["reversao"] or {}).get(k):
                erros.append("%s.reversao.%s mudou: %r -> %r" % (slug, k, m["reversao"].get(k), s["reversao"].get(k)))
        texto = json.dumps(s, ensure_ascii=False)
        if pasta in texto or "~/" in texto or '"~' in texto:
            erros.append("%s ainda cita a pasta de trabalho ou o home: %s" % (slug, texto[:160]))
        curto = s["repo"].replace("platafirma-", "", 1)
        for c in como_lista(s["compose"]):
            if not c.startswith("%s/current/%s/" % (OPT, curto)) or ".." in c:
                erros.append("%s: compose fora da release da familia: %s" % (slug, c))
        for c in como_lista(s["rotas"]) + como_lista(s["gate"]) + como_lista(s["segredos"]):
            if not (c.startswith(SRV + "/") or c.startswith(OPT + "/")) or ".." in c:
                erros.append("%s: caminho fora das raizes: %s" % (slug, c))
    if erros:
        print("\n".join(erros))
        sys.exit(1)
    print("12 stacks no contrato; campos medidos preservados")


def mapeia(v, opt, srv):
    if isinstance(v, str):
        if v.startswith(OPT + "/"):
            return opt + v[len(OPT):]
        if v.startswith(SRV + "/"):
            return srv + v[len(SRV):]
        return v
    if isinstance(v, list):
        return [mapeia(x, opt, srv) for x in v]
    return v


def cmd_palco(topo, opt, srv, sha, envdir, saida):
    """Release e instancia falsas com o layout do desenho §2-§3, a topologia com as raizes trocadas
    para o tmp, e para cada stack a invocacao EXATA que o deploy deve fazer no `config --quiet`."""
    st = json.load(open(topo))["stacks"]
    for slug, s in st.items():
        repo, curto = s["repo"], s["repo"].replace("platafirma-", "", 1)
        arv = os.path.join(opt, repo, sha)
        for i, c in enumerate(como_lista(s["compose"])):
            rel = c[len("%s/current/%s/" % (OPT, curto)):]
            p = os.path.join(arv, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                if i == 0:
                    f.write("name: %s\n" % ESPERADO[slug]["projeto"])
                f.write("services:\n  app:\n    image: busybox\n")
        if not os.path.islink(os.path.join(opt, repo, "current")):
            os.symlink(sha, os.path.join(opt, repo, "current"))
        os.makedirs(os.path.join(opt, "current"), exist_ok=True)
        atalho = os.path.join(opt, "current", curto)
        if not os.path.islink(atalho):
            os.symlink(os.path.join("..", repo, "current"), atalho)
        for item in como_lista(s["segredos"]):
            alvo = mapeia(item, opt, srv)
            if alvo.endswith("/"):
                os.makedirs(alvo, mode=0o700, exist_ok=True)
                # um arquivo por variavel, com valor FALSO, para o env-file ter o que materializar
                with open(os.path.join(alvo, "SENHA_FALSA"), "w") as f:
                    f.write("valor-falso-0091")
            else:
                os.makedirs(os.path.dirname(alvo), mode=0o700, exist_ok=True)
                with open(alvo, "w") as f:
                    f.write("valor-falso-0091")
        s["compose"] = mapeia(s["compose"], opt, srv)
        for campo in ("rotas", "gate", "segredos"):
            s[campo] = mapeia(s[campo], opt, srv)
    cf = mapeia(CF, opt, srv)
    os.makedirs(os.path.dirname(cf), exist_ok=True)
    with open(cf, "w") as f:
        f.write("ingress:\n  - hostname: exemplo.invalid\n    service: http://app:80\n  - service: http_status:404\n")
    ov = os.path.join(srv, "deploy", "core", "compose.override.yaml")
    with open(ov, "w") as f:
        f.write("services:\n  app:\n    environment:\n      X: \"1\"\n")
    json.dump({"stacks": st}, open(saida, "w"), ensure_ascii=False, indent=1)
    for slug in sorted(st):
        s = st[slug]
        repo, curto = s["repo"], s["repo"].replace("platafirma-", "", 1)
        arv = os.path.join(opt, repo, sha)
        args = ["docker", "compose", "-p", ESPERADO[slug]["projeto"]]
        for c in como_lista(s["compose"]):
            args += ["-f", os.path.join(arv, c[len("%s/current/%s/" % (opt, curto)):])]
        ovs = os.path.join(srv, "deploy", slug, "compose.override.yaml")
        if os.path.exists(ovs):
            args += ["-f", ovs]
        args += ["--env-file", os.path.join(envdir, slug + ".env")]
        for p in como_lista(s["profiles"]):
            args += ["--profile", p]
        args += ["config", "--quiet"]
        print("\t".join([slug, ESPERADO[slug]["projeto"], " ".join(args),
                         "1" if s["rotas"] else "0", s["gate"] or ""]))


def cmd_familia(topo, repo_root):
    """O palco escreve composes falsos com o name: esperado; sem isto o teste passaria mesmo se o
    compose REAL tivesse outro projeto. Para a familia deste repo (platafirma-harness), o arquivo
    que a 0091 declara existe aqui, o name: dele e o projeto medido, e nao ha
    docker-compose.override.yml ao lado sem estar declarado (o deploy sairia 3)."""
    import yaml
    st = json.load(open(topo))["stacks"]
    erros, vistos = [], 0
    for slug, s in sorted(st.items()):
        if s["repo"] != "platafirma-harness":
            continue
        decl = como_lista(s["compose"])
        rels = [c[len("%s/current/harness/" % OPT):] for c in decl]
        for i, rel in enumerate(rels):
            p = os.path.join(repo_root, rel)
            if not os.path.isfile(p):
                erros.append("%s: compose declarado nao existe no repo: %s" % (slug, rel))
                continue
            vistos += 1
            ov = os.path.join(os.path.dirname(rel), "docker-compose.override.yml")
            if os.path.exists(os.path.join(repo_root, ov)) and ov not in rels:
                erros.append("%s: override nao declarado: %s" % (slug, ov))
            if i == 0:
                nome = (yaml.safe_load(open(p)) or {}).get("name")
                if nome != ESPERADO[slug]["projeto"]:
                    erros.append("%s: name: real %r != projeto medido %r" % (slug, nome, ESPERADO[slug]["projeto"]))
    if vistos < 4:
        erros.append("esperava os 4 composes da familia harness, vi %d" % vistos)
    if erros:
        print("\n".join(erros))
        sys.exit(1)
    print("familia harness: %d composes reais com o projeto medido" % vistos)


if __name__ == "__main__":
    ato, resto = sys.argv[1], sys.argv[2:]
    {"carga": cmd_carga, "topo": cmd_topo, "confere": cmd_confere, "palco": cmd_palco,
     "familia": cmd_familia}[ato](*resto)
PYEOF

preparar_banco() {  # $1=banco ; schema minimo do acervo (ferramental_instancia so com o que a FK usa) + 0076c real
  PSQL -d postgres -q -c "create database \"$1\"" >/dev/null
  PSQL -d "$1" -q -v ON_ERROR_STOP=1 >/dev/null <<'SQL'
create schema acervo;
create table acervo.ferramental_instancia (id bigint generated always as identity primary key, slug text not null unique);
SQL
  PSQL -d "$1" -q -v ON_ERROR_STOP=1 -f "$DDL" >/dev/null || falha "0076c nao aplicou em $1"
}

echo "--- 1: banco com as 12 linhas medidas (todas na pasta de trabalho) e as 4 ligacoes"
preparar_banco rag_extractor
python3 "$PY" carga "$FIXTURE" "$PASTA" | PSQL -d rag_extractor -q -v ON_ERROR_STOP=1 >/dev/null || falha "carga das linhas medidas"
[ "$(PSQL -d rag_extractor -tA -c 'select count(*) from acervo.stack')" = 12 ] || falha "fixture devia ter 12 linhas"
[ "$(PSQL -d rag_extractor -tA -c "$SQL_TEM_PASTA")" = 12 ] || falha "as 12 linhas medidas deviam casar o padrao da pasta de trabalho"
[ "$(PSQL -d rag_extractor -tA -c 'select count(*) from acervo.instancia_roda_em_stack')" = 4 ] || falha "ligacoes medidas"
echo "OK"

echo "--- 2: aceites abortam a migracao INTEIRA quando sobra linha que o deploy recusaria"
fantasma() {  # $1=compose (text) $2=segredos (jsonb) $3=repo $4=mensagem esperada [$5=rotas jsonb] [$6=gate jsonb]
  PSQL -d rag_extractor -q -v ON_ERROR_STOP=1 \
    -c "insert into acervo.stack (slug,repo,compose,segredos,rotas,gate) values ('fantasma', '$3', '$1', '$2'::jsonb, ${5:-null}, ${6:-null})" >/dev/null
  local antes depois out rc
  antes="$(retrato rag_extractor)"
  set +e; out="$(aplicar rag_extractor 2>&1)"; rc=$?; set -e
  [ "$rc" -ne 0 ] || falha "migracao devia abortar com fantasma compose=$1 segredos=$2: $out"
  grep -qF "$4" <<<"$out" || falha "mensagem do aceite (esperava '$4'): $out"
  grep -q "fantasma" <<<"$out" || falha "aceite devia nomear a linha: $out"
  depois="$(retrato rag_extractor)"
  [ "$antes" = "$depois" ] || falha "abortou mas gravou (nao transacional) com fantasma $1"
  [ "$(PSQL -d rag_extractor -tA -c "$SQL_TEM_PASTA")" -ge 12 ] || falha "linhas medidas foram reescritas apesar do aborto"
  PSQL -d rag_extractor -q -c "delete from acervo.stack where slug='fantasma'" >/dev/null
}
# a) defeito medido da 0091 da main: sobreposicao de /srv dentro de `compose`
fantasma '["/opt/platafirma/current/core/docker-compose.yml", "/srv/platafirma/casa/deploy/fantasma/compose.override.yaml"]' '[]' platafirma-core \
  "compose fora do contrato do deploy"
# b) defeito medido: segredo no home da conta (~/.config/ops/env)
fantasma '/opt/platafirma/current/core/docker-compose.yml' '["~/.config/ops/env"]' platafirma-core \
  "rotas/gate/segredos fora das raizes de producao"
# c) defeito medido: linha que a migracao nao reescreve e segue na pasta de trabalho (era a searxng)
fantasma "$PASTA/platafirma-core/deploy/searxng/docker-compose.yml" '[]' platafirma-core \
  "ainda apontam a pasta de trabalho da conta"
# d) base na release de OUTRA familia (rel_na_familia recusa)
fantasma '/opt/platafirma/current/core/docker-compose.yml' '[]' platafirma-motor \
  "compose fora do contrato do deploy"
# e) repo VAZIO com compose relativo: o deploy sai 3 ("nao declara repo"); o aceite tinha de pegar
#    '' e nao so null (verificador adversarial: passava com rc 0)
fantasma 'docker-compose.yml' '[]' '' "compose fora do contrato do deploy"
# f) rotas absoluta fora de /srv/platafirma/casa e /opt/platafirma (resolve recusa)
fantasma '/opt/platafirma/current/core/docker-compose.yml' '[]' platafirma-core \
  "rotas/gate/segredos fora das raizes de producao" "'\"/etc/cloudflared/config.yml\"'::jsonb"
# g) gate relativo com .. (resolve recusa)
fantasma '/opt/platafirma/current/core/docker-compose.yml' '[]' platafirma-core \
  "rotas/gate/segredos fora das raizes de producao" null "'\"../core/docker-compose.yml\"'::jsonb"
# h) segredos com tipo que o deploy nao le (objeto)
fantasma '/opt/platafirma/current/core/docker-compose.yml' '{"a": "b"}' platafirma-core \
  "rotas/gate/segredos fora das raizes de producao"
# i) compose relativo com .. (rel_na_familia recusa)
fantasma '../motor/docker-compose.yml' '[]' platafirma-core "compose fora do contrato do deploy"
echo "OK"

echo "--- 3: ensaio do dono (commit -> rollback): prova com 12 linhas, nada gravado"
antes="$(retrato rag_extractor)"
out="$(sed 's/^commit;$/rollback;/' "$MIG" | PSQL -d rag_extractor -v ON_ERROR_STOP=1 -P pager=off -f - 2>&1)" \
  || falha "ensaio com rollback: $out"
grep -q "(12 rows)" <<<"$out" && grep -q "^ROLLBACK" <<<"$out" || falha "ensaio devia imprimir 12 linhas e ROLLBACK: $out"
! grep -q "ERROR" <<<"$out" || falha "ensaio com ERROR: $out"
[ "$(retrato rag_extractor)" = "$antes" ] || falha "ensaio com rollback gravou"
echo "OK"

echo "--- 4: aplicada como o migrar (psql -1, ON_ERROR_STOP), duas vezes: idempotente"
out="$(aplicar rag_extractor 2>&1)" || falha "1a aplicacao: $out"
grep -q "(12 rows)" <<<"$out" || falha "prova da 1a aplicacao devia ter 12 linhas: $out"
r1="$(retrato rag_extractor)"
[ "$r1" != "$antes" ] || falha "1a aplicacao nao mudou nada"
out="$(aplicar rag_extractor 2>&1)" || falha "2a aplicacao: $out"
[ "$(retrato rag_extractor)" = "$r1" ] || falha "2a aplicacao mudou o resultado (nao idempotente)"
[ "$(PSQL -d rag_extractor -tA -c "$SQL_TEM_PASTA")" = 0 ] || falha "sobrou linha na pasta de trabalho"
[ "$(PSQL -d rag_extractor -tA -c 'select count(*) from acervo.stack')" = 12 ] || falha "devia continuar com 12 stacks"
[ "$(PSQL -d rag_extractor -tA -c 'select count(*) from acervo.instancia_roda_em_stack')" = 4 ] || falha "ligacoes duplicaram ou sumiram"
echo "OK"

echo "--- 5: resultado stack a stack = contrato do bin/deploy; medidos preservados (serializacao do acervo stack ver)"
TOPO="$TMP_DIR/topo-banco.json"
python3 "$PY" topo "$STACK_PY" "$PG_BIN/psql" "$SOCK" rag_extractor "$TOPO" || falha "acervo stack ver --json sobre o banco"
out="$(python3 "$PY" confere "$FIXTURE" "$PASTA" "$TOPO" 2>&1)" || falha "contrato por stack:
$out"
echo "$out"
out="$(python3 "$PY" familia "$TOPO" "$REPO_ROOT" 2>&1)" || falha "composes reais da familia harness:
$out"
echo "$out"
echo "OK"

echo "--- 6: bin/deploy real sobre a topologia migrada (release e instancia num tmp, docker stub)"
RELEASE="$TMP_DIR/opt"; INSTANCIA="$TMP_DIR/srv"; STUBS="$TMP_DIR/stubs"
SHA="3333333333333333333333333333333333333333"
mkdir -p "$RELEASE" "$INSTANCIA" "$STUBS"
export PF_RELEASE_RAIZ="$RELEASE" PLATAFIRMA_INSTANCIA="$INSTANCIA" PLATAFIRMA_BANCADA="$TMP_DIR/bancada-inexistente"
export DEPLOY_ENV_DIR="$TMP_DIR/run/platafirma" DEPLOY_TOPO_ARQUIVO="$TMP_DIR/topo-palco.json"
export DEPLOY_PONTOS="$INSTANCIA/var/deploy" DOCKER_HOST="unix://$TMP_DIR/sem-docker.sock"
unset PLATAFIRMA_RELEASE PF_SIM 2>/dev/null || true
export DOCKER_LOG="$TMP_DIR/docker.log"; : > "$DOCKER_LOG"
cat > "$STUBS/docker" <<'EOF'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "${DOCKER_LOG:?}"
case " $* " in *" config --services "*) echo app ;; esac
exit 0
EOF
chmod +x "$STUBS/docker"
export PATH="$STUBS:$PATH"
PLANO="$TMP_DIR/plano.tsv"
python3 "$PY" palco "$TOPO" "$RELEASE" "$INSTANCIA" "$SHA" "$DEPLOY_ENV_DIR" "$DEPLOY_TOPO_ARQUIVO" > "$PLANO" || falha "palco"
[ "$(wc -l < "$PLANO")" -eq 12 ] || falha "plano devia ter 12 stacks: $(cat "$PLANO")"
TEM_YQ=1; command -v yq >/dev/null || { TEM_YQ=0; pulado "sem yq: 'deploy <stack> rotas' nao conferido"; }
tudo=""
while IFS=$'\t' read -r slug projeto invocacao tem_rotas gate; do
  out="$("$DEPLOY" "$slug" 2>&1)" || falha "$slug (ver): $out"
  grep -qx "projeto : $projeto" <<<"$out" || falha "$slug: projeto devia ser $projeto: $out"
  tudo+="$out"

  : > "$DOCKER_LOG"
  set +e; out="$("$DEPLOY" "$slug" config --quiet 2>&1)"; rc=$?; set -e
  [ "$rc" -eq 0 ] || falha "$slug config --quiet rc=$rc: $out"
  [ "$(grep -c '^docker ' "$DOCKER_LOG")" -eq 1 ] && grep -qxF "$invocacao" "$DOCKER_LOG" \
    || falha "$slug: invocacao do compose
 esperada: $invocacao
 feita   : $(cat "$DOCKER_LOG")"
  tudo+="$out"

  out="$("$DEPLOY" "$slug" segredos 2>&1)" || falha "$slug segredos: $out"
  ! grep -q AUSENTE <<<"$out" || falha "$slug segredos acusou ausente: $out"
  tudo+="$out"

  if [ "$tem_rotas" = 1 ] && [ "$TEM_YQ" = 1 ]; then
    out="$("$DEPLOY" "$slug" rotas 2>&1)" || falha "$slug rotas: $out"
    grep -qF "ingress : $INSTANCIA/deploy/core/cloudflared.yml" <<<"$out" || falha "$slug rotas: $out"
    tudo+="$out"
  fi
  if [ -n "$gate" ]; then
    out="$("$DEPLOY" "$slug" acessos 2>&1)" || falha "$slug acessos: $out"
    grep -qF "gate    : $gate" <<<"$out" || falha "$slug acessos devia ler o gate $gate: $out"
    tudo+="$out"
  fi
done < "$PLANO"
! grep -q "valor-falso-0091" <<<"$tudo" || falha "valor de segredo impresso pelo deploy"
! grep -q "fora da release\|fora das raizes" <<<"$tudo" || falha "deploy recusou caminho: $tudo"
[ -z "$(ls -A "$DEPLOY_ENV_DIR")" ] || falha "sobrou env-file no tmpfs: $(ls -A "$DEPLOY_ENV_DIR")"
find "$RELEASE" -name '.env' | grep -q . && falha ".env escrito na release"
echo "OK (12 stacks: ver, config, segredos; rotas e acessos onde declarados)"

echo "--- 7: chat com o cofre matrix incompleto (estado medido) -> segredos acusa 1, nunca 3"
mv "$INSTANCIA/segredos/matrix/signing.key" "$TMP_DIR/guardado"
set +e; out="$("$DEPLOY" chat segredos 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "AUSENTE : $INSTANCIA/segredos/matrix/signing.key" <<<"$out" || falha "chat sem signing.key: rc=$rc $out"
: > "$DOCKER_LOG"
set +e; out="$("$DEPLOY" chat up -d 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "chat up sem signing.key devia recusar 1: rc=$rc $out"
# rc 1 tem de ser a recusa por segredo, e nada pode ter chegado ao docker (up pela metade)
grep -q "recusa: faltam 1 segredo" <<<"$out" || falha "chat up recusou 1 por outro motivo: $out"
! grep -q " up" "$DOCKER_LOG" || falha "chat up sem signing.key chamou o docker: $(cat "$DOCKER_LOG")"
mv "$TMP_DIR/guardado" "$INSTANCIA/segredos/matrix/signing.key"
echo "OK"

echo "--- 8: banco novo (sem stack nenhuma): a migracao cria as 12 e as 4 ligacoes"
preparar_banco novo
PSQL -d novo -q -c "insert into acervo.ferramental_instancia (slug) values ('keycloak'),('matrix'),('rastreador')" >/dev/null
out="$(aplicar novo 2>&1)" || falha "banco novo: $out"
[ "$(PSQL -d novo -tA -c 'select count(*) from acervo.stack')" = 12 ] || falha "banco novo devia ter 12 stacks"
[ "$(PSQL -d novo -tA -c 'select count(*) from acervo.instancia_roda_em_stack')" = 4 ] || falha "banco novo devia ter 4 ligacoes"
python3 "$PY" topo "$STACK_PY" "$PG_BIN/psql" "$SOCK" novo "$TMP_DIR/topo-novo.json" || falha "topo do banco novo"
cmp -s <(jq -S '.stacks | map_values(del(.nota, .reversao.nota, .reversao.provado_em))' "$TOPO") \
       <(jq -S '.stacks | map_values(del(.nota, .reversao.nota, .reversao.provado_em))' "$TMP_DIR/topo-novo.json") \
  || falha "banco novo e banco medido deviam sair com a mesma topologia"
echo "OK"

echo "=== migracao 0091: todos os casos passaram ==="
