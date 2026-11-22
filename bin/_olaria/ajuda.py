"""A ajuda do verbo `ontologia` (cards #4214 e #4254; documento do verbo, referencias/instancias/verbo/ontologia.md).

Duas partes. A primeira é do verbo e não depende de nada: as doze formas da usage e os seis códigos de saída. A segunda vem do
serviço (GET /ajuda), que a monta do catálogo gravado. Com o serviço fora ou a chave faltando, a primeira parte sai sozinha e
sai 0: pedir ajuda nunca falha.
"""
from __future__ import annotations

from .saida import Saida

USAGE = """\
ontologia ler <classe> [<chave>...] [--fichas] [--json]
ontologia listar [<classe>] [--filhas <slug> | --aponta-para <slug> | --capacidade <slug>] [--json]
ontologia criar [<classe>] [<arquivo.yaml>] [--pedido <id>] [--json]
ontologia trocar <classe> <chave> <versao> [<arquivo.yaml>] [--pedido <id>] [--json]
ontologia recompor <classe> <versao> [<arquivo.yaml>] [--pedido <id>] [--json]
ontologia ensaiar [<criar|trocar|recompor>] [<classe>] [<chave>] [<versao>] [<arquivo.yaml>] [--json]
ontologia renomear <classe> <chave> <nova_chave> [--pedido <id>] [--json]
ontologia apagar <classe> <chave> <motivo> [--com <classe> <chave>]... [--pedido <id>] [--json]
ontologia transitar <classe> <chave> <estado> [--pedido <id>] [--json]
ontologia nomes abrir <termo> <chave> <origem> [--pedido <id>] [--json]
ontologia nomes encerrar <termo> <chave> [--pedido <id>] [--json]
ontologia gerar [--json]
ontologia --help\
"""

SAIDAS = (
    (0, "fez o que o ato pede, inclusive listar vazio e repetição de --pedido com mesmo YAML"),
    (1, "não: classe ou ficha inexistente, régua ou raciocinador recusou, versão diferente, pedido com conteúdo diferente, lote em parte"),
    (2, "uso: ato, flag ou chave fora da gramática (`gravar`, variante em escrita, falta de `<versao>`, `parte`, YAML ilegível)"),
    (3, "dependência: Olaria, banco ou raciocinador fora antes de escrita, ou variável OLARIA_URL / OLARIA_CHAVE / PF_CADEIRA ausente"),
    (4, "recusa: política de acesso negou o par (ato, classe)"),
    (5, "indeterminável: prazo estourado ou queda de conexão após o envio; traz o pedido e aponta `conferir` em `proximo`"),
)

NOTAS = (
    "Leia antes de mudar com `ontologia ler <classe> <chave>` ou `ontologia ler <classe> --fichas` para obter a versão (fornada <id>).",
    "Em `shape`, `ler shape <slug>` traz a linhagem e as restrições herdadas, e `listar shape` aceita `--filhas <slug>`, `--aponta-para <slug>` ou `--capacidade <slug>`.",
    "Os itens do catálogo leem-se e listam-se por `shape`, `dicionario`, `tipo-de-ligacao` (ou `ligacao`), `axioma` e `tipo-de-evento`.",
    "Para conferir o que já está gravado (estrato, capacidade ou classe), use `conferir ontologia <estrato:slug|capacidade:slug|classe>`.",
    "Escritas (`criar`, `trocar`, `recompor`, `renomear`, `apagar`, `transitar`) aceitam `--pedido <uuid7>` para repetição idempotente após saída 5.",
    "Fichas que só se apontam entre si saem num pedido só: `apagar <classe> <chave> <motivo> --com <classe> <chave>`, uma fornada e uma transação; ficha apontada por quem está fora do conjunto recusa com `ficha-apontada`.",
    "O YAML pode entrar como caminho `.yaml` (ou `.yml`) ou pela entrada padrão (`-`).",
    "A variante `olaria` (ou `preparar`) só roda em leitura com aviso; na escrita e em `gravar`, sai 2 com `proximo` em `ontologia`.",
)


def texto_do_verbo() -> str:
    saidas = "\n".join(f"  {n}  {texto}" for n, texto in SAIDAS)
    notas = "\n".join(f"  {n}" for n in NOTAS)
    formas = "\n".join(f"  {linha}" for linha in USAGE.splitlines())
    return f"uso:\n{formas}\n\n{notas}\n\nsaídas:\n{saidas}\n"


def _aceita(campo: dict) -> str:
    tipo = campo.get("tipo")
    if campo.get("dicionario"):
        valores = [str(v) for v in campo.get("valores") or []]
        lista = f" ({', '.join(valores)})" if valores else ""
        return f"um valor do dicionário {campo['dicionario']}{lista}"
    if tipo == "ligacao":
        destinos = [str(d) for d in campo.get("destinos") or []]
        categorias = [str(c) for c in campo.get("categorias_de_destino") or []]
        if destinos and categorias:
            return f"a chave humana de uma ficha de {', '.join(destinos)} (ou categoria {', '.join(categorias)})"
        if destinos:
            return f"a chave humana de uma ficha de {', '.join(destinos)}"
        if categorias:
            return f"a chave humana de uma ficha de categoria {', '.join(categorias)}"
        return "a chave humana de uma ficha de destino"
    return "texto livre"


def _quantidade(campo: dict) -> str:
    minimo, maximo = campo.get("minimo") or 0, campo.get("maximo")
    return f"{minimo} a {maximo if maximo is not None else 'n'}"


def _campo_de_ficha(campo: dict) -> str:
    obrigatorio = "obrigatório" if campo.get("obrigatorio") else "opcional"
    return (f"    {campo.get('campo')} · {campo.get('tipo')} · {obrigatorio} · {_quantidade(campo)} · {_aceita(campo)}"
            f" · exemplo {campo.get('exemplo')}")


def _montar_exemplo(slug: str, campos: list[dict], *, so_ensaiaveis: bool) -> list[str]:
    uteis = [c for c in campos if c.get("tipo") != "secao"]
    if not uteis:
        return []
    if so_ensaiaveis:
        if any(not c.get("ensaiavel") for c in uteis if c.get("obrigatorio")):
            return []
        uteis = [c for c in uteis if c.get("ensaiavel")]
        if not uteis:
            return []
    dados = [c for c in uteis if c.get("tipo") != "ligacao"]
    ligacoes = [c for c in uteis if c.get("tipo") == "ligacao"]
    linhas = ["fichas:", f"- classe: {slug}", f"  chave: {slug}:exemplo"]
    if dados:
        linhas += ["  dados:"] + [f"    {c['campo']}: {c.get('exemplo')}" for c in dados]
    if ligacoes:
        linhas += ["  ligacoes:"] + [f"    {c['campo']}: {c.get('exemplo')}" for c in ligacoes]
    return linhas


def _exemplo_de_ficha(classes: dict) -> list:
    for so_ensaiaveis in (True, False):
        for slug in sorted(classes):
            campos = [c for c in classes[slug] if isinstance(c, dict)]
            linhas = _montar_exemplo(slug, campos, so_ensaiaveis=so_ensaiaveis)
            if linhas:
                return linhas
    return []


def texto_dos_campos(corpo: dict) -> str:
    saida = ["", "a mudança é um mapa com estas chaves, nesta ordem (chave fora delas faz o YAML não se ler):",
             "  " + ", ".join(map(str, corpo.get("envelope") or []))]
    catalogo = corpo.get("catalogo") or {}
    if catalogo:
        saida += ["", "campos dos itens de catálogo (nome · obrigatório ou opcional):"]
        for tipo in sorted(catalogo):
            saida.append(f"  {tipo}:")
            saida += [f"    {nome} · obrigatório" for nome in catalogo[tipo].get("obrigatorios") or []]
            saida += [f"    {nome} · opcional" for nome in catalogo[tipo].get("opcionais") or []]
    classes = corpo.get("classes") or {}
    if classes:
        saida += ["", "campos da ficha de cada classe gravada (nome · tipo · obrigatoriedade · quantos · valores aceitos · exemplo):"]
        for slug in sorted(classes):
            saida.append(f"  {slug}:")
            saida += [_campo_de_ficha(c) for c in classes[slug] if isinstance(c, dict)]
        exemplo = _exemplo_de_ficha(classes)
        if exemplo:
            saida += ["", "uma ficha preenchida:"] + [f"  {linha}" for linha in exemplo]
    return "\n".join(saida) + "\n"


HTTP_OK = 200


def ajuda(cliente: object, motivo_sem_servico: str = "") -> Saida:
    base = texto_do_verbo()
    if cliente is None:
        return Saida(0, base + f"\na ajuda dos campos depende do serviço: {motivo_sem_servico}\n")
    from .cliente import PrazoAcabou, SemConexao, SemResposta
    try:
        resposta = cliente.ajuda()
    except (SemConexao, SemResposta, PrazoAcabou) as erro:
        return Saida(0, base + f"\na ajuda dos campos depende do serviço, que não respondeu: {erro or type(erro).__name__}\n")
    if resposta.status != HTTP_OK:
        return Saida(0, base + f"\na ajuda dos campos depende do serviço, que respondeu {resposta.status}\n")
    return Saida(0, base + texto_dos_campos(resposta.corpo))
