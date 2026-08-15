#!/usr/bin/env bash
# provisiona-cadeiras.sh <mxid-do-dono> — poe as cadeiras do org canonico de pe na
# superficie de conversa: usuario no namespace da recepcao, alias como displayname,
# avatar e sala direta com o dono.
# capacidade: mudanca
# dono: claudinha-fabrica (card 448, fatia B-3)
#
# Idempotente por desenho: rodar duas vezes NAO cria usuario, sala nem convite novo, e
# o que ja esta no estado desejado nao e reescrito. Isso ultimo nao e capricho — cada
# PUT de displayname ou avatar_url emite `m.room.member` em toda sala da cadeira, e a
# conversa do dono viraria mural de evento de perfil a cada corrida.
#
# Nenhuma credencial nova: o par as_token/hs_token do card 447 ja cobre o namespace
# inteiro (`@_pf.*`) — e essa e a razao de a topologia ser Application Service. A
# identidade registrada (id: pf, sender_localpart: _pf) nao se toca: mexer nela
# desregistra o servico.
#
# Por que o trabalho roda DENTRO do container: o Synapse nao publica porta e vive na
# rede `interna` (arq:0026, federacao fechada). Do host nao se alcanca; de
# `chat-recepcao`, que esta na mesma rede, sim. O token nao passa por argv (`ps` mostra
# argv): entra por ambiente do exec, e o resto por arquivo copiado.
#
# Roda DEPOIS do primeiro login OIDC do dono: antes disso o MXID dele nao existe.
#
#   ./provisiona-cadeiras.sh @megafone:chat.platafirma.org
#
# Variaveis de escape (todas com padrao util): PF_DONO, PF_COFRE, PF_ORG, PF_AVATARES,
# PF_RECEPCAO.
set -euo pipefail

DONO="${1:-${PF_DONO:-}}"
: "${DONO:?uso: ./provisiona-cadeiras.sh @megafone:chat.platafirma.org}"

export DOCKER_HOST="${DOCKER_HOST:-unix:///run/user/$(id -u)/docker.sock}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COFRE="${PF_COFRE:-$HOME/AI/var/secrets/matrix}"
RECEPCAO="${PF_RECEPCAO:-chat-recepcao}"
AVATARES="${PF_AVATARES:-$AQUI/avatares}"
# O alias sai do org canonico e nao se fixa aqui: quem ocupa a cadeira e com que nome e
# decisao de claudinha-gestao-estrategica, versionada no repo de arquitetura. Codigo com
# a tabela dentro seria uma segunda fonte da verdade envelhecendo em silencio.
ORG="${PF_ORG:-$AQUI/../../platafirma-arquitetura/docs/org-template-canonico.md}"

[ -s "$COFRE/as-token" ] || { echo "erro: falta $COFRE/as-token — rode ./prepara.sh" >&2; exit 1; }
[ -s "$ORG" ] || {
  echo "erro: org canonico nao encontrado em $ORG" >&2
  echo "      e de la que sai o alias de cada cadeira. Aponte PF_ORG se o clone mora noutro lugar." >&2
  exit 1
}

PALCO="$(mktemp -d)"
limpa() {
  rm -rf "$PALCO"
  docker exec "$RECEPCAO" rm -rf /tmp/pf-provisiona >/dev/null 2>&1 || true
}
trap limpa EXIT

# ---------------------------------------------------------------------------
# Lado do host: le o org canonico e as imagens, monta o palco que sera copiado.
# ---------------------------------------------------------------------------
python3 - "$ORG" "$AVATARES" "$PALCO" <<'PYPALCO'
import json, os, re, shutil, sys

org, dir_avatares, palco = sys.argv[1], sys.argv[2], sys.argv[3]

# Localpart Matrix so aceita [a-z0-9._=-/+]: o slug `claudinho-TI` do org NAO cabe cru.
# Caixa baixa e conversao forcada pela spec, nao escolha de estilo.
VALIDO = re.compile(r"^[a-z0-9._=/+-]+$")
EXTENSOES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
TIPOS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif"}

# A tabela vive sob "## Ocupacao das cadeiras" e acaba no proximo cabecalho. Ler assim,
# e nao o arquivo inteiro, evita colher linha de tabela de outra secao.
linhas, dentro = [], False
for linha in open(org, encoding="utf-8"):
    if linha.startswith("## "):
        if dentro:
            break
        dentro = "cadeiras" in linha.lower()
        continue
    if dentro and linha.lstrip().startswith("|"):
        linhas.append(linha.strip())

cadeiras = []
for linha in linhas:
    colunas = [c.strip() for c in linha.strip("|").split("|")]
    if len(colunas) < 3:
        continue
    slug = colunas[1].strip("* ").strip()
    alias = colunas[2].strip("* ").strip()
    if not slug or slug.lower() == "project" or set(slug) <= set("-: "):
        continue          # cabecalho e linha separadora
    if not alias or alias == "—":
        continue
    localpart = "_pf" + slug.lower()
    if not VALIDO.match(localpart):
        sys.exit(f"erro: slug '{slug}' nao vira localpart Matrix valido ('{localpart}')")
    cadeiras.append({"slug": slug, "alias": alias, "localpart": localpart})

if not cadeiras:
    sys.exit(f"erro: nenhuma cadeira lida de {org} — a tabela mudou de forma?")

# Imagem por cadeira. Ausencia NAO e erro: o card manda seguir e avisar qual faltou.
os.makedirs(os.path.join(palco, "avatares"), exist_ok=True)
for cadeira in cadeiras:
    achada = None
    for base in (cadeira["slug"], cadeira["slug"].lower()):
        for ext in EXTENSOES:
            caminho = os.path.join(dir_avatares, base + ext)
            if os.path.isfile(caminho):
                achada = (caminho, ext)
                break
        if achada:
            break
    if achada:
        caminho, ext = achada
        destino = os.path.join("avatares", cadeira["localpart"] + ext)
        shutil.copyfile(caminho, os.path.join(palco, destino))
        cadeira["avatar"] = destino
        cadeira["avatar_tipo"] = TIPOS[ext]
        cadeira["avatar_nome"] = os.path.basename(caminho)
    else:
        cadeira["avatar"] = None

with open(os.path.join(palco, "cadeiras.json"), "w", encoding="utf-8") as saida:
    json.dump(cadeiras, saida, ensure_ascii=False, indent=2)

print(f"org canonico: {len(cadeiras)} cadeira(s) lida(s) de {org}")
PYPALCO

# mktemp -d nasce 700 e o container roda como uid 10001 (recepcao): sem isto o `docker
# cp` entrega arquivo que o processo de dentro nao le.
chmod -R a+rX "$PALCO"
docker exec "$RECEPCAO" mkdir -p /tmp/pf-provisiona
docker cp -q "$PALCO/." "$RECEPCAO:/tmp/pf-provisiona" 2>/dev/null \
  || docker cp "$PALCO/." "$RECEPCAO:/tmp/pf-provisiona"

# ---------------------------------------------------------------------------
# Lado da rede interna: fala com o Synapse pelo as_token, impersonando cada cadeira.
# ---------------------------------------------------------------------------
docker exec -i \
  -e DONO="$DONO" \
  -e AS_TOKEN="$(cat "$COFRE/as-token")" \
  -e DOMINIO="${PF_DOMINIO:-chat.platafirma.org}" \
  "$RECEPCAO" python - <<'PYCADEIRA'
import hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

BASE = "http://chat-synapse:8008"
TOKEN = os.environ["AS_TOKEN"]
DONO = os.environ["DONO"]
DOMINIO = os.environ["DOMINIO"]
PALCO = "/tmp/pf-provisiona"

cadeiras = json.load(open(os.path.join(PALCO, "cadeiras.json"), encoding="utf-8"))

avisos, erros = [], []


def esc(valor):
    return urllib.parse.quote(valor, safe="")


def chama(metodo, caminho, corpo=None, como=None, bruto=None, tipo=None):
    """Uma porta so para o Synapse. `como` e a impersonacao de Application Service
    (?user_id=), que so vale para MXID dentro do namespace registrado."""
    url = BASE + caminho
    if como:
        url += ("&" if "?" in caminho else "?") + urllib.parse.urlencode({"user_id": como})
    cabecalho = {"Authorization": "Bearer " + TOKEN}
    dados = None
    if bruto is not None:
        dados, cabecalho["Content-Type"] = bruto, tipo or "application/octet-stream"
    elif corpo is not None:
        dados = json.dumps(corpo).encode()
        cabecalho["Content-Type"] = "application/json"
    pedido = urllib.request.Request(url, data=dados, headers=cabecalho, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            texto = resposta.read()
            return resposta.status, (json.loads(texto) if texto else {})
    except urllib.error.HTTPError as falha:
        texto = falha.read()
        try:
            return falha.code, json.loads(texto)
        except ValueError:
            return falha.code, {"errcode": "?", "error": texto.decode("utf-8", "replace")}


def garante_usuario(cadeira, mxid):
    codigo, resposta = chama("POST", "/_matrix/client/v3/register", {
        "type": "m.login.application_service",
        "username": cadeira["localpart"],
    })
    if codigo == 200:
        return "usuario criado"
    if resposta.get("errcode") == "M_USER_IN_USE":
        return "usuario ja havia"
    erros.append(f"{cadeira['slug']}: registro falhou ({codigo} {resposta.get('errcode')} "
                 f"{resposta.get('error')})")
    return None


def garante_alias(cadeira, mxid):
    _, atual = chama("GET", f"/_matrix/client/v3/profile/{esc(mxid)}/displayname", como=mxid)
    if atual.get("displayname") == cadeira["alias"]:
        return "alias ja estava"
    codigo, resposta = chama("PUT", f"/_matrix/client/v3/profile/{esc(mxid)}/displayname",
                             {"displayname": cadeira["alias"]}, como=mxid)
    if codigo != 200:
        erros.append(f"{cadeira['slug']}: displayname falhou ({codigo} {resposta.get('errcode')})")
        return None
    return "alias posto"


def garante_avatar(cadeira, mxid):
    if not cadeira.get("avatar"):
        avisos.append(f"{cadeira['slug']} ({cadeira['alias']}): sem imagem de avatar "
                      f"em chat/avatares/ — a cadeira sobe sem retrato")
        return "sem imagem"

    dados = open(os.path.join(PALCO, cadeira["avatar"]), "rb").read()
    impressao = hashlib.sha256(dados).hexdigest()

    # O mxc:// de um upload novo e sempre novo, entao "ja subiu esta imagem?" nao se
    # responde olhando o perfil: guarda-se a impressao da imagem ao lado dele.
    _, marca = chama("GET", f"/_matrix/client/v3/user/{esc(mxid)}/account_data/org.platafirma.avatar",
                     como=mxid)
    _, perfil = chama("GET", f"/_matrix/client/v3/profile/{esc(mxid)}/avatar_url", como=mxid)
    if marca.get("sha256") == impressao and perfil.get("avatar_url") == marca.get("mxc"):
        return "avatar ja estava"

    codigo, resposta = chama(
        "POST", "/_matrix/media/v3/upload?filename=" + esc(cadeira["avatar_nome"]),
        como=mxid, bruto=dados, tipo=cadeira["avatar_tipo"])
    if codigo != 200 or "content_uri" not in resposta:
        erros.append(f"{cadeira['slug']}: upload do avatar falhou ({codigo} {resposta.get('errcode')})")
        return None
    mxc = resposta["content_uri"]

    codigo, resposta = chama("PUT", f"/_matrix/client/v3/profile/{esc(mxid)}/avatar_url",
                             {"avatar_url": mxc}, como=mxid)
    if codigo != 200:
        erros.append(f"{cadeira['slug']}: avatar_url falhou ({codigo} {resposta.get('errcode')})")
        return None
    chama("PUT", f"/_matrix/client/v3/user/{esc(mxid)}/account_data/org.platafirma.avatar",
          {"sha256": impressao, "mxc": mxc}, como=mxid)
    return "avatar posto"


def membro(sala, quem, como):
    _, estado = chama("GET",
                      f"/_matrix/client/v3/rooms/{esc(sala)}/state/m.room.member/{esc(quem)}",
                      como=como)
    return estado.get("membership")


def garante_sala(cadeira, mxid):
    # A memoria de "qual e a sala desta cadeira" mora no m.direct do lado DELA. Do lado
    # do dono quem escreve e o cliente dele, ao aceitar um convite marcado is_direct —
    # e conta fora do namespace o AS nao impersona.
    _, direto = chama("GET", f"/_matrix/client/v3/user/{esc(mxid)}/account_data/m.direct", como=mxid)
    if not isinstance(direto, dict) or "errcode" in direto:
        direto = {}
    candidatas = [s for s in direto.get(DONO, []) if isinstance(s, str)]

    sala, nota = None, None
    for candidata in candidatas:
        minha = membro(candidata, mxid, mxid)
        dele = membro(candidata, DONO, mxid)
        if minha in ("join", "invite") and dele in ("join", "invite"):
            sala, nota = candidata, "sala ja havia"
            break

    if sala is None:
        # Criada PELA cadeira: quem cria ja entra, e o convite pendente e o do dono —
        # que e o que ele aceita no celular. is_direct e o que faz o Element mostrar
        # conversa, e nao sala; sem nome nem topico de proposito, para a conversa se
        # chamar pelo displayname da cadeira (aceite 7) e nao por rotulo de sala.
        codigo, resposta = chama("POST", "/_matrix/client/v3/createRoom", {
            "preset": "trusted_private_chat",
            "is_direct": True,
            "invite": [DONO],
        }, como=mxid)
        if codigo != 200 or "room_id" not in resposta:
            erros.append(f"{cadeira['slug']}: createRoom falhou ({codigo} {resposta.get('errcode')} "
                         f"{resposta.get('error')})")
            return None, None
        sala, nota = resposta["room_id"], "sala criada"

    # "Convite aceito pelo lado da cadeira": criadora ja entra, mas sala herdada de
    # convite alheio (o bot da recepcao, por exemplo) fica em `invite` ate isto.
    if membro(sala, mxid, mxid) == "invite":
        codigo, resposta = chama("POST", f"/_matrix/client/v3/rooms/{esc(sala)}/join", {}, como=mxid)
        if codigo != 200:
            erros.append(f"{cadeira['slug']}: join falhou ({codigo} {resposta.get('errcode')})")
            return sala, nota

    if sala not in candidatas:
        direto[DONO] = candidatas + [sala]
        chama("PUT", f"/_matrix/client/v3/user/{esc(mxid)}/account_data/m.direct", direto, como=mxid)

    return sala, nota


print(f"dono: {DONO}")
print(f"cadeiras: {len(cadeiras)}\n")

for cadeira in cadeiras:
    mxid = f"@{cadeira['localpart']}:{DOMINIO}"
    notas = [garante_usuario(cadeira, mxid)]
    if notas[0] is None:
        print(f"  {cadeira['alias']:<22} {mxid:<44} FALHOU no registro")
        continue
    notas.append(garante_alias(cadeira, mxid))
    notas.append(garante_avatar(cadeira, mxid))
    sala, nota_sala = garante_sala(cadeira, mxid)
    notas.append(nota_sala)
    print(f"  {cadeira['alias']:<22} {mxid:<44} {sala or '(sem sala)'}")
    print(f"  {'':<22} {', '.join(n for n in notas if n)}")

if avisos:
    print("\navisos (nao impedem a corrida):")
    for aviso in avisos:
        print(f"  - {aviso}")

if erros:
    print("\nERROS:", file=sys.stderr)
    for erro in erros:
        print(f"  - {erro}", file=sys.stderr)
    sys.exit(1)

print("\nprovisionamento concluido.")
PYCADEIRA
