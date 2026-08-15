#!/usr/bin/env bash
# provisiona-cadeiras.sh <mxid-do-dono> — poe as cadeiras de pe na superficie de
# conversa: usuario no namespace da recepcao, alias como displayname, avatar e sala
# direta com o dono.
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
# QUEM SAO AS CADEIRAS: `cadeiras()`, de chat/comum/cadeiras.py, que le
# personas/persona-*.md. Nao e a tabela do org, e a diferenca importa: a tabela cobre
# as heads, e `claudinho-politicas-publicas` e assessor do dono, tem sala por decisao
# dele (card 460, comentario 315) e nao esta la. Roster pelo harness e o que faz cadeira
# nova entrar sozinha — nao ha lista de excecao neste arquivo, e nao deve haver.
#
# Por que a traducao roda no HOST e nao dentro do container: `cadeiras()` le
# personas/*.md, e a recepcao nao ve esse diretorio hoje — monta-lo e da fatia B-1, dona
# do compose. Entao o host resolve slug -> sufixo -> localpart -> MXID e copia a lista
# PRONTA para dentro; o lado de dentro so fala Matrix, e nao sabe traduzir cadeira
# nenhuma. Esta fatia nao depende do compose da outra.
#
# Por que o trabalho fala com o Synapse de DENTRO do container: o Synapse nao publica
# porta e vive na rede `interna` (arq:0026, federacao fechada). Do host nao se alcanca;
# de `chat-recepcao`, que esta na mesma rede, sim. O token nao passa por argv (`ps`
# mostra argv): entra por ambiente do exec, e o resto por arquivo copiado.
#
# Roda DEPOIS do primeiro login OIDC do dono: antes disso o MXID dele nao existe.
#
#   ./provisiona-cadeiras.sh @megafone:chat.platafirma.org
#
# Variaveis de escape (todas com padrao util): PF_DONO, PF_COFRE, PF_ORG, PF_AVATARES,
# PF_RECEPCAO, PF_DOMINIO, PF_RAIZ.
set -euo pipefail

DONO="${1:-${PF_DONO:-}}"
: "${DONO:?uso: ./provisiona-cadeiras.sh @megafone:chat.platafirma.org}"

export DOCKER_HOST="${DOCKER_HOST:-unix:///run/user/$(id -u)/docker.sock}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COFRE="${PF_COFRE:-$HOME/AI/var/secrets/matrix}"
RECEPCAO="${PF_RECEPCAO:-chat-recepcao}"
AVATARES="${PF_AVATARES:-$AQUI/avatares}"
DOMINIO="${PF_DOMINIO:-chat.platafirma.org}"
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
# Lado do host: traduz as cadeiras, le o org e as imagens, monta o palco copiado.
# ---------------------------------------------------------------------------
python3 - "$AQUI/comum" "$ORG" "$AVATARES" "$PALCO" "$DOMINIO" <<'PYPALCO'
import json, os, shutil, sys

comum, org, dir_avatares, palco, dominio = sys.argv[1:6]

# A traducao entre slug do org, sufixo do harness e MXID e de chat/comum/cadeiras.py e
# NAO se reimplementa aqui (card 460, comentario 305): duas implementacoes divergem, e
# a que diverge em identidade produz MXID errado, que e irreversivel.
sys.path.insert(0, comum)
from cadeiras import (          # noqa: E402
    cadeiras,
    localpart_da_cadeira,
    mxid_da_cadeira,
    sufixo_canonico,
    valida_localpart,
)

EXTENSOES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
TIPOS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif"}

# --- quem: o conjunto vem do harness -----------------------------------------
# `cadeiras()` levanta FileNotFoundError se personas/ nao esta la — ausencia se declara,
# e provisionar zero cadeira em silencio seria pior que parar.
sufixos = cadeiras()

# --- alias: a tabela do org, quando ela cobre a cadeira -----------------------
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

alias_do_org, slug_do_org, orfas = {}, {}, []
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
    sufixo = sufixo_canonico(slug)
    if sufixo is None:
        # Linha do org sem persona correspondente: o alias nao tem onde pousar. Nao e
        # erro desta fatia — mas some sem aviso se nao se disser, e o sintoma la na
        # frente seria uma cadeira exibindo o sufixo sem ninguem saber por que.
        orfas.append(slug)
        continue
    alias_do_org[sufixo] = alias
    slug_do_org[sufixo] = slug

if not alias_do_org:
    sys.exit(f"erro: nenhum alias lido de {org} — a tabela mudou de forma?")

# --- a lista pronta ----------------------------------------------------------
lista = []
for sufixo in sufixos:
    localpart = localpart_da_cadeira(sufixo)
    mxid = mxid_da_cadeira(sufixo, dominio)
    if localpart is None or mxid is None:
        sys.exit(f"erro: cadeiras() devolveu '{sufixo}', que nao traduz para MXID")
    if not valida_localpart(localpart):
        sys.exit(f"erro: '{sufixo}' nao vira localpart Matrix valido ('{localpart}')")
    lista.append({
        "sufixo": sufixo,
        # Alias quando o org da; o sufixo quando nao da. Regra geral, nao caso especial:
        # cadeira fora da tabela sobe com o identificador que existe, e o alias entra
        # numa corrida posterior — displayname e reversivel, MXID nao. Nenhum nome de
        # pessoa entra neste arquivo; a fonte e sempre o org.
        "alias": alias_do_org.get(sufixo) or sufixo,
        "rotulo": slug_do_org.get(sufixo) or sufixo,   # so para mensagem ao operador
        "localpart": localpart,
        "mxid": mxid,
    })

# --- imagem por cadeira ------------------------------------------------------
# Ausencia NAO e erro: o card manda seguir e avisar qual faltou. As bases aceitas cobrem
# o slug do org (como o README pede) e o sufixo, que e o unico nome que cadeira fora da
# tabela tem.
os.makedirs(os.path.join(palco, "avatares"), exist_ok=True)
for cadeira in lista:
    bases = []
    for nome in (slug_do_org.get(cadeira["sufixo"]), cadeira["sufixo"], cadeira["localpart"]):
        if nome and nome not in bases:
            bases.append(nome)
        if nome and nome.lower() not in bases:
            bases.append(nome.lower())
    achada = None
    for base in bases:
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
    json.dump(lista, saida, ensure_ascii=False, indent=2)

print(f"cadeiras (personas/): {len(lista)} — {', '.join(c['sufixo'] for c in lista)}")
sem_alias = [c["sufixo"] for c in lista if c["sufixo"] not in alias_do_org]
if sem_alias:
    print(f"alias do org: {len(alias_do_org)}; sem alias na tabela, sobe pelo sufixo: "
          f"{', '.join(sem_alias)}")
for slug in orfas:
    print(f"aviso: '{slug}' esta na tabela do org e nao tem persona — alias ignorado",
          file=sys.stderr)
PYPALCO

# mktemp -d nasce 700 e o container roda como uid 10001 (recepcao): sem isto o `docker
# cp` entrega arquivo que o processo de dentro nao le.
chmod -R a+rX "$PALCO"
docker exec "$RECEPCAO" mkdir -p /tmp/pf-provisiona
docker cp -q "$PALCO/." "$RECEPCAO:/tmp/pf-provisiona" 2>/dev/null \
  || docker cp "$PALCO/." "$RECEPCAO:/tmp/pf-provisiona"

# ---------------------------------------------------------------------------
# Lado da rede interna: fala com o Synapse pelo as_token, impersonando cada cadeira.
# Nao traduz cadeira: o MXID ja veio resolvido do host, em cadeiras.json.
# ---------------------------------------------------------------------------
docker exec -i \
  -e DONO="$DONO" \
  -e AS_TOKEN="$(cat "$COFRE/as-token")" \
  "$RECEPCAO" python - <<'PYCADEIRA'
import hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

BASE = "http://chat-synapse:8008"
TOKEN = os.environ["AS_TOKEN"]
DONO = os.environ["DONO"]
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
    erros.append(f"{cadeira['rotulo']}: registro falhou ({codigo} {resposta.get('errcode')} "
                 f"{resposta.get('error')})")
    return None


def garante_alias(cadeira, mxid):
    _, atual = chama("GET", f"/_matrix/client/v3/profile/{esc(mxid)}/displayname", como=mxid)
    if atual.get("displayname") == cadeira["alias"]:
        return "alias ja estava"
    codigo, resposta = chama("PUT", f"/_matrix/client/v3/profile/{esc(mxid)}/displayname",
                             {"displayname": cadeira["alias"]}, como=mxid)
    if codigo != 200:
        erros.append(f"{cadeira['rotulo']}: displayname falhou ({codigo} {resposta.get('errcode')})")
        return None
    return "alias posto"


def garante_avatar(cadeira, mxid):
    if not cadeira.get("avatar"):
        avisos.append(f"{cadeira['rotulo']} ({cadeira['alias']}): sem imagem de avatar "
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
        erros.append(f"{cadeira['rotulo']}: upload do avatar falhou ({codigo} {resposta.get('errcode')})")
        return None
    mxc = resposta["content_uri"]

    codigo, resposta = chama("PUT", f"/_matrix/client/v3/profile/{esc(mxid)}/avatar_url",
                             {"avatar_url": mxc}, como=mxid)
    if codigo != 200:
        erros.append(f"{cadeira['rotulo']}: avatar_url falhou ({codigo} {resposta.get('errcode')})")
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
        # `private_chat`, e nao `trusted_private_chat`: o trusted da poder 100 ao
        # convidado, e em Matrix ninguem expulsa quem tem poder igual ao seu — a
        # rotacao do card 449 nao consegue descartar sala assim, e ela fica na
        # lista do dono para sempre. Sala criada antes desta linha carrega o
        # defeito: na primeira rotacao dela o kick falha, o leave e o forget da
        # cadeira acontecem, e a sala nova ja nasce descartavel.
        codigo, resposta = chama("POST", "/_matrix/client/v3/createRoom", {
            "preset": "private_chat",
            "is_direct": True,
            "invite": [DONO],
        }, como=mxid)
        if codigo != 200 or "room_id" not in resposta:
            erros.append(f"{cadeira['rotulo']}: createRoom falhou ({codigo} {resposta.get('errcode')} "
                         f"{resposta.get('error')})")
            return None, None
        sala, nota = resposta["room_id"], "sala criada"

    # "Convite aceito pelo lado da cadeira": criadora ja entra, mas sala herdada de
    # convite alheio (o bot da recepcao, por exemplo) fica em `invite` ate isto.
    if membro(sala, mxid, mxid) == "invite":
        codigo, resposta = chama("POST", f"/_matrix/client/v3/rooms/{esc(sala)}/join", {}, como=mxid)
        if codigo != 200:
            erros.append(f"{cadeira['rotulo']}: join falhou ({codigo} {resposta.get('errcode')})")
            return sala, nota

    if sala not in candidatas:
        direto[DONO] = candidatas + [sala]
        chama("PUT", f"/_matrix/client/v3/user/{esc(mxid)}/account_data/m.direct", direto, como=mxid)

    return sala, nota


print(f"dono: {DONO}")
print(f"cadeiras: {len(cadeiras)}\n")

for cadeira in cadeiras:
    mxid = cadeira["mxid"]
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
