"""metrica investigar — a linha inteira do bruto, só com incidente aberto (card #3355; arq:0123 regras 8, 10 e 15).

    metrica investigar <AAAA-MM-DD> --incidente <n> [--sessao <prefixo-ou-id>] [--tool <verbo>] [--classe <c>]
                       [--limite N] [--resumo]

MODULO IMPORTAVEL (como `abertura` e `particao`): `bin/metrica` o despacha antes do parser comum, porque os
argumentos são outros. Aqui não se abre o diretório do bruto: quem lê o arquivo é só `lib/oplog` (`ler_inteiras`,
que exige o número do incidente e grava o `leitura_bruto` antes de entregar).

A REGRA (arq:0123 regra 15): o argumento, o texto de erro, a identidade e o texto do turno ficam no bruto e só saem
por este ato, com incidente ABERTO. Aberto é o que `tarefas ler <n>` diz: estado da fase `incidente` (detectado,
em-mitigacao, mitigado). Incidente que não existe, resolvido ou que nem é incidente sai 4, com o caminho. O verbo não
abre incidente para destravar a leitura: o número vem de quem investiga. Não há exceção por cadeira: toda cadeira entra
pelo mesmo login e a regra é rastro, não barreira.

DE ONDE A LINHA VEM. O dia que ainda está no disco sai do arquivo (as linhas que casam com o filtro, inteiras). O dia
que já saiu do bruto (35 dias) só devolve o que a partição guarda: a amostra (91 dias) e a linha já citada (um ano da
última citação), por D5.11. Fora disso sai 1, «sem linha inteira guardada para <dia>».

O RASTRO E A CITAÇÃO. Toda leitura grava, pelo módulo, o evento `leitura_bruto` (incidente, filtros, de onde e quantas
linhas saíram) ANTES de entregar; sem rastro gravado nada é devolvido (exit 5). As linhas devolvidas atravessam
inteiras para a partição como linha citada do incidente (D5.10: `log_conteudo` e `log_citacao`, prazo de um ano da
última citação). A linha cujo evento a partição ainda não tem (o dia aberto, ou fechado e ainda não extraído) volta em
`citacao.ausentes`: repete-se o ato depois da passada do dia, que a linha ainda está no bruto (35 dias).

Linha `turno` só vira citada se o filtro a pega: `--sessao` a pega, `--tool` não (a linha de turno não é giro).

exit: 0 devolveu · 1 nenhuma linha casa (ou o dia saiu do bruto e a partição não guarda) · 2 uso · 3 o rastreador ou a
partição não respondeu (ou a citação não gravou: as linhas saem e o `citacao.estado` diz) · 4 o incidente não está
aberto, token recusado ou alarme de integridade · 5 indeterminável (o rastro não gravou, resposta fora do contrato).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import oplog
import oplog_extracao as extracao

VERBO = "metrica"
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 500        # cabe num D5.10 só (até 1.000 itens) e dentro dos 50 KB da porta, com o teto de bytes
MAX_BYTES = 36000          # o que o verbo devolve; a porta corta a saída em 50 KB, calada, e o verbo corta antes e diz
FASE_ABERTA = "incidente"
ESTADOS_ABERTOS = ("detectado", "em-mitigacao", "mitigado")     # só na mensagem; quem decide é a fase do estado
PASSADA_DO_DIA = "00:20"   # a hora em que o timer `linhagem-ops` extrai o dia fechado (D4)

_CABECALHO = re.compile(r"#(\d+) · (.+?) · (.+) \(([a-z]+)\)(?: · .*)?")
_SESSAO = re.compile(r"[0-9a-f-]{1,36}")
_TOOL = re.compile(r"[A-Za-z0-9_.:-]{1,60}")
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")

USO = f"""uso: {VERBO} investigar <AAAA-MM-DD> --incidente <n> [--sessao <prefixo-ou-id>] [--tool <verbo>] [--classe <c>]
                       [--limite N] [--resumo]
a linha INTEIRA do bruto (argumento, erro, identidade, texto do turno), so com incidente ABERTO:
  --incidente  o numero do card de incidente (detectado, em-mitigacao ou mitigado). Obrigatorio: o verbo nao abre
               incidente para destravar a leitura, o numero vem de quem investiga
  --sessao     so as linhas da sessao (prefixo do sessao_id ou ele inteiro); pega tambem a linha `turno`
  --tool       so as chamadas desse verbo; a linha `turno` nao e chamada e nao entra
  --classe     so as chamadas dessa classe: {', '.join(oplog.CLASSES)}
  --limite     teto de linhas devolvidas (padrao {LIMITE_PADRAO}, ate {LIMITE_MAXIMO}); o que casou e ficou de fora e dito
  --resumo     o texto legivel, no lugar do JSON
o dia que ja saiu do bruto (35 dias) devolve so a amostra e a linha ja citada que a particao guarda.
toda leitura grava o rastro (`leitura_bruto`) e as linhas devolvidas ficam citadas pelo incidente por um ano.
exit: 0 devolveu · 1 nenhuma linha casa · 2 uso · 3 rastreador ou particao fora · 4 incidente nao aberto · 5 indeterminavel"""


class Recusa(Exception):
    """O ato termina com `codigo` (arq:0110 §4) e a mensagem; `caminho` é o que fecha o pedido dentro das regras."""

    def __init__(self, codigo: int, mensagem: str, caminho=()):
        super().__init__(mensagem)
        self.codigo, self.caminho = codigo, tuple(caminho)


def dica_de_argumentos(dia: str) -> str:
    """A linha que `casos` e `eventos` devolvem no lugar do argumento, do erro e do texto do turno."""
    return f"{VERBO} investigar {dia} --incidente <n>"


# --- os argumentos ---------------------------------------------------------------------------------

def _argumentos(argv: list[str], hoje: date) -> dict:
    args = list(argv)

    def valor(flag: str) -> str:
        if not args:
            raise Recusa(2, f"{flag} pede um valor", [USO.splitlines()[0]])
        return args.pop(0)

    dia = incidente = sessao = tool = classe = None
    limite, resumo = LIMITE_PADRAO, False
    while args:
        a = args.pop(0)
        if a == "--incidente":
            incidente = valor(a)
        elif a == "--sessao":
            sessao = valor(a)
        elif a == "--tool":
            tool = valor(a)
        elif a == "--classe":
            classe = valor(a)
        elif a == "--limite":
            limite = valor(a)
        elif a == "--resumo":
            resumo = True
        elif a.startswith("-") or dia is not None:
            raise Recusa(2, f"argumento desconhecido «{a}»", [USO.splitlines()[0]])
        else:
            dia = a
    if dia is None:
        raise Recusa(2, "falta o dia", [USO.splitlines()[0], "o dia é obrigatório: a leitura é deliberada, sem padrão"])
    try:
        d = date.fromisoformat(dia)
    except ValueError:
        raise Recusa(2, f"dia inválido «{dia}»", ["o formato é AAAA-MM-DD"]) from None
    if d > hoje:
        raise Recusa(2, f"{dia} ainda não existe (hoje é {hoje.isoformat()})", ["o dia mais novo é hoje"])
    if incidente is None:
        raise Recusa(2, "sem --incidente: a linha inteira só sai com incidente aberto (arq:0123 regra 15)", [
            "o número vem de quem investiga: o card do incidente (tarefas listar --estado detectado)",
            "este verbo não abre incidente para destravar a leitura; o argumento, o erro e o texto do turno "
            f"ficam no bruto até lá ({VERBO} casos e {VERBO} eventos dão o giro sem conteúdo)"])
    try:
        numero = int(incidente)
        if numero < 1:
            raise ValueError
    except ValueError:
        raise Recusa(2, f"--incidente «{incidente}» não é número de card", ["um inteiro maior que zero"]) from None
    if sessao is not None:
        sessao = sessao.strip().lower()
        if not _SESSAO.fullmatch(sessao):
            raise Recusa(2, f"--sessao «{sessao}» não é prefixo de sessao_id", ["hex e hífen, até 36 caracteres"])
    if tool is not None and not _TOOL.fullmatch(tool):
        raise Recusa(2, f"--tool «{tool}» não é nome de verbo", ["letras, dígitos e _ . : -"])
    if classe is not None and classe not in oplog.CLASSES:
        raise Recusa(2, f"--classe «{classe}» fora do vocabulário", [f"as classes: {', '.join(oplog.CLASSES)}"])
    try:
        limite = int(limite)
        if not 1 <= limite <= LIMITE_MAXIMO:
            raise ValueError
    except ValueError:
        raise Recusa(2, f"--limite «{limite}» fora de 1..{LIMITE_MAXIMO}", ["o teto de linhas devolvidas"]) from None
    return {"dia": dia, "incidente": numero, "sessao": sessao, "tool": tool, "classe": classe, "limite": limite,
            "resumo": resumo}


# --- o incidente aberto ---------------------------------------------------------------------------------

def _tarefas_ler(numero: int, binario: str | None = None) -> tuple[int, str, str]:
    """(exit, stdout, stderr) de `tarefas ler <n>`: o mesmo verbo que o resto da casa usa para ler o card."""
    padrao = Path(os.path.realpath(__file__)).parent.parent / "tarefas"
    caminho = binario or os.environ.get("PF_TAREFAS_BIN") or str(padrao)
    try:
        p = subprocess.run([caminho, "ler", str(numero)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, check=False)
    except subprocess.TimeoutExpired:
        raise Recusa(3, "tarefas ler: passou de 60s sem resposta", ["o rastreador: infra saude"]) from None
    except OSError as e:
        raise Recusa(3, f"tarefas ler: não executou ({e.strerror})", ["o rastreador: infra saude"]) from None
    return p.returncode, p.stdout, p.stderr


def conferir_incidente(numero: int, tarefas=None) -> str:
    """Devolve o estado do incidente (o rótulo) ou levanta `Recusa`: 4 se não existe ou não está aberto, 3 se o
    rastreador não respondeu, 5 se a resposta não tem o cabeçalho de sempre. A fase do estado é que decide, e só se
    lê o cabeçalho (a segunda linha), nunca o corpo do card."""
    saiu, texto, erro = (tarefas or _tarefas_ler)(numero)
    caminho_do_numero = [f"o número vem de quem investiga; os abertos: tarefas listar --estado {e}"
                         for e in ESTADOS_ABERTOS]
    if saiu == 1:
        raise Recusa(4, f"o incidente #{numero} não existe", caminho_do_numero)
    if saiu != 0:
        motivo = (erro.strip().splitlines() or ["sem retorno"])[0]
        raise Recusa(3, f"tarefas ler {numero} saiu {saiu}: {motivo}", ["o rastreador: infra saude"])
    linhas = texto.splitlines()
    achado = _CABECALHO.fullmatch(linhas[1]) if len(linhas) >= 2 else None
    if achado is None or int(achado.group(1)) != numero:
        raise Recusa(5, f"tarefas ler {numero}: o cabeçalho do card não tem a forma de sempre",
                     ["a segunda linha é «#N · tipo · Estado (fase)»; avise a mesa de ti"])
    estado, fase = achado.group(3), achado.group(4)
    if fase != FASE_ABERTA:
        raise Recusa(4, f"#{numero} está «{estado}» ({fase}): não é incidente aberto",
                     [f"aberto é {', '.join(ESTADOS_ABERTOS)}", *caminho_do_numero[:1],
                      "este verbo não abre nem reabre incidente para destravar a leitura"])
    return estado


# --- o que casa -----------------------------------------------------------------------------------------

def _casa(sessao: str | None, tool: str | None, classe: str | None):
    """O predicado das linhas do bruto. `--sessao` casa por prefixo e pega qualquer linha da sessão (o turno
    inclusive); `--tool` e `--classe` são do giro, e a linha que não é chamada de verbo não os casa."""
    def casa(reg: dict) -> bool:
        if sessao and not str(reg.get("sessao_id") or "").lower().startswith(sessao):
            return False
        if tool or classe:
            try:
                if extracao.tipo_particao(reg) != "giro":
                    return False
            except extracao.SemTraducao:
                return False
            if tool and reg.get("tool") != tool:
                return False
            if classe and extracao.classe_do_giro(reg) != classe:
                return False
        return True
    return casa


def _slug(valor: str | None) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", (valor or "").lower()).strip("-")
    return s if _SLUG.fullmatch(s) else "desconhecida"


# --- a citação (D5.10) -----------------------------------------------------------------------------------

def _depois_da_passada(dia: str) -> str:
    return f"{(date.fromisoformat(dia) + timedelta(days=1)).isoformat()} {PASSADA_DO_DIA}"


def _citar(api, autor: str, numero: int, dia: str, itens: list[dict]) -> tuple[dict, int]:
    """D5.10 para as linhas devolvidas. Devolve o bloco `citacao` da saída e o exit que ele pede: 0 se gravou ou se só
    falta a passada do dia; o da falha (3, 4 ou 5) quando a citação não gravou, e as linhas saem mesmo assim."""
    if not itens:
        return {"estado": "nenhuma", "citadas": 0, "ja_citadas": 0, "ausentes": 0}, 0
    try:
        _, r = api.chamar("POST", "/acervo/log/citacoes", {"autor": autor, "incidente": numero, "itens": itens},
                          contrato="1.6.0")
    except extracao.Falha as f:
        codigo = 4 if f.titulo == "ConteudoDivergente" else (f.codigo if f.codigo in (3, 4) else 5)
        proximo = ("integridade: a linha guardada tem outro sha256; abra incidente na mesa de seguranca e não repita"
                   if f.titulo == "ConteudoDivergente" else
                   f"a citação não gravou; repita {VERBO} investigar {dia} --incidente {numero} (a linha segue no bruto)")
        return {"estado": "nao_gravada", "motivo": str(f), "codigo": codigo, "proximo_passo": proximo}, codigo
    if not isinstance(r, dict) or not isinstance(r.get("ausentes"), list):
        return ({"estado": "nao_gravada", "motivo": "a partição respondeu fora do contrato (D5.10)", "codigo": 5,
                 "proximo_passo": f"repita {VERBO} investigar {dia} --incidente {numero}"}, 5)
    ausentes = len(r["ausentes"])
    bloco = {"estado": "gravada" if not ausentes else ("pendente" if ausentes == len(itens) else "parcial"),
             "citadas": r.get("citadas"), "ja_citadas": r.get("ja_citadas"), "ausentes": ausentes}
    if ausentes:
        bloco["proximo_passo"] = (
            f"a partição ainda não tem {ausentes} das {len(itens)} linhas (o dia {dia} entra depois da passada de "
            f"{_depois_da_passada(dia)}): repita {VERBO} investigar {dia} --incidente {numero} depois dela, para a "
            "linha ficar citada por um ano; o bruto a guarda por 35 dias")
    return bloco, 0


# --- as duas fontes --------------------------------------------------------------------------------------

def _do_bruto(a: dict, ambiente, diretorio_) -> dict | None:
    """As linhas do arquivo do dia, ou None se o dia já saiu do bruto. O rastro grava dentro de `ler_inteiras`."""
    filtros = {"sessao": a["sessao"], "tool": a["tool"], "classe": a["classe"]}
    achadas = oplog.ler_inteiras(a["dia"], incidente=a["incidente"], casa=_casa(a["sessao"], a["tool"], a["classe"]),
                                 filtros=filtros, limite=a["limite"], max_bytes=MAX_BYTES, ambiente=ambiente,
                                 diretorio_=diretorio_)
    if achadas.ausente:
        return None
    if not achadas.registrada:
        raise Recusa(5, "o rastro da leitura (leitura_bruto) não gravou; nada foi devolvido",
                     ["o disco do bruto e o stderr da porta dizem o motivo: infra saude"])
    itens = [extracao.item_de_citacao(reg, bruta, a["dia"], n) for n, bruta, reg in achadas.linhas]
    r = {"fonte": "bruto", "omitidas": achadas.omitidas, "ha_mais": achadas.omitidas > 0,
         "linhas": [{"linha_n": n, "evento_id": it["evento_id"], "linha": it["linha"]}
                    for (n, _, _), it in zip(achadas.linhas, itens, strict=True)],
         "para_citar": itens}
    if achadas.ilegiveis:
        r["linhas_ilegiveis"] = achadas.ilegiveis
    return r


def _da_particao(api, a: dict, ambiente, diretorio_) -> dict:
    """D5.11: o que a partição guarda do dia que saiu do bruto. Rastro gravado, ainda que nada case."""
    params = {"limite": a["limite"] + 1, **{k: a[k] for k in ("sessao", "tool", "classe") if a[k]}}
    try:
        _, resposta = api.chamar("GET", f"/acervo/log/dias/{a['dia']}/conteudo", params=params, contrato="1.6.0")
    except extracao.Falha as f:
        raise Recusa(f.codigo if f.codigo in (3, 4) else 5, f"a partição não respondeu: {f}",
                     ["o acervo e o banco: infra saude"]) from None
    if not isinstance(resposta, dict) or not isinstance(resposta.get("itens"), list):
        raise Recusa(5, "a partição respondeu fora do contrato (D5.11)", ["o acervo e o banco: infra saude"])
    itens = resposta["itens"]
    ha_mais = len(itens) > a["limite"]
    guardadas, usados = [], 0
    for it in itens[:a["limite"]]:
        custo = len(json.dumps(it.get("linha"), ensure_ascii=False)) + oplog.SOBRA_POR_LINHA
        if guardadas and usados + custo > MAX_BYTES:
            ha_mais = True
            break
        guardadas.append(it)
        usados += custo
    filtros = {"sessao": a["sessao"], "tool": a["tool"], "classe": a["classe"]}
    if not oplog.registrar_leitura(a["dia"], incidente=a["incidente"], origem="particao", filtros=filtros,
                                   devolvidas=len(guardadas), omitidas=None, ambiente=ambiente,
                                   diretorio_=diretorio_):
        raise Recusa(5, "o rastro da leitura (leitura_bruto) não gravou; nada foi devolvido",
                     ["o disco do bruto e o stderr da porta dizem o motivo: infra saude"])
    return {"fonte": "particao", "omitidas": None, "ha_mais": ha_mais,
            "cobertura": {k: resposta.get(k) for k in ("cobertura", "motivo", "versao_extrator")},
            "linhas": [{"linha_n": it.get("linha_n"), "evento_id": it["evento_id"], "amostra": it.get("amostra"),
                        "incidentes_antes": it.get("incidentes") or [], "linha": it["linha"]} for it in guardadas],
            "para_citar": [{"evento_id": it["evento_id"], "linha": it["linha"], "linha_sha256": it["linha_sha256"]}
                           for it in guardadas]}


# --- a saída ---------------------------------------------------------------------------------------------

def _texto(r: dict) -> list[str]:
    c = r["citacao"]
    linhas = [f"== {VERBO} investigar — {r['dia']} · fonte: {r['fonte']} · incidente #{r['incidente']} ==",
              f"{r['devolvidas']} linha(s) inteira(s)" + (" · tem mais: afine o filtro ou suba --limite" if r["ha_mais"]
                                                         else "") + " · leitura registrada (leitura_bruto)",
              f"citação: {c['estado']}" + (f" · {c['citadas']} nova(s), {c['ja_citadas']} já citada(s)"
                                          if c.get("citadas") is not None else "")]
    if c.get("proximo_passo"):
        linhas.append(f"  {c['proximo_passo']}")
    for item in r["linhas"]:
        linhas.append(f"-- linha {item['linha_n']} · {item['evento_id']}")
        linhas.append(json.dumps(item["linha"], ensure_ascii=False, indent=2))
    return linhas


def _erro(r: Recusa, saida_erro) -> None:
    saida_erro(f"erro: {VERBO} investigar: {r}")
    if r.caminho:
        saida_erro("corrija:")
        for linha in r.caminho:
            saida_erro(f"  {linha}")


def investigar(argv: list[str], *, api=None, tarefas=None, ambiente=None, saida=print, saida_erro=None,
               diretorio_=None, hoje: date | None = None) -> int:
    """Roda o ato. `api`, `tarefas`, `ambiente`, `diretorio_` e `hoje` existem para o teste trocar o que é de fora."""
    saida_erro = saida_erro or (lambda t: print(t, file=sys.stderr))
    if argv and argv[0] in ("-h", "--help", "--ajuda", "ajuda"):
        saida(USO)
        return 0
    env = os.environ if ambiente is None else ambiente
    api = api or extracao.Api()
    try:
        a = _argumentos(argv, hoje or oplog.hoje_local())
        estado = conferir_incidente(a["incidente"], tarefas)
        lido = _do_bruto(a, env, diretorio_)
        if lido is None:
            lido = _da_particao(api, a, env, diretorio_)
        if not lido["linhas"]:
            raise Recusa(1, f"sem linha inteira guardada para {a['dia']}" if lido["fonte"] == "particao"
                         else f"nenhuma linha de {a['dia']} casa com o filtro",
                         ["a leitura ficou registrada (leitura_bruto)",
                          *(["o dia já saiu do bruto: só a amostra e a linha já citada ficam na partição"]
                            if lido["fonte"] == "particao" else ["afine ou tire o filtro (--sessao, --tool, --classe)"])])
        citacao, codigo = _citar(api, _slug(env.get("PF_CADEIRA")), a["incidente"], a["dia"],
                                 lido.pop("para_citar"))
    except Recusa as r:
        _erro(r, saida_erro)
        return r.codigo
    r = {"dia": a["dia"], "fonte": lido.pop("fonte"), "incidente": a["incidente"], "estado_do_incidente": estado,
         "filtros": {"sessao": a["sessao"], "tool": a["tool"], "classe": a["classe"]}, "limite": a["limite"],
         "devolvidas": len(lido["linhas"]), **lido, "leitura_bruto": "gravada", "citacao": citacao}
    if a["resumo"]:
        for linha in _texto(r):
            saida(linha)
    else:
        saida(json.dumps(r, ensure_ascii=False, indent=1))
    if codigo:
        saida_erro(f"erro: {VERBO} investigar: {citacao.get('motivo', 'a citação não gravou')}")
        saida_erro("corrija:")
        saida_erro(f"  {citacao['proximo_passo']}")
    return codigo


main = investigar
