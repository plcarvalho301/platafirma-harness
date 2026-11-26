"""Testes de contrato dos clientes de serviços internos no harness (DTs #979, #1377, #1398, #1404)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

import terceiros_olaria
from descanso.publicar import GravadorEventos, Mensagem, Recusada
from postura import casa as postura_casa
from postura import composicao as postura_composicao


def _carregar_bot():
    loader = importlib.machinery.SourceFileLoader("bin_bot_dt1398", str(RAIZ / "bin" / "bot"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _montar_armario(tmp_path: Path, entradas: list[tuple[str, str, str]]) -> tuple[Path, Path]:
    inst = tmp_path / "instancia"
    release = tmp_path / "release"
    armario = release / "core" / "deploy" / "armario-de-chaves.yaml"
    armario.parent.mkdir(parents=True, exist_ok=True)
    linhas = ["versao: 1", "segredos:"]
    for nome, rel, valor in entradas:
        linhas.append(f"  - nome: {nome}")
        linhas.append(f"    caminho: {rel}")
        arq = inst / rel
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(valor + "\n", encoding="utf-8")
    armario.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return inst, release


# --- DT #979: terceiros_olaria lê do armário e não falha com OLARIA_URL ausente -------------------


def test_dt979_terceiros_olaria_le_chave_do_armario_e_usa_url_padrao(tmp_path, monkeypatch):
    inst, release = _montar_armario(
        tmp_path,
        [("olaria/OLARIA_CHAVE", "cofre/custom/chave", "chave-do-armario")],
    )
    chamadas: list[tuple[str, str, str]] = []

    def _fake_consultar(classe: str, url: str, chave: str, prazo_s: float = 15.0) -> dict:
        chamadas.append((classe, url, chave))
        return {"fichas": []}

    monkeypatch.setattr(terceiros_olaria, "_consultar_classe", _fake_consultar)
    env = {
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_RELEASE": str(release),
        "OLARIA_URL": "",
    }
    itens = terceiros_olaria.ler_terceiros_da_olaria(env=env)
    assert itens == []
    assert chamadas == [("stack", terceiros_olaria.OLARIA_URL_PADRAO, "chave-do-armario")]


def test_dt979_terceiros_olaria_sem_chave_reporta_chave_ausente_nao_url(tmp_path):
    env = {
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "vazio"),
        "PLATAFIRMA_RELEASE": str(tmp_path / "rel-vazio"),
    }
    with pytest.raises(terceiros_olaria.OlariaIndisponivel, match="OLARIA_CHAVE ausente"):
        terceiros_olaria.ler_terceiros_da_olaria(env=env)


# --- DT #1398: bot usa lib/acervo_token e mapeia HTTP 401 para saída 3 ----------------------------


def test_dt1398_bot_chama_usa_token_do_armario(tmp_path, monkeypatch):
    inst, release = _montar_armario(
        tmp_path,
        [("acervo-guarda/RAG_API_TOKEN", "segredos/acervo-guarda/RAG_API_TOKEN", "tok-armario-1398")],
    )
    monkeypatch.delenv("RAG_API_TOKEN", raising=False)
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(release))

    bot = _carregar_bot()
    headers_vistos: dict[str, str] = {}

    class _Resp:
        status = 200

        def read(self):
            return b'{"itens": []}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(req, timeout=10):
        headers_vistos.update(dict(req.header_items()))
        return _Resp()

    monkeypatch.setattr(bot.urllib.request, "urlopen", _fake_urlopen)
    status, obj = bot._chama("GET", "/acervo/automacoes")
    assert status == 200
    assert obj == {"itens": []}
    assert headers_vistos.get("Authorization") == "Bearer tok-armario-1398"


@pytest.mark.parametrize(("http_code", "exit_esperado"), [(401, 3), (403, 4)])
def test_dt1398_bot_mapeia_401_para_3_e_403_para_4(monkeypatch, http_code, exit_esperado):
    bot = _carregar_bot()

    def _fake_urlopen(req, timeout=10):
        raise urllib.error.HTTPError(
            req.full_url,
            http_code,
            "erro",
            {},
            io.BytesIO(b'{"title": "SemCredencial", "detail": "token recusado"}'),
        )

    monkeypatch.setattr(bot.urllib.request, "urlopen", _fake_urlopen)
    with pytest.raises(bot.Falha) as exc:
        bot._chama("GET", "/acervo/automacoes")
    assert exc.value.codigo == exit_esperado


# --- DT #1404: postura/casa lê credencial do armário e aviso nomeia banco da ontologia da casa ----


def test_dt1404_postura_casa_dsn_le_credencial_do_armario(tmp_path):
    inst, release = _montar_armario(
        tmp_path,
        [("harness/CASA_LEITOR_PORTA_PASSWORD", "segredos/harness/CASA_LEITOR_PORTA_PASSWORD", "s3nha/segura")],
    )
    dsn = postura_casa._dsn({
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_RELEASE": str(release),
    })
    assert dsn == "postgresql://casa_leitor_porta:s3nha%2Fsegura@127.0.0.1:5439/casa"


def test_dt1404_postura_casa_dsn_respeita_env_explicito(tmp_path):
    inst, release = _montar_armario(
        tmp_path,
        [("harness/CASA_LEITOR_PORTA_PASSWORD", "segredos/harness/CASA_LEITOR_PORTA_PASSWORD", "do-armario")],
    )
    dsn = postura_casa._dsn({
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_RELEASE": str(release),
        "CASA_PG_USER": "outro_user",
        "CASA_PG_PASSWORD": "senha-env",
    })
    assert dsn == "postgresql://outro_user:senha-env@127.0.0.1:5439/casa"


def test_dt1404_aviso_nomeia_banco_da_ontologia_da_casa(tmp_path):
    persona_dir = tmp_path / "instancias" / "persona"
    persona_dir.mkdir(parents=True)
    (persona_dir / "engenharia.md").write_text(
        "# Gabriel\n\nPostura preferencial: construtivo\n",
        encoding="utf-8",
    )

    class _LigacoesFora:
        def perfil(self, cadeira: str) -> str | None:
            raise postura_casa.SemBanco("OperationalError: connection refused")

    avisos: list[str] = []
    perfil = postura_composicao.perfil_da_persona(tmp_path, "engenharia", _LigacoesFora(), avisos)
    assert perfil == "construtivo"
    assert len(avisos) == 1
    assert "banco da ontologia da casa fora" in avisos[0]
    assert "banco do acervo" not in avisos[0]


# --- DT #1377: GravadorEventos inclui recusados[] no HTTP 422 -------------------------------------


def test_dt1377_gravador_eventos_inclui_recusados_no_422(monkeypatch):
    corpo_422 = {
        "tipo": "EventoInvalido",
        "status": 422,
        "detalhe": "1 de 1 evento(s) recusado(s); o lote inteiro volta e nada foi gravado",
        "recusados": [
            {
                "indice": 0,
                "evento_id": "11111111-1111-1111-1111-111111111111",
                "motivo": "EtiquetaDesconhecida",
                "campo": "etiquetas[0]",
                "detalhe": "chave 'foo' não existe no fichário",
            }
        ],
    }

    def _fake_urlopen(req, timeout=15.0):
        raise urllib.error.HTTPError(
            req.full_url,
            422,
            "Unprocessable Entity",
            {},
            io.BytesIO(json.dumps(corpo_422).encode("utf-8")),
        )

    monkeypatch.setattr("descanso.publicar.urllib.request.urlopen", _fake_urlopen)
    msg = Mensagem(
        enunciado="Teste de publicação com etiqueta inválida.",
        quem="engenharia",
        destinatario=["engenharia"],
        tipo="afirmacao",
        ocorrido_em="2026-11-26T20:00:00Z",
        etiqueta=["foo"],
    )
    credencial_ficticia = f"fixture-{id(msg)}"
    gravador = GravadorEventos(url="http://127.0.0.1:8111", token=credencial_ficticia)
    with pytest.raises(Recusada) as exc:
        gravador.gravar(msg)
    texto = str(exc.value)
    assert "EventoInvalido" in texto
    assert "EtiquetaDesconhecida" in texto
    assert "etiquetas[0]" in texto
    assert "chave 'foo' não existe no fichário" in texto
    assert "capacidade:foo" in texto
