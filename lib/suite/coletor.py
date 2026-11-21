"""Coletor da esteira: julga os resultados brutos da rodada, grava o veredito e abre débitos (#4297)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from suite.admissao import RecusaAdmissao, ResultadoAdmissao

PRAZO_QUARENTENA_DIAS = 30
ESTADOS_VEREDITO = frozenset({"verde", "vermelho", "nao-medido"})
PREFIXO_QUARENTENA = "errático: "
PREFIXO_QUARENTENA_ASCII = "erratico: "
MAX_DEBITOS_POR_RODADA = 1
_MAX_CASOS_NO_TEXTO_DT = 10
_RE_IDADE_DIAS = re.compile(r"^(\d+)d?$")
_MAX_TAMANHO_PREFIXO_VERBO = 25
_COLUNAS_TABELA_DT = 4
_SAIDA_NAO_MEDIDO = 3


@dataclass(frozen=True)
class LinhaBalde:
    numero: int
    idade_dias: int
    stack: str
    texto: str

    def como_dict(self) -> dict[str, Any]:
        return {
            "numero": self.numero,
            "idade_dias": self.idade_dias,
            "stack": self.stack,
            "texto": self.texto,
        }


@dataclass(frozen=True)
class CasoSelecionado:
    id_caso: str
    arquivo: str
    nome_caso: str
    componente: str
    classe: str
    exige: tuple[str, ...] = ()
    incidentes: tuple[int, ...] = ()
    no_alcance: bool = True
    stack: str = "harness"

    @property
    def fora_do_alcance_incidente(self) -> bool:
        return bool(self.incidentes) and not self.no_alcance


@dataclass(frozen=True)
class ResultadoBrutoCaso:
    id_caso: str
    aprovado: bool
    tentativas: int = 1
    passou_em_repeticao: bool = False
    saida: str = ""

    @property
    def medido_erratico(self) -> bool:
        return (not self.aprovado) and self.passou_em_repeticao

    def como_dict(self) -> dict[str, Any]:
        return {
            "id_caso": self.id_caso,
            "aprovado": self.aprovado,
            "tentativas": self.tentativas,
            "passou_em_repeticao": self.passou_em_repeticao,
            "saida": self.saida,
        }


@dataclass(frozen=True)
class VereditoRodada:
    repositorio: str
    arvore_mudanca: str
    arvore_main: str
    estado: str
    casos_reprovados: tuple[str, ...]
    fichas_ensaiadas: tuple[dict[str, Any], ...]
    hora: str
    codigo_saida: int
    motivo: str | None = None
    casos_rodados: tuple[str, ...] = ()
    casos_quarentena: tuple[str, ...] = ()
    debitos_abertos: tuple[str, ...] = ()

    def como_registro(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "repositorio": self.repositorio,
            "arvore_mudanca": self.arvore_mudanca,
            "arvore_main": self.arvore_main,
            "estado": self.estado,
            "casos_reprovados": list(self.casos_reprovados),
            "fichas_ensaiadas": list(self.fichas_ensaiadas),
            "hora": self.hora,
        }
        if self.motivo:
            d["motivo"] = self.motivo
        return d

    def como_dict(self) -> dict[str, Any]:
        d = self.como_registro()
        d["codigo_saida"] = self.codigo_saida
        d["casos_rodados"] = list(self.casos_rodados)
        d["casos_quarentena"] = list(self.casos_quarentena)
        d["debitos_abertos"] = list(self.debitos_abertos)
        return d

    def resumo_texto(self) -> str:
        mud_curto = self.arvore_mudanca[:12] if self.arvore_mudanca else "?"
        main_curto = self.arvore_main[:12] if self.arvore_main else "?"
        cab = f"veredito {self.repositorio} (mudanca={mud_curto} base={main_curto}): {self.estado}"
        linhas = [cab]
        if self.motivo:
            linhas.append(f"  motivo: {self.motivo}")
        if self.casos_reprovados:
            linhas.append(f"  reprovados ({len(self.casos_reprovados)}): {', '.join(self.casos_reprovados)}")
        if self.casos_quarentena:
            linhas.append(f"  quarentena ({len(self.casos_quarentena)}): {', '.join(self.casos_quarentena)}")
        if self.debitos_abertos:
            linhas.append(f"  débitos abertos ({len(self.debitos_abertos)}): {'; '.join(self.debitos_abertos)}")
        return "\n".join(linhas)


def _limpar_prefixo_verbo(texto: str) -> str:
    limpo = texto.strip()
    if " — " in limpo:
        pos = limpo.find(" — ")
        if 0 < pos <= _MAX_TAMANHO_PREFIXO_VERBO:
            candidato = limpo[pos + 3 :].strip()
            if candidato.startswith(("incidente ", PREFIXO_QUARENTENA, PREFIXO_QUARENTENA_ASCII)):
                return candidato
    return limpo


def texto_debito_incidente(numero_incidente: int, id_caso: str) -> str:
    return f"incidente {numero_incidente}: {id_caso} quebrou fora do alcance"


def texto_debito_quarentena(id_caso: str) -> str:
    return f"{PREFIXO_QUARENTENA}{id_caso}"


def _extrair_corpo_debito(texto: str) -> str:
    limpo = _limpar_prefixo_verbo(texto)
    for sep in (" · Raio:", " · Esperado:", " · Onde:", " · Tipo:"):
        if sep in limpo:
            limpo = limpo.split(sep, 1)[0].strip()
    return limpo


def tem_debito_aberto_com_comeco(comeco: str, abertas: Iterable[LinhaBalde]) -> bool:
    alvo = comeco.strip()
    if not alvo:
        return False
    variantes = {alvo}
    if alvo.startswith(PREFIXO_QUARENTENA):
        variantes.add(PREFIXO_QUARENTENA_ASCII + alvo.removeprefix(PREFIXO_QUARENTENA))
    elif alvo.startswith(PREFIXO_QUARENTENA_ASCII):
        variantes.add(PREFIXO_QUARENTENA + alvo.removeprefix(PREFIXO_QUARENTENA_ASCII))

    for linha in abertas:
        bruto = linha.texto.strip()
        corpo = _extrair_corpo_debito(bruto)
        if any(bruto.startswith(v) or corpo.startswith(v) for v in variantes):
            return True
    return False


def buscar_quarentena_aberta(id_caso: str, abertas: Iterable[LinhaBalde]) -> LinhaBalde | None:
    alvos = (f"{PREFIXO_QUARENTENA}{id_caso}", f"{PREFIXO_QUARENTENA_ASCII}{id_caso}")
    encontradas: list[LinhaBalde] = []
    for linha in abertas:
        corpo = _extrair_corpo_debito(linha.texto)
        for alvo in alvos:
            if corpo == alvo or corpo.startswith((f"{alvo} ", f"{alvo}·")):
                encontradas.append(linha)
                break
    if not encontradas:
        return None
    return min(encontradas, key=lambda item: item.idade_dias)


def estado_quarentena_caso(
    id_caso: str,
    abertas: Iterable[LinhaBalde],
    *,
    prazo_dias: int = PRAZO_QUARENTENA_DIAS,
) -> str:
    """Retorna 'ativa' (<= prazo), 'vencida' (> prazo) ou 'nenhuma'."""
    linha = buscar_quarentena_aberta(id_caso, abertas)
    if linha is None:
        return "nenhuma"
    if linha.idade_dias <= prazo_dias:
        return "ativa"
    return "vencida"


class DubleBalde:
    """Dublê em memória (ou persistido em JSON) do balde de débito técnico para testes."""

    def __init__(
        self,
        linhas: Iterable[LinhaBalde | dict[str, Any]] = (),
        *,
        arquivo: str | Path | None = None,
    ) -> None:
        self.arquivo = Path(arquivo) if arquivo else None
        self.linhas: list[LinhaBalde] = []
        self.admitidos_nesta_rodada: list[LinhaBalde] = []
        self._carregar_arquivo()
        for item in linhas:
            if isinstance(item, LinhaBalde):
                self.linhas.append(item)
            elif isinstance(item, dict):
                self.linhas.append(
                    LinhaBalde(
                        numero=int(item.get("numero", len(self.linhas) + 1)),
                        idade_dias=int(item.get("idade_dias", 0)),
                        stack=str(item.get("stack", "harness")),
                        texto=str(item.get("texto", "")),
                    )
                )

    def _carregar_arquivo(self) -> None:
        if not self.arquivo:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with self.arquivo.open("a+", encoding="utf-8") as fp:
            fp.seek(0)
            bruto = fp.read()
        dados = json.loads(bruto) if bruto.strip() else []
        if isinstance(dados, list):
            for idx, item in enumerate(dados, start=1):
                if isinstance(item, dict):
                    self.linhas.append(
                        LinhaBalde(
                            numero=int(item.get("numero", idx)),
                            idade_dias=int(item.get("idade_dias", 0)),
                            stack=str(item.get("stack", "harness")),
                            texto=str(item.get("texto", "")),
                        )
                    )

    def _salvar_arquivo(self) -> None:
        if not self.arquivo:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.arquivo.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([item.como_dict() for item in self.linhas], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.arquivo)

    def listar_abertas(self) -> list[LinhaBalde]:
        return list(self.linhas)

    def adicionar_aberta(
        self,
        texto: str,
        *,
        idade_dias: int = 0,
        stack: str = "harness",
        numero: int | None = None,
    ) -> LinhaBalde:
        num = numero if numero is not None else (max((item.numero for item in self.linhas), default=0) + 1)
        nova = LinhaBalde(numero=num, idade_dias=idade_dias, stack=stack, texto=texto)
        self.linhas.append(nova)
        self._salvar_arquivo()
        return nova

    def admitir(self, texto: str, **campos: Any) -> LinhaBalde:
        stack = str(campos.get("stack") or "harness")
        nova = self.adicionar_aberta(texto, idade_dias=0, stack=stack)
        self.admitidos_nesta_rodada.append(nova)
        return nova


def _parse_linhas_dt_listar(saida: str) -> list[LinhaBalde]:
    linhas: list[LinhaBalde] = []
    for crua in saida.splitlines():
        if not crua.strip() or crua.startswith(("n\t", "corpo #", "AVISO:", "(balde vazio")):
            continue
        partes = crua.split("\t", _COLUNAS_TABELA_DT - 1)
        if len(partes) < _COLUNAS_TABELA_DT or not partes[0].strip().isdigit():
            continue
        numero = int(partes[0].strip())
        m_idade = _RE_IDADE_DIAS.match(partes[1].strip())
        idade = int(m_idade.group(1)) if m_idade else 0
        stack = partes[2].strip()
        texto = partes[3].strip()
        linhas.append(LinhaBalde(numero=numero, idade_dias=idade, stack=stack, texto=texto))
    return linhas


def _resolver_binario_tarefas() -> str:
    env_bin = os.environ.get("PF_TAREFAS_BIN")
    if env_bin and Path(env_bin).is_file():
        return env_bin
    release_bin = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current")) / "harness" / "bin" / "tarefas"
    if release_bin.is_file():
        return str(release_bin)
    local_bin = Path(__file__).resolve().parents[2] / "bin" / "tarefas"
    if local_bin.is_file():
        return str(local_bin)
    return shutil.which("tarefas") or "tarefas"


class ClienteBalde:
    """Cliente real do balde de débito técnico pelo verbo `tarefas dt`."""

    def __init__(self, tarefas_bin: str | None = None, timeout_s: int = 30) -> None:
        self.tarefas_bin = tarefas_bin or _resolver_binario_tarefas()
        self.timeout_s = timeout_s

    def listar_abertas(self) -> list[LinhaBalde]:
        proc = subprocess.run(
            [self.tarefas_bin, "dt", "listar", "--situacao", "abertas"],
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            return []
        return _parse_linhas_dt_listar(proc.stdout or "")

    def admitir(self, texto: str, **campos: Any) -> LinhaBalde | None:
        medido_em = str(campos.get("medido_em") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        evidencia = str(campos.get("evidencia") or "esteira rodar")
        raio = str(campos.get("raio") or "platafirma-harness")
        esperado = str(campos.get("esperado") or "caso passa na esteira")
        stack = str(campos.get("stack") or "harness")
        cmd = [
            self.tarefas_bin,
            "dt",
            "admitir",
            texto,
            "--medido-em",
            medido_em,
            "--evidencia",
            evidencia,
            "--raio",
            raio,
            "--esperado",
            esperado,
            "--stack",
            stack,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
        )
        if proc.returncode != 0 and stack != "harness":
            cmd[-1] = "harness"
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        if proc.returncode != 0:
            return None
        m = re.search(r"(?:débito|achado|desvio)\s+(\d+)\s+admitido", proc.stdout or "")
        num = int(m.group(1)) if m else 0
        return LinhaBalde(numero=num, idade_dias=0, stack=stack, texto=texto)


def resolver_balde(balde: Any = None) -> Any:
    if balde is not None:
        return balde
    arq_env = os.environ.get("PF_ESTEIRA_BALDE_ARQUIVO")
    if arq_env:
        return DubleBalde(arquivo=arq_env)
    return ClienteBalde()


def colocar_em_quarentena(
    id_caso: str,
    *,
    passou: bool,
    falhou: bool,
    **opcoes: Any,
) -> LinhaBalde:
    """Coloca um caso em quarentena se, e só se, foi medido passando e falhando na mesma árvore."""
    if not (passou and falhou):
        raise ValueError(
            f"quarentena recusada para '{id_caso}': caso sem medida de erraticidade "
            "(precisa passar e falhar sobre a mesma árvore)"
        )
    cliente = resolver_balde(opcoes.get("balde"))
    abertas = cliente.listar_abertas()
    existente = buscar_quarentena_aberta(id_caso, abertas)
    if existente is not None and existente.idade_dias <= PRAZO_QUARENTENA_DIAS:
        return existente
    repositorio = str(opcoes.get("repositorio") or "platafirma-casa")
    stack = str(opcoes.get("stack") or "harness")
    hoje = str(opcoes.get("data_medida") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    texto = texto_debito_quarentena(id_caso)
    arq_rel = id_caso.split("::", 1)[0]
    admitida = cliente.admitir(
        texto,
        medido_em=hoje,
        evidencia=f"esteira rodar {repositorio} (medida de erraticidade na mesma árvore)",
        raio=f"{repositorio}@{arq_rel}",
        esperado=f"caso {id_caso} passa de forma determinística na esteira",
        stack=stack,
    )
    if admitida is None:
        return LinhaBalde(numero=0, idade_dias=0, stack=stack, texto=texto)
    return admitida


def pasta_vereditos_padrao() -> Path:
    env_dir = os.environ.get("PF_ESTEIRA_VEREDITOS_DIR")
    if env_dir:
        return Path(env_dir)
    instancia = Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    return instancia / "var" / "esteira"


def _slug_repositorio(repositorio: str) -> str:
    limpo = repositorio.strip().split("@", 1)[0].strip("/")
    if "/" in limpo:
        limpo = Path(limpo).name
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", limpo) or "repositorio"


def caminho_veredito_repositorio(repositorio: str, pasta: str | Path | None = None) -> Path:
    raiz = Path(pasta) if pasta is not None else pasta_vereditos_padrao()
    return raiz / f"{_slug_repositorio(repositorio)}.jsonl"


def gravar_veredito(veredito: VereditoRodada, pasta: str | Path | None = None) -> Path:
    arq = caminho_veredito_repositorio(veredito.repositorio, pasta=pasta)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.parent.chmod(0o700)
    linha = json.dumps(veredito.como_registro(), ensure_ascii=False) + "\n"
    with arq.open("a", encoding="utf-8") as fp:
        fp.write(linha)
    arq.chmod(0o600)
    return arq


def listar_vereditos(repositorio: str, pasta: str | Path | None = None) -> list[dict[str, Any]]:
    arq = caminho_veredito_repositorio(repositorio, pasta=pasta)
    arq.parent.mkdir(parents=True, exist_ok=True)
    with arq.open("a+", encoding="utf-8") as fp:
        fp.seek(0)
        linhas = fp.read().splitlines()
    registros: list[dict[str, Any]] = []
    for linha in linhas:
        if not linha.strip():
            continue
        obj = json.loads(linha)
        if isinstance(obj, dict):
            registros.append(obj)
    return registros


def ler_veredito(
    repositorio: str,
    *,
    arvore_mudanca: str | None = None,
    arvore_main: str | None = None,
    pasta: str | Path | None = None,
) -> dict[str, Any] | None:
    registros = listar_vereditos(repositorio, pasta=pasta)
    for reg in reversed(registros):
        if arvore_mudanca and reg.get("arvore_mudanca") != arvore_mudanca:
            continue
        if arvore_main and reg.get("arvore_main") != arvore_main:
            continue
        return reg
    return None


def _recusas_estruturais_fora_exige(recusas: Sequence[RecusaAdmissao]) -> list[RecusaAdmissao]:
    """Separa recusas de admissão que não decorrem apenas de ficha de exige fora do ar."""
    return [
        r
        for r in recusas
        if r.codigo != "ficha-invalida" or "/ligacoes/exige/" not in r.mensagem
    ]


def _determinar_estado_e_motivo(
    admissao: ResultadoAdmissao,
    *,
    sem_testes_declarados: bool,
    componentes_sem_verificacao: Sequence[str],
    entidades_indisponiveis: Sequence[str],
    casos_reprovados: Sequence[str],
) -> tuple[str, str | None, int]:
    if sem_testes_declarados:
        return "nao-medido", "nenhum arquivo de teste da árvore declara vínculo de componente", _SAIDA_NAO_MEDIDO
    if admissao.codigo_saida == _SAIDA_NAO_MEDIDO:
        return (
            "nao-medido",
            admissao.motivo_indisponivel or "Olaria indisponível na admissão",
            _SAIDA_NAO_MEDIDO,
        )

    estruturais = _recusas_estruturais_fora_exige(admissao.recusas)
    if estruturais:
        return "vermelho", estruturais[0].mensagem, 1

    if componentes_sem_verificacao:
        comps = ", ".join(componentes_sem_verificacao)
        return "nao-medido", f"componente alcançado sem verificação declarada: {comps}", _SAIDA_NAO_MEDIDO

    if entidades_indisponiveis:
        ents = ", ".join(entidades_indisponiveis)
        return "nao-medido", f"entidade exigida indisponível no host: {ents}", _SAIDA_NAO_MEDIDO

    if admissao.recusas:
        return "vermelho", admissao.recusas[0].mensagem, 1

    if casos_reprovados:
        return "vermelho", f"{len(casos_reprovados)} caso(s) reprovado(s)", 1

    return "verde", None, 0


@dataclass
class _AcumuladorJulgamento:
    abertas: list[LinhaBalde]
    prazo_quarentena_dias: int
    reprovados: list[str]
    quarentenados: list[str]
    rodados: list[str]
    debitos_pendentes: list[tuple[str, str, str, str]]


def _classificar_falha_caso(
    caso: CasoSelecionado,
    bruto: ResultadoBrutoCaso,
    acum: _AcumuladorJulgamento,
) -> None:
    if caso.fora_do_alcance_incidente:
        for inc in caso.incidentes:
            txt = texto_debito_incidente(inc, caso.id_caso)
            esperado = f"caso {caso.id_caso} (incidente #{inc}) passa na rodada da esteira"
            acum.debitos_pendentes.append((txt, caso.arquivo, esperado, caso.stack))
        return

    est_q = estado_quarentena_caso(caso.id_caso, acum.abertas, prazo_dias=acum.prazo_quarentena_dias)
    if est_q == "ativa":
        acum.quarentenados.append(caso.id_caso)
        return
    if est_q == "vencida":
        acum.reprovados.append(caso.id_caso)
        return

    if bruto.medido_erratico:
        acum.quarentenados.append(caso.id_caso)
        txt_q = texto_debito_quarentena(caso.id_caso)
        esperado_q = f"caso {caso.id_caso} passa de forma determinística sem falhar na mesma árvore"
        acum.debitos_pendentes.append((txt_q, caso.arquivo, esperado_q, caso.stack))
        return

    acum.reprovados.append(caso.id_caso)


def _formatar_lista_casos_dt(itens: Sequence[str], limite: int = _MAX_CASOS_NO_TEXTO_DT) -> str:
    visiveis = ", ".join(itens[:limite])
    if len(itens) > limite:
        return f"{visiveis} (+{len(itens) - limite})"
    return visiveis


def _agregar_debitos_da_rodada(
    debitos_pendentes: Sequence[tuple[str, str, str, str]],
    abertas: Sequence[LinhaBalde],
    *,
    repositorio: str,
) -> list[tuple[str, str, str, str]]:
    unicos: list[tuple[str, str, str, str]] = []
    vistos: set[str] = set()
    for item in debitos_pendentes:
        texto = item[0]
        if texto in vistos or tem_debito_aberto_com_comeco(texto, abertas):
            continue
        vistos.add(texto)
        unicos.append(item)

    if len(unicos) <= 1:
        return unicos

    todos_erraticos = all(t.startswith(PREFIXO_QUARENTENA) for t, _, _, _ in unicos)
    arquivos = sorted({arq for _, arq, _, _ in unicos if arq})
    arquivo_rel = arquivos[0] if len(arquivos) == 1 else ""
    stack = unicos[0][3] or "harness"

    if todos_erraticos:
        prefixo_lote = f"{PREFIXO_QUARENTENA}{repositorio} ("
        if tem_debito_aberto_com_comeco(prefixo_lote, abertas):
            return []
        casos = [t.removeprefix(PREFIXO_QUARENTENA) for t, _, _, _ in unicos]
        texto_lote = f"{prefixo_lote}{len(casos)} casos na rodada): {_formatar_lista_casos_dt(casos)}"
        esperado_lote = f"os {len(casos)} casos passam de forma determinística sem falhar na mesma árvore"
        return [(texto_lote, arquivo_rel, esperado_lote, stack)]

    prefixo_lote = f"esteira {repositorio} ("
    if tem_debito_aberto_com_comeco(prefixo_lote, abertas):
        return []
    textos = [t for t, _, _, _ in unicos]
    texto_lote = f"{prefixo_lote}{len(textos)} falhas fora de bloqueio na rodada): {_formatar_lista_casos_dt(textos)}"
    esperado_lote = f"os {len(textos)} casos passam de forma determinística na rodada da esteira"
    return [(texto_lote, arquivo_rel, esperado_lote, stack)]


def _admitir_debitos_pendentes(
    cliente_balde: Any,
    acum: _AcumuladorJulgamento,
    *,
    repositorio: str,
    arvore_mudanca: str,
    data_medida: str,
) -> list[str]:
    debitos_abertos: list[str] = []
    agregados = _agregar_debitos_da_rodada(
        acum.debitos_pendentes,
        acum.abertas,
        repositorio=repositorio,
    )
    for texto, arquivo_rel, esperado, stack in agregados[:MAX_DEBITOS_POR_RODADA]:
        raio = f"{repositorio}@{arquivo_rel}" if arquivo_rel else repositorio
        nova = cliente_balde.admitir(
            texto,
            medido_em=data_medida,
            evidencia=f"esteira rodar {repositorio} (arvore {arvore_mudanca[:12]})",
            raio=raio,
            esperado=esperado,
            stack=stack or "harness",
        )
        if nova is not None:
            acum.abertas.append(nova)
            debitos_abertos.append(texto)
    return debitos_abertos


def julgar_e_gravar(**parametros: Any) -> VereditoRodada:
    """Julga o resultado da rodada, grava o veredito e depois admite os débitos novos."""
    repositorio = str(parametros["repositorio"])
    arvore_mudanca = str(parametros["arvore_mudanca"])
    arvore_main = str(parametros["arvore_main"])
    admissao: ResultadoAdmissao = parametros["admissao"]
    casos_selecionados: Sequence[CasoSelecionado] = parametros["casos_selecionados"]
    resultados_brutos: Mapping[str, ResultadoBrutoCaso] = parametros["resultados_brutos"]
    sem_testes_declarados = bool(parametros.get("sem_testes_declarados", False))
    componentes_sem_verificacao: Sequence[str] = parametros.get("componentes_sem_verificacao") or ()
    entidades_indisponiveis: Sequence[str] = parametros.get("entidades_indisponiveis") or ()
    pasta_vereditos = parametros.get("pasta_vereditos")
    prazo_quarentena_dias = int(parametros.get("prazo_quarentena_dias", PRAZO_QUARENTENA_DIAS))

    cliente_balde = resolver_balde(parametros.get("balde"))
    acum = _AcumuladorJulgamento(
        abertas=list(cliente_balde.listar_abertas()),
        prazo_quarentena_dias=prazo_quarentena_dias,
        reprovados=[],
        quarentenados=[],
        rodados=[],
        debitos_pendentes=[],
    )

    for caso in casos_selecionados:
        bruto = resultados_brutos.get(caso.id_caso)
        if bruto is None:
            continue
        acum.rodados.append(caso.id_caso)
        if bruto.aprovado:
            continue
        _classificar_falha_caso(caso, bruto, acum)

    if admissao.recusas and not sem_testes_declarados and not entidades_indisponiveis:
        for r in admissao.recusas:
            if r.arquivo not in acum.reprovados:
                acum.reprovados.append(r.arquivo)

    estado, motivo, codigo_saida = _determinar_estado_e_motivo(
        admissao,
        sem_testes_declarados=sem_testes_declarados,
        componentes_sem_verificacao=componentes_sem_verificacao,
        entidades_indisponiveis=entidades_indisponiveis,
        casos_reprovados=acum.reprovados,
    )

    instante = str(parametros.get("hora") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    hoje = str(parametros.get("data_medida") or instante[:10])

    veredito_provisorio = VereditoRodada(
        repositorio=repositorio,
        arvore_mudanca=arvore_mudanca,
        arvore_main=arvore_main,
        estado=estado,
        casos_reprovados=tuple(acum.reprovados),
        fichas_ensaiadas=admissao.fichas_ensaiadas,
        hora=instante,
        codigo_saida=codigo_saida,
        motivo=motivo,
        casos_rodados=tuple(acum.rodados),
        casos_quarentena=tuple(acum.quarentenados),
        debitos_abertos=(),
    )
    gravar_veredito(veredito_provisorio, pasta=pasta_vereditos)

    debitos_abertos = _admitir_debitos_pendentes(
        cliente_balde,
        acum,
        repositorio=repositorio,
        arvore_mudanca=arvore_mudanca,
        data_medida=hoje,
    )
    return replace(veredito_provisorio, debitos_abertos=tuple(debitos_abertos))
