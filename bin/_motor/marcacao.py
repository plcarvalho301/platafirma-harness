"""`motor marcacao` — cliente fino da marcacao-api (rotas /interno/), card #3349, feature #3340.

A marcacao-api (platafirma-motor, deploy/marcacao) é o serviço que guarda o lote da tela do gold set e
grava as marcas. As rotas /interno/ levam token e ficam fora do gate: só a porta as chama, por loopback.
Aqui não há regra de negócio: o verbo manda o que o escritor e o juiz produzem e devolve o que a API diz.

Saída (arq:0110 §4): 0 ok · 1 resultado negativo de mérito (lote desconhecido, lote já existe) ·
2 uso errado ou entrada que a API recusa (422) · 3 API fora do ar ou 5xx · 4 token recusado.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

USO = """motor marcacao — o lote da tela de marcação e o que ela grava (marcacao-api)

  motor marcacao lote gravar <arquivo|-> [--ativar] [--json]
                                        grava o lote (corpo público + respostas com braço e mapa) no banco;
                                        --ativar põe o lote como o que a tela recebe
  motor marcacao lote ler (--atual | <lote_id>) [--com-braco] [--json]
                                        sem --com-braco, o que a tela recebe; com ele, braço, mapa e carimbo
  motor marcacao lote ativar <lote_id>  troca o lote ativo
  motor marcacao eventos --lote <lote_id> [--json]
                                        as marcas, preferências e exclusões gravadas pela tela
  motor marcacao juiz gravar <arquivo|-> [--json]
                                        grava as marcas do juiz ({lote_id, marcas:[…]})
  motor marcacao juiz ler --lote <lote_id> [--json]
                                        as marcas do juiz do lote, com a hora de cada gravação
"""


class Falha(Exception):
    def __init__(self, codigo: int, msg: str):
        super().__init__(msg)
        self.codigo = codigo
        self.msg = msg


def chamar(base: str, token: str, metodo: str, caminho: str, corpo=None, timeout: int = 60):
    dado = json.dumps(corpo, ensure_ascii=False).encode() if corpo is not None else None
    req = urllib.request.Request(
        base.rstrip("/") + caminho, data=dado, method=metodo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            detalhe = json.loads(e.read().decode()).get("erro", "")
        except (ValueError, UnicodeDecodeError, AttributeError):
            detalhe = ""
        if e.code in (401, 403):
            raise Falha(4, f"marcacao-api recusou o token ({e.code}); regrave com `seg segredo gravar marcacao-api/MARCACAO_TOKEN` "
                           "e suba a stack: infra up marcacao-api -d") from None
        if e.code in (404, 409):
            raise Falha(1, f"{e.code}: {detalhe}") from None
        if e.code in (400, 422):
            raise Falha(2, f"{e.code}: {detalhe}") from None
        if e.code == 503:
            raise Falha(3, f"503: {detalhe}") from None
        raise Falha(3, f"HTTP {e.code}: {detalhe}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Falha(3, f"marcacao-api fora do ar ({type(e).__name__}); infra ps marcacao-api") from None


def _le_json(origem: str, stdin) -> dict:
    texto = stdin.read() if origem == "-" else open(origem, encoding="utf-8").read()
    try:
        return json.loads(texto)
    except ValueError as e:
        raise Falha(2, f"{origem}: não é JSON ({e})") from None


def _flags(argv: list, com_valor: tuple, booleanas: tuple):
    """(posicionais, opções) ou Falha(2) em opção desconhecida."""
    pos, op, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a in booleanas:
            op[a] = True
        elif a in com_valor:
            if i + 1 >= len(argv):
                raise Falha(2, f"{a} pede um valor")
            op[a] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise Falha(2, f"opção desconhecida: {a}")
        else:
            pos.append(a)
        i += 1
    return pos, op


def executar(base: str, token: str, argv: list, stdin=None, saida=None, erro=None, chamada=chamar) -> int:
    saida = saida or sys.stdout
    erro = erro or sys.stderr
    stdin = stdin or sys.stdin

    def imprime(obj, json_, linha):
        saida.write((json.dumps(obj, ensure_ascii=False, indent=1) if json_ else linha) + "\n")

    try:
        if not argv or argv[0] in ("--ajuda", "-h", "--help"):
            erro.write(USO)
            return 2
        if argv[:2] == ["lote", "gravar"]:
            pos, op = _flags(argv[2:], (), ("--ativar", "--json"))
            if len(pos) != 1:
                raise Falha(2, "lote gravar pede <arquivo|->")
            corpo = _le_json(pos[0], stdin)
            if op.get("--ativar"):
                corpo["ativo"] = True
            r = chamada(base, token, "PUT", "/interno/lote", corpo)
            imprime(r, op.get("--json"), f"lote {r['lote_id']} gravado · {r['perguntas']} perguntas · "
                    f"{r['respostas']} respostas · {'ativo' if r['ativo'] else 'inativo'}")
            return 0
        if argv[:2] == ["lote", "ler"]:
            pos, op = _flags(argv[2:], (), ("--atual", "--com-braco", "--json"))
            if bool(pos) == bool(op.get("--atual")) or len(pos) > 1:
                raise Falha(2, "lote ler pede --atual ou <lote_id>")
            caminho = "/interno/lote/" + ("atual" if op.get("--atual") else pos[0])
            if op.get("--com-braco"):
                caminho += "?com_braco=1"
            r = chamada(base, token, "GET", caminho)
            if op.get("--com-braco"):
                resumo = (f"lote {r['lote_id']} · {'ativo' if r['ativo'] else 'inativo'} · "
                          f"{len({x['pergunta_id'] for x in r['respostas']})} perguntas · {len(r['respostas'])} respostas")
            else:
                resumo = f"lote {r['lote_id']} · {len(r['perguntas'])} perguntas"
            imprime(r, op.get("--json"), resumo)
            return 0
        if argv[:2] == ["lote", "ativar"]:
            pos, op = _flags(argv[2:], (), ("--json",))
            if len(pos) != 1:
                raise Falha(2, "lote ativar pede <lote_id>")
            r = chamada(base, token, "POST", f"/interno/lote/{pos[0]}/ativar")
            imprime(r, op.get("--json"), f"lote {r['lote_id']} ativo")
            return 0
        if argv[0] == "eventos":
            pos, op = _flags(argv[1:], ("--lote",), ("--json",))
            if pos or not op.get("--lote"):
                raise Falha(2, "eventos pede --lote <lote_id>")
            r = chamada(base, token, "GET", "/interno/eventos?lote_id=" + urllib.parse.quote(op["--lote"]))
            por_tipo: dict = {}
            for e in r["eventos"]:
                por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
            imprime(r, op.get("--json"), f"lote {r['lote_id']} · {len(r['eventos'])} eventos"
                    + ("".join(f" · {k} {v}" for k, v in sorted(por_tipo.items()))))
            return 0
        if argv[:2] == ["juiz", "gravar"]:
            pos, op = _flags(argv[2:], (), ("--json",))
            if len(pos) != 1:
                raise Falha(2, "juiz gravar pede <arquivo|->")
            r = chamada(base, token, "POST", "/interno/juiz", _le_json(pos[0], stdin))
            imprime(r, op.get("--json"), f"{r['gravadas']} marca(s) do juiz gravada(s)")
            return 0
        if argv[:2] == ["juiz", "ler"]:
            pos, op = _flags(argv[2:], ("--lote",), ("--json",))
            if pos or not op.get("--lote"):
                raise Falha(2, "juiz ler pede --lote <lote_id>")
            r = chamada(base, token, "GET", "/interno/juiz?lote_id=" + urllib.parse.quote(op["--lote"]))
            ultima = max((m["criado_em"] for m in r["marcas"]), default=None)
            imprime(r, op.get("--json"), f"lote {r['lote_id']} · {len(r['marcas'])} marca(s) do juiz"
                    + (f" · última gravada em {ultima}" if ultima else ""))
            return 0
        raise Falha(2, f"ato desconhecido: {' '.join(argv[:2])}")
    except Falha as f:
        erro.write(f"motor marcacao: {f.msg}\n")
        if f.codigo == 2 and any(p in f.msg for p in ("desconhecid", "pede", "opção")):
            erro.write("  motor marcacao --ajuda\n")
        return f.codigo
