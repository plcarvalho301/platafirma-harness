"""`persona salvar` nao faz git e nunca escreve no clone-cache (incidente #3273).

Em 04/10/2026 `persona salvar` achou o clone-cache `<bancada>/platafirma-harness` (a bancada
de card, depois da arq:0109, fica em wt/platafirma-harness/<cadeira>/<card-slug>), commitou
em HEAD destacado e o `git push origin HEAD` recusou: o commit ficou preso no cache e o
`persona sanear` respondeu "clone em dia". Contrato novo: o verbo confere a persona na
bancada de card e para; commit, push e PR sao do fluxo de bancada. Estes testes rodam o
bin/persona de verdade contra bancada, cache e git montados em tmp_path.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PERSONA = RAIZ / "bin" / "persona"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("git") is None or shutil.which("python3") is None,
    reason="sem bash, git ou python3 no PATH")

VALIDA = (
    "Voce e uma cadeira no molde novo da PlataFirma.\n"
    "Linha 2 de introducao.\n\n"
    "## Perguntas de competência\n\n1. Pergunta 1?\n\n"
    "## Vocabulário canônico\n\n- termo: definicao\n\n"
    "## Escopo\n\n- o que nao faz\n\n"
    "## Sinais de reconhecimento\n\n- sinal 1\n\n"
    "## Gerências\n\n- **teste** — linha de teste\n"
)
VELHA = "POSTURA: cadeira no molde velho\n\nTexto solto sem as secoes do molde novo.\n"


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _repo(caminho, ramo):
    caminho.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", ramo, str(caminho)], check=True)
    _git(caminho, "config", "user.name", "Teste")
    _git(caminho, "config", "user.email", "teste@platafirma.org")
    (caminho / "abertura" / "teste").mkdir(parents=True)
    (caminho / "abertura" / "teste" / "persona.md").write_text(VALIDA)
    (caminho / "registro").mkdir()
    (caminho / "registro" / "eventos-org.jsonl").write_text("")
    _git(caminho, "add", ".")
    _git(caminho, "commit", "-q", "-m", "init")
    return caminho


class Casa:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.bancada = tmp_path / "bancada"
        # o clone-cache, como o `repo sanear` o deixa: destacado
        self.cache = _repo(self.bancada / "platafirma-harness", "main")
        _git(self.cache, "checkout", "-q", "--detach")

    def abrir_bancada(self, slug):
        return _repo(self.bancada / "wt" / "platafirma-harness" / "engenharia" / slug,
                     "fabrica/" + slug)

    def persona(self, *args, env_extra=None):
        env = dict(os.environ)
        for k in ("PERSONA_REPO", "PF_ABERTURA_DIR", "PLATAFIRMA_ARQUIVO_BANCADA"):
            env.pop(k, None)
        env.update(PLATAFIRMA_BANCADA=str(self.bancada), PF_CADEIRA="engenharia",
                   HOME=str(self.tmp), PLATAFIRMA_INSTANCIA=str(self.tmp / "instancia"))
        env.update(env_extra or {})
        return subprocess.run([str(PERSONA), *args], capture_output=True, text=True,
                              cwd=str(self.tmp), env=env)

    def cache_intacto(self, head):
        assert _git(self.cache, "rev-parse", "HEAD") == head
        assert _git(self.cache, "status", "--porcelain") == ""
        assert _git(self.cache, "branch", "--show-current") == ""


def _edita(bancada, texto=None):
    p = bancada / "abertura" / "teste" / "persona.md"
    p.write_text(texto or VALIDA.replace("- o que nao faz", "- o que nao faz\n- e outra coisa"))


@pytest.fixture
def casa(tmp_path):
    return Casa(tmp_path)


def test_salvar_confere_na_bancada_sem_commitar_nem_tocar_o_cache(casa):
    b = casa.abrir_bancada("persona-x")
    head_b = _git(b, "rev-parse", "HEAD")
    head_cache = _git(casa.cache, "rev-parse", "HEAD")
    _edita(b)
    p = casa.persona("salvar", "-m", "msg")
    assert p.returncode == 0, p.stderr + p.stdout
    assert "nada commitado" in p.stdout and "persona-x" in p.stdout
    assert "repo commitar" in p.stdout
    assert _git(b, "rev-parse", "HEAD") == head_b
    assert "abertura/teste/persona.md" in _git(b, "status", "--porcelain")
    casa.cache_intacto(head_cache)


def test_salvar_molde_velho_reprova_na_bancada(casa):
    b = casa.abrir_bancada("persona-x")
    head_b = _git(b, "rev-parse", "HEAD")
    _edita(b, VELHA)
    p = casa.persona("salvar", "-m", "invalido")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "ERRO" in p.stdout
    assert _git(b, "rev-parse", "HEAD") == head_b


def test_salvar_confere_cadeira_nova_ainda_nao_rastreada(casa):
    b = casa.abrir_bancada("persona-x")
    (b / "abertura" / "nova").mkdir()
    (b / "abertura" / "nova" / "persona.md").write_text(VELHA)
    p = casa.persona("salvar", "-m", "nova")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "nova: falta a secao" in p.stdout


def test_salvar_sem_mudanca_diz_nada_a_salvar(casa):
    casa.abrir_bancada("persona-x")
    p = casa.persona("salvar", "-m", "msg")
    assert p.returncode == 0, p.stderr
    assert "nada a salvar" in p.stdout


def test_sem_bancada_de_card_recusa_e_nao_cai_no_cache(casa):
    """O defeito do #3273: so existe o cache destacado, com a persona editada nele."""
    head_cache = _git(casa.cache, "rev-parse", "HEAD")
    (casa.cache / "abertura" / "teste" / "persona.md").write_text(VALIDA + "\n")
    for ato in (["salvar", "-m", "msg"], ["idade"]):
        p = casa.persona(*ato)
        assert p.returncode == 3, p.stdout + p.stderr
        assert "sem bancada de card" in p.stderr
        assert "repo abrir platafirma-harness" in p.stderr
    assert _git(casa.cache, "rev-parse", "HEAD") == head_cache
    assert _git(casa.cache, "log", "--oneline").count("\n") == 0
    assert _git(casa.cache, "branch", "--show-current") == ""


def test_duas_bancadas_pedem_a_escolha_e_bancada_resolve(casa):
    casa.abrir_bancada("persona-a")
    casa.abrir_bancada("persona-b")
    p = casa.persona("salvar", "-m", "msg")
    assert p.returncode == 3
    assert "persona-a" in p.stderr and "persona-b" in p.stderr and "--bancada" in p.stderr
    p = casa.persona("--bancada", "persona-b", "salvar", "-m", "msg")
    assert p.returncode == 0, p.stderr
    assert "nada a salvar" in p.stdout
    p = casa.persona("salvar", "--bancada", "nao-existe", "-m", "msg")
    assert p.returncode == 3
    assert "persona-a" in p.stderr


def test_clone_destacado_nunca_e_bancada(casa):
    head_cache = _git(casa.cache, "rev-parse", "HEAD")
    p = casa.persona("salvar", "-m", "msg", env_extra={"PERSONA_REPO": str(casa.cache)})
    assert p.returncode == 3, p.stdout + p.stderr
    assert "HEAD destacado" in p.stderr
    casa.cache_intacto(head_cache)


@pytest.mark.parametrize("ato", ["abrir", "sanear"])
def test_abrir_e_sanear_aposentados_nao_mexem_no_git(casa, ato):
    head_cache = _git(casa.cache, "rev-parse", "HEAD")
    p = casa.persona(ato)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "aposentado" in p.stderr and "repo abrir platafirma-harness" in p.stderr
    assert "clone em dia" not in p.stdout
    casa.cache_intacto(head_cache)
