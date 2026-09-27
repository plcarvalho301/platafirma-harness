"""Contrato do gate de rotas de `publicar-abertura` (card #3143).

Antes, `validar_snapshot` so conferia que `rotas-chapeu.json` existia: persona editada sem
`persona rotas`, ou conceito curado depois da ultima geracao, publicava rota velha calada.
Agora o publicador roda `gerar_rotas_chapeu.py --conferir` sobre o snapshot:

- conforme publica; divergente e orfao de CHAPEU recusam com current intacto;
- so reprova nas cadeiras que a publicacao muda; a deriva herdada das outras avisa;
- orfao de CONCEITO so avisa; golden fora de alcance avisa que nao conferiu e publica;
- PF_ROTAS_GATE=aviso (o que `release` usa em --so-caderno e no reverter) nao recusa;
- ordem e caixa dos gatilhos nao divergem (regua de `casa()` do roteador).

Hermetico: golden record de arquivo (PF_ROTAS_GOLDEN), harness num repo git local em
tmp_path, morada em tmp_path, gancho da casa desligado.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLICAR = REPO_ROOT / "bin" / "publicar-abertura"
GERADOR = REPO_ROOT / "recuperacao" / "gerar_rotas_chapeu.py"

GOLDEN = [
    {"rotulo": "rotulo real", "slug": "rotulo-real"},
    {"rotulo": "outro rotulo", "slug": "outro-rotulo", "outros_rotulos": "apelido do outro"},
]


def _persona(*bullets: str) -> str:
    return "Cadeira de teste.\n\n## Gerências\n\nCada gerência é um chapéu.\n\n" + "".join(
        f"{b}\n" for b in bullets)


BULLET_ALFA = "- **alfa** — descrição solta. rotulo real · outro rotulo."


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return r.stdout.strip()


class Harness:
    """Um repo git com abertura/ minima, o golden em arquivo e a morada vazia."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.repo = tmp / "harness"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.name", "fixture")
        _git(self.repo, "config", "user.email", "fixture@test.local")
        self.abertura = self.repo / "abertura"
        for rel, texto in {
            "aliases.json": "{}\n",
            "dono.md": "# dono\nfixture.\n",
            "oficio.md": "# oficio\nfixture.\n",
            "testecadeira/alfa/chapeu.md": "# alfa\n",
        }.items():
            p = self.abertura / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texto, encoding="utf-8")
        self.golden = tmp / "golden.json"
        self.golden.write_text(json.dumps({"itens": GOLDEN}), encoding="utf-8")
        self.morada = tmp / "srv" / "var" / "abertura-publicada"
        self.env = dict(os.environ)
        self.env.update({
            "PF_HARNESS": str(self.repo),
            "PF_ABERTURA_DIR": str(self.morada),
            "PF_RELEASE_RAIZ": str(tmp / "opt"),
            "PLATAFIRMA_INSTANCIA": str(tmp / "srv"),
            "PF_CASA_REINDEXA": "0",
            "PF_ROTAS_GOLDEN": str(self.golden),
        })

    def persona(self, texto: str) -> None:
        (self.abertura / "testecadeira" / "persona.md").write_text(texto, encoding="utf-8")

    def rotas_geradas(self) -> dict:
        """rotas-chapeu.json escrito pelo proprio gerador, com o mesmo golden."""
        subprocess.run([sys.executable, str(GERADOR), "--abertura", str(self.abertura),
                        "--golden", str(self.golden)],
                       capture_output=True, text=True, check=True, env=self.env)
        return json.loads((self.abertura / "rotas-chapeu.json").read_text(encoding="utf-8"))

    def rotas(self, tabela: dict) -> None:
        (self.abertura / "rotas-chapeu.json").write_text(
            json.dumps(tabela, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def commit(self) -> str:
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "fixture")
        return _git(self.repo, "rev-parse", "HEAD")

    def publicar(self, **env) -> subprocess.CompletedProcess:
        return subprocess.run([str(PUBLICAR), "main"], env={**self.env, **env},
                              capture_output=True, text=True, timeout=60)

    def current(self) -> str | None:
        link = self.morada / "current"
        return link.resolve().name if link.is_symlink() else None


@pytest.fixture()
def h(tmp_path):
    return Harness(tmp_path)


def test_conforme_publica(h):
    h.persona(_persona(BULLET_ALFA))
    tabela = h.rotas_geradas()
    assert tabela["testecadeira"]["alfa"]  # o fixture gera rota de verdade
    sha = h.commit()
    r = h.publicar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: conforme" in r.stdout
    assert h.current() == sha


def test_divergente_recusa_com_current_intacto(h):
    h.persona(_persona(BULLET_ALFA))
    h.rotas({})  # persona declara alfa, arquivo velho sem rota
    h.commit()
    r = h.publicar()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "rotas: divergente" in r.stdout
    assert "testecadeira/alfa" in r.stdout
    assert "recusa: rotas-chapeu.json" in r.stderr
    assert "persona rotas" in r.stderr  # a cura vem nomeada
    assert h.current() is None


def test_divergente_depois_de_publicado_nao_move_current(h):
    h.persona(_persona(BULLET_ALFA))
    h.rotas_geradas()
    sha1 = h.commit()
    assert h.publicar().returncode == 0
    # conceito novo curado no acervo (golden muda) sem regenerar o arquivo
    h.persona(_persona(BULLET_ALFA.rstrip(".") + " · rotulo curado depois."))
    h.golden.write_text(json.dumps(GOLDEN + [{"rotulo": "rotulo curado depois",
                                              "slug": "rotulo-curado-depois"}]),
                        encoding="utf-8")
    h.commit()
    r = h.publicar()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "rotulo curado depois" in r.stdout
    assert h.current() == sha1


def test_deriva_anterior_fora_do_escopo_avisa_e_quem_muda_a_cadeira_responde(h):
    h.persona(_persona("- **alfa** — descrição solta. rotulo real · rotulo curado depois."))
    h.rotas_geradas()  # golden ainda sem o conceito: orfao de conceito, aviso
    sha1 = h.commit()
    assert h.publicar().returncode == 0
    assert h.current() == sha1

    # dados cura o conceito no acervo; ninguem regenera; a publicacao seguinte nao toca a cadeira
    h.golden.write_text(json.dumps(GOLDEN + [{"rotulo": "rotulo curado depois",
                                              "slug": "rotulo-curado-depois"}]),
                        encoding="utf-8")
    (h.abertura / "dono.md").write_text("# dono\nmudou.\n", encoding="utf-8")
    sha2 = h.commit()
    r = h.publicar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: conforme" in r.stdout
    assert "deriva anterior" in r.stdout
    assert "rotulo curado depois" in r.stdout
    assert h.current() == sha2

    # quem muda a persona da cadeira passa a responder pela rota dela
    h.persona(_persona("- **alfa** — outra descrição. rotulo real · rotulo curado depois."))
    h.commit()
    r = h.publicar()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "cadeiras que esta publicação muda: testecadeira" in r.stdout
    assert h.current() == sha2


def test_orfao_de_chapeu_recusa(h):
    h.persona(_persona(BULLET_ALFA, "- **fantasma** — sem diretório. rotulo real."))
    h.rotas_geradas()  # a tabela bate; o que sobra e o orfao
    h.commit()
    r = h.publicar()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "órfão de chapéu" in r.stdout
    assert "fantasma" in r.stdout
    assert h.current() is None


def test_orfao_de_conceito_so_avisa(h):
    h.persona(_persona("- **alfa** — descrição solta. rotulo real · rotulo que dados nao curou."))
    h.rotas_geradas()
    sha = h.commit()
    r = h.publicar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: conforme" in r.stdout
    assert "órfão de conceito" in r.stdout
    assert "rotulo que dados nao curou" in r.stdout
    assert h.current() == sha


def test_ordem_e_caixa_dos_gatilhos_nao_divergem(h):
    h.persona(_persona(BULLET_ALFA))
    tabela = h.rotas_geradas()
    tabela["testecadeira"]["alfa"] = [g.upper() for g in reversed(tabela["testecadeira"]["alfa"])]
    h.rotas(tabela)
    sha = h.commit()
    r = h.publicar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: conforme" in r.stdout
    assert h.current() == sha


def test_golden_fora_de_alcance_avisa_e_publica(h):
    h.persona(_persona(BULLET_ALFA))
    h.rotas({})
    sha = h.commit()
    r = h.publicar(PF_ROTAS_GOLDEN=str(h.tmp / "nao-existe.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: indeterminavel" in r.stdout
    assert "NAO conferido" in r.stderr
    assert h.current() == sha


@pytest.mark.parametrize("golden", [{"itens": [{"slug": "sem-rotulo"}]}, {"itens": None}])
def test_golden_fora_da_forma_e_indeterminavel_nunca_traceback(h, golden):
    h.persona(_persona(BULLET_ALFA))
    h.rotas({})
    sha = h.commit()
    h.golden.write_text(json.dumps(golden), encoding="utf-8")
    r = h.publicar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: indeterminavel" in r.stdout
    assert "Traceback" not in r.stdout + r.stderr
    assert h.current() == sha


def test_modo_aviso_nao_recusa_divergente(h):
    h.persona(_persona(BULLET_ALFA))
    h.rotas({})
    sha = h.commit()
    r = h.publicar(PF_ROTAS_GATE="aviso")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: divergente" in r.stdout
    assert "PF_ROTAS_GATE=aviso" in r.stderr
    assert h.current() == sha


def test_gate_desligado_nao_confere(h):
    h.persona(_persona(BULLET_ALFA))
    h.rotas({})
    sha = h.commit()
    r = h.publicar(PF_ROTAS_GATE="0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotas: " not in r.stdout
    assert "gate desligado" in r.stderr
    assert h.current() == sha
