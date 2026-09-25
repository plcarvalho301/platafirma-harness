"""Adaptador do registro de decisão — `adr:` · `seg:` · `ont:` · `infra:` · `integracao:` ·
`org:`.

`spec_recuperador.md` §5: contrato = a tabela `acervo.casa` do suporte platafirma-casa;
carimbo = sha da última ingestão (`acervo.casa_fonte`); classe exata. §4: `chave =
<serie>:<NNNN>`, versão = sha da linha (`acervo.casa.sha`, o mesmo que `acervo ler casa`
serve como "servido").

**Morada única, desde arq:0111/arq:0115.** As seis séries do registro setorial da
PlataFirma moram todas no suporte `platafirma-casa`, espécie `adr`, distinguidas pela
coluna `serie`: `adr/arq/` (canônico) e `adr/<serie>/` para `seg`, `ont`, `infra`,
`integracao`, `org`. Não há mais leitura por caminho de repositório (`platafirma-arquitetura`
saiu do inventário do release na Frente 1 do rescaldo #3115) — a fonte é a tabela, lida do
mesmo jeito que todo `acervo casa` lê: `docker exec` no container do Postgres do acervo
(`recuperacao/adaptadores/base.py` §"ao contrato da fonte, nunca ao binário" — o contrato
aqui é o schema `acervo.casa`, o mesmo que `bin/_acervo/casa` consulta, não a saída de
texto do CLI).

Antes desta versão, o adaptador lia arquivo por caminho de release
(`<release>/arquitetura/macro-global/decisions/`, `.../capabilities/seguranca/decisions/`,
`<release>/conhecimento/ontologia/adr/`) — desenho anterior a arq:0111/0115, que ficou
quebrado (`FonteIndisponivel`) assim que a Frente 1 retirou `platafirma-arquitetura` do
inventário do release. Achado e corrigido no card #3138.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess

from ..envelope import Causa, Item, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

# Runtime lê a tabela `acervo.casa` (rag_extractor, schema acervo) pelo mesmo caminho que
# `platafirma-harness/bin/_acervo/casa` usa: `docker exec` no container do Postgres do
# acervo. Não há credencial de rede aqui — é o mesmo socket local que todo verbo `acervo`
# já usa nesta máquina.
PG_CONTAINER = os.environ.get("ACERVO_PG_CONTAINER", "rag-extractor-pg")
PG_DB = os.environ.get("ACERVO_PG_DB", "rag_extractor")
PG_USER = os.environ.get("ACERVO_PG_USER", "rag")
PG_TIMEOUT_S = float(os.environ.get("ACERVO_PG_TIMEOUT_S", "10"))

SUPORTE = "platafirma-casa"
ESPECIE = "adr"

# arq:0111 §1: alcance = `arq` (canônico) e os setoriais `seg`, `ont`, `infra`,
# `integracao`, `org`. `mdm` e `plat` não entram (não são arquitetura da plataforma).
SERIES = ("arq", "seg", "ont", "infra", "integracao", "org")

CHAVE_RE = re.compile(r"^(" + "|".join(SERIES) + r"):(\d{1,4})$", re.IGNORECASE)


def _lit(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


class AdaptadorRegistro(Adaptador):
    fonte = Fonte.REGISTRO
    tem_gold = False

    def __init__(self, pg_container: str = PG_CONTAINER, pg_db: str = PG_DB,
                 pg_user: str = PG_USER, timeout_s: float = PG_TIMEOUT_S) -> None:
        self.pg_container, self.pg_db, self.pg_user = pg_container, pg_db, pg_user
        self.timeout_s = timeout_s

    # ---- transporte -------------------------------------------------------------

    def _psql(self, sql: str) -> str:
        """Uma consulta, texto cru (`-tAq`). Container inalcançável ou comando ausente
        vira `SEM_ROTA`; psql que roda e falha (SQL, banco fora) vira `FORA_DO_AR` — a
        mesma distinção que `AdaptadorAcervo` faz para a API do rag."""
        env = dict(os.environ)
        env.setdefault("DOCKER_HOST", "unix:///run/user/1001/docker.sock")
        try:
            p = subprocess.run(
                ["docker", "exec", "-i", self.pg_container, "psql", "-U", self.pg_user,
                 "-d", self.pg_db, "-tAq", "-v", "ON_ERROR_STOP=1", "-c", sql],
                capture_output=True, timeout=self.timeout_s, env=env)
        except subprocess.TimeoutExpired as e:
            raise FonteIndisponivel(Causa.TIMEOUT, str(e)) from e
        except (OSError, subprocess.SubprocessError) as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, f"docker exec {self.pg_container}: {e}") from e
        if p.returncode != 0:
            erro = p.stderr.decode("utf-8", "replace").strip()[:200]
            causa = Causa.SEM_ROTA if "No such container" in erro else Causa.FORA_DO_AR
            raise FonteIndisponivel(causa, erro) from None
        return p.stdout.decode("utf-8", "replace").strip()

    def _psql_json(self, sql: str):
        saida = self._psql(sql)
        if not saida:
            return None
        try:
            return json.loads(saida)
        except ValueError as e:
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"psql devolveu json ilegível: {e}") from e

    # ---- carimbo ------------------------------------------------------------------

    def _carimbo(self) -> str:
        """Sha da última ingestão de `platafirma-casa` (`acervo.casa_fonte`) — o mesmo
        carimbo que `acervo listar casa` serve como fonte."""
        sha = self._psql(
            f"select f.sha from acervo.casa_fonte f where f.repo = {_lit(SUPORTE)} "
            f"order by f.ingerido_em desc limit 1;")
        if not sha:
            raise FonteIndisponivel(Causa.SEM_INDICE, f"{SUPORTE}: nunca ingerido em acervo.casa_fonte")
        return f"casa:{sha[:12]}"

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = filtros or {}
        series = tuple(s.lower() for s in filtros.get("serie", SERIES))
        alvo = (alvo or "").strip()

        m = CHAVE_RE.match(alvo)
        if m:
            serie, num = m.group(1).lower(), m.group(2).zfill(4)
            ficha = self._ficha(f"{serie}:{num}")
            return [self._item(ficha, texto)] if ficha else []

        termos = [t for t in re.split(r"[\s_-]+", alvo.lower()) if t]
        arr = "array[" + ", ".join(_lit(s) for s in series) + "]::text[]"
        linhas = self._linhas(
            f"c.serie = any({arr}) and c.retirada_em is null") or []
        achados = []
        for l in linhas:
            alvo_busca = f"{l.get('numero')} {(l.get('titulo') or '').lower()}"
            if not termos or all(t in alvo_busca for t in termos):
                # Busca por palavra-chave sempre traz `ref` (nunca o corpo inteiro da
                # ADR): o corpo só é lido para o hit exato por chave — mesmo desenho de
                # antes desta correção.
                achados.append(self._item(l, "nenhum"))
        return achados

    def _linhas(self, where: str) -> list[dict]:
        """Metadado (sem `corpo`) das fichas da espécie `adr` que casam `where`."""
        return self._psql_json(f"""
          select coalesce(json_agg(row_to_json(t) order by t.serie, t.numero), '[]') from (
            select c.chave, c.serie, c.numero, c.titulo, c.sha, c.retirada_em,
                   c.substituida_por
              from acervo.casa c
              join acervo.especie_tipo e on e.id = c.especie_id
             where e.slug = {_lit(ESPECIE)} and {where}) t;
        """) or []

    def _ficha(self, chave: str) -> dict | None:
        """Uma ficha, com `corpo` — o hit exato por chave."""
        linhas = self._psql_json(f"""
          select coalesce(json_agg(row_to_json(t)), '[]') from (
            select c.chave, c.serie, c.numero, c.titulo, c.sha, c.retirada_em,
                   c.substituida_por, c.corpo
              from acervo.casa c
              join acervo.especie_tipo e on e.id = c.especie_id
             where e.slug = {_lit(ESPECIE)} and c.chave = {_lit(chave)}
             limit 1) t;
        """) or []
        return linhas[0] if linhas else None

    def _item(self, linha: dict, texto: str) -> Item:
        chave = linha["chave"]
        sha = linha.get("sha")
        if sha:
            versao = Versao(tipo=VersaoTipo.SHA, valor=sha[:12])
        else:
            digest = hashlib.sha256((linha.get("corpo") or chave).encode()).hexdigest()
            versao = Versao(tipo=VersaoTipo.DIGEST, valor=digest[:12])
        proc = Procedencia(fonte=Fonte.REGISTRO, chave=chave, versao=versao)

        if linha.get("retirada_em"):
            # arq:0111 item 5 / arq:0115: citação de ADR retirada segue resolvível —
            # responde a data e a sucessora, nunca com o texto (mesmo comportamento de
            # `acervo ler casa`).
            suc = linha.get("substituida_por")
            ref = f"{chave} — retirada em {linha['retirada_em']}" + (
                f"; sucessora {suc}" if suc else "; sem sucessora declarada")
            return Item(procedencia=proc, ref=ref)

        if texto == "nenhum":
            return Item(procedencia=proc, ref=f"{chave} — {linha.get('titulo') or ''}".rstrip(" —"))

        corpo = linha.get("corpo")
        if corpo is None:
            corpo = (self._ficha(chave) or {}).get("corpo") or ""
        if texto == "trecho":
            corpo = corpo[:800] + ("\n[…]" if len(corpo) > 800 else "")
        return Item(procedencia=proc, conteudo=corpo)
