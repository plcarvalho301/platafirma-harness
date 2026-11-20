"""A peça persona: o verbo persona em sessão de ensaio, para `infra rodar persona -- <ato> … --cadeira <cadeira>`.

Roda os mesmos atos do verbo servido em uma sessão de ensaio (o id leva o prefixo «ensaio-»). Os eventos vão a uma pasta
temporária, e o incidente não é aberto, só dito. O perfil preferencial vem do arquivo da persona na árvore conferida,
para permitir o ensaio antes da primeira fornada no banco.

  python -m postura ler|trocar|voltar|cenario|cultura|apelidos … [--cadeira <c>] [--chapeu <h>]
  python -m postura peca --cadeira <c> [--chapeu <h>]        a peça de posturas como a montagem a serve, com os tokens
  python -m postura ensaio chave-perdida|ritual-que-suprime|perfil-malformado|sessao-filha|compactacao --cadeira <c>
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from . import documentos as doc
from .atos import USO, Contexto, _tira, ato_ler, contexto, despacha, parte_do_chapeu
from .casa import Ligacoes
from .eventos import Log

ENSAIOS = ("chave-perdida", "ritual-que-suprime", "perfil-malformado", "sessao-filha", "compactacao")
RITUAL_DE_ENSAIO = "incidente-de-ensaio"
PERFIL_DE_ENSAIO = "exaustivo"
EIXOS_NO_PERFIL = 4

def _incidente_de_ensaio(titulo: str, corpo: str) -> str:
    return f"incidente de ensaio, não aberto: {titulo}"

def _ctx(cadeira: str, chapeu: str, sufixo: str = "") -> Contexto:
    sessao = f"ensaio-{os.environ.get('PF_SESSAO') or 'mao'}-{cadeira}{sufixo}"
    log = Log(Path(tempfile.gettempdir()) / "postura-ensaio-log")
    ctx = contexto(cadeira, chapeu, sessao, log=log, incidente=_incidente_de_ensaio)
    # O ensaio confere a árvore nova, antes de sua carga no banco. A postura preferencial
    # vem do cabeçalho que a ingestão usa para gravar a ligação, sem ler uma ficha antiga.
    class PerfisDaArvore(Ligacoes):
        def perfil(self, nome: str) -> str | None:
            texto, _ = doc.ler_documento(ctx.base, "persona", nome)
            achado = re.search(r"^Postura preferencial:\s*([a-z0-9-]+)\s*$", texto, re.MULTILINE)
            return achado.group(1) if achado else None

    ctx.ligacoes = PerfisDaArvore()
    return ctx

def _copia_da_arvore(base: Path) -> Path:
    """Uma cópia das fichas de comportamento e da lista dos eixos numa pasta temporária, para o ensaio que precisa de documento que a
    casa não tem (o ritual que suprime) ou de documento estragado (o perfil malformado)."""
    destino = Path(tempfile.mkdtemp(prefix="postura-ensaio-"))
    shutil.copytree(base / doc.PASTA, destino / doc.PASTA)
    (destino / doc.EIXOS).parent.mkdir(parents=True)
    shutil.copy(doc.caminho_eixos(base), destino / doc.EIXOS)
    return destino

def _passo(titulo: str) -> None:
    print(f"\n--- {titulo}")

def _rotulos(ctx: Contexto) -> list[str]:
    from .atos import _compoe
    return [linha.rotulo() for linha in _compoe(ctx, fecha=False).servidas()]

def _ensaio_chave_perdida(ctx: Contexto, perfil: list[str]) -> bool:
    _passo(f"trocar {PERFIL_DE_ENSAIO}")
    despacha(ctx, "trocar", [PERFIL_DE_ENSAIO])
    _passo("a chave da sessão some da memória de trabalho, como no prazo vencido ou no reinício")
    ctx.lousa.apagar_tudo(ctx.sessao_id)
    _passo("ler: o perfil, com o aviso dos eixos que perderam a invocação")
    from .atos import _compoe
    v = _compoe(ctx)
    print(v.bloco())
    for aviso in v.avisos:
        print(f"aviso: {aviso}")
    _passo("ler de novo: o aviso já foi dado, e não se repete")
    depois = _compoe(ctx)
    print(depois.bloco())
    ok = (len([a for a in v.avisos if "perdeu a invocação" in a]) == EIXOS_NO_PERFIL and [linha.rotulo() for linha in v.servidas()] == perfil
          and not [a for a in depois.avisos if "perdeu a invocação" in a])
    return ok


def _ensaio_ritual_que_suprime(ctx: Contexto, _perfil: list[str]) -> bool:
    ctx.base = _copia_da_arvore(ctx.base)
    (ctx.base / doc.PASTA / "ritual" / f"{RITUAL_DE_ENSAIO}.md").write_text(
        "# Incidente de ensaio\n\nEntidade: ritual\n\nSuprime postura: sim\n\n## Para que lado puxa\n\n"
        "- Diante de um serviço fora do ar, puxo para restabelecer, em vez de explicar, porque a causa se apura depois.\n",
        encoding="utf-8")
    _passo("trocar inventivo, pelo dono, antes do ritual")
    despacha(ctx, "trocar", ["inventivo"])
    _passo(f"o ritual {RITUAL_DE_ENSAIO}, que declara suprimir a postura, entra em vigor")
    despacha(ctx, "trocar", ["--ritual", RITUAL_DE_ENSAIO])
    durante = _rotulos(ctx)
    print(f"posturas servidas durante o ritual: {durante or 'nenhuma'}")
    _passo(f"o dono invoca {PERFIL_DE_ENSAIO} durante o ritual: só ele é servido")
    despacha(ctx, "trocar", [PERFIL_DE_ENSAIO])
    com_dono = _rotulos(ctx)
    _passo("o ritual acaba: o bloco volta, com o que estava guardado")
    despacha(ctx, "voltar", ["--ritual"])
    fim = _rotulos(ctx)
    despacha(ctx, "voltar", [])
    shutil.rmtree(ctx.base, ignore_errors=True)
    esperado = [linha.rotulo() for linha in doc.postura(doc.raiz(), PERFIL_DE_ENSAIO, doc.ler_eixos(doc.raiz()))]
    ok = durante == [] and com_dono == esperado and fim == esperado
    return ok


def _ensaio_perfil_malformado(ctx: Contexto, _perfil: list[str]) -> bool:
    ctx.base = _copia_da_arvore(ctx.base)
    from .composicao import perfil_da_persona
    slug = perfil_da_persona(ctx.base, ctx.cadeira, ctx.ligacoes, [])
    alvo = ctx.base / doc.PASTA / "postura" / f"{slug}.md"
    alvo.write_text(alvo.read_text(encoding="utf-8").replace("- [", "- sem marca ["), encoding="utf-8")
    _passo(f"o perfil {slug} perde a marca de eixo; ler serve a postura da casa e leva o defeito a incidente")
    from .atos import _compoe
    v = _compoe(ctx)
    print(v.bloco())
    for aviso in v.avisos:
        print(f"aviso: {aviso}")
    shutil.rmtree(ctx.base, ignore_errors=True)
    ok = bool(v.reserva) and not v.servidas() and any("incidente de ensaio" in a for a in v.avisos)
    return ok


def _ensaio_sessao_filha(ctx: Contexto, perfil: list[str]) -> bool:
    _passo(f"a sessão de quem chama invoca {PERFIL_DE_ENSAIO}")
    despacha(ctx, "trocar", [PERFIL_DE_ENSAIO])
    _passo("a sessão filha, de id próprio, abre com as posturas do próprio agente e não lê a chave de quem a chamou")
    filha = _ctx(ctx.cadeira, ctx.chapeu, sufixo="-filha")
    ato_ler(filha, "posturas", False)
    ok = _rotulos(filha) == perfil and _rotulos(ctx) != perfil
    despacha(ctx, "voltar", [])
    return ok


def _ensaio_compactacao(ctx: Contexto, _perfil: list[str]) -> bool:
    _passo(f"trocar {PERFIL_DE_ENSAIO}")
    despacha(ctx, "trocar", [PERFIL_DE_ENSAIO])
    _passo("sem sinal de compactação: a remontagem não é chamada")
    _passo("a porta recebe o sinal de compactação e chama a remontagem")
    from .remontagem import remontar
    rem = remontar(ctx)
    print(f"posturas por valor: {', '.join(rem.rotulos_posturas)}")
    esperado = {"Foco: Modo de trabalhar", "Direção: Criar", "Contribuição: Pôr à prova", "Alternativas: Aprofundar"}
    ok = (set(rem.rotulos_posturas) == esperado
          and len(rem.rotulos_posturas) == EIXOS_NO_PERFIL
          and bool(rem.persona)
          and rem.cultura.startswith("## Abertura da sessão"))
    despacha(ctx, "voltar", [])
    return ok


def ensaio(nome: str, cadeira: str, chapeu: str) -> int:
    ensaios = {
        "chave-perdida": _ensaio_chave_perdida,
        "ritual-que-suprime": _ensaio_ritual_que_suprime,
        "perfil-malformado": _ensaio_perfil_malformado,
        "sessao-filha": _ensaio_sessao_filha,
        "compactacao": _ensaio_compactacao,
    }
    if nome not in ensaios:
        print(f"ensaio desconhecido: {nome} · os ensaios são {', '.join(ENSAIOS)}", file=sys.stderr)
        return 2
    ctx = _ctx(cadeira, chapeu)
    despacha(ctx, "voltar", [])
    perfil = _rotulos(ctx)
    ok = ensaios[nome](ctx, perfil)
    print(f"\nensaio {nome}: {'passou' if ok else 'NÃO PASSOU'}")
    return 0 if ok else 1

def peca(ctx: Contexto) -> int:
    """A peça de posturas como a montagem a serve: a referência, o frescor, a contagem de tokens e o conteúdo."""
    import tokenizador

    from .atos import _compoe
    v = _compoe(ctx)
    conteudo = v.bloco()
    tokens, metodo = tokenizador.conta_tokens(conteudo)
    ref = f"verbo:persona ler {ctx.cadeira} --parte posturas" + (f" --chapeu {ctx.chapeu}" if ctx.chapeu else "")
    print(f"===== posturas: {ref} (fresco, {tokens} tokens, {metodo}) =====")
    print(conteudo or "(sem linha em vigor: a peça não entra no pacote)")
    for aviso in v.avisos:
        print(f"aviso: {aviso}")
    return 0

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "--ajuda", "ajuda"):
        print(__doc__.strip() + "\n\n" + USO)
        return 0 if argv else 2
    ato = argv.pop(0)
    try:
        cadeira = _tira(argv, "--cadeira") or os.environ.get("PF_CADEIRA", "")
        chapeu = doc.slug_de(_tira(argv, "--chapeu") or "")
    except ValueError as erro:
        print(f"persona: {erro}", file=sys.stderr)
        return 2
    if (ato not in ("cultura", "apelidos") and not doc.slug_valido(cadeira)) or (chapeu and not doc.slug_valido(chapeu)):
        print("persona: a peça pede --cadeira <slug>, e o chapéu, quando vem, em slug", file=sys.stderr)
        return 2
    if ato == "ensaio":
        if len(argv) != 1:
            print(f"persona: ensaio pede um nome · os ensaios são {', '.join(ENSAIOS)}", file=sys.stderr)
            return 2
        return ensaio(argv[0], cadeira, chapeu)
    parte_do_chapeu(ato, argv, chapeu)
    ctx = _ctx(cadeira or "casa", chapeu)
    if ato == "peca":
        return peca(ctx)
    return despacha(ctx, ato, argv)

if __name__ == "__main__":
    sys.exit(main())
