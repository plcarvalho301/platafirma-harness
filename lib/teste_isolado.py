"""Isolamento de suíte de teste: teste não lê nem escreve estado real.

Regra do dono (27/09/2026): teste não depende de estado real — acervo, instância,
release no ar, bancada da conta, serviço de pé, forge, identidade de quem roda. Teste
que depende dele muda de cor quando o sistema evolui, e vermelho por evolução não é
risco a anotar: é teste errado. Regra e porquê: `referencias/classes/teste.md` no `platafirma-casa-espelho`.

Cada suíte chama `isolar()` do seu conftest.py, uma vez, antes da coleta:
  1. sai do ambiente toda variável da plataforma (PREFIXOS) e a identidade da conta
     (USER, LOGNAME viram «teste»);
  2. as raízes apontam para um diretório temporário vazio;
  3. os serviços apontam para a porta 9 (discard): nada responde, a falha é imediata;
  4. programas que falam com o mundo (DELATORES) entram no PATH como delatores: saem
     97 dizendo que o teste chamou o real sem stub. O stub de um teste vem antes no PATH
     e ganha do delator.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

PREFIXOS = (
    "PLATAFIRMA_", "PF_", "RAG_", "MOTOR_", "MEM_", "FILA_", "SESSAO_", "MW_",
    "KROKI_", "ACESSO_", "PDP_", "OPS_", "SEG_", "TAREFAS_", "REC_", "CHAT_",
    "INFRA_", "OIDC_", "MINUTA_", "PERSONA_", "AGREGADOR_", "ACERVO_", "CORPUS_",
    "JUIZ_", "OLLAMA_",
)

# variáveis que, mesmo com prefixo da plataforma, são ferramenta e não estado: o
# tokenizador do modelo é artefato pinado (registro/terceiros.json), como o uv
PRESERVAR = ("PLATAFIRMA_TOKENIZADOR",)

# navegador (arq:0129 D3): no degrau pequeno o navegador não existe; o teste que precisa dele leva
# `degrau: imagem` na lista de portão. CHROME e PUPPETEER_EXECUTABLE_PATH apontam para o delator;
# PLATAFIRMA_CHROMIUM fica de fora, porque é a entrada do resolver_chromium de lib/venv.sh e o teste de
# verbo que o lê (conferir dependencias) escolhe o dele.
NAVEGADORES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
VARIAVEIS_DE_NAVEGADOR = ("CHROME", "PUPPETEER_EXECUTABLE_PATH")

DELATORES = ("docker", "gh", "systemctl", "psql", "redis-cli") + NAVEGADORES

SERVICO_MORTO = "http://127.0.0.1:9"
MARCADOR = "isolamento_libera"
ENV_LIBERADOS = "PF_ISOLAMENTO_LIBERADOS"


class _PluginIsolamento:
    """Libera delatores listados em `@pytest.mark.isolamento_libera(...)` só durante o teste."""

    @staticmethod
    def _coletar_liberados(item) -> list[str]:
        liberados: list[str] = []
        for mark in item.iter_markers(MARCADOR):
            for arg in mark.args:
                if isinstance(arg, (list, tuple, set)):
                    liberados.extend(str(a) for a in arg)
                else:
                    liberados.append(str(arg))
        return liberados

    def pytest_runtest_protocol(self, item, nextitem):
        liberados = self._coletar_liberados(item)
        if not liberados:
            yield
            return
        antes = os.environ.get(ENV_LIBERADOS)
        atuais = [v for v in (antes or "").split(",") if v]
        os.environ[ENV_LIBERADOS] = ",".join(dict.fromkeys([*atuais, *liberados]))
        try:
            yield
        finally:
            if antes is None:
                os.environ.pop(ENV_LIBERADOS, None)
            else:
                os.environ[ENV_LIBERADOS] = antes


if pytest is not None:
    _PluginIsolamento.pytest_runtest_protocol = pytest.hookimpl(hookwrapper=True)(
        _PluginIsolamento.pytest_runtest_protocol
    )


def isolar(config=None) -> Path:
    raiz = Path(tempfile.mkdtemp(prefix="pf-teste-"))
    for nome in list(os.environ):
        if nome.startswith(PREFIXOS) and nome not in PRESERVAR:
            del os.environ[nome]

    for sub in ("instancia", "opt", "bancada"):
        (raiz / sub).mkdir()
    gitconfig = raiz / "gitconfig"
    tmp_gitconfig = raiz / "gitconfig.tmp"
    with open(tmp_gitconfig, "w", encoding="utf-8") as f:
        f.write("[user]\n    useConfigOnly = true\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_gitconfig, gitconfig)
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        os.environ.pop(var, None)
    os.environ.update({
        "USER": "teste",
        "LOGNAME": "teste",
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "PLATAFIRMA_INSTANCIA": str(raiz / "instancia"),
        "PF_RELEASE_RAIZ": str(raiz / "opt"),
        "PLATAFIRMA_RELEASE": str(raiz / "opt" / "current"),
        "PLATAFIRMA_BANCADA": str(raiz / "bancada"),
        "PLATAFIRMA_ARQUIVO_BANCADA": str(raiz / "bancada-nao-declarada"),
        "PF_LINT_ACERVO": "/bin/false",
        "RAG_API_URL": SERVICO_MORTO,
        "RAG_API_BASE": SERVICO_MORTO,
        "MOTOR_ACERVO_URL": SERVICO_MORTO,
        "MW_API_URL": SERVICO_MORTO + "/api.php",
        "KROKI_URL": SERVICO_MORTO,
        "TAREFAS_BASE": SERVICO_MORTO + "/api",
        "PF_RASTREADOR_BASE": SERVICO_MORTO,
        "MEM_REDIS_PORT": "9",
        "FILA_REDIS_PORT": "9",
        "REC_CACHE_PORT": "9",
        "SESSAO_PG_PORT": "9",
    })

    delatores = raiz / "delatores"
    delatores.mkdir()
    for prog in DELATORES:
        p = delatores / prog
        cura = (" (degrau pequeno: o teste que abre navegador leva `degrau: imagem` na lista)"
                if prog in NAVEGADORES else "")
        p.write_text(
            "#!/bin/sh\n"
            f'case ",${{{ENV_LIBERADOS}:-}}," in\n'
            f'  *,{prog},*)\n'
            '    _novo_path=""\n'
            '    _ifs="$IFS"; IFS=":"\n'
            '    for _p in $PATH; do\n'
            f'      [ "$_p" = "{delatores}" ] && continue\n'
            '      _novo_path="${_novo_path:+$_novo_path:}$_p"\n'
            '    done\n'
            '    IFS="$_ifs"\n'
            f'    PATH="$_novo_path" exec {prog} "$@"\n'
            '    ;;\n'
            'esac\n'
            f'echo "isolamento: teste chamou o {prog} real sem stub: $*{cura}" >&2\n'
            "exit 97\n")
        p.chmod(0o755)
    for var in VARIAVEIS_DE_NAVEGADOR:
        os.environ[var] = str(delatores / "chromium")
    os.environ["PATH"] = f"{delatores}{os.pathsep}{os.environ.get('PATH', '')}"
    if config is not None and pytest is not None:
        config.addinivalue_line(
            "markers",
            f"{MARCADOR}(*verbos): libera os delatores listados apenas durante o teste",
        )
        if not config.pluginmanager.has_plugin("pf_teste_isolado"):
            config.pluginmanager.register(_PluginIsolamento(), name="pf_teste_isolado")
    return raiz


def desfazer(raiz: Path | None) -> None:
    if raiz is not None:
        shutil.rmtree(raiz, ignore_errors=True)
