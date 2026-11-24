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

from ._raizes import instancia, release
from .verbos import HARNESS, ResultadoVerbo, chamar, chamar_texto
from abertura.nomes import SecaoDasCadeiras, carregar_secao_das_cadeiras  # noqa: E402

log = logging.getLogger("agregador")

# Estado e dado da instancia, nunca arquivo dentro da arvore de codigo (a release e r-x).
ESTADO_PATH = Path(
    os.environ.get("AGREGADOR_ESTADO_PATH",
                   str(instancia() / "var" / "run" / "harness-controle" / "estado.json"))
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


def _casa_raiz() -> Path:
    return Path(os.environ.get("PF_CASA_RAIZ") or str(release() / "casa"))


def _secao_cadeiras() -> SecaoDasCadeiras:
    try:
        return carregar_secao_das_cadeiras(base=_casa_raiz())
    except OSError:
        return SecaoDasCadeiras()


def _cadeiras_disponiveis() -> list[str]:
    # Fonte canonica na casa nova: secao Nomes das personas em <casa>/instancias/persona/*.md,
    # carregada por lib/abertura/nomes.py (o antigo `persona foto` saiu na migracao).
    return sorted(_secao_cadeiras().cadeiras)


def _chapeus_disponiveis() -> list[str]:
    """`<cadeira>/<chapeu>` de todo chapeu publicado na casa nova."""
    secao = _secao_cadeiras()
    return sorted(
        f"{cad}/{ch}"
        for cad, decl in secao.cadeiras.items()
        for ch in decl.chapeus
    )


def _skills_disponiveis() -> list[str]:
    d = HARNESS / "skills"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def _env_sonda() -> dict[str, str]:
    """O agregador nao e sessao de cadeira nenhuma: le como "sonda", identidade
    propria de leitura automatica (LEITOR em fila). Sonda mede
    profundidade de caixa e nada mais — ler e enviar sao negados no proprio
    verbo, e ela nao esta no roster do ledger, entao nem destinataria e."""
    e = dict(os.environ)
    e["PF_CADEIRA"] = "sonda"
    return e


def _env_caixa(persona: str) -> dict[str, str]:
    """Le a caixa a FRIO como a propria dona: PF_CADEIRA e o slug, entao `so_minha`
    aprova, e `fila ler --tudo` (XRANGE) nao move o ponteiro do grupo nem cria
    consumer. A tela le o conteudo sem queimar carta nem falsear a 'ultima
    leitura' — a leitura fria que a spec exige (bloco 3, §5)."""
    e = dict(os.environ)
    e["PF_CADEIRA"] = persona
    return e


def _env_casa(cadeira: str) -> dict[str, str]:
    e = dict(os.environ)
    e["PF_CADEIRA"] = cadeira
    e.setdefault("PF_CASA_RAIZ", str(_casa_raiz()))
    return e


def _env_padrao() -> dict[str, str]:
    return dict(os.environ)


def _peca_texto(pid: str, ref: str, r: ResultadoVerbo) -> dict:
    if r.ok and isinstance(r.dados, dict) and r.dados.get("texto"):
        texto = str(r.dados["texto"])
        return {
            "peca": pid,
            "ref": ref,
            "sha": None,
            "frescor": "fresco",
            "tokens": max(1, len(texto) // 4),
            "conteudo": texto,
            "motivo": None,
        }
    return {
        "peca": pid,
        "ref": ref,
        "sha": None,
        "frescor": "indisponivel",
        "tokens": 0,
        "conteudo": None,
        "motivo": r.motivo or "sem conteudo",
    }


def _formatar_lousa_mesa(itens: list[dict]) -> str:
    """Converte a lista JSON de `mesa ver --json` (lousa da casa nova) no formato
    que `md_render.render_mesa` e `contagem_mesa` leem por chapeu."""
    if not itens:
        return "mesa vazia"
    linhas: list[str] = []
    for it in itens:
        chave = str(it.get("chave") or it.get("card") or "item").strip()
        chapeu = str(it.get("chapeu") or "geral").strip()
        situacao = str(it.get("situacao") or "").strip()
        estagio = str(it.get("estagio") or "").strip()
        proxima = str(it.get("proxima_jogada") or "").strip()
        cab_ato = f"({situacao}) {estagio}".strip() if situacao else estagio
        if proxima:
            cab = f"#{chave} [{chapeu}] {cab_ato} → {proxima}"
        else:
            cab = f"#{chave} [{chapeu}] {cab_ato}"
        linhas.append(cab.strip())
        ocasiao = it.get("ocasiao")
        if isinstance(ocasiao, dict):
            partes_oc = [f"{k}: {v}" for k, v in ocasiao.items() if v]
            if partes_oc:
                linhas.append("ocasião: " + " · ".join(partes_oc))
        corpo = (it.get("corpo") or "").strip()
        if corpo:
            linhas.append(corpo)
    return "\n".join(linhas)


def _coletar_cadeira(cadeira: str, timeout: float) -> ResultadoVerbo:
    """Leitura fria de uma cadeira na casa nova (sem abrir sessao nem tocar o oplog):
    persona, cultura (GERAL), apelidos (Org) e mesa (`mesa ver --json`)."""
    env = _env_casa(cadeira)
    secao = _secao_cadeiras()
    chapeus = list(secao.cadeiras[cadeira].chapeus.keys()) if cadeira in secao.cadeiras else []

    r_persona = chamar_texto(["persona", "ler", cadeira, "--parte", "persona"], timeout=timeout, env=env)
    r_cultura = chamar_texto(["persona", "cultura"], timeout=timeout, env=env)
    r_org = chamar_texto(["persona", "apelidos"], timeout=timeout, env=env)
    r_mesa = chamar(["mesa", "ver", "--json"], timeout=timeout, env=env)

    dur = r_persona.duracao_seg + r_cultura.duracao_seg + r_org.duracao_seg + r_mesa.duracao_seg
    if not r_persona.ok and not r_mesa.ok:
        motivo = r_persona.motivo or r_mesa.motivo or "leitura indisponivel"
        return ResultadoVerbo(False, None, motivo, r_persona.exit_code, dur)

    if r_mesa.ok and isinstance(r_mesa.dados, list):
        mesa_txt = _formatar_lousa_mesa(r_mesa.dados)
        peca_mesa = {
            "peca": "mesa",
            "ref": "mesa ver --json",
            "sha": None,
            "frescor": "fresco",
            "tokens": max(1, len(mesa_txt) // 4),
            "conteudo": mesa_txt,
            "motivo": None,
        }
    else:
        peca_mesa = {
            "peca": "mesa",
            "ref": "mesa ver --json",
            "sha": None,
            "frescor": "indisponivel",
            "tokens": 0,
            "conteudo": None,
            "motivo": r_mesa.motivo or "saida invalida de mesa ver",
        }

    pecas = [
        _peca_texto("persona", f"persona ler {cadeira} --parte persona", r_persona),
        _peca_texto("conduta", "persona cultura", r_cultura),
        _peca_texto("alias-cadeiras", "persona apelidos", r_org),
        peca_mesa,
    ]
    return ResultadoVerbo(
        True,
        {
            "cadeira": cadeira,
            "nome_canonico": cadeira,
            "chapeus": chapeus,
            "pecas": pecas,
        },
        None,
        0,
        dur,
    )


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
    # verbo de leitura que devolve texto cru, sem --json (`persona ler`): dados = {"texto": ...}
    texto: bool = False
    # coletor composto (quando um item agrega leituras frias de varios verbos, sem abrir sessao)
    coletor: Callable[[str, float], ResultadoVerbo] | None = None


SONDAS: list[Sonda] = [
    Sonda("infra_estado", _intervalo("INFRA", 30), _timeout("INFRA", 15),
          lambda: ["infra", "estado", "--json"]),
    Sonda("infra_saude", _intervalo("INFRA", 30), _timeout("INFRA", 15),
          lambda: ["infra", "saude", "--json"]),
    Sonda("fila_status", _intervalo("FILA", 30), _timeout("FILA", 15),
          lambda: ["fila", "status", "--todas", "--json"], _env_sonda),
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
               lambda c: ["persona", "ler", c, "--parte", "persona"],
               fabrica_env=_env_casa,
               chave_item="cadeira",
               coletor=_coletar_cadeira),
    # O texto de cada chapeu da casa nova, pra tela ter onde LER o chapeu.
    # Um item por `<cadeira>/<chapeu>`.
    SondaGrupo("chapeus", _intervalo("CHAPEUS", 120), _timeout("CHAPEUS", 15),
               _chapeus_disponiveis,
               lambda it: ["persona", "ler", it.split("/", 1)[0], "--chapeu", it.split("/", 1)[1]],
               fabrica_env=lambda it: _env_casa(it.split("/", 1)[0]),
               chave_item="chapeu", texto=True),
    SondaGrupo("skills", _intervalo("SKILLS", 120), _timeout("SKILLS", 15),
               _skills_disponiveis,
               lambda s: ["conferir", "skill", s, "--json"],
               chave_item="skill"),
    # Conteudo das caixas, a FRIO (--tudo = XRANGE), uma por cadeira, lida como a
    # propria dona. O `status` (acima) so mede profundidade; este traz as cartas
    # pra tela ter onde ser lida. Nunca consome: leitura fria e o que a spec manda.
    SondaGrupo("caixa_conteudo", _intervalo("CAIXA", 60), _timeout("CAIXA", 20),
               _cadeiras_disponiveis,
               lambda p: ["fila", "ler", p, "--tudo", "--json"],
               _env_caixa,
               chave_item="persona"),
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
            if g.coletor is not None:
                resultado = g.coletor(item, g.timeout_seg)
            else:
                leitor = chamar_texto if g.texto else chamar
                resultado = leitor(g.fabrica_argv(item), timeout=g.timeout_seg, env=g.fabrica_env(item))
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
