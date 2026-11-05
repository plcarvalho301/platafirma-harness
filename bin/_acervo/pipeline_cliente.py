"""Cliente fino do job do pipeline do acervo (card #4120; U7 e U13).

Fala com as rotas /acervo/jobs, /acervo/jobs/{id}/classificacao e /acervo/indicacoes do serviço do
acervo. Só stdlib: o venv que roda `acervo` não precisa de `requests`. Um erro vira `Falha` com o
código de saída da tabela de `arq:0110` §4: 1 resultado negativo de mérito, 2 uso errado, 3 serviço
fora, 4 recusa de política ou de autenticação, 5 indeterminável.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HARNESS_DIR))
sys.path.insert(0, str(HARNESS_DIR / "lib"))

try:
    from recuperacao.adaptadores.motor_acervo_rest import BASE as DEFAULT_BASE
    from recuperacao.adaptadores.motor_acervo_rest import TOKEN as DEFAULT_TOKEN
except ImportError:
    from lib import motor_enderecos
    DEFAULT_BASE, DEFAULT_TOKEN = motor_enderecos.api_acervo(), ""

TETO_ESPERA_S = 540  # o teto do servidor no GET do job; abaixo dos 600 s da chamada da porta
# as etapas do job, na ordem em que cada obra as percorre (conhecimento@rag/motor_acervo/curadoria/job_pipeline.py)
ETAPAS = ("triagem", "espelhar", "catalogacao", "duplicata", "classificar", "indexar", "promocao")


class Falha(Exception):
    def __init__(self, codigo: int, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def base() -> str:
    return (os.environ.get("MOTOR_ACERVO_URL") or os.environ.get("RAG_API_URL")
            or os.environ.get("RAG_API_BASE") or DEFAULT_BASE).rstrip("/")


def _token() -> str:
    return os.environ.get("RAG_API_TOKEN") or DEFAULT_TOKEN


def _saida_do_status(status: int) -> int:
    if status in (401, 403):
        return 4
    if status == 400:
        return 2
    if status >= 500:
        return 3
    return 1


def chamar(metodo: str, caminho: str, corpo=None, timeout: float = 60):
    """Uma chamada JSON. Devolve o corpo decodificado; erro HTTP ou de rede levanta `Falha`."""
    cabecalhos = {"accept": "application/json"}
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        cabecalhos["content-type"] = "application/json"
    if _token():
        cabecalhos["authorization"] = f"Bearer {_token()}"
    req = urllib.request.Request(f"{base()}{caminho}", data=dados, method=metodo, headers=cabecalhos)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            bruto, status = resp.read(), resp.status
    except urllib.error.HTTPError as e:
        bruto, status = e.read(), e.code
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise Falha(3, f"rota fora: o serviço do acervo não respondeu em {base()} ({e.__class__.__name__})") from e
    try:
        obj = json.loads(bruto) if bruto else None
    except ValueError:
        obj = None
    if status >= 400:
        titulo = (obj or {}).get("title") if isinstance(obj, dict) else None
        detalhe = (obj or {}).get("detail") if isinstance(obj, dict) else None
        texto = f"{titulo or f'HTTP {status}'}: {detalhe or (bruto or b'')[:300].decode('utf-8', 'replace')}"
        raise Falha(_saida_do_status(status), texto)
    return obj


def pedido_de_classificacao(job_id: str, parte: int = 1) -> dict:
    return chamar("GET", f"/acervo/jobs/{job_id}/classificacao?parte={int(parte)}")


def enviar_respostas(job_id: str, corpo) -> dict:
    return chamar("POST", f"/acervo/jobs/{job_id}/classificacao", corpo)


def criar_job(pasta: str, lote_id: str) -> dict:
    return chamar("POST", "/acervo/jobs", {"pasta": pasta, "lote_id": lote_id})


def ver_job(job_id: str, espera: int = 0) -> dict:
    espera = max(0, min(int(espera), TETO_ESPERA_S))
    caminho = f"/acervo/jobs/{job_id}" + (f"?espera={espera}" if espera else "")
    return chamar("GET", caminho, timeout=espera + 30)


def liberar(corpo: dict) -> dict:
    """Solta as obras estacionadas do job e o retoma: `corpo` leva `itens` (sha256 ou obra) e um de job_id, lote_id, pasta."""
    return chamar("POST", "/acervo/jobs/liberar", corpo)


def curar_indicacoes(lote_id: str | None, aplicar: bool, termos: list[str] | None = None) -> dict:
    corpo = {"lote_id": lote_id, "aplicar": bool(aplicar)}
    if termos:
        corpo["termos"] = termos
    return chamar("POST", "/acervo/indicacoes", corpo)


def resumo_do_job(job: dict) -> str:
    """O estado do job e a contagem de cada etapa por estado, em linhas curtas."""
    etapas = job.get("etapas") or []
    obras = {e["obra_id"] for e in etapas}
    linhas = [f"job: {job['id']}", f"estado: {job.get('estado')}", f"obras: {len(obras)}"]
    por_etapa: dict[str, dict[str, int]] = {}
    for e in etapas:
        contagem = por_etapa.setdefault(e["etapa"], {})
        contagem[e["estado"]] = contagem.get(e["estado"], 0) + 1
    for etapa in ETAPAS:
        if etapa in por_etapa:
            linhas.append(f"  {etapa}: " + " · ".join(f"{estado} {n}" for estado, n in sorted(por_etapa[etapa].items())))
    # o que as etapas deixaram no detalhe e pede um olho: par de duplicata e promoção que ficou para depois
    com_par = [e for e in etapas if e["etapa"] == "duplicata" and (e.get("detalhe") or {}).get("pares")]
    provaveis = [e for e in com_par if (e["detalhe"] or {}).get("duplicata_provavel")]
    if com_par:
        linhas.append(f"duplicata: {len(com_par)} obra(s) com par, {len(provaveis)} provavel(is); "
                      f"os pares estao no detalhe (`--json`)")
    estacionadas = [e for e in etapas if e["estado"] == "estacionado"]
    if estacionadas:
        linhas.append(
            f"{len(estacionadas)} obra(s) estacionada(s) esperam o dono (duplicata provavel): libere com "
            f"`acervo pipeline --job {job['id']} --liberar <obra>` ou retire a obra com `acervo retirar biblioteca obra`")
        for e in estacionadas:
            pares = [p for p in (e.get("detalhe") or {}).get("pares") or [] if p.get("classificacao") == "duplicata_provavel"]
            ao_lado = ", ".join(
                f"{p['obra_id']} ({'Jaccard ' + str(p['jaccard']) if p.get('jaccard') is not None else p.get('motivo', '')})"
                for p in pares)
            linhas.append(f"  {e['obra_id']} ↔ {ao_lado}")
    sem_promocao = [e for e in etapas if e["etapa"] == "promocao"
                    and (e.get("detalhe") or {}).get("promovida") is False]
    if sem_promocao:
        linhas.append(f"promocao: {len(sem_promocao)} obra(s) ainda sem promocao (a impressao nao tem o que a "
                      "marcacao exige); promover e `acervo promover biblioteca obra <obra> --impressao <id>`")
    if job.get("erro"):
        linhas.append(f"erro: {job['erro']}")
    esperando = sum(1 for e in etapas if e["etapa"] == "classificar" and e["estado"] == "pausado")
    if esperando:
        linhas.append(f"{esperando} obra(s) esperam a classificação da sessão: "
                      f"acervo catalogar biblioteca obra --job {job['id']}")
    return "\n".join(linhas)
