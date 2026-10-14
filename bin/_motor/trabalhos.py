"""Os trabalhos longos do motor, com o sinal de vida (card #3513, tarefa 8; spec plano-de-controle-face-motor R17, R18).

`motor rag trabalhos` junta duas fontes num estado só, calculado aqui e em nenhum outro lugar (a face, a ronda da
ti e a cadeira leem o mesmo fato):

- os lotes de indexação e de troca, que o rag-api guarda no banco com batimento (`GET /motor/trabalhos`, #3510) e
  já diz vivo, parado ou indeterminável pelo limiar do próprio trabalho;
- as sombras de bench de embedder (`motor medir --sombra`), que moram no contêiner do rag, em
  `/tmp/sombra-<id>/`, com `log.txt` e, quando acabam, `fim`. Aqui o estado sai dos fatos que o contêiner dá: há
  processo da sombra, quando o log foi escrito pela última vez, existe `fim`.

O vocabulário é o de três da arq:0110 §4: `vivo`, `parado`, `indeterminavel` («não consegui olhar»). Sombra que
terminou (`fim`) não é trabalho em curso e fica fora da lista (só a contagem).
"""
from __future__ import annotations

import json
import os
import shlex
import time
from datetime import datetime

NAO_CONSEGUI = "nao consegui olhar"
# Segundos sem escrita no log além dos quais a sombra com processo se diz parada. ⚪ hipótese até a primeira
# sombra real dizer a cadência do log; corrige-se por SOMBRA_LIMIAR_S.
LIMIAR_PADRAO_S = 1800

# Roda DENTRO do contêiner do rag. Os pedaços 'sombra' + '-' evitam que o próprio processo se ache na varredura
# de /proc. Devolve uma linha JSON: o relógio do contêiner e os fatos de cada /tmp/sombra-<id>.
SCRIPT_DENTRO = r'''
import json, os, time
agora = time.time()
procs = []
for p in os.listdir('/proc'):
    if not p.isdigit() or int(p) == os.getpid():
        continue
    try:
        procs.append(open('/proc/' + p + '/cmdline', 'rb').read().decode(errors='ignore'))
    except OSError:
        pass
saida = []
for nome in sorted(os.listdir('/tmp')):
    if not nome.startswith('sombra' + '-'):
        continue
    sid = nome[len('sombra' + '-'):]
    d = '/tmp/' + nome
    def mt(arq):
        try:
            return os.stat(d + '/' + arq).st_mtime
        except OSError:
            return None
    fim = None
    try:
        fim = int(open(d + '/fim').read().strip())
    except (OSError, ValueError):
        pass
    ultima = None
    try:
        ultima = open(d + '/log.txt', errors='ignore').read().strip().splitlines()[-1][:200]
    except (OSError, IndexError):
        pass
    saida.append({'id': sid, 'fim': fim, 'fim_mtime': mt('fim'), 'log_mtime': mt('log.txt'),
                  'dir_mtime': mt('.'), 'vivo': any(('sombra' + '-' + sid) in c for c in procs),
                  'ultima_linha': ultima})
print(json.dumps({'agora': agora, 'sombras': saida}))
'''


def limiar_s() -> int:
    try:
        v = int(os.environ.get("SOMBRA_LIMIAR_S", ""))
    except ValueError:
        return LIMIAR_PADRAO_S
    return v if v > 0 else LIMIAR_PADRAO_S


def _iso(epoch: float | None) -> str | None:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds") if epoch else None


def _inicio_do_id(sid: str) -> str | None:
    try:
        return datetime.strptime(sid, "%Y%m%dT%H%M%S").astimezone().isoformat(timespec="seconds")
    except ValueError:
        return None


def ler_sombras(container: str | None, executa) -> tuple[list[dict], str | None]:
    """(sombras com os fatos, None) ou ([], motivo). `executa(cmd)` devolve (exit, stdout, stderr)."""
    if not container:
        return [], "a instancia nao declara `container`"
    rc, out, err = executa(f"docker exec {container} python -c {shlex.quote(SCRIPT_DENTRO)}")
    if rc != 0:
        return [], f"o conteiner {container} nao respondeu: {(err or '').strip()[-200:]}"
    try:
        dado = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [], f"o conteiner {container} devolveu o que nao e JSON"
    return [{**s, "agora": dado["agora"]} for s in dado.get("sombras") or []], None


def estado_da_sombra(f: dict, limiar: int) -> dict:
    """O trabalho no formato dos lotes do rag-api, com o estado de vida calculado dos fatos."""
    ref = f.get("log_mtime") or f.get("dir_mtime")
    base = {"id": f["id"], "tipo": "sombra-de-bench", "particao": None, "geracao": None,
            "iniciado_em": _inicio_do_id(f["id"]),
            "progresso": {"ultima_linha": f.get("ultima_linha")},
            "ultimo_batimento": _iso(ref), "limiar_s": limiar,
            "fonte": "sombra de bench no conteiner (/tmp/sombra-<id>)"}
    if ref is None:
        return {**base, "estado": "indeterminavel", "desde": None,
                "motivo": f"{NAO_CONSEGUI}: a pasta da sombra nao tem hora legivel"}
    if not f.get("vivo"):
        return {**base, "estado": "parado", "desde": _iso(ref),
                "motivo": "nenhum processo da sombra no conteiner e sem arquivo `fim`"}
    idade = f["agora"] - ref
    if idade > limiar:
        return {**base, "estado": "parado", "desde": _iso(ref),
                "motivo": f"sem escrita no log ha {int(idade)} s; o limiar deste trabalho e {limiar} s"}
    return {**base, "estado": "vivo", "desde": _inicio_do_id(f["id"]), "motivo": None}


def juntar(rag: list[dict] | None, sombras: list[dict] | None, limiar: int) -> dict:
    """O mesmo fato para quem lê: `itens` (do mais novo ao mais velho), `resumo` e o que não se conseguiu olhar.
    `rag` e `sombras` None = a fonte não respondeu."""
    itens = [{**t, "fonte": "rag-api GET /motor/trabalhos"} for t in (rag or [])]
    concluidas = 0
    for s in sombras or []:
        if s.get("fim") is not None:
            concluidas += 1
        else:
            itens.append(estado_da_sombra(s, limiar))
    itens.sort(key=lambda t: t.get("iniciado_em") or "", reverse=True)
    return {"itens": itens,
            "resumo": {"em_curso": len(itens), "parados": sum(t["estado"] == "parado" for t in itens),
                       "indeterminaveis": sum(t["estado"] == "indeterminavel" for t in itens),
                       "sombras_concluidas_fora_da_lista": concluidas}}


def texto(r: dict) -> str:
    res = r["resumo"]
    saida = [f"trabalhos em curso: {res['em_curso']} · {res['parados']} parado(s) · "
             f"{res['indeterminaveis']} {NAO_CONSEGUI} · lido {r['lido_em']}"]
    for t in r["itens"]:
        prog = t.get("progresso") or {}
        andamento = (f"{prog.get('feitos')}/{prog.get('total')}" if prog.get("total") is not None
                     else (prog.get("ultima_linha") or "-"))
        desde = f" desde {t['desde']}" if t.get("desde") else ""
        saida.append(f"  {t['tipo']:<16} {t['id']}  {t['estado'].upper() if t['estado'] != 'vivo' else 'vivo'}"
                     f"{desde}  {andamento}")
        if t.get("motivo"):
            saida.append(f"      {t['motivo']}")
    for fonte, motivo in (r.get("nao_consegui_olhar") or {}).items():
        saida.append(f"  {NAO_CONSEGUI}: {fonte} — {motivo}")
    if res["sombras_concluidas_fora_da_lista"]:
        saida.append(f"  ({res['sombras_concluidas_fora_da_lista']} sombra(s) de bench ja terminadas ficam fora da lista)")
    return "\n".join(saida)


def agora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
