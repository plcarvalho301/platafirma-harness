"""varrer_balde — `acervo balde varrer <colecao> [--limite <n>] [--retomar] [--prefixo <p>] [--teto-s <n>]
[--json]` (card #3468; ordem do dono de 04/10/2026: lote é fila durável desde o primeiro commit).

O que faz: lê, um por vez, cada objeto do balde, calcula o sha256 do que leu e compara com a chave. Só leitura:
não grava no balde nem no catálogo de obras; o que escreve é a própria fila, em acervo.varredura_balde e
acervo.varredura_balde_objeto (migração 099 de platafirma-conhecimento).

Por que lê o MinIO e não a rota do motor: `GET /acervo/objetos/{sha256}` devolve os metadados (`stat_object`) e
«nunca os bytes» (rotas_lotes.py); só a leitura dos bytes prova o conteúdo, e a listagem da rota corta em 1000
itens sem aviso (`lotes.listar_objetos_bucket(limite=1000)`). Aqui a listagem é paginada e a leitura é em blocos de
1 MiB, sem gravar nada em disco. O mesmo caminho de `acervo ler biblioteca objeto`: credencial do container
(`docker inspect`, nunca impressa) e boto3 do venv acervo.

A fila é o banco (a preferência do dono): cada objeto é uma linha com alvo, executor, estado, início, fim e causa.
O executor reivindica o próximo `pendente` com FOR UPDATE SKIP LOCKED e só fecha a linha que ainda é dele; quem
sobe de novo (`--retomar`) devolve à fila o `em_voo` de executor morto (mesma máquina e pid que não existe, ou
lease vencido) e segue de onde parou; o resumo sai das linhas, nunca da memória do processo.

Um objeto por vez, sempre: a varredura disputa disco com o lote de transcrição, e um executor vivo de outra
chamada recusa esta (exit 5).

estados do objeto: pendente · em_voo · ok · ilegivel (a leitura falhou ou passou do teto) · divergente (sha256 do
conteúdo ≠ chave) · ausente (a listagem o tinha, a leitura disse que não existe) · sem_comparacao (a chave não é
sha256 em hex: lido inteiro, não comparado).

exit: 0 tudo olhado e ok · 1 há ilegível, divergente ou ausente · 2 uso · 5 não foi possível olhar tudo (sobrou
pendente, store ou banco fora, interrompida, balde sem objeto): nunca 0 quando não olhou.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

PG, DB, USR = "rag-extractor-pg", "rag_extractor", "rag"
MINIO, MINIO_ENDPOINT = "rag-extractor-minio", "http://127.0.0.1:9000"
BUCKET_DA_COLECAO = {"firma": "acervo", "pessoal": "pessoal"}
BLOCO = 1 << 20
TETO_OBJETO_S = 300          # por objeto: passou disto, o objeto é ilegível (causa: prazo)
LEITURA_S = 30               # espera por bloco, no socket
CONEXAO_S = 5
MARGEM_LEASE_S = 60          # o lease do item em voo é o teto do objeto mais esta margem
TETO_PSQL_S = 300
MIGRACAO = "099_varredura_balde.sql"
_agora = time.monotonic      # o teste o troca
_maquina = socket.gethostname

SAIDA_OK, SAIDA_PROBLEMA, SAIDA_USO, SAIDA_NAO_OLHOU = 0, 1, 2, 5
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

USO = """uso: acervo balde varrer <colecao> [--limite <n>] [--retomar] [--prefixo <p>] [--teto-s <n>] [--json]
  <colecao>     firma (bucket acervo) ou pessoal
  --limite <n>  lê no máximo n objetos nesta chamada; os demais ficam pendentes (e a chamada nunca sai 0)
  --retomar     segue a varredura aberta da coleção: o que já foi lido não se lê de novo, o que estava em voo
                de executor morto volta à fila. Sem a flag, uma varredura nova (a aberta é abandonada)
  --prefixo <p> só as chaves que começam por <p>
  --teto-s <n>  teto de tempo por objeto, em segundos (padrão 300); passou, o objeto é ilegível
  --json        o resumo e os problemas em JSON
SÓ LEITURA, um objeto por vez. A primeira linha é o resumo (N lidos, n ok, n ilegíveis, n divergentes,
n ausentes); depois, uma linha por problema com chave, bytes e causa.
exit: 0 tudo ok · 1 há problema · 2 uso · 5 não foi possível olhar tudo (nunca 0 quando não olhou)
"""


class ObjetoAusente(Exception):
    """A listagem tinha o objeto e a leitura diz que ele não existe."""


class ObjetoIlegivel(Exception):
    """A leitura do objeto falhou, parou no meio ou passou do teto: o achado, não a falha da varredura."""


class FonteFora(Exception):
    """O store ou o banco não responderam: não foi possível olhar. Nunca vira achado sobre um objeto."""


class Parou(Exception):
    """O armazém caiu no meio da varredura: o item voltou à fila e o laço para."""


class Encerra(Exception):
    """A varredura não pôde começar: o exit e a mensagem de quem recusou."""

    def __init__(self, codigo: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass(frozen=True)
class Achado:
    """O que a leitura de um objeto concluiu, como a fila o guarda."""

    estado: str
    causa: str | None = None
    bytes_lidos: int | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class Pedido:
    """O que a chamada pediu."""

    colecao: str
    retomar: bool
    prefixo: str
    teto_s: int
    quem: str
    executor: str
    quero_json: bool
    limite: int | None = None


# --- o mundo de fora: banco (psql no container) e store (MinIO por boto3) -------------------------

def _env_docker() -> dict:
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    return env


def _psql(sql: str, timeout: int = TETO_PSQL_S) -> str:
    """Roda o script no rag-extractor-pg (stdin) e devolve o stdout. Falha é FonteFora, com a causa."""
    try:
        p = subprocess.run(["docker", "exec", "-i", PG, "psql", "-U", USR, "-d", DB, "-qtA", "-v", "ON_ERROR_STOP=1"],
                           input=sql, capture_output=True, text=True, env=_env_docker(), timeout=timeout,
                           check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise FonteFora(f"{PG}: {type(e).__name__}: {e}") from e
    if p.returncode != 0:
        linhas = (p.stderr or p.stdout or f"psql saiu {p.returncode}").strip().splitlines()
        msg = linhas[0] if linhas else f"psql saiu {p.returncode}"
        if "does not exist" in msg and "varredura_balde" in msg:
            raise FonteFora(f"as tabelas da varredura não existem no banco rag: aplique a migração {MIGRACAO} "
                            f"(`release migrar aplicar rag`, platafirma-conhecimento/rag/db/init) — {msg}")
        raise FonteFora(f"{PG}: {msg}")
    return p.stdout


def _credenciais_do_minio() -> dict:
    """USER e PASSWORD do container do MinIO, lidos do ambiente dele. Nunca saem daqui: nem na mensagem de erro."""
    chaves = {"MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"}
    try:
        saida = subprocess.run(["docker", "inspect", MINIO, "--format", "{{json .Config.Env}}"],
                               capture_output=True, text=True, check=True, timeout=30, env=_env_docker()).stdout
        ambiente = json.loads(saida)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        raise FonteFora(f"credencial do store: docker inspect {MINIO} falhou ({type(e).__name__})") from e
    achado = {}
    for linha in ambiente if isinstance(ambiente, list) else []:
        k, _, v = str(linha).partition("=")
        if k in chaves:
            achado[k] = v
    if chaves - set(achado):
        raise FonteFora(f"credencial ausente em {MINIO}: {sorted(chaves - set(achado))}")
    return achado


def _codigo_s3(e: BaseException) -> tuple:
    """(Code, Message) do erro do cliente S3, ou (None, '') se o erro não é de resposta do store."""
    resp = getattr(e, "response", None)
    err = resp.get("Error") if isinstance(resp, dict) else None
    if isinstance(err, dict) and err.get("Code"):
        return str(err["Code"]), str(err.get("Message") or "")
    return None, ""


# o que não é do objeto: o store inalcançável ou a credencial que ele recusa. Não vira «ilegível».
_CODIGOS_DO_STORE = ("NoSuchBucket", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch")
_ERROS_DE_CONEXAO = ("EndpointConnectionError", "ConnectTimeoutError")


def _classificar(e: BaseException) -> Exception:
    """O erro de leitura como achado (ObjetoAusente, ObjetoIlegivel) ou como falha da fonte (FonteFora)."""
    codigo, mensagem = _codigo_s3(e)
    if type(e).__name__ in _ERROS_DE_CONEXAO:
        return FonteFora(f"{type(e).__name__}: {str(e)[:200]}")
    if codigo in ("NoSuchKey", "404", "NotFound"):
        return ObjetoAusente(f"{codigo}: {mensagem}".rstrip(": "))
    if codigo in _CODIGOS_DO_STORE:
        return FonteFora(f"{codigo}: {mensagem}".rstrip(": "))
    if codigo:
        return ObjetoIlegivel(f"{codigo}: {mensagem}".rstrip(": "))
    return ObjetoIlegivel(f"{type(e).__name__}: {str(e)[:200]}")


class Armazem:
    """O que a varredura pede ao MinIO: `listar` (paginado, sem o corte de 1000 da rota) e `ler` (em blocos, com
    teto de tempo, sem gravar em disco). `cliente` troca o boto3 no teste."""

    def __init__(self, cliente: object = None) -> None:
        self._s3 = cliente

    def _cliente(self) -> object:
        if self._s3 is None:
            try:
                import boto3  # só o venv acervo da release tem
                from botocore.config import Config
            except ImportError as e:
                raise FonteFora("boto3 ausente neste python: rode pelo venv acervo da release "
                                "(`acervo balde varrer` já o escolhe)") from e
            cred = _credenciais_do_minio()
            self._s3 = boto3.client(
                "s3", endpoint_url=MINIO_ENDPOINT, aws_access_key_id=cred["MINIO_ROOT_USER"],
                aws_secret_access_key=cred["MINIO_ROOT_PASSWORD"],
                config=Config(connect_timeout=CONEXAO_S, read_timeout=LEITURA_S,
                              retries={"total_max_attempts": 1}, s3={"addressing_style": "path"}))
        return self._s3

    def listar(self, bucket: str, prefixo: str = "") -> Iterator[tuple]:
        """(chave, bytes) de cada objeto, na ordem do store."""
        try:
            paginas = self._cliente().get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefixo)
            for pagina in paginas:
                for o in pagina.get("Contents", []):
                    yield o["Key"], int(o["Size"])
        except FonteFora:
            raise
        except Exception as e:
            raise FonteFora(f"listagem do bucket {bucket}: {type(e).__name__}: {str(e)[:200]}") from e

    def ler(self, bucket: str, chave: str, teto_s: int) -> tuple:
        """(sha256 em hex, bytes) do conteúdo. ObjetoAusente, ObjetoIlegivel (inclui o prazo) ou FonteFora."""
        corpo = None
        try:
            limite = _agora() + teto_s
            corpo = self._cliente().get_object(Bucket=bucket, Key=chave)["Body"]
            soma, n = hashlib.sha256(), 0
            for bloco in corpo.iter_chunks(BLOCO):
                soma.update(bloco)
                n += len(bloco)
                if _agora() > limite:
                    raise ObjetoIlegivel(f"prazo de {teto_s} s esgotado após {n} bytes lidos")
            return soma.hexdigest(), n
        except (ObjetoIlegivel, FonteFora):
            raise
        except Exception as e:  # toda falha de leitura é classificada, nenhuma vira traceback
            raise _classificar(e) from e
        finally:
            if corpo is not None:
                corpo.close()


# --- a fila: o banco -----------------------------------------------------------------------------

def _lit(v: object) -> str:
    """Literal SQL de texto (standard_conforming_strings ligado: só o apóstrofo se dobra)."""
    return "null" if v is None else "'" + str(v).replace("\x00", "").replace("'", "''") + "'"


def _num(v: object) -> str:
    return "null" if v is None else str(int(v))


def _uuid(v: object) -> str:
    if not UUID_RE.match(str(v)):
        raise FonteFora(f"id de varredura fora da forma: {str(v)[:60]!r}")
    return f"'{v}'::uuid"


def _tag(*cargas: str) -> str:
    """Etiqueta de dollar-quote que não aparece em nenhuma das cargas."""
    n = 0
    while any(f"$v{n}$" in c for c in cargas):
        n += 1
    return f"$v{n}$"


class FilaPg:
    """A fila de execução em acervo.varredura_balde_objeto (migração 099). `psql` troca o container no teste."""

    def __init__(self, psql: object = None) -> None:
        self._psql = psql or _psql

    def _json(self, sql: str) -> object:
        """A última linha da saída, decodificada. Por isso toda consulta devolve `jsonb`: `json_agg` põe quebra
        de linha entre os elementos, e a última linha não seria o resultado inteiro."""
        saida = self._psql("set standard_conforming_strings = on;\n" + sql)
        linhas = [x for x in saida.splitlines() if x.strip()]
        if not linhas:
            return None
        try:
            return json.loads(linhas[-1])
        except ValueError as e:
            raise FonteFora(f"{PG}: resposta que não é json: {linhas[-1][:80]!r}") from e

    def aberta(self, colecao: str) -> str | None:
        """O id da varredura aberta da coleção, ou None."""
        r = self._json(f"select to_json(id::text) from acervo.varredura_balde "
                       f"where colecao = {_lit(colecao)} and estado = 'aberta'")
        return r or None

    def abrir(self, colecao: str, prefixo: str, quem: str, itens: list) -> tuple:
        """Abandona a aberta da coleção e enfileira `itens` [(chave, bytes)] numa varredura nova.
        Devolve (id da nova, [ids abandonados])."""
        abandonadas = self._json(
            "with a as (update acervo.varredura_balde set estado = 'abandonada', concluida_em = now() "
            "where id in (select id from acervo.varredura_balde "
            f"where colecao = {_lit(colecao)} and estado = 'aberta' for update) returning id::text) "
            "select coalesce(jsonb_agg(id), '[]'::jsonb) from a") or []
        carga = json.dumps([{"posicao": i, "chave": c, "bytes": n} for i, (c, n) in enumerate(itens, start=1)],
                           ensure_ascii=False)
        tag = _tag(carga)
        r = self._json(
            "with v as (insert into acervo.varredura_balde (colecao, prefixo, criada_por) "
            f"values ({_lit(colecao)}, {_lit(prefixo)}, {_lit(quem)}) returning id), "
            "i as (insert into acervo.varredura_balde_objeto (varredura_id, posicao, chave, bytes) "
            "select v.id, x.posicao, x.chave, x.bytes "
            f"from v, json_to_recordset({tag}{carga}{tag}::json) as x(posicao int, chave text, bytes bigint) "
            "returning 1) "
            "select jsonb_build_object('id', (select id::text from v), 'itens', (select count(*) from i))")
        if not r or r.get("itens") != len(itens):
            raise FonteFora(f"enfileirei {(r or {}).get('itens')} de {len(itens)} objetos: varredura não aberta")
        return r["id"], abandonadas

    def em_voo(self, vid: str) -> list:
        return self._json(
            "select coalesce(jsonb_agg(jsonb_build_object('chave', chave, 'executor', executor, "
            "'idade_s', extract(epoch from now() - iniciado_em)::int)), '[]'::jsonb) "
            f"from acervo.varredura_balde_objeto where varredura_id = {_uuid(vid)} and estado = 'em_voo'") or []

    def reivindicar(self, vid: str, executor: str) -> tuple | None:
        """O próximo pendente, já em voo e deste executor: (chave, bytes) ou None. SKIP LOCKED: dois executores
        nunca pegam o mesmo item."""
        r = self._json(
            "with alvo as (select varredura_id, chave from acervo.varredura_balde_objeto "
            f"where varredura_id = {_uuid(vid)} and estado = 'pendente' order by posicao limit 1 "
            "for update skip locked) "
            "update acervo.varredura_balde_objeto o set estado = 'em_voo', "
            f"executor = {_lit(executor)}, iniciado_em = now() "
            "from alvo where o.varredura_id = alvo.varredura_id and o.chave = alvo.chave "
            "returning jsonb_build_object('chave', o.chave, 'bytes', o.bytes)")
        return (r["chave"], r["bytes"]) if r else None

    def fechar(self, vid: str, chave: str, executor: str, achado: Achado) -> bool:
        """Grava o fim do item, só se ele ainda é deste executor e segue em voo."""
        r = self._json(
            "with alvo as (select varredura_id, chave from acervo.varredura_balde_objeto "
            f"where varredura_id = {_uuid(vid)} and chave = {_lit(chave)} and estado = 'em_voo' "
            f"and executor = {_lit(executor)} for update) "
            f"update acervo.varredura_balde_objeto o set estado = {_lit(achado.estado)}, "
            f"causa = {_lit(achado.causa)}, bytes_lidos = {_num(achado.bytes_lidos)}, "
            f"sha256_lido = {_lit(achado.sha256)}, terminado_em = now() "
            "from alvo where o.varredura_id = alvo.varredura_id and o.chave = alvo.chave returning 1")
        return bool(r)

    def devolver(self, vid: str, chave: str, executor: str, *, contar: bool = False) -> bool:
        """O item em voo volta à fila. `contar`: a devolução é de executor que morreu com ele."""
        r = self._json(
            "with alvo as (select varredura_id, chave from acervo.varredura_balde_objeto "
            f"where varredura_id = {_uuid(vid)} and chave = {_lit(chave)} and estado = 'em_voo' "
            f"and executor = {_lit(executor)} for update) "
            "update acervo.varredura_balde_objeto o set estado = 'pendente', executor = null, iniciado_em = null, "
            f"devolucoes = o.devolucoes + {1 if contar else 0} "
            "from alvo where o.varredura_id = alvo.varredura_id and o.chave = alvo.chave returning 1")
        return bool(r)

    def concluir(self, vid: str) -> None:
        """Fecha a varredura se não sobrou pendente nem em voo."""
        self._psql(
            "update acervo.varredura_balde v set estado = 'concluida', concluida_em = now() "
            f"where v.id in (select id from acervo.varredura_balde where id = {_uuid(vid)} "
            "and estado = 'aberta' for update) "
            "and not exists (select 1 from acervo.varredura_balde_objeto o "
            "where o.varredura_id = v.id and o.estado in ('pendente', 'em_voo'));")

    def resumo(self, vid: str) -> dict:
        """O estado da varredura, tirado das linhas: contagem por estado e os problemas, na ordem da listagem."""
        r = self._json(
            "select jsonb_build_object('varredura', v.id::text, 'colecao', v.colecao, 'prefixo', v.prefixo, "
            "'estado', v.estado, "
            "'contagem', (select coalesce(jsonb_object_agg(estado, n), '{}'::jsonb) from "
            "(select estado, count(*) as n from acervo.varredura_balde_objeto "
            "where varredura_id = v.id group by estado) c), "
            "'problemas', (select coalesce(jsonb_agg(jsonb_build_object('estado', estado, 'chave', chave, "
            "'bytes', coalesce(bytes_lidos, bytes), 'causa', causa) order by posicao), '[]'::jsonb) "
            "from acervo.varredura_balde_objeto "
            "where varredura_id = v.id and estado in ('ilegivel', 'divergente', 'ausente'))) "
            f"from acervo.varredura_balde v where v.id = {_uuid(vid)}")
        if not r:
            raise FonteFora(f"varredura {vid} não encontrada no banco")
        return r


# --- a varredura ---------------------------------------------------------------------------------

def _pid_existe(pid: int) -> bool:
    return os.path.exists(f"/proc/{pid}")


def _executor_morto(executor: str | None, idade_s: int | None, lease_s: int) -> bool:
    """O executor `host:pid:marca` morreu? Na mesma máquina vale o pid; de outra, o lease vencido."""
    host, _, resto = str(executor or "").partition(":")
    pid = resto.partition(":")[0]
    if host == _maquina() and pid.isdigit():
        return not _pid_existe(int(pid))
    return idade_s is None or idade_s > lease_s


def _recolher_orfaos(fila: FilaPg, vid: str, lease_s: int) -> tuple | None:
    """Devolve à fila o item em voo de executor morto. O que sobra é executor vivo de outra chamada:
    devolve (executor, idade_s) do primeiro, ou None."""
    vivo = None
    for r in fila.em_voo(vid):
        if _executor_morto(r["executor"], r["idade_s"], lease_s):
            fila.devolver(vid, r["chave"], r["executor"], contar=True)
        elif vivo is None:
            vivo = (r["executor"], r["idade_s"])
    return vivo


def _olhar(armazem: Armazem, bucket: str, chave: str, teto_s: int) -> Achado:
    """O que a leitura do objeto concluiu. O armazém fora é `Parou`, não achado."""
    try:
        soma, n = armazem.ler(bucket, chave, teto_s)
    except ObjetoAusente as e:
        return Achado("ausente", str(e))
    except ObjetoIlegivel as e:
        return Achado("ilegivel", str(e))
    except FonteFora as e:
        raise Parou(str(e)) from e
    if not SHA256.match(chave):
        causa = f"chave não é sha256 em hex: lido inteiro ({n} bytes), não comparado (sha256 lido {soma})"
        return Achado("sem_comparacao", causa, n, soma)
    if soma != chave.lower():
        return Achado("divergente", f"sha256 do conteúdo {soma} ≠ chave", n, soma)
    return Achado("ok", None, n, soma)


def _quem() -> str:
    """Quem abriu a varredura: `<cadeira>/<sujeito>@<sessão>`, do que a porta injeta."""
    cadeira = (os.environ.get("PF_CADEIRA") or os.environ.get("PF_CONTA") or "").strip().lower()
    for prefixo in ("claudinho-", "claudinha-"):
        cadeira = cadeira.removeprefix(prefixo)
    sujeito = os.environ.get("PF_SUJEITO", "").strip()
    sessao = (os.environ.get("PF_SESSAO") or os.environ.get("PF_SESSAO_ID") or "").strip()
    return f"{cadeira or '-'}/{sujeito[:8] or '-'}@{sessao[:8] or '-'}"


def _abrir(armazem: Armazem, fila: FilaPg, p: Pedido) -> str:
    """O id da varredura a rodar (a aberta, ou uma nova com a listagem de agora), com os órfãos já devolvidos."""
    bucket = BUCKET_DA_COLECAO[p.colecao]
    if p.retomar:
        vid = fila.aberta(p.colecao)
        if vid is None:
            raise Encerra(SAIDA_USO, f"acervo balde varrer: nenhuma varredura aberta para {p.colecao}; "
                                     "rode sem --retomar")
    else:
        itens = list(armazem.listar(bucket, p.prefixo))
        if not itens:
            raise Encerra(SAIDA_NAO_OLHOU, f"balde {p.colecao} (bucket {bucket}, prefixo {p.prefixo!r}) "
                                           "sem objeto: nada olhado")
        vid, abandonadas = fila.abrir(p.colecao, p.prefixo, p.quem, itens)
        for antiga in abandonadas:
            sys.stderr.write(f"varredura {antiga[:8]} abandonada: a nova começa do zero "
                             "(--retomar segue a aberta)\n")
    lease_s = p.teto_s + MARGEM_LEASE_S
    vivo = _recolher_orfaos(fila, vid, lease_s)
    if vivo is not None:
        raise Encerra(SAIDA_NAO_OLHOU, f"acervo balde varrer: o executor {vivo[0]} está lendo esta varredura há "
                                       f"{vivo[1]} s; um objeto por vez, nunca dois executores. Espere o lease "
                                       f"({lease_s} s) ou o fim dele e repita com --retomar")
    return vid


def _olhar_e_fechar(armazem: Armazem, fila: FilaPg, vid: str, chave: str, p: Pedido) -> None:
    try:
        achado = _olhar(armazem, BUCKET_DA_COLECAO[p.colecao], chave, p.teto_s)
    except BaseException:   # Parou e a interrupção: o item não foi olhado, volta à fila sem culpa
        fila.devolver(vid, chave, p.executor)
        raise
    if not fila.fechar(vid, chave, p.executor, achado):
        sys.stderr.write(f"aviso: {chave} já não era deste executor ao fechar; o resultado ficou com quem o tem\n")


def _laco(armazem: Armazem, fila: FilaPg, vid: str, p: Pedido) -> tuple:
    """Lê um objeto por vez até a fila acabar, o `--limite` chegar, o armazém cair ou vir a interrupção.
    Devolve (causa da parada do armazém ou None, interrompida)."""
    lidos = 0
    try:
        while p.limite is None or lidos < p.limite:
            item = fila.reivindicar(vid, p.executor)
            if item is None:
                break
            _olhar_e_fechar(armazem, fila, vid, item[0], p)
            lidos += 1
    except Parou as e:
        return str(e), False
    except KeyboardInterrupt:
        return None, True
    return None, False


def _formatar(r: dict, bucket: str, pendentes: int) -> list:
    c = r["contagem"]
    ok, ileg, div, aus, sem = (c.get(k, 0) for k in ("ok", "ilegivel", "divergente", "ausente", "sem_comparacao"))
    primeira = (f"balde {r['colecao']}: {ok + ileg + div + aus + sem} lidos, {ok} ok, {ileg} ilegíveis, "
                f"{div} divergentes, {aus} ausentes")
    if sem:
        primeira += f", {sem} sem comparação"
    if pendentes:
        primeira += f" · restam {pendentes} pendentes"
    linhas = [primeira + f" · varredura {r['varredura'][:8]}"]
    if sem:
        linhas.append(f"nota: {sem} objeto(s) com chave que não é sha256 em hex: lido(s) inteiro(s) e "
                      "não comparada(s) ao conteúdo")
    for p in r["problemas"]:
        tam = f"{p['bytes']} B" if p.get("bytes") is not None else "? B"
        linhas.append(f"  {p['estado']:<10} {bucket}/{p['chave']}  {tam}  {p.get('causa') or ''}".rstrip())
    return linhas


def _apresentar(r: dict, p: Pedido, parada: str | None, *, interrompida: bool) -> int:
    bucket = BUCKET_DA_COLECAO[p.colecao]
    c = r["contagem"]
    pendentes = c.get("pendente", 0) + c.get("em_voo", 0)
    incompleta = bool(pendentes or parada or interrompida)
    codigo = SAIDA_PROBLEMA if r["problemas"] else (SAIDA_NAO_OLHOU if incompleta else SAIDA_OK)
    if p.quero_json:
        print(json.dumps({**r, "bucket": bucket, "pendentes": pendentes, "parada": parada,
                          "interrompida": interrompida, "codigo": codigo}, ensure_ascii=False, indent=2))
    else:
        print("\n".join(_formatar(r, bucket, pendentes)))
    if parada:
        sys.stderr.write(f"parei: {parada}; o item voltou à fila, repita com --retomar\n")
    if interrompida:
        sys.stderr.write("varredura interrompida: o item em voo voltou à fila; repita com --retomar\n")
    return codigo


def varrer(armazem: Armazem, fila: FilaPg, p: Pedido) -> int:
    try:
        vid = _abrir(armazem, fila, p)
        parada, interrompida = _laco(armazem, fila, vid, p)
        fila.concluir(vid)
        r = fila.resumo(vid)
    except Encerra as e:
        sys.stderr.write(f"{e}\n")
        return e.codigo
    except FonteFora as e:
        sys.stderr.write(f"indeterminável: {e}\n")
        return SAIDA_NAO_OLHOU
    return _apresentar(r, p, parada, interrompida=interrompida)


def main(argv: list, *, armazem: Armazem | None = None, fila: FilaPg | None = None,
         executor: str | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acervo balde varrer", add_help=False)
    parser.add_argument("colecao", nargs="?")
    parser.add_argument("--limite", type=int)
    parser.add_argument("--retomar", action="store_true")
    parser.add_argument("--prefixo", default="")
    parser.add_argument("--teto-s", dest="teto_s", type=int, default=TETO_OBJETO_S)
    parser.add_argument("--json", dest="quero_json", action="store_true")
    parser.add_argument("-h", "--help", "--ajuda", dest="ajuda", action="store_true")
    try:
        a, resto = parser.parse_known_args(argv)
    except SystemExit:
        sys.stderr.write(USO)
        return SAIDA_USO
    if a.ajuda:
        sys.stdout.write(USO)
        return SAIDA_OK
    if resto or a.colecao not in BUCKET_DA_COLECAO or (a.limite is not None and a.limite < 1) or a.teto_s < 1:
        sys.stderr.write((f"argumento desconhecido: {' '.join(resto)}\n" if resto else "") + USO)
        return SAIDA_USO
    pedido = Pedido(colecao=a.colecao, retomar=a.retomar, prefixo=a.prefixo, teto_s=a.teto_s, quem=_quem(),
                    executor=executor or f"{_maquina()}:{os.getpid()}:{uuid.uuid4().hex[:8]}",
                    quero_json=a.quero_json, limite=a.limite)
    return varrer(armazem or Armazem(), fila or FilaPg(), pedido)


def _termina(*_: object) -> None:
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _termina)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main(sys.argv[1:]))
