"""Lint de plano de diagrama — validação contra esquema e regras estruturais."""
import json
import sys
from pathlib import Path
import jsonschema

TAXONOMIA = ("camada", "modulo", "componente-e-conector", "alocacao", "fluxo")
# No fluxo, o tipo da entidade é a forma do padrão de diagramas: elipse nas pontas, retângulo
# arredondado para passo, losango para decisão e retângulo para coisa.
FORMAS_DO_FLUXO = ("inicio", "fim", "passo", "decisao", "coisa")
CATEGORIAS = (
    "persistencia", "servico", "superficie", "porta",
    "conhecimento", "host", "mensageria", "identidade", "cadeira"
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "diagrama" / "plano.schema.json"


def _acha_linha(texto: str, termo: str) -> int:
    """Retorna o número da primeira linha (base 1) que contém o termo."""
    for num, linha in enumerate(texto.splitlines(), start=1):
        if termo in linha:
            return num
    return 1


def lint_plano(caminho: str | Path) -> tuple[int, list[str]]:
    """Valida um plano de diagrama. Retorna (codigo_saida, lista_de_defeitos)."""
    p = Path(caminho)
    if not p.is_file():
        return 1, [f"arquivo não encontrado: {caminho}"]

    texto = p.read_text(encoding="utf-8")
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as e:
        return 1, [f"{p}:{e.lineno}: JSON inválido: {e.msg}"]

    if not isinstance(dados, dict):
        return 1, [f"{p}:1: o plano deve ser um objeto JSON"]

    defeitos = []

    # 1. Esquema
    if SCHEMA_PATH.is_file():
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            validator = jsonschema.Draft7Validator(schema)
            for err in validator.iter_errors(dados):
                trecho = str(err.path[-1]) if err.path else ""
                lin = _acha_linha(texto, f'"{trecho}"') if trecho else 1
                defeitos.append(f"{p}:{lin}: esquema: {err.message}")
        except Exception as e:
            defeitos.append(f"{p}:1: falha ao carregar esquema: {e}")

    # 2. Tipo na taxonomia
    tipo = dados.get("tipo")
    if tipo not in TAXONOMIA:
        lin = _acha_linha(texto, f'"{tipo}"') if tipo else 1
        defeitos.append(f"{p}:{lin}: tipo '{tipo}' fora da taxonomia da casa: {', '.join(TAXONOMIA)}")

    fontes = dados.get("fontes", [])
    if not isinstance(fontes, list):
        fontes = []

    # 3. Entidades
    entidades = dados.get("entidades", [])
    entidade_ids = set()
    categorias = set()

    if isinstance(entidades, list):
        for ent in entidades:
            if not isinstance(ent, dict):
                continue
            eid = ent.get("id")
            if eid:
                entidade_ids.add(eid)
            efonte = ent.get("fonte")
            if not efonte or efonte not in fontes:
                lin = _acha_linha(texto, f'"{eid}"') if eid else 1
                defeitos.append(
                    f"{p}:{lin}: entidade '{eid or 'sem_id'}' com fonte '{efonte}' "
                    f"fora da lista de fontes declaradas do plano"
                )
            cat = ent.get("categoria")
            if cat:
                categorias.add(cat)
                if cat not in CATEGORIAS:
                    lin = _acha_linha(texto, f'"{cat}"')
                    defeitos.append(f"{p}:{lin}: categoria '{cat}' fora do catálogo fixo")

    # Teto de 4 categorias técnicas por figura
    cats_tecnicas = {c for c in categorias if c != "cadeira"}
    if len(cats_tecnicas) > 4:
        defeitos.append(
            f"{p}:1: figura excede o teto de 4 categorias técnicas (tem {len(cats_tecnicas)}: "
            f"{', '.join(sorted(cats_tecnicas))})"
        )

    # 4. Relações
    relacoes = dados.get("relacoes", [])
    if isinstance(relacoes, list):
        for rel in relacoes:
            if not isinstance(rel, dict):
                continue
            rotulo = rel.get("rotulo")
            de = rel.get("de")
            para = rel.get("para")
            if not rotulo or not str(rotulo).strip():
                lin = _acha_linha(texto, f'"{de}"') if de else 1
                defeitos.append(f"{p}:{lin}: relação de '{de}' para '{para}' sem rótulo / nome")
            if de and de not in entidade_ids:
                lin = _acha_linha(texto, f'"{de}"')
                defeitos.append(f"{p}:{lin}: relação aponta origem '{de}' não declarada em entidades")
            if para and para not in entidade_ids:
                lin = _acha_linha(texto, f'"{para}"')
                defeitos.append(f"{p}:{lin}: relação aponta destino '{para}' não declarada em entidades")

    # 5. Fluxo: a forma de cada entidade e o que cada forma exige
    if tipo == "fluxo" and isinstance(entidades, list) and isinstance(relacoes, list):
        defeitos += _lint_fluxo(p, texto, entidades, relacoes)

    return (1 if defeitos else 0), defeitos

def _lint_fluxo(p: Path, texto: str, entidades: list, relacoes: list) -> list[str]:
    """Elipse só nas pontas, losango com pergunta e saídas que se distinguem."""
    defeitos: list[str] = []
    rels = [r for r in relacoes if isinstance(r, dict)]
    saidas: dict[str, list[dict]] = {}
    entradas: dict[str, int] = {}
    for r in rels:
        saidas.setdefault(r.get("de"), []).append(r)
        entradas[r.get("para")] = entradas.get(r.get("para"), 0) + 1
    formas: dict[str, int] = {}
    for ent in entidades:
        if not isinstance(ent, dict):
            continue
        eid, forma, nome = ent.get("id"), ent.get("tipo"), str(ent.get("nome", ""))
        lin = _acha_linha(texto, f'"{eid}"') if eid else 1
        if forma not in FORMAS_DO_FLUXO:
            defeitos.append(f"{p}:{lin}: no fluxo, o tipo de '{eid}' é a forma, uma de: "
                            f"{', '.join(FORMAS_DO_FLUXO)}; veio '{forma}'")
            continue
        formas[forma] = formas.get(forma, 0) + 1
        if forma == "inicio" and entradas.get(eid):
            defeitos.append(f"{p}:{lin}: '{eid}' é início e recebe seta; a elipse fica só na ponta")
        if forma == "fim" and saidas.get(eid):
            defeitos.append(f"{p}:{lin}: '{eid}' é fim e solta seta; a elipse fica só na ponta")
        if forma == "decisao":
            if not nome.rstrip().endswith("?"):
                defeitos.append(f"{p}:{lin}: a decisão '{eid}' tem de ser pergunta, terminada em '?'")
            rotulos = [str(r.get("rotulo", "")).strip() for r in saidas.get(eid, [])]
            if len(rotulos) < 2:
                defeitos.append(f"{p}:{lin}: a decisão '{eid}' tem {len(rotulos)} saída; decisão tem duas ou mais")
            elif len(set(rotulos)) < len(rotulos):
                defeitos.append(f"{p}:{lin}: a decisão '{eid}' tem saídas com o mesmo rótulo")
        if forma in ("passo", "decisao") and not saidas.get(eid):
            defeitos.append(f"{p}:{lin}: '{eid}' não tem saída; o fluxo só para num fim")
    for forma in ("inicio", "fim"):
        if not formas.get(forma):
            defeitos.append(f"{p}:1: o fluxo não tem {forma}")
    return defeitos

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("uso: diagrama lint <plano.json>", file=sys.stderr)
        return 2
    cod, defeitos = lint_plano(argv[0])
    for d in defeitos:
        print(d, file=sys.stderr if cod != 0 else sys.stdout)
    return cod
