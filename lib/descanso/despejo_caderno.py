"""Despejo único dos cadernos de hoje como mensagens no banco de eventos (#4355, F4269).

Lê `sessao.caderno_entrada` (com o histórico de `sessao.caderno_evento` no payload),
`sessao.caderno_aresta_uso` e `sessao.caderno_legado`, converte cada linha numa mensagem da
família `negocio.mensagem` e grava pela rota `POST /eventos/mensagem` em lotes de até 1.000.

Regras e travas da #4355:
- Grava sempre pela rota de escrita (nunca por psql direto no banco de eventos).
- O id da mensagem é o uuid v5 de `mensagem|<origem>` no namespace da esfera de negócio, o que
  torna a reexecução idempotente (0 inseridos na segunda passada).
- Etiqueta e destinatário só recebem chaves que existem na cópia declarada das chaves do
  fichário; referências sem ficha (chapéu da casa velha, termo livre de aresta, categoria e
  estado do caderno) ficam apenas no `payload`.
- O token (`EVENTOS_NEGOCIO_TOKEN`) entra apenas por ambiente ou stdin (`--token-stdin`), nunca
  em argv nem em log.
- Se o banco de eventos estiver mudo, para com erro (`BancoMudo`) sem fechar a rota do caderno.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

NAMESPACE_NEGOCIO = uuid.UUID("18e2a69a-4215-516c-8ee6-18dd0f185f62")
LOTE_MAXIMO = 1000
ENUNCIADO_MAXIMO = 32768
EVENTOS_API_PADRAO = "http://127.0.0.1:8111"
RE_CARD = re.compile(r"(?:#|\bcard:)(\d+)\b")


class BancoMudo(RuntimeError):
    """A rota de escrita do banco de eventos não respondeu ou devolveu erro transitório."""


class DespejoRecusado(RuntimeError):
    """A rota recusou um lote (409/422) ou a contagem gravada não bateu com a origem."""


def id_mensagem(origem: str) -> str:
    return str(uuid.uuid5(NAMESPACE_NEGOCIO, f"mensagem|{origem}"))


def _ts_iso(valor: Any) -> str:
    if isinstance(valor, datetime):
        d = valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    texto = str(valor or "").strip()
    if not texto:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _serializar(valor: Any) -> Any:
    if isinstance(valor, datetime):
        return _ts_iso(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {str(k): _serializar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_serializar(v) for v in valor]
    return valor


def _resolver_cadeira(cadeira: str | None, chaves: set[str]) -> str:
    bruto = (cadeira or "").strip()
    for candidato in (bruto, f"persona:{bruto}"):
        if candidato and candidato in chaves:
            return candidato
    raise DespejoRecusado(f"cadeira sem chave no fichário: {cadeira!r}")


def _resolver_chapeu(chapeu: str | None, chaves: set[str]) -> str | None:
    bruto = (chapeu or "").strip()
    if not bruto:
        return None
    for candidato in (f"chapeu:{bruto}", bruto):
        if candidato in chaves:
            return candidato
    return None


def _montar_cita(dito_onde: Any, dito_em: Any) -> str | None:
    partes = []
    if dito_onde is not None and str(dito_onde).strip():
        partes.append(str(dito_onde).strip())
    if dito_em is not None and str(dito_em).strip():
        partes.append(str(dito_em).strip())
    return " · ".join(partes)[:512] if partes else None


def _cards_no_caso(caso: Any) -> list[str]:
    if not caso:
        return []
    texto = str(caso).strip()
    if texto.isdigit():
        return [f"card:{texto}"]
    return sorted({f"card:{m.group(1)}" for m in RE_CARD.finditer(texto)})


def entrada_para_mensagem(
    entrada: dict[str, Any], eventos_da_entrada: list[dict[str, Any]], chaves: set[str]
) -> dict[str, Any]:
    origem = f"caderno_entrada|{entrada['id']}"
    dest = _resolver_cadeira(entrada.get("cadeira"), chaves)
    chapeu_chave = _resolver_chapeu(entrada.get("chapeu"), chaves)
    apoios = _cards_no_caso(entrada.get("caso"))

    etiquetas: set[str] = {dest}
    if chapeu_chave:
        etiquetas.add(chapeu_chave)
    for card in apoios:
        if card in chaves:
            etiquetas.add(card)
    for ponta in (entrada.get("de_ponta"), entrada.get("para_ponta")):
        if isinstance(ponta, str) and ponta.strip() in chaves:
            etiquetas.add(ponta.strip())

    texto = (entrada.get("texto") or "").strip()
    enunciado = texto[:ENUNCIADO_MAXIMO] if texto else f"entrada de caderno #{entrada['id']}"
    quem = (entrada.get("criada_por") or "").strip() or dest
    cita = _montar_cita(entrada.get("dito_onde"), entrada.get("dito_em"))

    ev: dict[str, Any] = {
        "evento_id": id_mensagem(origem),
        "ts": _ts_iso(entrada.get("criada_em")),
        "produtor": "despejo-caderno",
        "origem": origem,
        "enunciado": enunciado,
        "quem": quem[:512],
        "tipo_de_mensagem": "afirmacao",
        "sobre": chapeu_chave or dest,
        "destinatarios": [dest],
        "etiquetas": sorted(etiquetas),
        "apoios": apoios,
        "payload": {
            "tabela": "sessao.caderno_entrada",
            "linha": _serializar(entrada),
            "eventos": [_serializar(e) for e in eventos_da_entrada],
        },
    }
    if cita:
        ev["cita"] = cita
    return ev


def aresta_uso_para_mensagem(
    uso: dict[str, Any], entrada_ref: dict[str, Any] | None, chaves: set[str]
) -> dict[str, Any]:
    em_iso = _ts_iso(uso.get("em"))
    origem = f"caderno_aresta_uso|{uso['entrada_id']}|{uso.get('fita') or ''}|{em_iso}"
    cadeira_bruta = (entrada_ref or {}).get("cadeira") or uso.get("quem")
    dest = _resolver_cadeira(cadeira_bruta, chaves)
    chapeu_chave = _resolver_chapeu((entrada_ref or {}).get("chapeu"), chaves)

    etiquetas: set[str] = {dest}
    if chapeu_chave:
        etiquetas.add(chapeu_chave)
    if entrada_ref:
        for ponta in (entrada_ref.get("de_ponta"), entrada_ref.get("para_ponta")):
            if isinstance(ponta, str) and ponta.strip() in chaves:
                etiquetas.add(ponta.strip())

    de_p = (entrada_ref or {}).get("de_ponta")
    para_p = (entrada_ref or {}).get("para_ponta")
    if de_p and para_p:
        enunciado = f"uso da aresta {de_p} -> {para_p} (entrada #{uso['entrada_id']}, fita {uso.get('fita') or '-'})"
    else:
        enunciado = f"uso da aresta da entrada #{uso['entrada_id']} na fita {uso.get('fita') or '-'}"

    quem = (uso.get("quem") or "").strip() or dest
    ev: dict[str, Any] = {
        "evento_id": id_mensagem(origem),
        "ts": em_iso,
        "produtor": "despejo-caderno",
        "origem": origem,
        "enunciado": enunciado[:ENUNCIADO_MAXIMO],
        "quem": quem[:512],
        "tipo_de_mensagem": "afirmacao",
        "sobre": chapeu_chave or dest,
        "destinatarios": [dest],
        "etiquetas": sorted(etiquetas),
        "apoios": [],
        "payload": {
            "tabela": "sessao.caderno_aresta_uso",
            "linha": _serializar(uso),
        },
    }
    if uso.get("fita"):
        ev["correlacao"] = str(uso["fita"]).strip()[:512]
    return ev


def legado_para_mensagem(legado: dict[str, Any], chaves: set[str]) -> dict[str, Any]:
    origem = f"caderno_legado|{legado['chave_origem']}"
    dest = _resolver_cadeira(legado.get("cadeira"), chaves)
    chapeu_chave = _resolver_chapeu(legado.get("chapeu"), chaves)
    etiquetas: set[str] = {dest}
    if chapeu_chave:
        etiquetas.add(chapeu_chave)
    texto = (legado.get("texto") or "").strip()
    enunciado = texto[:ENUNCIADO_MAXIMO] if texto else f"seção de legado {legado['chave_origem']}"
    return {
        "evento_id": id_mensagem(origem),
        "ts": _ts_iso(legado.get("capturado_em")),
        "produtor": "despejo-caderno",
        "origem": origem,
        "enunciado": enunciado,
        "quem": dest,
        "tipo_de_mensagem": "afirmacao",
        "sobre": chapeu_chave or dest,
        "destinatarios": [dest],
        "etiquetas": sorted(etiquetas),
        "apoios": [],
        "payload": {
            "tabela": "sessao.caderno_legado",
            "linha": _serializar(legado),
        },
    }


def montar_mensagens(
    entradas: list[dict[str, Any]],
    eventos: list[dict[str, Any]],
    usos_aresta: list[dict[str, Any]],
    legados: list[dict[str, Any]],
    chaves: set[str],
) -> list[dict[str, Any]]:
    eventos_por_entrada: dict[Any, list[dict[str, Any]]] = {}
    for ev in eventos:
        eventos_por_entrada.setdefault(ev.get("entrada_id"), []).append(ev)
    entradas_por_id = {e["id"]: e for e in entradas}

    mensagens: list[dict[str, Any]] = []
    for ent in entradas:
        mensagens.append(entrada_para_mensagem(ent, eventos_por_entrada.get(ent["id"], []), chaves))
    for uso in usos_aresta:
        mensagens.append(aresta_uso_para_mensagem(uso, entradas_por_id.get(uso.get("entrada_id")), chaves))
    for leg in legados:
        mensagens.append(legado_para_mensagem(leg, chaves))
    return mensagens


class GravadorRotaHttp:
    """Envia lotes de até 1.000 mensagens para POST /eventos/mensagem."""

    def __init__(self, url: str = EVENTOS_API_PADRAO, token: str = "", timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout

    def gravar_lote(self, lote: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.token:
            raise BancoMudo("sem token da esfera de negócio (EVENTOS_NEGOCIO_TOKEN)")
        corpo = json.dumps({"eventos": lote}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/eventos/mensagem",
            data=corpo,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                detalhe = json.loads(erro.read().decode("utf-8"))
            except (OSError, ValueError):
                detalhe = {}
            if erro.code in (409, 422):
                raise DespejoRecusado(f"rota recusou lote ({erro.code}): {detalhe}") from None
            raise BancoMudo(f"rota respondeu {erro.code}: {detalhe or erro}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise BancoMudo(f"banco de eventos mudo ({self.url}): {erro}") from None


class OrigemSessaoDocker:
    """Lê as quatro tabelas do caderno no contêiner harness-sessao-db via psql JSON."""

    def __init__(self, conteiner: str = "harness-sessao-db", user: str = "sessao", dbname: str = "sessao"):
        self.conteiner = conteiner
        self.user = user
        self.dbname = dbname

    def _ler_tabela(self, sql: str) -> list[dict[str, Any]]:
        query = f"SELECT coalesce(json_agg(t), '[]'::json) FROM ({sql}) t"
        env = dict(os.environ)
        env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
        cp = subprocess.run(
            ["docker", "exec", "-i", self.conteiner, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
             "-U", self.user, "-d", self.dbname, "-tA", "-c", query],
            capture_output=True, text=True, check=False, env=env,
        )
        if cp.returncode != 0:
            raise RuntimeError(f"falha ao ler {self.conteiner}: {cp.stderr.strip()}")
        return json.loads(cp.stdout.strip() or "[]")

    def ler(self) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        entradas = self._ler_tabela("SELECT * FROM sessao.caderno_entrada ORDER BY id")
        eventos = self._ler_tabela("SELECT * FROM sessao.caderno_evento ORDER BY id")
        usos = self._ler_tabela("SELECT * FROM sessao.caderno_aresta_uso ORDER BY em, entrada_id")
        legados = self._ler_tabela("SELECT * FROM sessao.caderno_legado ORDER BY chave_origem")
        return entradas, eventos, usos, legados


def despejar(
    origem: Any,
    gravador: Any,
    chaves: set[str],
    *,
    tamanho_lote: int = LOTE_MAXIMO,
) -> dict[str, int]:
    """Lê todas as tabelas do caderno, converte e grava pela rota em lotes de até `tamanho_lote`."""
    if not 1 <= tamanho_lote <= LOTE_MAXIMO:
        raise ValueError(f"tamanho_lote fora de [1, {LOTE_MAXIMO}]: {tamanho_lote}")
    entradas, eventos, usos_aresta, legados = origem.ler()
    mensagens = montar_mensagens(entradas, eventos, usos_aresta, legados, chaves)
    esperado = len(entradas) + len(usos_aresta) + len(legados)
    assert len(mensagens) == esperado

    inseridos = 0
    existentes = 0
    for i in range(0, len(mensagens), tamanho_lote):
        lote = mensagens[i : i + tamanho_lote]
        resp = gravador.gravar_lote(lote)
        inseridos += len(resp.get("inseridos", []))
        existentes += len(resp.get("existentes", []))

    if inseridos + existentes != esperado:
        raise DespejoRecusado(
            f"contagem não bate: esperado {esperado}, gravado {inseridos} + existentes {existentes}"
        )
    return {
        "esperado": esperado,
        "entradas": len(entradas),
        "usos_aresta": len(usos_aresta),
        "legados": len(legados),
        "inseridos": inseridos,
        "existentes": existentes,
    }


def _carregar_chaves(caminho: Path) -> set[str]:
    dado = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(dado, dict) and isinstance(dado.get("chaves"), list):
        return {str(c) for c in dado["chaves"]}
    if isinstance(dado, list):
        return {str(c) for c in dado}
    raise ValueError(f"formato de chaves inválido em {caminho}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Despejo único dos cadernos como mensagens no banco de eventos.")
    parser.add_argument("--url", default=os.environ.get("EVENTOS_API_URL", EVENTOS_API_PADRAO))
    parser.add_argument("--chaves", default="/srv/platafirma/casa/var/eventos/chaves.json")
    parser.add_argument("--lote", type=int, default=LOTE_MAXIMO)
    parser.add_argument("--token-stdin", action="store_true", help="lê EVENTOS_NEGOCIO_TOKEN da entrada padrão")
    args = parser.parse_args(argv)

    token = sys.stdin.read().strip() if args.token_stdin else (os.environ.get("EVENTOS_NEGOCIO_TOKEN") or "").strip()
    if not token:
        print("despejo_caderno: falta EVENTOS_NEGOCIO_TOKEN (ambiente ou --token-stdin)", file=sys.stderr)
        return 2
    chaves = _carregar_chaves(Path(args.chaves))
    origem = OrigemSessaoDocker()
    gravador = GravadorRotaHttp(url=args.url, token=token)
    try:
        resumo = despejar(origem, gravador, chaves, tamanho_lote=args.lote)
    except BancoMudo as erro:
        print(f"despejo_caderno: {erro}", file=sys.stderr)
        return 3
    except DespejoRecusado as erro:
        print(f"despejo_caderno: {erro}", file=sys.stderr)
        return 2
    print(json.dumps(resumo, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
