"""eixos — o que os quatro atos `infra medir <eixo>` têm em comum (spec eixos-do-host R1 a R5).

Módulo de apoio de bin/infra, fora do PATH e do golden record (como os sub-atos de bin/_infra/); quem o
usa é o ato de cada eixo (medir-rede, e os de RAM, VRAM e processamento que vêm depois), nunca o dono
direto. Três coisas moram aqui, porque servem a mais de um eixo:

  - o JSON do eixo: os campos de topo, o `schema_v` e a validação (R2). O ato monta o dicionário por
    `montar()`, que recusa o que a ficha da família `eixo_host` recusaria;
  - a frase, gerada do JSON por uma função só, `frase()` (R2): nenhum ato escreve a frase à mão;
  - a chave de serviço `<stack>/<serviço>` (R4), resolvida por dois caminhos: o contêiner pelo projeto do
    compose contra o compose registrado na stack, e a unit pelo registro unit→stack (`acervo stack
    resolver`, story #3942). O que não resolve não tem chave e sai como desvio, nunca omitido:
    `fora_de_compose_e_unit` ou `unit_sem_stack`. Label, nome da unit, pid e linha de comando vão ao lado.

O teto se lê da máquina no instante da leitura e declara a fonte (R5); nenhum teto vem fixo no código.
Medida não reprova (R2): o valor nunca muda o código de saída. Só a fonte que não respondeu sai 5.

Contêiner → stack repete a regra de `stack_do_container` do conferir (bin/_release/conferir/conferir.py):
o conferir é um módulo de 3.400 linhas que mede o servido e não se importa daqui. A duplicação está
declarada no balde de débito técnico, e a cura é extrair a regra para uma lib.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_V = 1
EIXOS = ("rede", "ram", "vram", "cpu")
ESTADOS = ("lida", "nao_consegui_olhar")
UNIDADES = ("bytes", "ms", "contagem", "fracao", "threads")
DESVIOS = ("fora_de_compose_e_unit", "unit_sem_stack")
TUNEIS = ("ops", "recuperacao", "wiki")

SAIDA_OK = 0
SAIDA_NAO_CONSEGUI_OLHAR = 5

PREFIXO_DA_FAMILIA = "platafirma-"
TIMEOUT_DO_REGISTRO_S = 20
TIMEOUT_DO_DRIVER_S = 15
SHA_DE_GIT_TAMANHO = 40
KIB = 1 << 10

_RE_CAUSA = re.compile(r"^[a-z][a-z0-9_]*$")
_RE_CARIMBO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_RE_CHAVE = re.compile(r"^[^/\s]+/[^/\s]+$")
_RE_SHA = re.compile(rf"^[0-9a-f]{{{SHA_DE_GIT_TAMANHO}}}$")
_RE_CGROUP_CONTEINER = re.compile(r"docker-([0-9a-f]{64})\.scope")
_RE_CGROUP_UNIT = re.compile(r"([^/]+\.service)")

ACERVO = Path(__file__).resolve().parents[1] / "acervo"


class ErroDeLeitura(Exception):
    """A fonte não respondeu: vira `nao_consegui_olhar`, com a causa (slug) e a fonte, nunca zero."""

    def __init__(self, causa: str, fonte: str) -> None:
        super().__init__(f"{fonte}: {causa}")
        self.causa = causa
        self.fonte = fonte


# --- o JSON -----------------------------------------------------------------------------------

def carimbo(agora: datetime | None = None) -> str:
    """UTC com milissegundo, a forma de `ts` do evento de plataforma (arq:0133)."""
    t = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def _e_numero(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validar_topo(j: dict) -> list[str]:
    erros = []
    if j.get("schema_v") != SCHEMA_V:
        erros.append(f"schema_v deve ser {SCHEMA_V}")
    if j.get("eixo") not in EIXOS:
        erros.append(f"eixo fora de {EIXOS}")
    if not isinstance(j.get("instrumento"), str) or not j.get("instrumento"):
        erros.append("instrumento ausente")
    if not _RE_CARIMBO.match(str(j.get("carimbo", ""))):
        erros.append("carimbo fora de AAAA-MM-DDTHH:MM:SS.mmmZ")
    return erros


def _validar_estado(j: dict) -> list[str]:
    estado = j.get("estado_leitura")
    if estado not in ESTADOS:
        return [f"estado_leitura fora de {ESTADOS}"]
    erros = []
    if estado == "lida":
        if j.get("causa") is not None or j.get("fonte") is not None:
            erros.append("leitura lida não leva causa nem fonte")
        if j.get("valor") is None and j.get("eixo") != "rede":
            erros.append("leitura lida sem valor (só a rede guarda o número nos túneis)")
        return erros
    if not _RE_CAUSA.match(str(j.get("causa") or "")):
        erros.append("nao_consegui_olhar exige causa em slug")
    if not j.get("fonte"):
        erros.append("nao_consegui_olhar exige a fonte que não respondeu")
    if j.get("valor") is not None:
        erros.append("nao_consegui_olhar não leva valor: nunca zero")
    return erros


def _validar_numeros(j: dict) -> list[str]:
    erros = []
    valor, unidade = j.get("valor"), j.get("unidade")
    if (valor is None) != (unidade is None):
        erros.append("valor e unidade vão juntos")
    if valor is not None and not _e_numero(valor):
        erros.append("valor deve ser número")
    if unidade is not None and unidade not in UNIDADES:
        erros.append(f"unidade fora de {UNIDADES}")
    if (j.get("teto") is None) != (j.get("teto_fonte") is None):
        erros.append("teto e teto_fonte vão juntos")
    if j.get("teto") is not None and not _e_numero(j["teto"]):
        erros.append("teto deve ser número")
    if (j.get("limiar") is None) != (j.get("limiar_por") is None):
        erros.append("limiar e limiar_por vão juntos")
    if not _e_numero(j.get("janela")) or j["janela"] < 0:
        erros.append("janela deve ser número maior ou igual a zero (segundos)")
    return erros


def _validar_consumidores(j: dict) -> list[str]:
    consumidores = j.get("consumidores")
    if not isinstance(consumidores, list):
        return ["consumidores deve ser lista"]
    erros = []
    for i, c in enumerate(consumidores):
        tem_servico, tem_desvio = c.get("servico") is not None, c.get("desvio") is not None
        if tem_servico == tem_desvio:
            erros.append(f"consumidores[{i}]: servico ou desvio, um dos dois e nunca os dois")
        elif tem_servico and not _RE_CHAVE.match(str(c["servico"])):
            erros.append(f"consumidores[{i}]: servico fora da forma <stack>/<serviço>")
        elif tem_desvio and c["desvio"] not in DESVIOS:
            erros.append(f"consumidores[{i}]: desvio fora de {DESVIOS}")
    return erros


def _validar_tuneis(j: dict) -> list[str]:
    tuneis = j.get("tuneis")
    if not isinstance(tuneis, list) or not tuneis:
        return ["rede exige tuneis"]
    erros = []
    for t in tuneis:
        nome = t.get("tunel")
        if nome not in TUNEIS:
            erros.append(f"tuneis: tunel {nome!r} fora de {TUNEIS}")
        if t.get("estado_leitura") not in ESTADOS:
            erros.append(f"tuneis[{nome}]: estado_leitura fora de {ESTADOS}")
        elif t["estado_leitura"] == "lida":
            if t.get("causa") is not None:
                erros.append(f"tuneis[{nome}]: túnel lido não leva causa")
        elif not _RE_CAUSA.match(str(t.get("causa") or "")):
            erros.append(f"tuneis[{nome}]: túnel não lido exige causa em slug")
    return erros


def validar(j: dict) -> list[str]:
    """Os motivos pelos quais `j` não cumpre o schema da versão corrente; lista vazia quando cumpre."""
    erros = [*_validar_topo(j), *_validar_estado(j), *_validar_numeros(j), *_validar_consumidores(j)]
    if j.get("eixo") == "rede":
        erros += _validar_tuneis(j)
    return erros


def montar(  # noqa: PLR0913 — são os campos de topo do JSON do eixo (R2); por nome, nunca por posição
    eixo: str, instrumento: str, *, agora: datetime | None = None, estado: str = "lida",
    causa: str | None = None, fonte: str | None = None, valor: float | None = None,
    unidade: str | None = None, teto: float | None = None, teto_fonte: str | None = None,
    janela: float = 0, consumidores: list[dict] | None = None, **extras: object,
) -> dict:
    """O JSON do eixo com os campos de topo comuns (R2). `limiar` e `limiar_por` saem vazios até a rotina
    de pactuar; `janela` zero é a leitura instantânea. Levanta ValueError se o resultado não cumpre o schema."""
    j = {
        "schema_v": SCHEMA_V, "eixo": eixo, "carimbo": carimbo(agora), "instrumento": instrumento,
        "estado_leitura": estado, "causa": causa, "fonte": fonte, "valor": valor, "unidade": unidade,
        "teto": teto, "teto_fonte": teto_fonte, "janela": janela,
        "consumidores": list(consumidores or []), "limiar": None, "limiar_por": None,
    }
    j.update(extras)
    erros = validar(j)
    if erros:
        raise ValueError("JSON do eixo fora do schema: " + "; ".join(erros))
    return j


def codigo_de_saida(j: dict) -> int:
    """5 só quando a fonte não respondeu; o valor lido, por alto que seja, sai 0 (R2, R3)."""
    return SAIDA_OK if j.get("estado_leitura") == "lida" else SAIDA_NAO_CONSEGUI_OLHAR


# --- a frase ----------------------------------------------------------------------------------

_NOME_DO_EIXO = {"rede": "Rede", "ram": "Memória", "vram": "VRAM", "cpu": "Processamento"}


def _num(v: float, casas: int = 1) -> str:
    texto = f"{v:.{casas}f}".rstrip("0").rstrip(".") if casas else f"{v:.0f}"
    return (texto or "0").replace(".", ",")


def _bytes(v: float) -> str:
    for limite, sufixo in ((1 << 30, "GiB"), (1 << 20, "MiB"), (KIB, "KiB")):
        if abs(v) >= limite:
            return f"{_num(v / limite)} {sufixo}"
    return f"{_num(v, 0)} B"


def formatar(valor: float | None, unidade: str | None) -> str:
    if valor is None:
        return "sem número"
    if unidade == "bytes":
        return _bytes(valor)
    if unidade == "ms":
        return f"{_num(valor)} ms"
    if unidade == "fracao":
        return f"{_num(valor * 100)}%"
    if unidade == "threads":
        return f"{_num(valor, 0)} threads"
    return _num(valor)


def _hora(j: dict) -> str:
    return str(j.get("carimbo", ""))[11:19] + " UTC"


def _plural(n: float, singular: str, plural: str) -> str:
    return f"{_num(n, 0)} {singular if n == 1 else plural}"


def _quem(c: dict) -> str:
    """Como a frase chama um consumidor: a chave, ou o desvio com o que o identifica."""
    if c.get("servico"):
        return c["servico"]
    onde = c.get("unit") or c.get("conteiner") or c.get("executavel") or "processo"
    resto = f", pid {c['pid']}" if c.get("pid") else ""
    comando = f", {c['linha_de_comando'][:80]}" if c.get("linha_de_comando") else ""
    return f"sem dono ({c['desvio']}: {onde}{resto}{comando})"


def _frase_do_tunel(t: dict) -> str:
    nome = t["tunel"]
    if t["estado_leitura"] != "lida":
        return f"{nome} não consegui olhar ({t['causa']})"
    partes = [f"{nome} com {_plural(t['conexoes_borda'], 'conexão', 'conexões')} na borda"
              if t.get("conexoes_borda") is not None else f"{nome} sem contagem de conexões"]
    if t.get("reconexoes_acumuladas") is not None:
        partes.append(f"{_plural(t['reconexoes_acumuladas'], 'reconexão', 'reconexões')} desde a partida")
    if t.get("latencia_externa_ms") is not None:
        porta = f"a porta leva {_num(t['latencia_externa_ms'])} ms por fora"
        if t.get("dur_ms_porta") is not None:
            porta += f" contra {_num(t['dur_ms_porta'])} ms que ela mesma registrou"
        partes.append(porta)
    if t.get("erros_transporte"):
        partes.append(f"{_plural(t['erros_transporte'], 'erro', 'erros')} de transporte")
    if t.get("erro_verbo"):
        partes.append(f"erro de verbo ({t['erro_verbo']})")
    if t.get("porta_nao_lida"):
        partes.append(f"porta não medida ({t['porta_nao_lida']})")
    return ", ".join(partes)


def _frase_do_valor(j: dict) -> str:
    texto = formatar(j.get("valor"), j.get("unidade"))
    if j.get("teto") is not None:
        texto += f" de {formatar(j['teto'], j.get('unidade'))} ({j['teto_fonte']})"
    if j.get("pressao_avg10") is not None:
        texto += (f"; pressão do kernel {_num(j['pressao_avg10'])}/{_num(j['pressao_avg60'])}/"
                  f"{_num(j['pressao_avg300'])}% em 10, 60 e 300 s")
    if j.get("cache_bytes") is not None:
        texto += f"; cache que o kernel devolve {_bytes(j['cache_bytes'])}"
    return texto


def frase(j: dict) -> str:
    """A frase do eixo, gerada do JSON. É a única: `infra medir <eixo>` imprime exatamente isto."""
    nome = _NOME_DO_EIXO.get(j.get("eixo"), str(j.get("eixo")))
    hora = _hora(j)
    tuneis = j.get("tuneis") or []
    if j.get("estado_leitura") != "lida":
        texto = f"{nome} às {hora}: não consegui olhar {j.get('fonte')} ({j.get('causa')})"
        if tuneis:
            texto += "; o que se leu: " + "; ".join(_frase_do_tunel(t) for t in tuneis)
        return texto + "."
    if j.get("eixo") == "rede":
        texto = f"{nome} às {hora}: " + "; ".join(_frase_do_tunel(t) for t in tuneis)
    else:
        texto = f"{nome} às {hora}: {_frase_do_valor(j)}"
    consumidores = j.get("consumidores") or []
    if consumidores:
        texto += "; consumidores: " + ", ".join(_quem(c) for c in consumidores)
    return texto + "."


# --- o teto, lido da máquina (R5) ---------------------------------------------------------------

def teto_ram(meminfo: str = "/proc/meminfo") -> tuple[int, str]:
    """(bytes, fonte) da memória total da máquina."""
    try:
        for linha in Path(meminfo).read_text(encoding="utf-8").splitlines():
            if linha.startswith("MemTotal:"):
                return int(linha.split()[1]) * KIB, f"{meminfo}:MemTotal"
    except (OSError, ValueError, IndexError):
        raise ErroDeLeitura("ilegivel", meminfo) from None
    raise ErroDeLeitura("memtotal_ausente", meminfo)


def teto_threads(cpuinfo: str = "/proc/cpuinfo") -> tuple[int, str]:
    """(threads, fonte) do processamento: uma linha `processor` por thread lógica."""
    try:
        n = sum(1 for linha in Path(cpuinfo).read_text(encoding="utf-8").splitlines() if linha.startswith("processor"))
    except OSError:
        raise ErroDeLeitura("ilegivel", cpuinfo) from None
    if n == 0:
        raise ErroDeLeitura("sem_processador", cpuinfo)
    return n, f"{cpuinfo}:processor"


def teto_vram(nvidia_smi: str = "nvidia-smi") -> tuple[int, str]:
    """(bytes, fonte) da memória da placa, pelo driver."""
    fonte = f"{nvidia_smi} --query-gpu=memory.total"
    try:
        p = subprocess.run([nvidia_smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=TIMEOUT_DO_DRIVER_S, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ErroDeLeitura("driver_fora", fonte) from None
    if p.returncode != 0 or not p.stdout.strip():
        raise ErroDeLeitura("driver_fora", fonte)
    try:
        return int(float(p.stdout.splitlines()[0].strip())) * (1 << 20), fonte
    except ValueError:
        raise ErroDeLeitura("saida_ilegivel", fonte) from None


# --- a chave de serviço (R4) ---------------------------------------------------------------------

def carregar_topologia(acervo: str | Path | None = None, timeout: int = TIMEOUT_DO_REGISTRO_S) -> list[dict]:
    """O registro de stacks (`acervo stack ver --json`): slug e compose declarado de cada uma."""
    fonte = "acervo stack ver"
    try:
        p = subprocess.run([str(acervo or ACERVO), "stack", "ver", "--json"], capture_output=True, text=True,
                           timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ErroDeLeitura("registro_de_stack_indisponivel", fonte) from None
    if p.returncode != 0:
        raise ErroDeLeitura("registro_de_stack_indisponivel", fonte)
    try:
        topologia = json.loads(p.stdout)
    except ValueError:
        raise ErroDeLeitura("registro_de_stack_ilegivel", fonte) from None
    if not isinstance(topologia, list):
        raise ErroDeLeitura("registro_de_stack_ilegivel", fonte)
    return topologia


def _composes(stack: dict) -> list[str]:
    v = stack.get("compose") or []
    return [v] if isinstance(v, str) else list(v)


def stack_do_conteiner(labels: dict, topologia: list[dict]) -> str | None:
    """Slug da stack cujo compose declarado é o do contêiner. O declarado mora sob .../current/<família
    curta>/<rel>; o contêiner sobe de .../<família>/<sha>/<rel> e casa pela família curta e pelo <rel>.
    Duas stacks com o mesmo compose desempatam pelo projeto que o contêiner declara; sem desempate, None."""
    pares = set()
    for arquivo in (labels.get("com.docker.compose.project.config_files") or "").split(","):
        partes = arquivo.strip().split("/")
        for i, parte in enumerate(partes):
            if _RE_SHA.match(parte):
                familia = partes[i - 1] if i > 0 else ""
                pares.add((familia.removeprefix(PREFIXO_DA_FAMILIA), "/".join(partes[i + 1:])))
                break
    achados = []
    for stack in topologia:
        for comp in _composes(stack):
            if "/current/" not in comp:
                continue
            resto = comp.split("/current/", 1)[1]
            if "/" in resto and tuple(resto.split("/", 1)) in pares:
                achados.append(stack.get("slug"))
    if len(achados) <= 1:
        return achados[0] if achados else None
    projeto = labels.get("com.docker.compose.project")
    do_projeto = [slug for slug in achados if slug == projeto]
    return do_projeto[0] if len(do_projeto) == 1 else None


def chave_de_conteiner(nome: str, labels: dict, topologia: list[dict]) -> dict:
    """{"conteiner", "servico"} quando o projeto do compose do contêiner é de uma stack do registro; senão
    {"conteiner", "desvio": "fora_de_compose_e_unit"}. Compose que o registro não conhece conta como fora."""
    base = {"conteiner": nome}
    servico = labels.get("com.docker.compose.service")
    if not labels.get("com.docker.compose.project") or not servico:
        return {**base, "desvio": "fora_de_compose_e_unit"}
    stack = stack_do_conteiner(labels, topologia)
    if not stack:
        return {**base, "desvio": "fora_de_compose_e_unit"}
    return {**base, "servico": f"{stack}/{servico}"}


def resolvedor_do_registro(
    acervo: str | Path | None = None, timeout: int = TIMEOUT_DO_REGISTRO_S,
) -> Callable[[str], str | None]:
    """Função unit → chave (ou None, quando a unit não está no registro), pelo `acervo stack resolver`."""
    fonte = "acervo stack resolver"

    def resolver(unit: str) -> str | None:
        try:
            p = subprocess.run([str(acervo or ACERVO), "stack", "resolver", unit], capture_output=True, text=True,
                               timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise ErroDeLeitura("registro_de_stack_indisponivel", fonte) from None
        if p.returncode == 0 and _RE_CHAVE.match(p.stdout.strip()):
            return p.stdout.strip()
        if p.returncode == 1 and "unit_sem_stack" in p.stderr:
            return None
        raise ErroDeLeitura("registro_de_stack_indisponivel", fonte)

    return resolver


def chave_de_unit(unit: str, resolver: Callable[[str], str | None]) -> dict:
    """{"unit", "servico"} pelo registro unit→stack; unit que ele não conhece sai {"unit", "desvio": "unit_sem_stack"}."""
    chave = resolver(unit)
    if chave:
        return {"unit": unit, "servico": chave}
    return {"unit": unit, "desvio": "unit_sem_stack"}


def resolver_pid(
    pid: int, *, proc: str | Path = "/proc", inspecionar: Callable[[str], tuple[str, dict]],
    resolver_unit: Callable[[str], str | None], topologia: list[dict],
) -> dict:
    """A chave de um processo pelo cgroup dele: contêiner de compose pelo projeto, unit pelo registro, ou o
    desvio `fora_de_compose_e_unit` quando não está em nenhum dos dois. `inspecionar(id)` devolve
    (nome, labels) do contêiner. Pid, executável e linha de comando vão ao lado, como forma de entrada."""
    raiz = Path(proc) / str(pid)
    lado = {"pid": pid}
    try:
        cgroup = (raiz / "cgroup").read_text(encoding="utf-8")
    except OSError:
        return {**lado, "desvio": "fora_de_compose_e_unit", "detalhe": "cgroup_ilegivel"}
    try:
        lado["executavel"] = (raiz / "comm").read_text(encoding="utf-8").strip()
        lado["linha_de_comando"] = (raiz / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except OSError:
        pass
    achado = _RE_CGROUP_CONTEINER.search(cgroup)
    if achado:
        nome, labels = inspecionar(achado.group(1))
        return {**lado, **chave_de_conteiner(nome, labels, topologia)}
    units = [u for u in _RE_CGROUP_UNIT.findall(cgroup) if not u.startswith("user@")]
    if units:
        return {**lado, **chave_de_unit(units[-1], resolver_unit)}
    return {**lado, "desvio": "fora_de_compose_e_unit"}


def imprimir_saida(j: dict, *, como_json: bool) -> int:
    """O que o ato escreve em stdout (o JSON, ou a frase gerada dele) e o código de saída (R2, R3)."""
    print(json.dumps(j, ensure_ascii=False, indent=2) if como_json else frase(j))
    return codigo_de_saida(j)
