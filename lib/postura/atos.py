"""Os atos do verbo persona da casa nova: ler, trocar, voltar, cenario, cultura e apelidos.

Saídas: 0 cumpriu · 1 não existe (postura, cenário, persona, nada a voltar) · 2 uso errado, com dois nomes no mesmo eixo
entre eles · 3 dependência fora (sem sessão, memória de trabalho muda, banco mudo) · 4 recusa: o documento existe e não cumpre
a forma, e o defeito vira incidente. Na recusa nada muda na memória de trabalho.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import documentos as doc
from .casa import Ligacoes, SemBanco
from .composicao import Vigor, compor
from .eventos import Log
from .lousa import Fora, Lousa

USO = """uso:
  persona ler [<cadeira>] [--chapeu <slug>] [--parte tudo|persona|chapeu|posturas|cenarios|cenario|circunstancia|ritual] [--chave <slug>] [--json]
  persona trocar <postura>… [--ritual <slug> [--ocorrencia <id>] [--card <n>]]
  persona voltar [<postura>] [--ritual]
  persona cenario <cenario> [--sai]
  persona cultura
  persona apelidos

  ler      a persona, as posturas em vigor (uma linha por eixo), os cenários presentes, a circunstância e o ritual em vigor;
           com --chapeu e sem --parte, devolve o chapéu, e é nesse giro que a porta veste o chapéu na sessão;
           com --chave <slug>, lê a instância indicada da parte pedida
  trocar   invoca uma ou mais posturas pelo nome; cada uma ocupa o eixo de cada linha dela
  voltar   sem nome, apaga todas as invocações; com um nome, só os eixos daquele documento; --ritual encerra o ritual e
           tira só o que ele invocou
  cenario  registra a entrada de um cenário, que vale a partir do turno seguinte; --sai registra a saída
  cultura  devolve a cultura da casa nova sem o título e sem a linha da entidade
  apelidos devolve os apelidos das doze personas, uma linha por cadeira, em ordem de apelido"""

PARTES = ("tudo", "persona", "chapeu", "posturas", "cenarios", "cenario", "circunstancia", "ritual")
_LIGA = {"e", ","}


@dataclass
class Contexto:
    base: Path
    cadeira: str
    sessao_id: str
    chapeu: str
    lousa: Lousa
    log: Log
    ligacoes: Ligacoes
    incidente: Callable[[str, str], str]
    agora: Callable[[], str]


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def incidente_pelo_verbo(titulo: str, corpo: str) -> str:
    """Abre o incidente pelo verbo tarefas, irmão deste na mesma release (PF_BIN só aponta outro diretório em teste)."""
    pasta = Path(os.environ.get("PF_BIN") or Path(__file__).resolve().parents[2] / "bin")
    try:
        r = subprocess.run([str(pasta / "tarefas"), "criar", titulo, "--incidente", "--desc-stdin"], input=corpo,
                           capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as erro:
        return f"incidente não aberto ({type(erro).__name__}: {erro}); o defeito: {titulo}"
    saida = (r.stdout or r.stderr).strip().splitlines()
    return saida[0] if r.returncode == 0 and saida else f"incidente não aberto (tarefas saiu {r.returncode}); o defeito: {titulo}"


def _erro(mensagem: str, codigo: int) -> int:
    print(f"persona: {mensagem}", file=sys.stderr)
    return codigo


def _leva_a_incidente(ctx: Contexto, defeito: doc.Malformado) -> str:
    """Um incidente por documento e por sha: a montagem roda a cada turno e não abre o mesmo incidente duas vezes."""
    try:
        _, sha = doc.ler_documento(ctx.base, defeito.entidade, defeito.slug)
    except doc.Inexistente:
        sha = "ausente"
    try:
        if ctx.log.defeito_ja_avisado(defeito.entidade, defeito.slug, sha):
            return "incidente já aberto para este documento neste sha"
    except Exception:      # noqa: BLE001 — log ilegível não segura o incidente
        pass
    titulo = f"{defeito.entidade} {defeito.slug} não cumpre a forma da entidade"
    corpo = (f"O documento {doc.PASTA}/{defeito.entidade}/{defeito.slug}.md (sha {sha[:12]}) não cumpre a forma: "
             + "; ".join(defeito.defeitos) + f". Quem achou: persona, na sessão {ctx.sessao_id or '-'} da cadeira "
             f"{ctx.cadeira}. Enquanto não se corrige, a postura da casa entra no lugar do perfil, e a instância de "
             "outra entidade fica fora.")
    retorno = ctx.incidente(titulo, corpo)
    ctx.log.emitir(ctx.sessao_id, "defeito", entidade=defeito.entidade, peca=defeito.slug, sha=sha, retorno=retorno[:200])
    return retorno


def _compoe(ctx: Contexto, fecha: bool = True) -> Vigor:
    """Compõe e, com `fecha`, grava o que a composição achou: o evento de cada invocação perdida e o incidente de cada
    defeito de forma."""
    v = compor(ctx.base, ctx.cadeira, ctx.chapeu, ctx.sessao_id, ctx.lousa, ctx.log, ctx.ligacoes)
    if fecha:
        for evento, campos in v.perdidos:
            ctx.log.emitir(ctx.sessao_id, evento, **campos)
        for defeito in v.defeitos:
            v.avisos.append(f"{defeito.entidade} {defeito.slug}: {_leva_a_incidente(ctx, defeito)}")
    return v


def _imprime_avisos(v: Vigor) -> None:
    for aviso in v.avisos:
        print(f"aviso: {aviso}")


def _persona(ctx: Contexto, slug: str = "") -> str:
    """O texto da persona, sem a linha que aponta o perfil: a inclinação chega pelo bloco de posturas."""
    texto, _ = doc.ler_documento(ctx.base, "persona", slug or ctx.cadeira)
    sem = "\n".join(l for l in texto.splitlines() if not l.startswith("Postura preferencial:"))
    return re.sub(r"\n{3,}", "\n\n", sem).strip()


def _bloco_itens(cabecalho: str, titulo: str, itens: list[str]) -> str:
    return "\n".join([f"{cabecalho}: {titulo}", *[f"- {i}" for i in itens]])


def _ler_por_chave(ctx: Contexto, parte: str, chave: str) -> tuple[str, dict]:
    """Lê diretamente uma instância específica para a parte pedida (override de tupla)."""
    meta: dict = {"perfil": None, "posturas": [], "cenarios": [], "circunstancia": None, "ritual": None}
    if parte == "persona":
        return _persona(ctx, chave), meta
    if parte == "chapeu":
        return doc.ler_documento(ctx.base, "chapeu", chave)[0].strip(), meta
    if parte == "posturas":
        if chave == doc.RESERVA:
            _, itens, _ = doc.itens_sem_marca(ctx.base, "postura", chave)
            bloco = "\n".join(["POSTURAS EM VIGOR: a postura da casa, e uma linha por eixo marcado.",
                               *[f"- {i}" for i in itens]])
            meta["perfil"] = chave
            return bloco, meta
        eixos = doc.ler_eixos(ctx.base)
        linhas = doc.postura(ctx.base, chave, eixos)
        bloco = "\n".join(["POSTURAS EM VIGOR: uma linha por eixo, e em cada eixo vale só esta.",
                           *[l.marcada() for l in linhas]])
        meta["perfil"] = chave
        meta["posturas"] = [l.rotulo() for l in linhas]
        return bloco, meta
    if parte in ("cenario", "cenarios"):
        titulo_c, condicao, _ = doc.cenario(ctx.base, chave)
        meta["cenarios"] = [chave]
        return f"CENÁRIOS PRESENTES\n- {titulo_c}: {condicao}", meta
    if parte == "circunstancia":
        titulo_circ, itens_circ, _ = doc.itens_sem_marca(ctx.base, "circunstancia", chave)
        meta["circunstancia"] = chave
        return _bloco_itens("CIRCUNSTÂNCIA EM VIGOR", titulo_circ, itens_circ), meta
    if parte == "ritual":
        titulo_rit, itens_rit, _ = doc.itens_sem_marca(ctx.base, "ritual", chave)
        meta["ritual"] = chave
        return _bloco_itens("RITUAL EM VIGOR", titulo_rit, itens_rit), meta
    raise ValueError(f"--chave não se aplica à parte '{parte}'")


# --- ler -----------------------------------------------------------------------------------------------------------------
def ato_ler(ctx: Contexto, parte: str, como_json: bool, chave: str = "") -> int:
    blocos: list[str] = []
    avisos: list[str] = []
    v = None
    perfil_json: str | None = None
    posturas_json: list[str] = []
    cenarios_json: list[str] = []
    circunstancia_json: str | None = None
    ritual_json: str | None = None

    if chave:
        try:
            conteudo, meta = _ler_por_chave(ctx, parte, chave)
        except ValueError as erro:
            return _erro(f"{erro}\n{USO}", 2)
        except doc.Inexistente as falta:
            return _erro(f"não existe na casa nova: {falta}", 1)
        except doc.Malformado as defeito:
            return _erro(f"recusa: {defeito} · {_leva_a_incidente(ctx, defeito)}", 4)
        perfil_json = meta["perfil"]
        posturas_json = meta["posturas"]
        cenarios_json = meta["cenarios"]
        circunstancia_json = meta["circunstancia"]
        ritual_json = meta["ritual"]
    else:
        try:
            if parte in ("tudo", "persona"):
                blocos.append(_persona(ctx))
            if parte == "chapeu" or (parte == "tudo" and ctx.chapeu):
                if not ctx.chapeu:
                    return _erro("--parte chapeu pede --chapeu <slug>", 2)
                blocos.append(doc.ler_documento(ctx.base, "chapeu", ctx.chapeu)[0].strip())
                if ctx.sessao_id and hasattr(ctx.lousa, "gravar_campo_sessao"):
                    try:
                        ctx.lousa.gravar_campo_sessao(ctx.sessao_id, "chapeu", ctx.chapeu)
                    except Fora:
                        pass
        except doc.Inexistente as falta:
            return _erro(f"não existe na casa nova: {falta}", 1)
        if parte in ("tudo", "posturas", "cenarios", "cenario", "circunstancia"):
            v = _compoe(ctx)
            avisos.extend(v.avisos)
            perfil_json = v.perfil
            posturas_json = [l.rotulo() for l in v.servidas()]
            cenarios_json = [c[0] for c in v.cenarios]
            circunstancia_json = v.circunstancia[0] if v.circunstancia else None
            if parte in ("tudo", "posturas"):
                blocos.append(v.bloco())
                if v.suspenso_por:
                    msg_susp = (f"o ritual {v.suspenso_por} suprime a postura enquanto dura: o bloco não é servido, "
                                "as invocações ficam guardadas e voltam quando ele acaba")
                    v.avisos.append(msg_susp)
                    avisos.append(msg_susp)
            if parte in ("tudo", "cenarios"):
                blocos.append(v.bloco_de_cenarios())
            elif parte == "cenario" and v.cenarios:
                blocos.append("\n".join(["CENÁRIOS PRESENTES"] + [f"- {t}: {c}" for _, t, c, _ in v.cenarios]))
            elif parte == "circunstancia" and v.circunstancia:
                _, titulo_circ, itens_circ = v.circunstancia
                blocos.append(_bloco_itens("CIRCUNSTÂNCIA EM VIGOR", titulo_circ, itens_circ))
        if parte == "ritual":
            rit_lousa: dict = {}
            if ctx.sessao_id:
                try:
                    rit_lousa = ctx.lousa.ritual(ctx.sessao_id)
                except Fora as erro:
                    avisos.append(f"memória de trabalho muda ({erro}): servindo o ritual da casa")
            ritual_slug = str(rit_lousa.get("slug") or "").strip() or "da-casa"
            try:
                titulo_rit, itens_rit, _ = doc.itens_sem_marca(ctx.base, "ritual", ritual_slug)
            except doc.Inexistente as falta:
                return _erro(f"não existe na casa nova: {falta}", 1)
            except doc.Malformado as defeito:
                return _erro(f"recusa: {defeito} · {_leva_a_incidente(ctx, defeito)}", 4)
            ritual_json = ritual_slug
            blocos.append(_bloco_itens("RITUAL EM VIGOR", titulo_rit, itens_rit))
        conteudo = "\n\n".join(b for b in blocos if b)

    if como_json:
        print(json.dumps({"cadeira": ctx.cadeira, "sessao_id": ctx.sessao_id or None, "chapeu": ctx.chapeu or None,
                          "parte": parte, "conteudo": conteudo, "avisos": avisos,
                          "perfil": perfil_json,
                          "posturas": posturas_json,
                          "cenarios": cenarios_json,
                          "circunstancia": circunstancia_json,
                          "ritual": ritual_json,
                          "suspenso_por": v.suspenso_por if v else None}, ensure_ascii=False))
        return 0
    if conteudo:
        print(conteudo)
    for aviso in avisos:
        print(f"aviso: {aviso}")
    return 0


# --- trocar --------------------------------------------------------------------------------------------------------------
def ato_trocar(ctx: Contexto, nomes: list[str], ritual: str, ocorrencia: str, card: str) -> int:
    if not ctx.sessao_id:
        return _erro("sem sessão: a troca vale para uma sessão, e a porta não a injetou (PF_SESSAO)", 3)
    slugs = [s for s in (doc.slug_de(n.strip(",")) for n in nomes) if s and s not in _LIGA]
    if not slugs and not ritual:
        return _erro("trocar pede o nome de uma postura\n" + USO, 2)
    if len(set(slugs)) != len(slugs):
        return _erro("o mesmo nome veio duas vezes na chamada", 2)
    eixos = doc.ler_eixos(ctx.base)
    novas: dict[str, doc.Linha] = {}
    for slug in slugs:
        if slug == doc.RESERVA:
            return _erro("a postura da casa é a reserva, que entra quando o perfil não cumpre a forma, e não se invoca", 2)
        try:
            linhas = doc.postura(ctx.base, slug, eixos)
        except doc.Inexistente:
            return _erro(f"não existe na casa nova: postura {slug}; nada mudou · varrido: {doc.PASTA}/postura/", 1)
        except doc.Malformado as defeito:
            return _erro(f"recusa: {defeito}; nada mudou · {_leva_a_incidente(ctx, defeito)}", 4)
        for linha in linhas:
            if linha.eixo in novas:
                return _erro(f"dois nomes no eixo «{linha.eixo_rotulo}»: {novas[linha.eixo].peca} e {slug}; "
                             "cada eixo leva um polo, e nada mudou", 2)
            novas[linha.eixo] = linha
    campo_do_ritual = None
    if ritual:
        ritual = doc.slug_de(ritual)
        try:
            doc.itens_sem_marca(ctx.base, "ritual", ritual)
        except doc.Inexistente:
            return _erro(f"não existe na casa nova: ritual {ritual}; nada mudou · varrido: {doc.PASTA}/ritual/", 1)
        except doc.Malformado as defeito:
            return _erro(f"recusa: {defeito}; nada mudou · {_leva_a_incidente(ctx, defeito)}", 4)
        ocorrencia = ocorrencia or f"{ritual}-{ctx.agora()}"
    hora = ctx.agora()
    motivo = "ritual" if ritual else "dono"
    try:
        antes = _compoe(ctx, fecha=False)
        if ritual:
            campo_do_ritual = {"slug": ritual, "ocorrencia": ocorrencia, "card": card or "", "hora": hora}
        campos = {eixo: {"peca": l.peca, "sha": l.sha, "motivo": motivo, "ocorrencia": ocorrencia if ritual else "",
                         "hora": hora} for eixo, l in novas.items()}
        ctx.lousa.gravar_invocacoes(ctx.sessao_id, campos, campo_do_ritual)
    except Fora as erro:
        return _erro(f"{erro}; nada mudou", 3)
    if ritual:
        ctx.log.emitir(ctx.sessao_id, "ritual", acao="comeco", ritual=ritual, ocorrencia=ocorrencia, card=card or None)
    mudancas = []
    for eixo, linha in sorted(novas.items(), key=lambda par: eixos[par[0]].ordem):
        saiu = antes.por_eixo.get(eixo)
        ctx.log.emitir(ctx.sessao_id, "postura", acao="troca", eixo=eixo, de=saiu.polo_rotulo if saiu else None,
                       para=linha.polo_rotulo, peca=linha.peca, sha=linha.sha, motivo=motivo,
                       ocorrencia=ocorrencia if ritual else None)
        if saiu is None:
            mudancas.append(f"- {linha.eixo_rotulo}: entrou {linha.polo_rotulo}; o eixo não tinha linha")
        elif saiu.polo == linha.polo:
            mudancas.append(f"- {linha.eixo_rotulo}: {linha.polo_rotulo} segue, agora pela invocação de {linha.peca}")
        else:
            mudancas.append(f"- {linha.eixo_rotulo}: saiu {saiu.polo_rotulo}, entrou {linha.polo_rotulo}")
    depois = _compoe(ctx)
    if depois.bloco():
        print(depois.bloco())
    if mudancas:
        print("O QUE MUDOU")
        print("\n".join(mudancas))
    if ritual:
        print(f"ritual em vigor: {ritual} (ocorrência {ocorrencia})")
    if depois.suspenso_por and not ritual:
        print(f"o ritual {depois.suspenso_por} suprime a postura: do bloco, só esta invocação é servida enquanto ele dura")
    _imprime_avisos(depois)
    return 0


# --- voltar --------------------------------------------------------------------------------------------------------------
def ato_voltar(ctx: Contexto, nome: str, do_ritual: bool) -> int:
    if not ctx.sessao_id:
        return _erro("sem sessão: a volta vale para uma sessão, e a porta não a injetou (PF_SESSAO)", 3)
    try:
        antes = _compoe(ctx, fecha=False)
        invocadas = ctx.lousa.invocacoes(ctx.sessao_id)
        ritual = ctx.lousa.ritual(ctx.sessao_id)
    except Fora as erro:
        return _erro(f"{erro}; nada mudou", 3)
    if do_ritual:
        if not ritual.get("slug"):
            return _erro("nenhum ritual em vigor nesta sessão; nada mudou", 1)
        alvo = [e for e, c in invocadas.items()
                if c.get("motivo") == "ritual" and c.get("ocorrencia") == ritual.get("ocorrencia")]
    elif nome:
        slug = doc.slug_de(nome)
        alvo = [e for e, c in invocadas.items() if c.get("peca") == slug]
        if not alvo:
            return _erro(f"nada invocado de {slug} nesta sessão; nada mudou", 1)
    else:
        alvo = list(invocadas)
    try:
        ctx.lousa.apagar_invocacoes(ctx.sessao_id, alvo, ritual_tambem=do_ritual)
    except Fora as erro:
        return _erro(f"{erro}; nada mudou", 3)
    if do_ritual:
        ctx.log.emitir(ctx.sessao_id, "ritual", acao="fim", ritual=ritual.get("slug"), ocorrencia=ritual.get("ocorrencia"))
    # o que fica em cada eixo que voltou é o ramo ou o perfil: a composição sem sessão dá as duas camadas de baixo
    fundo = compor(ctx.base, ctx.cadeira, ctx.chapeu, "", ctx.lousa, ctx.log, ctx.ligacoes)
    mudancas = []
    for eixo in sorted(alvo, key=lambda e: fundo.eixos[e].ordem if e in fundo.eixos else 99):
        saiu, ficou = antes.por_eixo.get(eixo), fundo.por_eixo.get(eixo)
        rotulo = fundo.eixos[eixo].rotulo if eixo in fundo.eixos else eixo
        ctx.log.emitir(ctx.sessao_id, "postura", acao="volta", eixo=eixo, de=saiu.polo_rotulo if saiu else None,
                       para=ficou.polo_rotulo if ficou else None, peca=(invocadas[eixo] or {}).get("peca"))
        de = f"saiu {saiu.polo_rotulo}" if saiu else "saiu a invocação"
        mudancas.append(f"- {rotulo}: {de}, " + (f"voltou {ficou.polo_rotulo}" if ficou else "e o eixo ficou sem linha"))
    depois = _compoe(ctx)
    if depois.bloco():
        print(depois.bloco())
    if mudancas:
        print("O QUE MUDOU")
        print("\n".join(mudancas))
    elif not do_ritual:
        print("nada estava invocado: a cadeira já estava no perfil" + (", com o ramo" if ctx.chapeu else ""))
    if do_ritual:
        print(f"ritual encerrado: {ritual.get('slug')}")
    _imprime_avisos(depois)
    return 0


# --- cenario -------------------------------------------------------------------------------------------------------------
def ato_cenario(ctx: Contexto, nome: str, sai: bool) -> int:
    if not ctx.sessao_id:
        return _erro("sem sessão: o cenário vale para uma sessão, e a porta não a injetou (PF_SESSAO)", 3)
    slug = doc.slug_de(nome)
    try:
        presentes = ctx.lousa.cenarios(ctx.sessao_id)
        if sai:
            if slug not in presentes:
                return _erro(f"o cenário {slug} não está presente nesta sessão; nada mudou", 1)
            ctx.lousa.sair_cenario(ctx.sessao_id, slug)
            ctx.log.emitir(ctx.sessao_id, "cenario", acao="sai", cenario=slug)
        else:
            try:
                _, _, sha = doc.cenario(ctx.base, slug)
            except doc.Inexistente:
                return _erro(f"não existe na casa nova: cenário {slug}; nada mudou · varrido: {doc.PASTA}/cenario/", 1)
            except doc.Malformado as defeito:
                return _erro(f"recusa: {defeito}; nada mudou · {_leva_a_incidente(ctx, defeito)}", 4)
            try:
                ativa = ctx.ligacoes.ativadas([slug]).get(slug)
            except SemBanco:
                ativa = None
            ctx.lousa.entrar_cenario(ctx.sessao_id, slug, {"sha": sha, "hora": ctx.agora()})
            ctx.log.emitir(ctx.sessao_id, "cenario", acao="entra", cenario=slug, circunstancia=ativa)
    except Fora as erro:
        return _erro(f"{erro}; nada mudou", 3)
    depois = _compoe(ctx)
    if sai:
        print(f"cenário {slug}: saída registrada")
    else:
        print(f"cenário {slug}: entrada registrada; vale a partir do turno seguinte")
    if depois.bloco_de_cenarios():
        print(depois.bloco_de_cenarios())
    else:
        print("nenhum cenário presente, e a vaga de circunstância está vazia")
    _imprime_avisos(depois)
    return 0


# --- cultura -------------------------------------------------------------------------------------------------------------
def ato_cultura(ctx: Contexto) -> int:
    try:
        texto, _ = doc.cultura(ctx.base)
    except doc.Inexistente:
        return _erro(f"não existe na casa nova: cultura; nada mudou · varrido: {doc.PASTA}/cultura/", 1)
    except doc.Malformado as defeito:
        return _erro(f"recusa: {defeito}; nada mudou · {_leva_a_incidente(ctx, defeito)}", 4)
    print(texto)
    return 0


# --- apelidos ------------------------------------------------------------------------------------------------------------
def ato_apelidos(ctx: Contexto) -> int:
    try:
        lista = doc.apelidos(ctx.base)
    except doc.Inexistente:
        return _erro(f"não existe na casa nova: personas; nada mudou · varrido: {doc.PASTA}/persona/", 1)
    except doc.Malformado as defeito:
        return _erro(f"recusa: {defeito}; nada mudou · {_leva_a_incidente(ctx, defeito)}", 4)
    linhas = [f"{apelido} -> {slug}" for apelido, slug in lista]
    print("\n".join(linhas))
    return 0


# --- a linha de comando --------------------------------------------------------------------------------------------------
def _tira(argv: list[str], opcao: str, com_valor: bool = True):
    """Tira `opcao` de argv e devolve o valor (ou True, na que não leva valor); None quando ela não veio."""
    if opcao not in argv:
        return None
    i = argv.index(opcao)
    if not com_valor:
        del argv[i]
        return True
    if i + 1 >= len(argv):
        raise ValueError(f"{opcao} pede um valor")
    valor = argv[i + 1]
    del argv[i:i + 2]
    return valor


def contexto(cadeira: str, chapeu: str, sessao_id: str, log: Log | None = None,
             incidente: Callable[[str, str], str] | None = None) -> Contexto:
    lousa = Lousa()
    if not chapeu and sessao_id:
        try:
            chapeu = lousa.chapeu_da_sessao(sessao_id)      # o chapéu que a porta gravou na chave da sessão; só leitura
        except Fora:
            chapeu = ""
    return Contexto(base=doc.raiz(), cadeira=cadeira, sessao_id=sessao_id, chapeu=chapeu, lousa=lousa, log=log or Log(),
                    ligacoes=Ligacoes(), incidente=incidente or incidente_pelo_verbo, agora=agora_utc)


def despacha(ctx: Contexto, ato: str, argv: list[str]) -> int:
    try:
        if ato == "ler":
            parte = _tira(argv, "--parte") or "tudo"
            chave = _tira(argv, "--chave") or ""
            como_json = bool(_tira(argv, "--json", False))
            if parte not in PARTES or argv:
                return _erro(f"ler: parte ou argumento desconhecido ({' '.join(argv) or parte})\n{USO}", 2)
            if chave and not doc.slug_valido(doc.slug_de(chave)):
                return _erro(f"chave fora da forma: {chave}", 2)
            return ato_ler(ctx, parte, como_json, chave=doc.slug_de(chave) if chave else "")
        if ato == "trocar":
            ritual = _tira(argv, "--ritual") or ""
            ocorrencia = _tira(argv, "--ocorrencia") or ""
            card = _tira(argv, "--card") or ""
            if any(a.startswith("--") for a in argv):
                return _erro(f"trocar: opção desconhecida ({' '.join(a for a in argv if a.startswith('--'))})\n{USO}", 2)
            return ato_trocar(ctx, argv, ritual, ocorrencia, card)
        if ato == "voltar":
            do_ritual = bool(_tira(argv, "--ritual", False))
            if len(argv) > 1 or any(a.startswith("--") for a in argv) or (do_ritual and argv):
                return _erro(f"voltar: um nome, ou nenhum, ou --ritual\n{USO}", 2)
            return ato_voltar(ctx, argv[0] if argv else "", do_ritual)
        if ato == "cenario":
            sai = bool(_tira(argv, "--sai", False))
            if len(argv) != 1 or argv[0].startswith("--"):
                return _erro(f"cenario pede um nome\n{USO}", 2)
            return ato_cenario(ctx, argv[0], sai)
        if ato == "cultura":
            if argv:
                return _erro(f"cultura não aceita argumentos\n{USO}", 2)
            return ato_cultura(ctx)
        if ato == "apelidos":
            if argv:
                return _erro(f"apelidos não aceita argumentos\n{USO}", 2)
            return ato_apelidos(ctx)
    except ValueError as erro:
        return _erro(f"{erro}\n{USO}", 2)
    except (OSError, KeyError) as erro:
        return _erro(f"a árvore da casa nova não pôde ser lida em {ctx.base}: {type(erro).__name__}: {erro}", 3)
    return _erro(f"ato desconhecido: {ato} · os atos são ler, trocar, voltar, cenario, cultura e apelidos\n{USO}", 2)


def parte_do_chapeu(ato: str, argv: list[str], chapeu_pedido: str) -> None:
    """`ler <cadeira> --chapeu <slug>` sem --parte devolve o chapéu: é a chamada que a montagem e a porta já fazem para
    servir e vestir o chapéu. A composição com o ramo se pede com --parte posturas."""
    if ato == "ler" and chapeu_pedido and "--parte" not in argv:
        argv += ["--parte", "chapeu"]


def main(argv: list[str] | None = None) -> int:
    """A entrada do verbo servido: a cadeira, a sessão e o chapéu vêm do ambiente que a porta injeta."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "--ajuda", "ajuda"):
        print(USO)
        return 0 if argv else 2
    ato = argv.pop(0)
    try:
        pedido = _tira(argv, "--chapeu") or ""
    except ValueError as erro:
        return _erro(f"{erro}\n{USO}", 2)
    chapeu = pedido or os.environ.get("PF_CHAPEU", "")
    parte_do_chapeu(ato, argv, pedido)
    cadeira = os.environ.get("PF_CADEIRA", "")
    if ato == "ler" and argv and not argv[0].startswith("--"):
        cadeira = argv.pop(0)
    if ato not in ("cultura", "apelidos") and not doc.slug_valido(cadeira):
        return _erro("sem cadeira: a porta não injetou (PF_CADEIRA), e ler aceita a cadeira como argumento", 3)
    if chapeu and not doc.slug_valido(doc.slug_de(chapeu)):
        return _erro(f"chapéu fora da forma: {chapeu}", 2)
    return despacha(contexto(cadeira or "casa", doc.slug_de(chapeu) if chapeu else "", os.environ.get("PF_SESSAO", "")), ato, argv)
