"""perfil_lint_codigo — cronometro por etapa, bytes de saida e diff de apontamentos do `lint codigo`.

Mede a classe `codigo` em dois alvos (bin/curar e o repositorio inteiro) e confere tres coisas:
a lista de apontamentos e a mesma da referencia, o tempo cabe no teto e a saida de texto do
arquivo unico cabe no teto de bytes (#3286).

Fora de VERDES e sem o prefixo `test_`: o tempo de parede num host compartilhado e erratico, e
teste que depende dele nao entra no portao (lista antipadroes-de-codigo, TESTE_ERRATICO). Roda
sob demanda, com o ambiente real (ruff, shellcheck, acervo), que o subprocesso monta do zero:

    sessao longjob run perfil teste rodar platafirma-harness@<chave> controle/tests/perfil_lint_codigo.py

Grava em $PF_LINT_PERFIL_DIR (padrao /srv/platafirma/casa/var/lint-perfil):
    <sha>/perfil-<alvo>.json      tempo por etapa, por indice auxiliar e por predicado; bytes da saida
    <sha>/apontamentos-<alvo>.json
    referencia/apontamentos-<alvo>.json   a primeira rodada vira referencia; as seguintes comparam
Para trocar a referencia, apague a pasta referencia/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
TETO_S = {"bin/curar": 5.0, "": 15.0}
TETO_BYTES = {"bin/curar": 16_000}
PRAZO_RODADA_S = 600

# O que roda no subprocesso: instrumenta pelo nome o que existir (a forma do lint muda, o
# cronometro nao quebra) e imprime um JSON com o perfil e a lista.
INTERNO = r'''
import contextlib, hashlib, io, json, sys, time
from pathlib import Path
RAIZ = Path(sys.argv[1]); ALVO = sys.argv[2] or None
sys.path[:0] = [str(RAIZ / "bin"), str(RAIZ)]
import _lint.codigo as C
import _lint.predicados as P
import _lint.predicados_stack as S
from _lint.resultado import relatorio_lint

tempos = {}
def soma(chave, dt):
    d = tempos.setdefault(chave, [0.0, 0]); d[0] += dt; d[1] += 1
def cron(mod, nome, chave):
    f = getattr(mod, nome, None)
    if not callable(f):
        return
    def embrulho(*a, **k):
        t = time.perf_counter()
        try:
            return f(*a, **k)
        finally:
            soma(chave, time.perf_counter() - t)
    setattr(mod, nome, embrulho)

for n in ("resolver_lista", "_contexto", "_ruff", "_selecao_ruff", "_shellcheck", "_predicados"):
    cron(C, n, "etapa:" + n)
for n in ("rotas", "_por_nome", "fazem_io"):
    cron(S, n, "indice:" + n)
rodar = C._rodar
def rodar_cronometrado(cmd, raiz):
    t = time.perf_counter()
    try:
        return rodar(cmd, raiz)
    finally:
        soma("sub:" + " ".join(x for x in cmd[1:3] if not x.startswith("/")), time.perf_counter() - t)
C._rodar = rodar_cronometrado
arvore = P.Contexto.arvore
def arvore_cronometrada(self, p):
    novo = p not in self._arvores
    t = time.perf_counter()
    try:
        return arvore(self, p)
    finally:
        if novo:
            soma("parse", time.perf_counter() - t)
P.Contexto.arvore = arvore_cronometrada
predicados = {}
for nome, (f, candidata) in list(C.TODOS_PREDICADOS.items()):
    def medido(ctx, item, f=f, nome=nome):
        t = time.perf_counter()
        r = list(f(ctx, item))
        predicados[nome] = predicados.get(nome, 0.0) + time.perf_counter() - t
        return r
    C.TODOS_PREDICADOS[nome] = (medido, candidata)

t = time.perf_counter()
ap, chave, rev, avisos = C.verificar_codigo(RAIZ, ALVO)
total = time.perf_counter() - t

ancora = "platafirma-harness" + (f"/{ALVO}" if ALVO else "")
texto, como_json = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(texto):
    relatorio_lint("codigo", ancora, ap, chave, rev=rev)
with contextlib.redirect_stdout(como_json):
    relatorio_lint("codigo", ancora, ap, chave, rev=rev, como_json=True)
bruto_json = como_json.getvalue().encode("utf-8")
print(json.dumps({
    "alvo": ALVO, "total_s": round(total, 3), "n": len(ap), "avisos": avisos,
    "bytes_texto": len(texto.getvalue().encode("utf-8")),
    "bytes_json": len(bruto_json), "sha256_json": hashlib.sha256(bruto_json).hexdigest(),
    "etapas": {k: [round(v[0], 3), v[1]] for k, v in sorted(tempos.items(), key=lambda x: -x[1][0])},
    "predicados": {k: round(v, 3) for k, v in sorted(predicados.items(), key=lambda x: -x[1])},
    "apontamentos": [a.dict() for a in ap],
}, ensure_ascii=False))
'''


def _env() -> dict[str, str]:
    """O ambiente real: o isolamento da suite poe delatores no PATH e um acervo de fixture."""
    env = {k: v for k, v in os.environ.items() if k not in ("PF_LINT_ACERVO", "PYTEST_CURRENT_TEST")}
    env.update({"PATH": "/home/claudinho/.local/bin:/usr/local/bin:/usr/bin:/bin",
                "HOME": "/home/claudinho", "PLATAFIRMA_INSTANCIA": "/srv/platafirma/casa"})
    return env


def _sha() -> str:
    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True,
                              timeout=30, check=True).stdout.strip()
    sujo = git("status", "--porcelain", "--", "bin")
    return git("rev-parse", "--short=12", "HEAD") + ("-sujo" if sujo else "")


# O codigo do proprio lint muda enquanto se mede (as linhas andam); o que aponta nele, ou cita
# linha dele, fica fora da comparacao.
_FORA_DO_DIFF = ("bin/_lint/", "controle/tests/perfil_lint_codigo.py")


def _chave(ap: dict) -> tuple:
    return (ap["arquivo"], ap["linha"], ap.get("id") or "", ap["o_que_fere"], ap["cura"])


def _comparaveis(apontamentos: list[dict]) -> set[tuple]:
    return {_chave(a) for a in apontamentos
            if not a["arquivo"].startswith(_FORA_DO_DIFF) and not any(f in a["o_que_fere"] for f in _FORA_DO_DIFF)}


@pytest.mark.parametrize("alvo", ["bin/curar", ""], ids=["arquivo-unico", "repositorio"])
def test_perfil(alvo: str) -> None:
    proc = subprocess.run([sys.executable, "-c", INTERNO, str(RAIZ), alvo], env=_env(),
                          capture_output=True, text=True, timeout=PRAZO_RODADA_S, check=False)
    assert proc.returncode == 0, f"a rodada quebrou: {proc.stderr[-2000:]}"
    medida = json.loads(proc.stdout)
    apontamentos = medida.pop("apontamentos")

    base = Path(os.environ.get("PF_LINT_PERFIL_DIR", "/srv/platafirma/casa/var/lint-perfil"))
    nome = alvo.replace("/", "_") or "repositorio"
    pasta = base / _sha()
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"perfil-{nome}.json").write_text(json.dumps(medida, indent=1, ensure_ascii=False), encoding="utf-8")
    (pasta / f"apontamentos-{nome}.json").write_text(json.dumps(apontamentos, ensure_ascii=False), encoding="utf-8")

    referencia = base / "referencia" / f"apontamentos-{nome}.json"
    if not referencia.exists():
        referencia.parent.mkdir(parents=True, exist_ok=True)
        referencia.write_text(json.dumps(apontamentos, ensure_ascii=False), encoding="utf-8")

    antes = _comparaveis(json.loads(referencia.read_text(encoding="utf-8")))
    agora = _comparaveis(apontamentos)
    falhas = []
    if antes != agora:
        sumiram, surgiram = sorted(antes - agora)[:5], sorted(agora - antes)[:5]
        falhas.append(f"lista mudou: {len(antes - agora)} sumiram {sumiram}, {len(agora - antes)} surgiram {surgiram}")
    if medida["total_s"] >= TETO_S[alvo]:
        falhas.append(f"{medida['total_s']} s, teto {TETO_S[alvo]} s")
    if alvo in TETO_BYTES and medida["bytes_texto"] > TETO_BYTES[alvo]:
        falhas.append(f"saida de texto com {medida['bytes_texto']} B, teto {TETO_BYTES[alvo]} B")
    assert not falhas, f"{alvo or 'repositorio'} ({pasta}): " + "; ".join(falhas)
