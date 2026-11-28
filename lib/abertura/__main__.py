"""Ponto de entrada CLI JSON da `lib/abertura`.

Invocado pela porta (`core/porta`) por subprocesso (`python -m abertura abrir|remontar|exigir-sessao`),
porque o core nunca importa módulo do harness, e sem chamar `bin/expediente`
nem ler cópia publicada em disco.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import yaml

from abertura.nomes import SecaoDasCadeiras, resolver as resolver_nomes
from abertura.pauta import (
    Carta,
    ContextoDaSessao,
    Guardado,
    carregar_guardados_da_lousa,
    ler_cartas_da_fila,
    montar_pauta,
)
from abertura.roteiro import (
    FALLBACK_CLASSES,
    ParteLida,
    PedidoDeRoteiro,
    PecaDoRoteiro,
    extrair_tupla,
    montar_roteiro,
)
from abertura.rotinas import formatar_rotinas, rotinas
from abertura.sessao import LIVRES_PADRAO, exigir_sessao
from postura import atos as postura_atos
from postura import documentos as postura_doc
from postura.casa import Ligacoes, SemBanco
from postura.eventos import Log
from postura.lousa import Lousa, lousa_do_ambiente
from postura.remontagem import TETO_REMONTAGEM_CHARS, remontar


def _raiz_casa_padrao(entrada: dict[str, Any]) -> Path:
    informada = (entrada.get("casa_raiz") or os.environ.get("PF_CASA_RAIZ") or "").strip()
    if informada:
        return Path(informada)
    release = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    return release / "casa"


def _carregar_secao_cadeiras(base: Path) -> tuple[SecaoDasCadeiras, list[str]]:
    """Lê todas as personas de `instancias/persona/*.md` da casa nova, sem fallback à release."""
    pasta = base / "instancias" / "persona"
    if not pasta.is_dir():
        return SecaoDasCadeiras(), []
    blocos: list[str] = []
    slugs: list[str] = []
    for arq in sorted(pasta.glob("*.md")):
        try:
            texto = arq.read_text(encoding="utf-8")
        except OSError:
            continue
        if texto.strip():
            blocos.append(texto)
            slugs.append(arq.stem)
    if not blocos:
        return SecaoDasCadeiras(), []
    secao = SecaoDasCadeiras.de_texto("\n\n".join(blocos))
    # Garante que toda persona em disco com Entidade: persona figure na seção mesmo sem seção Nomes.
    if not secao.cadeiras and slugs:
        from abertura.nomes import CadeiraDeclarada

        cadeiras = {slug: CadeiraDeclarada(slug=slug) for slug in slugs}
        return SecaoDasCadeiras(cadeiras=cadeiras), slugs
    return secao, slugs


def _validar_entidade_markdown(texto: str, esperada: str) -> str | None:
    if not texto.strip():
        return "documento vazio"
    if f"Entidade: {esperada}" not in texto:
        return f"falta declaração 'Entidade: {esperada}'"
    return None


def _validar_tabela_harnesses(caminho_str: str | None) -> tuple[bool, str | None]:
    if not caminho_str:
        return True, None
    caminho = Path(caminho_str)
    if not caminho.is_file():
        return False, f"tabela de harnesses ausente: {caminho}"
    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, f"tabela de harnesses inválida ({type(exc).__name__}: {exc})"
    if not isinstance(dados, dict) or not isinstance(dados.get("harnesses"), list) or not dados["harnesses"]:
        return False, "tabela de harnesses inválida: falta lista não vazia 'harnesses'"
    return True, None


def _validar_registro_verbos(caminho_str: str | None) -> tuple[bool, str | None]:
    if not caminho_str:
        return True, None
    caminho = Path(caminho_str)
    if not caminho.is_file():
        return False, f"registro de verbos ausente: {caminho}"
    try:
        bruto = caminho.read_text(encoding="utf-8")
        dados = json.loads(bruto) if caminho.suffix == ".json" else yaml.safe_load(bruto)
    except Exception as exc:  # noqa: BLE001
        return False, f"registro de verbos inválido ({type(exc).__name__}: {exc})"
    if not isinstance(dados, dict) or not dados:
        return False, "registro de verbos inválido: estrutura vazia ou fora de forma"
    return True, None


class _LeitorRoteiroPadrao:
    def construido_de(self, roteiro: str = "porta") -> list[PecaDoRoteiro]:
        return [
            PecaDoRoteiro(classe=cls, chave=f"{cls}:*", posicao=idx + 1)
            for idx, cls in enumerate(FALLBACK_CLASSES)
        ]


class _LeitorParteCasaNova:
    """Lê peças da casa nova exclusivamente de `base/instancias/<classe>/<slug>.md`."""

    def __init__(self, base: Path, *, ligacoes: Any | None = None) -> None:
        self._base = base
        self._ligacoes = ligacoes

    def _slug_postura_preferencial(self, cadeira: str) -> str | None:
        if self._ligacoes is not None:
            try:
                slug = self._ligacoes.perfil(cadeira)
                if slug:
                    return str(slug)
            except SemBanco:
                pass
        arq = self._base / "instancias" / "persona" / f"{cadeira}.md"
        if arq.is_file():
            try:
                texto = arq.read_text(encoding="utf-8")[:2000]
                for linha in texto.splitlines():
                    if linha.lower().startswith("postura preferencial:"):
                        val = linha.split(":", 1)[1].strip()
                        if val:
                            return val
            except OSError:
                pass
        return None

    def ler(
        self,
        classe: str,
        cadeira: str,
        chapeu: str | None,
        *,
        chave: str | None = None,
    ) -> ParteLida:
        if classe == "persona":
            slug = chave or cadeira
            arq = self._base / "instancias" / "persona" / f"{slug}.md"
            if not arq.is_file():
                return ParteLida(ok=False, conteudo="", ref=f"persona:{slug}", erro=f"arquivo ausente: {arq}")
            texto = arq.read_text(encoding="utf-8").strip()
            erro = _validar_entidade_markdown(texto, "persona")
            if erro:
                return ParteLida(ok=False, conteudo="", ref=f"persona:{slug}", erro=erro)
            return ParteLida(ok=True, conteudo=texto, ref=f"persona:{slug}", instancias=(slug,))

        if classe == "chapeu":
            slug = chave or chapeu
            if not slug:
                return ParteLida(ok=False, conteudo="", ref="chapeu:", erro="chapéu não informado")
            arq = self._base / "instancias" / "chapeu" / f"{slug}.md"
            if not arq.is_file():
                return ParteLida(ok=False, conteudo="", ref=f"chapeu:{slug}", erro=f"arquivo ausente: {arq}")
            texto = arq.read_text(encoding="utf-8").strip()
            erro = _validar_entidade_markdown(texto, "chapeu")
            if erro:
                return ParteLida(ok=False, conteudo="", ref=f"chapeu:{slug}", erro=erro)
            return ParteLida(ok=True, conteudo=texto, ref=f"chapeu:{slug}", instancias=(slug,))

        if classe == "cultura":
            slug = chave or "da-casa"
            try:
                texto, _sha = postura_doc.cultura(self._base, slug=slug)
            except postura_doc.Inexistente as exc:
                return ParteLida(ok=False, conteudo="", ref=f"cultura:{slug}", erro=f"arquivo ausente: {exc}")
            except postura_doc.Malformado as exc:
                return ParteLida(ok=False, conteudo="", ref=f"cultura:{slug}", erro=str(exc))
            return ParteLida(ok=True, conteudo=texto, ref=f"cultura:{slug}", instancias=(slug,))

        if classe == "postura":
            slug = chave or self._slug_postura_preferencial(cadeira)
            if not slug:
                return ParteLida(ok=True, conteudo="", ref="postura:", instancias=())
            arq = self._base / "instancias" / "postura" / f"{slug}.md"
            if not arq.is_file():
                if chave:
                    return ParteLida(ok=False, conteudo="", ref=f"postura:{slug}", erro=f"arquivo ausente: {arq}")
                return ParteLida(ok=True, conteudo="", ref=f"postura:{slug}", instancias=())
            texto = arq.read_text(encoding="utf-8").strip()
            return ParteLida(ok=True, conteudo=texto, ref=f"postura:{slug}", instancias=(slug,))

        if classe == "ritual":
            slug = chave or "da-casa"
            arq = self._base / "instancias" / "ritual" / f"{slug}.md"
            if not arq.is_file():
                if chave:
                    return ParteLida(ok=False, conteudo="", ref=f"ritual:{slug}", erro=f"arquivo ausente: {arq}")
                return ParteLida(ok=True, conteudo="", ref=f"ritual:{slug}", instancias=())
            texto = arq.read_text(encoding="utf-8").strip()
            return ParteLida(ok=True, conteudo=texto, ref=f"ritual:{slug}", instancias=(slug,))

        if classe in ("cenario", "circunstancia"):
            if not chave:
                return ParteLida(ok=True, conteudo="", ref=f"{classe}:", instancias=())
            arq = self._base / "instancias" / classe / f"{chave}.md"
            if not arq.is_file():
                return ParteLida(ok=False, conteudo="", ref=f"{classe}:{chave}", erro=f"arquivo ausente: {arq}")
            texto = arq.read_text(encoding="utf-8").strip()
            return ParteLida(ok=True, conteudo=texto, ref=f"{classe}:{chave}", instancias=(chave,))

        return ParteLida(ok=False, conteudo="", ref=f"{classe}:", erro="sem leitura direta")


class _LeitorProcessosVazio:
    def processos_de_rotina(self) -> list[Any]:
        return []


def _achar_bin_fila() -> Path | None:
    candidatos: list[Path] = []
    env_bin = (os.environ.get("PF_BIN") or "").strip()
    if env_bin:
        candidatos.append(Path(env_bin))
    candidatos.append(Path(__file__).resolve().parents[2] / "bin")
    for pasta in candidatos:
        cam = pasta / "fila"
        if cam.is_file():
            return cam
    no_path = shutil.which("fila")
    return Path(no_path) if no_path else None


def _ler_cartas_da_caixa(
    cadeira: str,
    *,
    base: Path,
    timeout_s: float = 3.0,
) -> tuple[list[Carta], str | None]:
    """Lê penduradas e não lidas da caixa da cadeira sem mover o ponteiro do grupo."""
    exe = _achar_bin_fila()
    if exe is None:
        return [], "binário fila ausente"
    env = dict(os.environ)
    env["PF_CADEIRA"] = cadeira
    env["PF_CASA_RAIZ"] = str(base)
    try:
        proc = subprocess.run(
            [str(exe), "ler", "--penduradas", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], str(exc)
    if proc.returncode != 0:
        motivo = [ln.strip() for ln in (proc.stderr or proc.stdout).splitlines() if ln.strip()]
        return [], (motivo[-1][:160] if motivo else f"exit {proc.returncode}")
    try:
        brutas = ler_cartas_da_fila(proc.stdout)
    except ValueError as exc:
        return [], f"saída inválida da fila: {exc}"
    compactas = [
        Carta(
            id=c.id,
            de=c.de,
            assunto=c.assunto,
            corpo="" if c.assunto else c.corpo[:120],
            texto=c.texto,
            estado=c.estado,
            tipo=c.tipo,
            idade_seg=c.idade_seg,
            ref=c.ref,
            responde=c.responde,
        )
        for c in brutas
    ]
    return compactas, None


def _erro_recusa(codigo: str, mensagem: str, **extras: Any) -> dict[str, Any]:
    return {"ok": False, "codigo": codigo, "erro": mensagem, **extras}


def _ato_abrir(entrada: dict[str, Any]) -> tuple[dict[str, Any], int]:
    base = _raiz_casa_padrao(entrada)
    pergunta = str(entrada.get("pergunta") or "")
    tupla = extrair_tupla(pergunta)
    cadeira_bruta = str(entrada.get("cadeira") or (tupla.cadeira if tupla else "") or "").strip()
    chapeu_bruto = entrada.get("chapeu")
    if chapeu_bruto is None and tupla is not None:
        chapeu_bruto = tupla.chapeu
    chapeu_str = str(chapeu_bruto).strip() if chapeu_bruto else None

    # 1. Validação das configurações declaradas (tabela de harnesses e registro de verbos)
    avisos: list[str] = list(tupla.avisos) if tupla else []
    ok_tab, erro_tab = _validar_tabela_harnesses(entrada.get("harnesses_tabela"))
    if not ok_tab:
        return _erro_recusa("tabela-harnesses-invalida", erro_tab or "tabela de harnesses inválida"), 2

    ok_reg, erro_reg = _validar_registro_verbos(entrada.get("verbos_registro"))
    if not ok_reg:
        return _erro_recusa("registro-verbos-invalido", erro_reg or "registro de verbos inválido"), 2

    # 2. Catálogo de cadeiras e chapéus lido da casa nova
    secao, _slugs = _carregar_secao_cadeiras(base)
    if not cadeira_bruta:
        return _erro_recusa(
            "cadeira-ausente",
            "cadeira não informada",
            cadeiras=secao.como_lista(),
        ), 2

    cadeira_slug = cadeira_bruta
    chapeu_slug = chapeu_str
    if secao.cadeiras:
        res = resolver_nomes(cadeira_bruta, chapeu_str, secao=secao)
        if res.ok and res.cadeira:
            cadeira_slug = res.cadeira
            chapeu_slug = res.chapeu
            avisos.extend(res.avisos)
        elif not (base / "instancias" / "persona" / f"{cadeira_bruta}.md").is_file():
            return _erro_recusa(
                "persona-ausente",
                res.erro or f"persona ausente para '{cadeira_bruta}'",
                cadeiras=secao.como_lista(),
            ), 2

    # 3. Leitura estrita de persona, cultura e chapéu (quando pedido) da casa nova
    leitor_roteiro: Any = _LeitorRoteiroPadrao() if entrada.get("sem_valkey") else Ligacoes()
    leitor_parte = _LeitorParteCasaNova(base, ligacoes=None if entrada.get("sem_valkey") else leitor_roteiro)
    p_persona = leitor_parte.ler("persona", cadeira_slug, chapeu_slug)
    if not p_persona.ok:
        codigo = "persona-ausente" if "ausente" in (p_persona.erro or "") else "persona-invalida"
        return _erro_recusa(codigo, f"persona '{cadeira_slug}': {p_persona.erro}", cadeira=cadeira_slug), 2

    p_cultura = leitor_parte.ler("cultura", cadeira_slug, chapeu_slug)
    if not p_cultura.ok:
        codigo = "cultura-ausente" if "ausente" in (p_cultura.erro or "").lower() or "inexistente" in (p_cultura.erro or "").lower() else "cultura-invalida"
        return _erro_recusa(codigo, f"cultura 'da-casa': {p_cultura.erro}", cadeira=cadeira_slug), 2

    p_chapeu: ParteLida | None = None
    if chapeu_slug:
        p_chapeu = leitor_parte.ler("chapeu", cadeira_slug, chapeu_slug)
        if not p_chapeu.ok:
            codigo = "chapeu-ausente" if "ausente" in (p_chapeu.erro or "") else "chapeu-invalido"
            return _erro_recusa(
                codigo,
                f"chapéu '{chapeu_slug}': {p_chapeu.erro}",
                cadeira=cadeira_slug,
                chapeu=chapeu_slug,
            ), 2

    # 4. Montagem do roteiro, rotinas e pauta
    pedido = PedidoDeRoteiro(
        cadeira=cadeira_slug,
        chapeu=chapeu_slug,
        overrides=tupla.overrides if tupla else (),
    )
    roteiro = montar_roteiro(pedido, leitor_roteiro, leitor_parte)
    processos, recusas_rotinas = rotinas(_LeitorProcessosVazio(), base=base)

    lousa_erro: str | None = None
    transicoes: dict[str, object] = {}
    if "guardados" in entrada and entrada["guardados"] is not None:
        guardados = [
            Guardado(
                trabalho=str(g.get("trabalho") or ""),
                chapeu=g.get("chapeu"),
                card=g.get("card"),
                chave=g.get("chave"),
                estagio=str(g.get("estagio") or ""),
                proxima_jogada=str(g.get("proxima_jogada") or ""),
                ocasiao=str(g.get("ocasiao") or ""),
            )
            for g in (entrada["guardados"] or [])
            if isinstance(g, dict)
        ]
    elif entrada.get("sem_valkey"):
        guardados = []
        lousa_erro = "memória de trabalho desativada"
    else:
        avisos_lousa: list[str] = []
        guardados, transicoes = carregar_guardados_da_lousa(
            cadeira_slug,
            lousa_do_ambiente(),
            avisos=avisos_lousa,
        )
        for av in avisos_lousa:
            if av.startswith("lousa indisponível:"):
                lousa_erro = av.split(":", 1)[1].strip() or av
            avisos.append(av)

    caixa_erro: str | None = None
    if "cartas" in entrada and entrada["cartas"] is not None:
        cartas_brutas = entrada.get("cartas") or []
        cartas = [
            Carta(
                id=str(c.get("id") or c.get("msgid") or ""),
                de=str(c.get("de") or c.get("remetente") or ""),
                assunto=str(c.get("assunto") or ""),
                corpo=str(c.get("corpo") or c.get("texto") or ""),
                estado=str(c.get("estado") or ""),
                tipo=str(c.get("tipo") or ""),
                idade_seg=c.get("idade_seg") if isinstance(c.get("idade_seg"), int) else None,
                ref=str(c.get("ref") or ""),
                responde=str(c.get("responde") or ""),
            )
            for c in cartas_brutas
            if isinstance(c, dict)
        ]
    elif entrada.get("sem_valkey"):
        cartas = []
        caixa_erro = "caixa desativada"
    else:
        cartas, caixa_erro = _ler_cartas_da_caixa(cadeira_slug, base=base)
        if caixa_erro:
            avisos.append(f"caixa indisponível: {caixa_erro}")

    pauta = montar_pauta(
        guardados=guardados,
        cartas=cartas,
        sessao=ContextoDaSessao(
            cadeira=cadeira_slug,
            turno=pergunta,
            chapeu=chapeu_slug,
            transicoes_de_card=transicoes,
        ),
        lousa_erro=lousa_erro,
        caixa_erro=caixa_erro,
    )

    pecas_principais = frozenset({"persona", "chapeu", "cultura"})
    pecas = {p.parte: p.conteudo for p in roteiro.partes if p.conteudo and p.parte in pecas_principais}
    if "persona" not in pecas:
        pecas["persona"] = p_persona.conteudo
    if "cultura" not in pecas:
        pecas["cultura"] = p_cultura.conteudo
    if chapeu_slug and "chapeu" not in pecas and p_chapeu is not None and p_chapeu.ok:
        pecas["chapeu"] = p_chapeu.conteudo

    # Persona, chapéu e cultura já vão em `pecas`; `roteiro` carrega só as peças complementares.
    partes_extras = [p for p in roteiro.partes if p.parte not in pecas_principais]
    partes_dict = [p.como_dict() for p in partes_extras]
    roteiro_conteudo = "\n\n".join(p.conteudo for p in partes_extras if p.conteudo)
    avisos_unicos = list(dict.fromkeys([*avisos, *roteiro.avisos]))

    return {
        "ok": True,
        "cadeira": cadeira_slug,
        "chapeu": chapeu_slug,
        "cadeiras": secao.como_lista(),
        "pecas": pecas,
        "roteiro": {
            "partes": partes_dict,
            "avisos": list(roteiro.avisos),
            "conteudo": roteiro_conteudo,
        },
        "rotinas": {
            "processos": [p.como_dict() for p in processos],
            "recusas": [r.como_dict() for r in recusas_rotinas],
            "conteudo": formatar_rotinas(processos),
        },
        "pauta": {
            "turno": pauta.turno,
            "total_guardados": pauta.total_guardados,
            "fora_da_ocasiao": pauta.fora_da_ocasiao,
            "cartas": len(pauta.cartas),
            "reforco": list(pauta.reforco),
            "conteudo": pauta.conteudo,
            **({"lousa_erro": pauta.lousa_erro} if pauta.lousa_erro else {}),
            **({"caixa_erro": pauta.caixa_erro} if pauta.caixa_erro else {}),
        },
        "avisos": avisos_unicos,
    }, 0


class _LousaVazia:
    def invocacoes(self, _sid: str) -> dict:
        return {}

    def ritual(self, _sid: str) -> dict:
        return {}

    def cenarios(self, _sid: str) -> dict:
        return {}

    def chapeu_da_sessao(self, _sid: str) -> str:
        return ""


class _LogVazio:
    def defeito_ja_avisado(self, *_a: Any) -> bool:
        return True

    def registrar(self, *_a: Any, **_kw: Any) -> None:
        return None


class _LigacoesVazias:
    def perfil(self, _cadeira: str) -> str | None:
        raise SemBanco("sem banco configurado")

    def ativa(self, _cenarios: list[str]) -> dict[str, list[str]]:
        raise SemBanco("sem banco configurado")

    def instancias(self, *_a: Any, **_kw: Any) -> list:
        return []

    def circunstancia(self, *_a: Any, **_kw: Any) -> list:
        return []


def _ato_remontar(entrada: dict[str, Any]) -> tuple[dict[str, Any], int]:
    base = _raiz_casa_padrao(entrada)
    cadeira = str(entrada.get("cadeira") or "").strip()
    chapeu = str(entrada.get("chapeu") or "").strip()
    sessao_id = str(entrada.get("sessao_id") or "").strip()
    incluir_cultura = bool(entrada.get("incluir_cultura", False))
    teto = int(entrada.get("teto_caracteres") or TETO_REMONTAGEM_CHARS)

    if not cadeira:
        return _erro_recusa("cadeira-ausente", "cadeira é obrigatória para remontar"), 2

    sem_valkey = bool(entrada.get("sem_valkey"))
    lousa: Any = _LousaVazia() if sem_valkey else Lousa()
    log: Any = _LogVazio() if sem_valkey else Log()
    ligacoes: Any = _LigacoesVazias() if sem_valkey else Ligacoes()

    ctx = postura_atos.Contexto(
        base=base,
        cadeira=cadeira,
        sessao_id=sessao_id,
        chapeu=chapeu,
        lousa=lousa,
        log=log,
        ligacoes=ligacoes,
        incidente=lambda _t, _c: "",
        agora=postura_atos.agora_utc,
    )
    rem = remontar(ctx, incluir_cultura=incluir_cultura, teto_caracteres=teto)
    texto = rem.texto_formatado(teto_caracteres=teto)
    dados = rem.por_valor()
    dados["ok"] = True
    dados["texto"] = texto
    dados["caracteres"] = len(texto)
    return dados, 0


def _ato_exigir_sessao(entrada: dict[str, Any]) -> tuple[dict[str, Any], int]:
    tool = str(entrada.get("tool") or "")
    sessao_id = entrada.get("sessao_id")
    livres_brutos = entrada.get("livres")
    livres = frozenset(str(x) for x in livres_brutos) if isinstance(livres_brutos, list) else LIVRES_PADRAO
    recusa = exigir_sessao(tool, sessao_id, livres=livres)
    if recusa is None:
        return {"ok": True, "permitido": True, "recusa": None}, 0
    return {"ok": False, "permitido": False, "recusa": recusa.como_dict()}, 2


def _ato_tronco(entrada: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from abertura.tronco import resolver_tronco

    card = entrada.get("card")
    if not isinstance(card, dict):
        return {"processo": None, "passo": None, "sem_processo": True}, 0
    chapeu = entrada.get("chapeu")
    decisao_aposta = entrada.get("decisao_aposta")
    prazo_s = float(entrada.get("prazo_s") or os.environ.get("PF_TRONCO_PRAZO_S") or 8.0)
    return resolver_tronco(card, chapeu=chapeu, decisao_aposta=decisao_aposta, prazo_s=prazo_s), 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("abrir", "remontar", "exigir-sessao", "tronco"):
        print(json.dumps(_erro_recusa("uso-invalido", "uso: python -m abertura abrir|remontar|exigir-sessao|tronco"), ensure_ascii=False))
        return 2
    ato = args[0]
    bruto = sys.stdin.read().strip()
    try:
        entrada = json.loads(bruto) if bruto else {}
    except ValueError as exc:
        print(json.dumps(_erro_recusa("json-invalido", f"stdin inválido: {exc}"), ensure_ascii=False))
        return 2
    if not isinstance(entrada, dict):
        print(json.dumps(_erro_recusa("json-invalido", "stdin deve ser objeto JSON"), ensure_ascii=False))
        return 2

    if ato == "abrir":
        saida, rc = _ato_abrir(entrada)
    elif ato == "remontar":
        saida, rc = _ato_remontar(entrada)
    elif ato == "tronco":
        saida, rc = _ato_tronco(entrada)
    else:
        saida, rc = _ato_exigir_sessao(entrada)

    print(json.dumps(saida, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
