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


TAMANHO_PAGINA = 20
ESTADOS_REGULARES = {"pendente", "executando", "em_andamento", "concluido"}
# Campos que documentam sucesso no job existente. Campo novo continua visível até ser julgado.
CAMPOS_REGULARES = {
    "triagem": set(),
    "espelhar": {"metodo", "trechos", "servivel", "ja_selada", "julgamento", "impressao_id"},
    "catalogacao": {"ja_tinha", "preenchidos", "sem_espelho", "registro"},
    "duplicata": {"pares", "sem_espelho", "duplicata_provavel"},
    "classificar": {"especie", "conceitos", "nenhum_cobre", "versao_ficha"},
    "indexar": {"indexada", "lote_motor", "gate_aprovado"},
    "promocao": {"promovida", "motivo"},
}

def eh_excecao(etapa: dict) -> bool:
    """Só omite o detalhe conhecido de andamento regular; desvio e campo novo aparecem."""
    if etapa.get("estado") not in ESTADOS_REGULARES or etapa.get("erro"):
        return True
    d = etapa.get("detalhe") or {}
    if not isinstance(d, dict) or set(d) - CAMPOS_REGULARES.get(etapa.get("etapa"), set()):
        return True
    for campo in ("sem_espelho", "duplicata_provavel", "nenhum_cobre", "pares", "motivo", "registro"):
        if d.get(campo):
            return True
    for campo in ("servivel", "indexada", "gate_aprovado", "promovida"):
        if campo in d and d[campo] is not True:
            return True
    return bool(d.get("julgamento") and d["julgamento"] != "servível")

def status_compacto(job: dict, parte: int = 1) -> dict:
    """Contrato v1: contagem global e uma página de etapas excepcionais, sem alterar o job."""
    if parte < 1:
        raise ValueError("--parte deve ser positiva")
    etapas = job.get("etapas") or []
    por_etapa: dict[str, dict[str, int]] = {}
    por_estado: dict[str, int] = {}
    for e in etapas:
        nome, estado = str(e.get("etapa", "desconhecida")), str(e.get("estado", "desconhecido"))
        contagem = por_etapa.setdefault(nome, {})
        contagem[estado] = contagem.get(estado, 0) + 1
        por_estado[estado] = por_estado.get(estado, 0) + 1
    excecoes = sorted((e for e in etapas if eh_excecao(e)),
                      key=lambda e: (str(e.get("etapa", "")), str(e.get("obra_id", "")), str(e.get("id", ""))))
    paginas = max(1, (len(excecoes) + TAMANHO_PAGINA - 1) // TAMANHO_PAGINA)
    if parte > paginas:
        raise ValueError(f"--parte vai de 1 a {paginas}")
    inicio = (parte - 1) * TAMANHO_PAGINA
    # Não carregar outros campos do job: eles podem crescer com a população.
    return {
        "versao": 1, "id": job["id"], "estado": job.get("estado"), "erro": job.get("erro"),
        "obras": len({e["obra_id"] for e in etapas}), "etapas_total": len(etapas),
        "por_etapa": por_etapa, "por_estado": por_estado,
        "excecoes": {"total": len(excecoes), "parte": parte, "partes": paginas,
                     "por_pagina": TAMANHO_PAGINA,
                     "proxima_parte": parte + 1 if parte < paginas else None,
                     "itens": excecoes[inicio:inicio + TAMANHO_PAGINA]},
        "tabela": f"acervo pipeline --job {job['id']} --tabela --json",
    }

def resumo_do_job(job: dict, parte: int = 1) -> str:
    """Contagens de toda a população, com detalhe somente da página de exceções."""
    res = status_compacto(job, parte)
    etapas = job.get("etapas") or []
    pagina = res["excecoes"]
    linhas = [f"job: {job['id']}", f"estado: {job.get('estado')}", f"obras: {res['obras']}"]
    nomes = [n for n in ETAPAS if n in res["por_etapa"]]
    nomes += sorted(set(res["por_etapa"]) - set(ETAPAS))
    for nome in nomes:
        linhas.append(f"  {nome}: " + " · ".join(
            f"{estado} {n}" for estado, n in sorted(res["por_etapa"][nome].items())))
    com_par = [e for e in etapas if e["etapa"] == "duplicata" and (e.get("detalhe") or {}).get("pares")]
    if com_par:
        provaveis = sum(bool((e.get("detalhe") or {}).get("duplicata_provavel")) for e in com_par)
        linhas.append(f"duplicata: {len(com_par)} obra(s) com par, {provaveis} provavel(is); os pares estao nas excecoes")
    estacionadas = sum(e["estado"] == "estacionado" for e in etapas)
    if estacionadas:
        linhas.append(f"{estacionadas} obra(s) estacionada(s) esperam o dono (duplicata provavel): libere com "
                      f"`acervo pipeline --job {job['id']} --liberar <obra>` ou retire a obra com `acervo retirar biblioteca obra`")
    sem_promocao = sum(e["etapa"] == "promocao" and (e.get("detalhe") or {}).get("promovida") is False for e in etapas)
    if sem_promocao:
        linhas.append(f"promocao: {sem_promocao} obra(s) ainda sem promocao")
    esperando = sum(e["etapa"] == "classificar" and e["estado"] == "pausado" for e in etapas)
    if esperando:
        linhas.append(f"{esperando} obra(s) esperam a classificação da sessão: acervo catalogar biblioteca obra --job {job['id']}")
    if job.get("erro"):
        linhas.append(f"erro: {job['erro']}")
    linhas.append(f"excecoes: {pagina['total']} · parte {parte}/{pagina['partes']}")
    for e in pagina["itens"]:
        linhas.append(json.dumps(e, ensure_ascii=False, separators=(",", ":")))
        if e["estado"] == "estacionado":
            pares = [p for p in (e.get("detalhe") or {}).get("pares") or [] if p.get("classificacao") == "duplicata_provavel"]
            ao_lado = ", ".join(f"{p['obra_id']} (Jaccard {p['jaccard']})" if p.get("jaccard") is not None else p["obra_id"] for p in pares)
            linhas.append(f"  {e['obra_id']} ↔ {ao_lado}")
    if pagina["proxima_parte"]:
        linhas.append(f"continua: acervo pipeline --job {job['id']} --parte {pagina['proxima_parte']}")
    linhas.append(f"tabela inteira: {res['tabela']}")
    return "\n".join(linhas)

def medida_do_retorno(job: dict) -> dict:
    """Comparação pareada sobre o mesmo snapshot; mede texto servido, nunca uso do modelo."""
    from math import ceil
    from statistics import mean

    from tokenizador import conta_tokens

    total_partes = status_compacto(job)["excecoes"]["partes"]
    antes = json.dumps(job, ensure_ascii=False, indent=2)
    series = {"antes_json_integral": [antes] * total_partes,
              "depois_json": [json.dumps(status_compacto(job, n), ensure_ascii=False, indent=2)
                              for n in range(1, total_partes + 1)],
              "depois_texto": [resumo_do_job(job, n) for n in range(1, total_partes + 1)]}
    saida = {"job": job["id"], "tarefa": "status do job", "obras": len({e["obra_id"] for e in job.get("etapas") or []}),
             "escopo": "tokens do texto servido pela ferramenta; entrada, cache e saída do modelo não medidos",
             "series": {}}
    for nome, textos in series.items():
        medidas = [conta_tokens(t) for t in textos]
        valores = sorted(v for v, _ in medidas)
        saida["series"][nome] = {"chamadas": len(textos), "media": mean(valores),
                                "p90": valores[ceil(len(valores) * 0.9) - 1],
                                "bytes_media": mean(len(t.encode("utf-8")) for t in textos),
                                "metodo": medidas[0][1]}
    return saida
