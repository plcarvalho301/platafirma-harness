# componente: componente:leitura
"""Testes do resolvedor (estágios 3-4) e das moradas git e banco (story #4442, t5)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from leitura import resolvedor
from leitura.moradas import ErroMorada, RegistroMoradas
from leitura.moradas.banco import PAPEL_LEITOR, SQL_BEGIN_RO, AdaptadorBanco
from leitura.moradas.git import AdaptadorGit
from leitura.tipos import AlvoResolvido, CursorDecodificado, SeletorParte


# ================================================================== resolvedor (estágios 3 e 4)
def test_resolvedor_seis_construcoes_e_portao_do_verbo() -> None:
    vista = resolvedor.carregar_vista_alcance()

    # 1. Chave canônica git
    alvo, membro = resolvedor.resolver_alvo("busca", "ato:ler", vista=vista)
    assert alvo.chave_canonica == "ato:ler"
    assert alvo.morada == "git"
    assert alvo.endereco == "referencias/instancias/ato/ler.md"
    assert alvo.eh_ficha_da_classe is False
    assert membro is None

    # 2. Chave só com a classe (`sessao:`) -> ficha da classe
    alvo_cl, _ = resolvedor.resolver_alvo("busca", "sessao:", vista=vista)
    assert alvo_cl.chave_canonica == "shape:sessao"
    assert alvo_cl.classe == "shape"
    assert alvo_cl.morada == "banco"
    assert alvo_cl.eh_ficha_da_classe is True

    # 3. Identificador curto em verbo de classe única (`fila`) e ambíguo em multiclasse (`tarefas`)
    alvo_curto, _ = resolvedor.resolver_alvo("fila", "msg-1", vista=vista)
    assert alvo_curto.chave_canonica == "mensagem:msg-1"
    assert alvo_curto.morada == "fila"

    with pytest.raises(resolvedor.ErroResolucao) as exc_amb:
        resolvedor.resolver_alvo("tarefas", "4442", vista=vista)
    assert exc_amb.value.saida == 2
    assert exc_amb.value.recusa.codigo == "chave-ambigua"

    # 4. Formatos fechados + membro interno
    alvo_obra, mem = resolvedor.resolver_alvo("acervo", "obra:42!cap1/texto.xhtml", vista=vista)
    assert alvo_obra.chave_canonica == "obra:42"
    assert alvo_obra.morada == "banco"
    assert mem == "cap1/texto.xhtml"

    # 5. Caminho solto recusado
    with pytest.raises(resolvedor.ErroResolucao) as exc_cam:
        resolvedor.resolver_alvo("busca", "/etc/passwd", vista=vista)
    assert exc_cam.value.saida == 2
    assert exc_cam.value.recusa.codigo == "caminho-solto-recusado"

    # 6. Portão do verbo: classe fora do alcance sai 1 com verbo dono em proximo, antes da morada
    with pytest.raises(resolvedor.ErroResolucao) as exc_fora:
        resolvedor.resolver_alvo("tarefas", "obra:42", vista=vista)
    assert exc_fora.value.saida == 1
    assert exc_fora.value.recusa.codigo == "classe-fora-do-verbo"
    assert exc_fora.value.recusa.proximo == "acervo ler obra:42"

    # 7. Verbo que não aceita ato:ler sai 2 ato-nao-aceito
    with pytest.raises(resolvedor.ErroResolucao) as exc_verbo:
        resolvedor.resolver_alvo("verbo-sem-ler", "ato:ler", vista=vista)
    assert exc_verbo.value.saida == 2
    assert exc_verbo.value.recusa.codigo == "ato-nao-aceito"
    assert exc_verbo.value.recusa.proximo == "busca ler ato:ler"


# ================================================================== morada git
def test_morada_git_le_blob_recusa_symlink_e_vedado(tmp_path: Path) -> None:
    rel = tmp_path / "release"
    (rel / "referencias" / "instancias" / "ato").mkdir(parents=True)
    arq = rel / "referencias" / "instancias" / "ato" / "ler.md"
    conteudo = b"# ato ler\nconteudo\n"
    arq.write_bytes(conteudo)

    # Elo simbólico apontando para fora
    fora = tmp_path / "externo.txt"
    fora.write_text("fora", encoding="utf-8")
    os.symlink(fora, rel / "referencias" / "instancias" / "ato" / "atalho.md")

    # Arquivo vedado
    (rel / "acesso").mkdir()
    (rel / "acesso" / "politica.yaml").write_text("segredo: 1\n", encoding="utf-8")

    git = AdaptadorGit(rel)
    alvo_ok = AlvoResolvido(
        chave_pedida="ato:ler",
        chave_canonica="ato:ler",
        classe="ato",
        morada="git",
        endereco="referencias/instancias/ato/ler.md",
        universo_fechado=True,
        digest_release=None,
    )
    bruto = git.ler_objeto(alvo_ok, SeletorParte(), prazo_ms=5_000)
    sha_esperado = hashlib.sha1(f"blob {len(conteudo)}\0".encode() + conteudo).hexdigest()
    assert bruto.dados == conteudo
    assert bruto.versao == sha_esperado
    assert bruto.avisos == ()

    # Symlink -> saída 4 acesso-negado
    alvo_sym = AlvoResolvido(
        chave_pedida="ato:atalho",
        chave_canonica="ato:atalho",
        classe="ato",
        morada="git",
        endereco="referencias/instancias/ato/atalho.md",
        universo_fechado=True,
        digest_release=None,
    )
    with pytest.raises(ErroMorada) as exc_sym:
        git.ler_objeto(alvo_sym, SeletorParte(), prazo_ms=5_000)
    assert exc_sym.value.saida == 4
    assert exc_sym.value.recusa.codigo == "acesso-negado"

    # Arquivo vedado -> saída 4 segredo-fora-do-leitor
    alvo_ved = AlvoResolvido(
        chave_pedida="politica:acesso",
        chave_canonica="politica:acesso",
        classe="politica",
        morada="git",
        endereco="acesso/politica.yaml",
        universo_fechado=True,
        digest_release=None,
    )
    with pytest.raises(ErroMorada) as exc_ved:
        git.ler_objeto(alvo_ved, SeletorParte(), prazo_ms=5_000)
    assert exc_ved.value.saida == 4
    assert exc_ved.value.recusa.codigo == "segredo-fora-do-leitor"

    # --versao divergente -> saída 2 versao-divergente
    with pytest.raises(ErroMorada) as exc_ver:
        git.ler_objeto(alvo_ok, SeletorParte(versao_pedida="0" * 40), prazo_ms=5_000)
    assert exc_ver.value.saida == 2
    assert exc_ver.value.recusa.codigo == "versao-divergente"

    # listar_chaves omite symlinks e vedados e pagina deterministamente
    pag = git.listar_chaves("ato", (), None, 10, None, 5_000)
    chaves = [it["chave"] for it in pag.itens]
    assert any("ler" in c for c in chaves)
    assert not any("atalho" in c or "politica" in c for c in chaves)


# ================================================================== morada banco (PostgreSQL falso)
class _CursorFalso:
    def __init__(self, estado: dict[str, Any]) -> None:
        self._estado = estado
        self._res: list[tuple[Any, ...]] = []

    def __enter__(self) -> _CursorFalso:
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self._estado["sqls"].append((sql.strip(), params))
        if self._estado.get("erro_exec"):
            raise self._estado["erro_exec"]
        if "FROM casa.ficha" in sql and "WHERE f.chave_humana" in sql:
            chave = params[0]
            ficha = self._estado["fichas"].get(chave)
            if ficha is None:
                self._res = []
            else:
                self._res = [("u-1", chave, ficha["classe"], self._estado["fornada"], ficha)]
        elif "string_agg(f.chave_humana" in sql:
            classe = params[0]
            chaves = sorted(k for k, v in self._estado["fichas"].items() if v["classe"] == classe)
            digest = self._estado.get("digest_override") or hashlib.md5("\n".join(chaves).encode()).hexdigest()
            self._res = [(self._estado["fornada"], digest, len(chaves))]
        elif "ORDER BY ordem ASC" in sql:
            classe, ult_chave, _ult_ord, _ult_ch2, limite = params
            chaves = sorted(k for k, v in self._estado["fichas"].items() if v["classe"] == classe)
            if ult_chave is not None:
                chaves = [k for k in chaves if k > ult_chave]
            self._res = [(0, k, k, classe) for k in chaves[:limite]]
        else:
            self._res = []

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._res[0] if self._res else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._res)


class _ConexaoFalsa:
    def __init__(self, estado: dict[str, Any]) -> None:
        self._estado = estado
        self.fechada = False
        self.rollbacks = 0

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self._estado)

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.fechada = True


def test_morada_banco_transacao_ro_digest_e_paginacao_chave_de_corte() -> None:
    estado: dict[str, Any] = {
        "sqls": [],
        "fornada": "42",
        "fichas": {
            "sessao": {"chave": "sessao", "classe": "shape", "dados": {"rotulo": ["Sessão"]}},
            "ato:a": {"chave": "ato:a", "classe": "ato", "dados": {}},
            "ato:b": {"chave": "ato:b", "classe": "ato", "dados": {}},
            "ato:c": {"chave": "ato:c", "classe": "ato", "dados": {}},
        },
    }
    conexoes: list[_ConexaoFalsa] = []

    def _fabrica() -> _ConexaoFalsa:
        c = _ConexaoFalsa(estado)
        conexoes.append(c)
        return c

    banco = AdaptadorBanco(fabrica_conexao=_fabrica)
    assert banco.papel == PAPEL_LEITOR

    # Leitura de ficha de classe (shape:sessao) abre REPEATABLE READ READ ONLY e fecha conexão
    alvo_shape = AlvoResolvido(
        chave_pedida="sessao:",
        chave_canonica="shape:sessao",
        classe="shape",
        morada="banco",
        endereco="shape:sessao",
        universo_fechado=True,
        digest_release=None,
        eh_ficha_da_classe=True,
    )
    bruto = banco.ler_objeto(alvo_shape, SeletorParte(), prazo_ms=3_000)
    assert bruto.versao == "42"
    assert json.loads(bruto.dados.decode("utf-8"))["chave"] == "sessao"
    assert conexoes[-1].fechada is True
    assert conexoes[-1].rollbacks == 1
    assert any(SQL_BEGIN_RO in s for s, _ in estado["sqls"])
    assert any("SET LOCAL statement_timeout" in s for s, _ in estado["sqls"])

    # Inexistência com digest divergente sai 3 digest-divergente
    alvo_aus = AlvoResolvido(
        chave_pedida="ato:inexistente",
        chave_canonica="ato:inexistente",
        classe="ato",
        morada="banco",
        endereco="ato:inexistente",
        universo_fechado=True,
        digest_release="digest-antigo-da-release",
    )
    with pytest.raises(ErroMorada) as exc_dig:
        banco.ler_objeto(alvo_aus, SeletorParte(), prazo_ms=3_000)
    assert exc_dig.value.saida == 3
    assert exc_dig.value.recusa.codigo == "digest-divergente"

    # Paginação por chave de corte estável sob inserção concorrente + detecção de mudança de versão
    p1 = banco.listar_chaves("ato", (), None, 2, None, 3_000)
    assert [it["chave"] for it in p1.itens] == ["ato:a", "ato:b"]
    assert p1.proxima_tupla == (0, "ato:b")

    # Inserção concorrente antes do corte e avanço da fornada
    estado["fichas"]["ato:00-novo"] = {"chave": "ato:00-novo", "classe": "ato", "dados": {}}
    estado["fornada"] = "43"
    cur = CursorDecodificado(
        versao_token="v1",
        sujeito="pedro",
        verbo="busca",
        classe="ato",
        query_hash="h",
        versao_retrato="42",
        ultima_ordem=0,
        ultima_chave="ato:b",
    )
    p2 = banco.listar_chaves("ato", (), None, 2, cur, 3_000)
    assert [it["chave"] for it in p2.itens] == ["ato:c"]
    assert p2.proxima_tupla is None
    assert p2.mudou == {"de": "42", "para": "43"}
    assert "versao_alterada_entre_paginas" in p2.avisos

    # Lista vazia legítima sai 0 (total=0, itens=())
    vazia = banco.listar_chaves("classe-vazia", (), None, 10, None, 3_000)
    assert vazia.total == 0
    assert vazia.itens == ()

    # Timeout no banco sai 5 tempo-esgotado
    estado["erro_exec"] = RuntimeError("canceling statement due to statement timeout")
    with pytest.raises(ErroMorada) as exc_to:
        banco.ler_objeto(alvo_shape, SeletorParte(), prazo_ms=500)
    assert exc_to.value.saida == 5
    assert exc_to.value.recusa.codigo == "tempo-esgotado"

    # RegistroMoradas despacha para git e banco e sai 3 para morada não registrada
    reg = RegistroMoradas({"banco": banco})
    with pytest.raises(ErroMorada) as exc_sem:
        reg.obter("wiki")
    assert exc_sem.value.saida == 3
    assert exc_sem.value.recusa.codigo == "morada-sem-resposta"
