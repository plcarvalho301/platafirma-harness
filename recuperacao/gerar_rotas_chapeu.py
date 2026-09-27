#!/usr/bin/env python3
"""Gera a tabela de rotas rótulo->chapéu do roteador determinístico (a), a partir do
golden record `acervo.conceito` cruzado com a curadoria de PERTENCIMENTO de cada
`persona.md`, seção `## Gerências` (card #3110 — a antiga `## b)` de cada `chapeu.md`
saiu com o molde velho; o vocabulário do pertencimento agora mora na persona).

## Por que materializar, e não consultar na montagem

`acervo listar conceitos` lê o Postgres por `docker exec` (ver bin/_acervo/listar). Rodar
docker a cada montagem de sessão é custo proibido — o roteador precisa da tabela em
memória, barata. Então este gerador roda FORA da montagem (à mão, ou no deploy), e
materializa `<abertura>/rotas-chapeu.json`. `rotas_do_disco()` lê esse JSON, sem docker.

O golden record é a fonte de VERDADE do slug e dos gatilhos (rótulo canônico +
`outros_rotulos`). A seção `## Gerências` de cada `persona.md` é a curadoria de
PERTENCIMENTO: qual conceito dispara qual chapéu. Nenhum conceito entra numa rota por
conta própria; entra porque uma gerência o declarou na sua lista de rótulos. Isso mantém
a régua do (a): relação declarada, não semelhança.

## Rótulo órfão é erro declarado, nunca silêncio

Dois tipos de órfão, os dois avisados em stderr como `AVISO órfão: ...` e os dois
contam para `--estrito` sair != 0:

- órfão de CHAPÉU — o slug do bullet (`**slug**`) não bate nenhum diretório real
  irmão da persona (a gerência foi renomeada ou o diretório não existe/foi renomeado).
- órfão de CONCEITO — um rótulo da cauda do bullet não casa nenhum conceito do golden
  record (a gerência cita um rótulo que a `dados` ainda não curou no acervo).

Deriva de tabela mantida à mão (o modo de falha que #250 existe para matar) só se pega
se o gerador ACUSAR o descasamento, em vez de gerar uma rota curta em silêncio.

## Formato do bullet de gerência (persona.md, molde novo)

    - **slug** — descrição solta que gruda no 1º rótulo. 1º rotulo · 2º rótulo ·
      3º rótulo, possivelmente quebrado em continuação de linha · último rótulo.

O slug é o primeiro `**...**` do bullet, normalizado sem acento (`governança` ->
`governanca`) e conferido contra o diretório real da cadeira. A cauda de rótulos sai por
`split(" · ")`; linhas de continuação do mesmo bullet se juntam antes disso. No primeiro
segmento — onde a descrição solta gruda no primeiro rótulo — o corte é depois do ÚLTIMO
". " ou ÚLTIMO ": " do segmento, o que vier mais tarde no texto (cobre tanto "descrição.
rótulo" quanto "destrava: rótulo"). Um rótulo com ". " interno nos demais segmentos (ex.
"direcionamento vs. implementabilidade") não é tocado por este corte — só o primeiro
segmento sofre o corte de descrição. O ponto final do último rótulo do bullet é removido.

## Contrato de saída (<abertura>/rotas-chapeu.json)

    { "<cadeira>": { "<slug-chapeu>": ["<gatilho>", ...], ... }, ... }

Gatilhos por chapéu: para cada rótulo da gerência que casou, o slug do conceito, o
rótulo canônico e cada `outros_rotulos`. Deduplicados, normalizados na leitura (não aqui
— o roteador normaliza com a mesma régua na hora de casar). Contrato intacto desde a
versão anterior (card #3105); só a FONTE do rótulo mudou.

## Conferir: o gate de `publicar-abertura` (card #3143)

`--conferir` gera a tabela em memória e a compara com o `rotas-chapeu.json` que já está
na árvore, sem escrever nada. A comparação usa a régua de `casa()` do roteador
(`bin/_expediente/rotear`): por chapéu, o CONJUNTO de gatilhos normalizados com 3+
caracteres. Ordem e grafia que o roteador não distingue não divergem.

    exit 0  conforme                      tabela gerada = arquivo; órfão de conceito só avisa
    exit 1  divergente                    tabela ≠ arquivo, arquivo ilegível, ou órfão de CHAPÉU
    exit 5  indeterminável                golden record fora de alcance: não conferiu

A primeira linha do stdout é a âncora (`rotas: conforme|divergente|indeterminavel — ...`).
Órfão de CONCEITO não reprova: é matéria de `dados`, e o que já casa segue roteando.

`--anterior <abertura>` (a que está no ar) limita a reprovação às cadeiras que a
publicação MUDA: `persona.md`, conjunto de diretórios de chapéu ou bloco do
`rotas-chapeu.json` diferente entre as duas árvores. Nas outras, divergência é deriva
anterior (conceito curado depois da última geração, cadeira ainda não rematerializada) e
só avisa: quem publica responde pela rota do que mudou, não pela deriva que herdou.
Sem `--anterior`, todas as cadeiras estão no escopo.
`--golden <arquivo.json>` lê o golden record de um arquivo (lista, ou `{itens: [...]}`
como a API serve) em vez da rede — teste e base sem motor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

# Fonte ÚNICA da régua de normalização: o próprio roteador. Importar em vez de recopiar
# garante que gerar e casar usem o mesmo _normaliza — recópia diverge no primeiro ajuste.
# Import qualificado pelo pacote (não `sys.path` na própria `recuperacao/`): o cliente REST
# usa import relativo (`..envelope`) e só resolve dentro do pacote `recuperacao`.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from recuperacao.roteador_chapeu import _normaliza  # noqa: E402
from recuperacao.adaptadores.motor_acervo_rest import conceitos as _conceitos_http  # noqa: E402

ABERTURA_PADRAO = os.path.join(RAIZ, "abertura")

_RE_BULLET_INICIO = re.compile(r"^-\s+\*\*")
_RE_BULLET = re.compile(r"^-\s+\*\*([^*]+)\*\*\s*[—–-]\s*(.*)$")
_RE_GERENCIAS = re.compile(r"^##\s+Ger[êe]ncias\b.*?$(.*?)(?=^##\s+|\Z)", re.M | re.S)


def golden_record(arquivo: str | None = None) -> list[dict]:
    """O golden record inteiro, via `GET /acervo/conceitos` (#2957, arq:0089 §2). Único
    ponto que toca a rede; roda uma vez, fora da montagem. `arquivo` lê o mesmo payload
    de um JSON local (lista, ou `{itens: [...]}`), sem rede."""
    if arquivo is not None:
        with open(arquivo, encoding="utf-8") as f:
            payload = json.load(f)
        itens = payload if isinstance(payload, list) else (
            payload.get("itens") if isinstance(payload, dict) else None)
        if not isinstance(itens, list):
            raise ValueError(f"{arquivo}: golden sem lista de itens")
        return itens
    payload = _conceitos_http()
    return payload.get("itens", [])


def indice_por_rotulo(golden: list[dict]) -> dict[str, dict]:
    """rótulo normalizado -> conceito. Indexa pelo rótulo canônico E por cada
    `outros_rotulos`, para a gerência poder citar qualquer alias que o golden reconhece."""
    idx: dict[str, dict] = {}
    for c in golden:
        chaves = [c["rotulo"]]
        outros = c.get("outros_rotulos")
        if outros:
            # o --json serve outros_rotulos ora como str "a / b", ora lista; normaliza os dois
            partes = outros if isinstance(outros, list) else re.split(r"[/,]", outros)
            chaves.extend(partes)
        for k in chaves:
            n = _normaliza(k)
            if len(n) >= 3:
                idx.setdefault(n, c)
    return idx


def _sem_acento(s: str) -> str:
    """Slug sem diacrítico: 'governança' -> 'governanca', 'recuperação' -> 'recuperacao'."""
    nf = unicodedata.normalize("NFKD", s.strip())
    return "".join(c for c in nf if not unicodedata.combining(c))


def rotulos_da_gerencias(persona_md: str, base_dir: str | None = None) -> tuple[dict[str, list[str]], list[str]]:
    """{slug-do-chapeu: [rótulos]} a partir da seção `## Gerências` de um `persona.md`
    (molde novo, card #3110 — substitui `rotulos_da_secao_b`/`## b)` do `chapeu.md`
    antigo). Recorta de `^## Gerências` até o próximo `^## ` ou fim de arquivo; junta
    linhas de continuação de cada bullet antes de dividir. `base_dir`, se dado, confere
    o slug contra o diretório real — sem bater, o bullet vira órfão de chapéu (2º valor
    de retorno, mensagens sem o prefixo de cadeira, que quem chama antepõe)."""
    m = _RE_GERENCIAS.search(persona_md)
    if not m:
        return {}, []
    corpo = m.group(1)

    # Junta cada bullet ('- **slug** — ...') com suas linhas de continuação (o
    # word-wrap do markdown quebra a linha onde haveria um espaço só).
    blocos: list[str] = []
    atual: list[str] = []
    for linha in corpo.splitlines():
        if _RE_BULLET_INICIO.match(linha):
            if atual:
                blocos.append(" ".join(atual))
            atual = [linha.strip()]
        elif linha.strip():
            atual.append(linha.strip())
    if atual:
        blocos.append(" ".join(atual))

    gerencias: dict[str, list[str]] = {}
    orfaos_chapeu: list[str] = []

    for bloco in blocos:
        mb = _RE_BULLET.match(bloco)
        if not mb:
            continue
        slug_bruto, cauda = mb.group(1).strip(), mb.group(2).strip()
        slug = _sem_acento(slug_bruto).lower()

        if base_dir is not None and not os.path.isdir(os.path.join(base_dir, slug)):
            orfaos_chapeu.append(
                f"gerência '{slug_bruto}' (slug '{slug}') sem diretório de chapéu "
                f"correspondente — órfão de chapéu")
            continue

        segmentos = [s.strip() for s in cauda.split(" · ") if s.strip()]
        if not segmentos:
            gerencias[slug] = []
            continue

        # 1º segmento: a descrição solta gruda no 1º rótulo — corta depois do ÚLTIMO
        # ". " ou ÚLTIMO ": ", o que vier mais tarde no texto.
        primeiro = segmentos[0]
        corte = max(primeiro.rfind(". "), primeiro.rfind(": "))
        primeiro_rotulo = primeiro[corte + 2:].strip() if corte >= 0 else primeiro.strip()

        rotulos = [primeiro_rotulo] + segmentos[1:]
        if rotulos and rotulos[-1].endswith("."):
            rotulos[-1] = rotulos[-1][:-1].strip()
        rotulos = [r for r in rotulos if r]

        gerencias[slug] = rotulos

    return gerencias, orfaos_chapeu


def gatilhos(conceito: dict) -> list[str]:
    """Os disparadores de um conceito: rótulo canônico + outros_rotulos + o próprio slug.
    O roteador normaliza na hora de casar; aqui saem em forma legível, deduplicados."""
    saida = [conceito["rotulo"], conceito["slug"]]
    outros = conceito.get("outros_rotulos")
    if outros:
        partes = outros if isinstance(outros, list) else re.split(r"[/,]", outros)
        saida.extend(p.strip() for p in partes if p.strip())
    vistos, unicos = set(), []
    for g in saida:
        n = _normaliza(g)
        if n and n not in vistos:
            vistos.add(n)
            unicos.append(g)
    return unicos


def gerar(estrito: bool, abertura: str, apenas_cadeira: str | None = None,
          golden: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Varre `<abertura>/*/persona.md`. `apenas_cadeira` restringe a varredura a uma só
    cadeira (persona rotas --cadeira); `estrito` não filtra aqui — só o chamador decide
    o código de saída a partir de `orfaos`. `golden` já lido dispensa a rede."""
    tabela, orfaos = _gerar(abertura, apenas_cadeira, golden)
    return tabela, [msg for _, _, msg in orfaos]


def _gerar(abertura: str, apenas_cadeira: str | None = None,
           golden: list[dict] | None = None) -> tuple[dict, list[tuple[str, str, str]]]:
    """O miolo de `gerar`, com o órfão tipado: `("chapeu"|"conceito", cadeira,
    mensagem)`, na ordem em que aparece. O tipo separa recusa de aviso em `conferir`."""
    if golden is None:
        golden = golden_record()
    idx = indice_por_rotulo(golden)
    tabela: dict[str, dict[str, list[str]]] = {}
    orfaos: list[tuple[str, str, str]] = []

    if not os.path.isdir(abertura):
        return tabela, orfaos

    cadeiras = sorted(
        c for c in os.listdir(abertura)
        if os.path.isdir(os.path.join(abertura, c)))
    if apenas_cadeira is not None:
        cadeiras = [c for c in cadeiras if c == apenas_cadeira]

    for cadeira in cadeiras:
        base = os.path.join(abertura, cadeira)
        persona_md = os.path.join(base, "persona.md")
        if not os.path.isfile(persona_md):
            continue
        with open(persona_md, encoding="utf-8") as f:
            texto = f.read()

        gerencias, orfaos_chapeu = rotulos_da_gerencias(texto, base)
        orfaos.extend(("chapeu", cadeira, f"{cadeira}: {msg}") for msg in orfaos_chapeu)

        for chapeu, rotulos in gerencias.items():
            disparadores: list[str] = []
            vistos: set[str] = set()
            for rotulo in rotulos:
                conceito = idx.get(_normaliza(rotulo))
                if conceito is None:
                    orfaos.append(("conceito", cadeira,
                                   f"{cadeira}/{chapeu}: rótulo '{rotulo}' "
                                   f"não casa nenhum conceito do golden record"))
                    continue
                for g in gatilhos(conceito):
                    n = _normaliza(g)
                    if n not in vistos:
                        vistos.add(n)
                        disparadores.append(g)
            if disparadores:
                tabela.setdefault(cadeira, {})[chapeu] = disparadores

    return tabela, orfaos


def _casaveis(gats) -> dict[str, str]:
    """A régua de `casa()` do roteador: gatilho normalizado, só com 3+ caracteres, sem
    ordem. Duas listas com as mesmas chaves roteiam igual. O valor é a primeira grafia,
    para o relato mostrar o gatilho como está escrito, não a forma normalizada."""
    saida: dict[str, str] = {}
    for g in gats:
        n = _normaliza(g)
        if len(n) >= 3:
            saida.setdefault(n, g)
    return saida


def _amostra(itens: list[str], n: int = 5) -> str:
    resto = len(itens) - n
    return ", ".join(itens[:n]) + (f" (+{resto})" if resto > 0 else "")


def comparar(gerada: dict, publicada: dict) -> list[tuple[str, str]]:
    """`(cadeira, linha)` por chapéu cujo conjunto casável difere entre a tabela gerada
    e a do arquivo. Cadeira ou chapéu ausente de um lado conta como conjunto vazio."""
    difs: list[tuple[str, str]] = []
    for cadeira in sorted(set(gerada) | set(publicada)):
        g, p = gerada.get(cadeira, {}), publicada.get(cadeira, {})
        for chapeu in sorted(set(g) | set(p)):
            ng, np_ = _casaveis(g.get(chapeu, [])), _casaveis(p.get(chapeu, []))
            if ng.keys() == np_.keys():
                continue
            partes = []
            if ng.keys() - np_.keys():
                falta = sorted(ng[n] for n in ng.keys() - np_.keys())
                partes.append(f"falta no arquivo: {_amostra(falta)}")
            if np_.keys() - ng.keys():
                sobra = sorted(np_[n] for n in np_.keys() - ng.keys())
                partes.append(f"sobra no arquivo: {_amostra(sobra)}")
            difs.append((cadeira, f"{cadeira}/{chapeu}: " + "; ".join(partes)))
    return difs


def _le_tabela(caminho: str):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def cadeiras_tocadas(abertura: str, anterior: str) -> set[str] | None:
    """As cadeiras cuja rota esta publicação pode mudar: `persona.md`, conjunto de
    diretórios de chapéu ou bloco do `rotas-chapeu.json` diferente entre `anterior` (a
    abertura no ar) e `abertura`. `None` = anterior ausente ou ilegível: todas."""
    if not os.path.isdir(anterior):
        return None
    try:
        rotas_antes = _le_tabela(os.path.join(anterior, "rotas-chapeu.json"))
        rotas_agora = _le_tabela(os.path.join(abertura, "rotas-chapeu.json"))
    except (OSError, ValueError):
        return None
    if not isinstance(rotas_antes, dict) or not isinstance(rotas_agora, dict):
        return None

    def assinatura(raiz: str, cadeira: str):
        base = os.path.join(raiz, cadeira)
        if not os.path.isdir(base):
            return None
        try:
            with open(os.path.join(base, "persona.md"), "rb") as f:
                persona = f.read()
        except OSError:
            persona = None
        chapeus = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
        return persona, chapeus

    cadeiras = {c for raiz in (anterior, abertura) for c in os.listdir(raiz)
                if os.path.isdir(os.path.join(raiz, c))}
    return {c for c in cadeiras
            if assinatura(anterior, c) != assinatura(abertura, c)
            or rotas_antes.get(c) != rotas_agora.get(c)}


def _forma_valida(tabela) -> bool:
    """`{cadeira: {chapeu: [gatilho, ...]}}`, o contrato de saída."""
    return isinstance(tabela, dict) and all(
        isinstance(chapeus, dict) and all(
            isinstance(gats, list) and all(isinstance(x, str) for x in gats)
            for gats in chapeus.values())
        for chapeus in tabela.values())


def conferir(abertura: str, apenas_cadeira: str | None = None,
             golden_arquivo: str | None = None, anterior: str | None = None) -> int:
    """O gate de `publicar-abertura` (card #3143): compara a tabela gerada com o
    `rotas-chapeu.json` de `abertura`, sem escrever. Exit 0/1/5, âncora e escopo de
    `anterior` no docstring do módulo."""
    caminho = os.path.join(abertura, "rotas-chapeu.json")
    try:
        golden = golden_record(golden_arquivo)
    except Exception as e:  # noqa: BLE001 — FonteIndisponivel, OSError, JSON: não olhei
        print(f"rotas: indeterminavel — golden record fora de alcance, nada conferido: {e}")
        return 5
    if not golden:
        print("rotas: indeterminavel — golden record veio vazio, nada conferido")
        return 5

    try:
        tabela, orfaos = _gerar(abertura, apenas_cadeira, golden)
    except (KeyError, TypeError, AttributeError) as e:  # item do golden fora da forma
        print(f"rotas: indeterminavel — golden record com item fora da forma, nada conferido: {e!r}")
        return 5
    escopo = cadeiras_tocadas(abertura, anterior) if anterior is not None else None

    def no_escopo(cadeira: str) -> bool:
        return escopo is None or cadeira in escopo

    de_conceito = [m for t, _, m in orfaos if t == "conceito"]

    try:
        with open(caminho, encoding="utf-8") as f:
            publicada = json.load(f)
    except (OSError, ValueError) as e:
        print(f"rotas: divergente — {caminho} ilegível: {e}")
        return 1
    if apenas_cadeira is not None and isinstance(publicada, dict):
        publicada = {apenas_cadeira: publicada.get(apenas_cadeira, {})}
    if not _forma_valida(publicada):
        print(f"rotas: divergente — {caminho} fora da forma {{cadeira: {{chapeu: [gatilho]}}}}")
        return 1

    difs = comparar(tabela, publicada)
    difs_escopo = [d for c, d in difs if no_escopo(c)]
    deriva = [d for c, d in difs if not no_escopo(c)]
    chapeu_escopo = [m for t, c, m in orfaos if t == "chapeu" and no_escopo(c)]
    chapeu_deriva = [m for t, c, m in orfaos if t == "chapeu" and not no_escopo(c)]
    alcance = ("todas as cadeiras" if escopo is None
               else f"cadeiras que esta publicação muda: {', '.join(sorted(escopo)) or 'nenhuma'}")

    if difs_escopo or chapeu_escopo:
        print(f"rotas: divergente — {len(difs_escopo)} chapéu(s) diferem do gerado, "
              f"{len(chapeu_escopo)} órfão(s) de chapéu ({alcance})")
        for d in difs_escopo:
            print(f"  diverge: {d}")
        for o in chapeu_escopo:
            print(f"  órfão de chapéu: {o}")
        rc = 1
    else:
        cauda = (f"; deriva anterior em {len(deriva) + len(chapeu_deriva)} ponto(s) fora do escopo, aviso"
                 if deriva or chapeu_deriva else "")
        print(f"rotas: conforme — {alcance} iguais ao gerado{cauda}")
        rc = 0
    for d in deriva:
        print(f"  aviso, deriva anterior: {d}")
    for o in chapeu_deriva:
        print(f"  aviso, deriva anterior (órfão de chapéu): {o}")
    for o in de_conceito:
        print(f"  aviso, órfão de conceito: {o}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estrito", action="store_true",
                    help="sai != 0 se houver rótulo ou chapéu órfão (para gate de deploy)")
    ap.add_argument("--dry-run", action="store_true",
                    help="imprime a tabela e os órfãos, não escreve o arquivo")
    ap.add_argument("--abertura", default=ABERTURA_PADRAO,
                    help="raiz de abertura/ a varrer e onde mora rotas-chapeu.json "
                         "(default: RAIZ/abertura)")
    ap.add_argument("--cadeira", default=None,
                    help="regenera só o bloco desta cadeira, mesclando no "
                         "rotas-chapeu.json existente em vez de reescrever tudo")
    ap.add_argument("--conferir", action="store_true",
                    help="compara a tabela gerada com o rotas-chapeu.json, sem escrever: "
                         "0 conforme, 1 divergente, 5 indeterminável (gate de publicar-abertura)")
    ap.add_argument("--golden", default=None,
                    help="lê o golden record deste arquivo JSON em vez da API (teste, base sem motor)")
    ap.add_argument("--anterior", default=None,
                    help="com --conferir: abertura no ar; só as cadeiras que mudam em relação a "
                         "ela reprovam, a deriva das outras avisa")
    args = ap.parse_args()

    abertura = args.abertura
    saida = os.path.join(abertura, "rotas-chapeu.json")

    if args.cadeira is not None and not os.path.isdir(os.path.join(abertura, args.cadeira)):
        print(f"gerar_rotas_chapeu: cadeira '{args.cadeira}' não existe em {abertura}",
              file=sys.stderr)
        return 2

    if args.conferir:
        return conferir(abertura, args.cadeira, args.golden, args.anterior)

    golden = golden_record(args.golden) if args.golden is not None else None
    tabela, orfaos = gerar(args.estrito, abertura, apenas_cadeira=args.cadeira, golden=golden)

    for o in orfaos:
        print(f"AVISO órfão: {o}", file=sys.stderr)

    if args.cadeira is not None:
        recorte = {args.cadeira: tabela[args.cadeira]} if args.cadeira in tabela else {args.cadeira: {}}
    else:
        recorte = tabela

    if args.dry_run:
        print(json.dumps(recorte, ensure_ascii=False, indent=2))
    else:
        if args.cadeira is not None:
            # Carrega o existente preservando a ordem de chave tal como está no disco
            # (json.load mantém a ordem de inserção) e só troca o bloco da cadeira
            # pedida — nunca um sort_keys=True no dict inteiro aqui: isso resortiria
            # as chaves aninhadas das OUTRAS cadeiras, mudando byte a byte um bloco
            # que --cadeira prometeu não tocar (achado na materialização real do
            # #3109). Só o bloco da própria cadeira, que é conteúdo novo, sai ordenado.
            final = {}
            if os.path.isfile(saida):
                with open(saida, encoding="utf-8") as f:
                    final = json.load(f)
            if tabela.get(args.cadeira):
                final[args.cadeira] = dict(sorted(tabela[args.cadeira].items()))
            else:
                final.pop(args.cadeira, None)
            sort_keys = False
        else:
            final = tabela
            sort_keys = True

        with open(saida, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            f.write("\n")

        n_cad = len(recorte) if args.cadeira is None else 1
        n_rotas = sum(len(v) for v in recorte.values())
        n_gat = sum(len(r) for v in recorte.values() for r in v.values())
        print(f"escrito {saida}: {n_cad} cadeira(s) tocada(s), {n_rotas} chapéus, "
              f"{n_gat} gatilhos, {len(orfaos)} órfãos", file=sys.stderr)

    if args.estrito and orfaos:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
