# agregador — le os verbos em timer independente por verbo e escreve um unico
# arquivo de estado em JSON (controle/estado.json). A tela nunca executa verbo
# em resposta a request: so le este arquivo.
# capacidade: expediente
# dono: claudinho-TI
"""LOTE 2 do card #390. Duas camadas, deliberadamente separadas:

- `bloco_de()` — funcao pura: ResultadoVerbo -> bloco de estado. Esta e a
  camada inegociavel do modelo de teste do card: "verbo morto -> indisponivel
  com motivo, nunca ausencia do bloco e nunca zero". Testada sem subprocess,
  sem thread, sem arquivo.
- `Agregador` — orquestra: uma thread por sonda (ou por item de SondaGrupo),
  timer proprio, escreve o `estado.json` inteiro a cada atualizacao via
  arquivo temporario + os.replace (a tela nunca le uma leitura pela metade).

O agregador NAO escreve em lugar nenhum alem do proprio arquivo de estado —
inclusive a leitura de fila e sempre fria (`fila status`, nunca `fila ler`).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .verbos import ResultadoVerbo, chamar

log = logging.getLogger("agregador")

ESTADO_PATH = Path(
    os.environ.get("AGREGADOR_ESTADO_PATH", str(Path(__file__).resolve().parents[1] / "estado.json"))
)


# --- camada inegociavel: saida-de-verbo -> bloco de estado ------------------


def bloco_de(resultado: ResultadoVerbo, *, agora: float | None = None) -> dict:
    """Transforma o resultado de UMA chamada de verbo num bloco de estado.

    Regra dura (spec + card): zero legitimo (ex. 0 divergencias) e ausencia de
    leitura sao valores distintos — nunca colapsados. Verbo que falhou, deu
    timeout ou nao respondeu vira {"estado": "indisponivel", "motivo": ...},
    nunca {"estado": "ok", "dados": None} nem qualquer forma que pareca zero.
    """
    agora = time.time() if agora is None else agora
    if not resultado.ok:
        return {
            "lido_em": agora,
            "estado": "indisponivel",
            "motivo": resultado.motivo,
            "dados": None,
        }
    dados = resultado.dados
    # "erro" so faz sentido checar quando dados e um objeto (alguns verbos —
    # fila status --json — devolvem array no caminho feliz).
    if isinstance(dados, dict) and dados.get("erro"):
        return {
            "lido_em": agora,
            "estado": "indisponivel",
            "motivo": dados["erro"],
            "dados": None,
        }
    return {"lido_em": agora, "estado": "ok", "motivo": None, "dados": dados}


# --- sondas: o que chamar, com que intervalo -------------------------------


def _raiz() -> Path:
    return Path(os.environ.get("PF_RAIZ", os.path.expanduser("~/AI")))


def _cadeiras_disponiveis() -> list[str]:
    d = _raiz() / "platafirma-harness" / "personas"
    if not d.is_dir():
        return []
    return sorted(p.name.removeprefix("persona-").removesuffix(".md") for p in d.glob("persona-*.md"))


def _skills_disponiveis() -> list[str]:
    d = _raiz() / "platafirma-harness" / "skills"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def _env_sonda() -> dict[str, str]:
    """O agregador nao e sessao de cadeira nenhuma: le como "sonda", identidade
    propria de leitura automatica (LEITOR em fila_streams.py). Sonda mede
    profundidade de caixa e nada mais — ler e enviar sao negados no proprio
    verbo, e ela nao esta em .personas, entao nem destinataria e."""
    e = dict(os.environ)
    e["PF_CADEIRA"] = "sonda"
    return e


def _env_padrao() -> dict[str, str]:
    return dict(os.environ)


def _intervalo(nome: str, default: float) -> float:
    return float(os.environ.get(f"AGREGADOR_INTERVALO_{nome.upper()}", default))


def _timeout(nome: str, default: float) -> float:
    return float(os.environ.get(f"AGREGADOR_TIMEOUT_{nome.upper()}", default))


@dataclass(frozen=True)
class Sonda:
    """Uma leitura de verbo por tick — um timer/thread proprio."""

    nome: str
    intervalo_seg: float
    timeout_seg: float
    fabrica_argv: Callable[[], list[str]]
    fabrica_env: Callable[[], dict[str, str]] = _env_padrao


@dataclass(frozen=True)
class SondaGrupo:
    """N leituras por tick — uma por item de uma lista descoberta na hora (ex.:
    uma por cadeira, uma por skill). Cada item carrega o proprio estado/motivo;
    UM item indisponivel nunca derruba os outros nem o bloco do grupo inteiro."""

    nome: str
    intervalo_seg: float
    timeout_seg: float
    fabrica_itens: Callable[[], list[str]]
    fabrica_argv: Callable[[str], list[str]]
    fabrica_env: Callable[[str], dict[str, str]] = lambda _item: _env_padrao()
    chave_item: str = "item"


SONDAS: list[Sonda] = [
    Sonda("infra_estado", _intervalo("INFRA", 30), _timeout("INFRA", 15),
          lambda: ["infra", "estado", "--json"]),
    Sonda("infra_saude", _intervalo("INFRA", 30), _timeout("INFRA", 15),
          lambda: ["infra", "saude", "--json"]),
    Sonda("fila_status", _intervalo("FILA", 30), _timeout("FILA", 15),
          lambda: ["fila_streams.py", "status", "--todas", "--json"], _env_sonda),
    Sonda("conferir_servico", _intervalo("CONFERIR", 90), _timeout("CONFERIR", 60),
          lambda: ["conferir", "servico", "--json"]),
    Sonda("conferir_verbo", _intervalo("CONFERIR", 90), _timeout("CONFERIR", 30),
          lambda: ["conferir", "verbo", "--json"]),
    Sonda("conferir_repo", _intervalo("CONFERIR", 90), _timeout("CONFERIR", 60),
          lambda: ["conferir", "repo", "--json"]),
]

SONDAS_GRUPO: list[SondaGrupo] = [
    SondaGrupo("cadeiras", _intervalo("CADEIRAS", 45), _timeout("CADEIRAS", 15),
               _cadeiras_disponiveis,
               lambda c: ["monta-sessao", c, "--json", "--sem-atualizar"],
               chave_item="cadeira"),
    SondaGrupo("skills", _intervalo("SKILLS", 120), _timeout("SKILLS", 15),
               _skills_disponiveis,
               lambda s: ["conferir", "skill", s, "--json"],
               chave_item="skill"),
]


# --- orquestracao -------------------------------------------------------


def _grava_atomico(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(caminho.parent), prefix=".estado-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=None, separators=(",", ":"))
        os.replace(tmp, caminho)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Agregador:
    """Mantem um dict de estado em memoria (uma chave por sonda), atualizado
    por threads independentes, e persiste o dict inteiro a cada atualizacao."""

    def __init__(
        self,
        estado_path: Path = ESTADO_PATH,
        sondas: list[Sonda] | None = None,
        sondas_grupo: list[SondaGrupo] | None = None,
    ):
        self.estado_path = estado_path
        self.sondas = SONDAS if sondas is None else sondas
        self.sondas_grupo = SONDAS_GRUPO if sondas_grupo is None else sondas_grupo
        self._lock = threading.Lock()
        self._estado: dict = {}
        self._parar = threading.Event()
        self._threads: list[threading.Thread] = []

    # -- ciclo de uma sonda simples --

    def _ciclo_sonda(self, s: Sonda) -> None:
        resultado = chamar(s.fabrica_argv(), timeout=s.timeout_seg, env=s.fabrica_env())
        bloco = bloco_de(resultado)
        with self._lock:
            self._estado[s.nome] = bloco
            self._persiste()

    def _ciclo_sonda_grupo(self, g: SondaGrupo) -> None:
        try:
            itens = g.fabrica_itens()
        except OSError as e:
            with self._lock:
                self._estado[g.nome] = {
                    "lido_em": time.time(),
                    "estado": "indisponivel",
                    "motivo": f"nao foi possivel listar itens de {g.nome}: {e}",
                    "itens": [],
                }
                self._persiste()
            return

        blocos = []
        for item in itens:
            resultado = chamar(g.fabrica_argv(item), timeout=g.timeout_seg, env=g.fabrica_env(item))
            bloco = bloco_de(resultado)
            bloco[g.chave_item] = item
            blocos.append(bloco)

        with self._lock:
            self._estado[g.nome] = {
                "lido_em": time.time(),
                "estado": "ok" if itens else "indisponivel",
                "motivo": None if itens else "nenhum item encontrado",
                "itens": blocos,
            }
            self._persiste()

    def _persiste(self) -> None:
        """Chamado sob self._lock — grava o dict inteiro, atomico."""
        _grava_atomico(self.estado_path, self._estado)

    # -- loop por sonda, timer independente --

    def _loop(self, ciclo: Callable[[], None], intervalo: float, nome: str) -> None:
        while not self._parar.is_set():
            try:
                ciclo()
            except Exception:  # nunca deixa uma sonda matar o processo inteiro
                log.exception("sonda %s: falha inesperada no ciclo", nome)
            self._parar.wait(intervalo)

    def iniciar(self) -> None:
        for s in self.sondas:
            t = threading.Thread(
                target=self._loop, args=(lambda s=s: self._ciclo_sonda(s), s.intervalo_seg, s.nome),
                name=f"sonda-{s.nome}", daemon=True,
            )
            self._threads.append(t)
            t.start()
        for g in self.sondas_grupo:
            t = threading.Thread(
                target=self._loop,
                args=(lambda g=g: self._ciclo_sonda_grupo(g), g.intervalo_seg, g.nome),
                name=f"sonda-{g.nome}", daemon=True,
            )
            self._threads.append(t)
            t.start()

    def parar(self, timeout: float = 5.0) -> None:
        self._parar.set()
        for t in self._threads:
            t.join(timeout=timeout)

    def rodar_para_sempre(self) -> None:
        self.iniciar()
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            self.parar()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log.info("agregador: escrevendo estado em %s", ESTADO_PATH)
    Agregador().rodar_para_sempre()


if __name__ == "__main__":
    main()
