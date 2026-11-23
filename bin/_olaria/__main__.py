"""Despacho do verbo `ontologia` (cards #4214 e #4254; documento do verbo, referencias/instancias/verbo/ontologia.md).

Formas canônicas em `ontologia <ato> ...`; `olaria` é variante aceita apenas na leitura (com aviso na primeira linha)
e recusada com saída 2 na escrita e em `gravar`. Não abre o banco nem importa `olaria`: só chama o serviço por HTTP.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from . import ajuda as ajuda_
from . import saida as sd
from .cliente import AmbienteIncompleto, Cliente, PrazoAcabou, SemConexao, SemResposta, e_uuid7, novo_id
from .saida import Saida

PEDIDOS_DE_AJUDA = ("--help", "-h", "--ajuda")
VARIANTES_VERBO = {"olaria", "gerador"}
VARIANTES_DESTRUICAO = {"delete", "remover", "excluir", "drop", "destroy", "purge", "rm"}
VARIANTES_CLASSE_CATALOGO = {
    "ligacao": "tipo-de-ligacao",
    "ligacoes": "tipo-de-ligacao",
    "tipos-de-ligacao": "tipo-de-ligacao",
    "tipos_de_ligacao": "tipo-de-ligacao",
    "dicionarios": "dicionario",
    "axiomas": "axioma",
    "tipos-de-evento": "tipo-de-evento",
    "tipos_de_evento": "tipo-de-evento",
    "classes": "shape",
    "shapes": "shape",
}
FLAGS_DE_ENSAIO = ("--dry-run", "--ensaio")
ATOS_LEITURA = {"ler", "listar", "ensaiar", "gerar", "preparar"}
ATOS_ESCRITA = {"criar", "trocar", "recompor", "renomear", "apagar", "transitar", "nomes"}
_PARTE_YAML = re.compile(r"(?m)^\s*(?:#\s*parte\b|parte\s*:\s*true\b)")


def _classe_canonica(classe: str) -> str:
    return VARIANTES_CLASSE_CATALOGO.get(classe, classe)


class Uso(Exception):
    """Erro de forma/uso da chamada: devolve saída 2 e o próximo comando em 6 campos."""

    def __init__(self, mensagem: str, *, codigo: str = "uso-invalido", onde: str = "chamada",
                 recebido: object = "", regra: str | None = None, proximo: str = "ontologia --help"):
        super().__init__(mensagem)
        self.codigo = codigo
        self.onde = onde
        self.recebido = recebido
        self.regra = regra or "A chamada segue a gramática e a forma posicional de `ontologia`."
        self.proximo = proximo


def _separar_json(args: list) -> tuple[list, bool]:
    return [a for a in args if a != "--json"], "--json" in args


def _extrair_pedido(args: list, ato: str) -> tuple[list, str]:
    if "--fornada" in args:
        idx = args.index("--fornada")
        tem_val = idx + 1 < len(args) and not _e_entrada_yaml(args[idx + 1]) and not args[idx + 1].startswith("--")
        if tem_val:
            val = args[idx + 1]
            limpos = args[:idx] + args[idx + 2:]
            partes = ["ontologia", ato, *limpos, "--pedido", val]
        else:
            limpos = args[:idx] + args[idx + 1:]
            partes = ["ontologia", ato, *limpos]
        sugestao = " ".join(p for p in partes if p)
        raise Uso(
            "`--fornada` é variante de flag em escrita; use `--pedido`.",
            codigo="variante-de-flag",
            onde="flag",
            recebido="--fornada",
            regra="Na escrita, o identificador de repetição vem na flag `--pedido <uuid7>`.",
            proximo=sugestao,
        )
    out, pedido = [], ""
    i = 0
    while i < len(args):
        if args[i] == "--pedido":
            if i + 1 >= len(args) or not e_uuid7(args[i + 1]):
                raise Uso(
                    "`--pedido` exige um uuid v7 válido.",
                    codigo="pedido-invalido",
                    onde="--pedido",
                    recebido=args[i + 1] if i + 1 < len(args) else "",
                    regra="O identificador de `--pedido` é um uuid v7 válido.",
                    proximo=f"ontologia {ato} --help",
                )
            pedido = args[i + 1]
            i += 2
        else:
            out.append(args[i])
            i += 1
    return out, pedido


def _arquivo(caminho: str, proximo: str = "ontologia --help") -> str:
    try:
        return Path(caminho).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        raise Uso(
            f"não consegui ler {caminho}: {erro}",
            codigo="arquivo-ilegivel",
            onde="arquivo",
            recebido=caminho,
            regra="O caminho do arquivo YAML precisa existir e ser legível em UTF-8.",
            proximo=proximo,
        ) from erro


def _ler_entrada_yaml(caminho: str | None, *, proximo: str) -> tuple[str, str]:
    if caminho is not None and caminho != "-":
        return caminho, _arquivo(caminho, proximo=proximo)
    if caminho == "-" or not sys.stdin.isatty():
        texto = sys.stdin.read()
        if texto.strip():
            return "<stdin>", texto
    raise Uso(
        "falta o arquivo `.yaml` (ou YAML pela entrada padrão).",
        codigo="yaml-ausente",
        onde="entrada",
        recebido="(vazio)",
        regra="O conteúdo YAML entra por caminho `.yaml` ou pela entrada padrão.",
        proximo=proximo,
    )


def _recusar_parte(texto: str, proximo: str) -> None:
    if _PARTE_YAML.search(texto):
        raise Uso(
            "recorte marcado como `parte` é recusado antes da escrita.",
            codigo="recorte-parcial",
            onde="yaml",
            recebido="parte",
            regra="Conteúdo YAML marcado como `parte` é recusado com saída 2 antes do envio ao escritor.",
            proximo=proximo,
        )


def _e_yaml(argumento: str) -> bool:
    return argumento.endswith((".yaml", ".yml"))


def _e_entrada_yaml(argumento: str) -> bool:
    return argumento == "-" or _e_yaml(argumento)


def _ler(cliente: Cliente, args: list, *, como_json: bool = False, aviso_variante: str = "") -> Saida:
    if not args or args[0].startswith("--"):
        raise Uso("ler exige a classe como primeiro argumento", onde="classe", recebido=args[0] if args else "",
                  proximo="ontologia listar")
    classe, resto = _classe_canonica(args[0]), args[1:]
    fichas = "--fichas" in resto
    chaves = [a for a in resto if a != "--fichas"]
    if any(c.startswith("--") for c in chaves):
        ruins = next(c for c in chaves if c.startswith("--"))
        raise Uso(f"opção desconhecida: {ruins}", onde="flag", recebido=ruins, proximo=f"ontologia ler {classe} --help")
    if fichas and chaves:
        raise Uso("use `--fichas` sem chaves, ou passe as chaves para ler", onde="args", recebido=" ".join(resto),
                  proximo=f"ontologia ler {classe} --fichas")
    r = cliente.ler(classe, chaves, fichas)
    return sd.traduzir("ler", r.status, r.corpo, como_json=como_json, aviso_variante=aviso_variante)


def _preparar(cliente: Cliente, args: list, *, como_json: bool = False, aviso_variante: str = "") -> Saida:
    if not args or args[0].startswith("--"):
        raise Uso("preparar exige a classe como primeiro argumento", onde="classe", recebido="", proximo="ontologia listar")
    classe = _classe_canonica(args[0])
    nota = aviso_variante or f"aviso: forma canônica ontologia ler {classe}"
    return _ler(cliente, [classe, *args[1:]], como_json=como_json, aviso_variante=nota)


def _listar(cliente: Cliente, args: list, *, como_json: bool = False, aviso_variante: str = "") -> Saida:
    flags_validas = ("--filhas", "--aponta-para", "--capacidade")
    for a in args:
        if a.startswith("--") and a not in flags_validas:
            raise Uso(f"opção desconhecida: {a}", onde="flag", recebido=a, proximo="ontologia listar")
    usadas = [f for f in flags_validas if f in args]
    if len(usadas) > 1:
        raise Uso(
            "use `--filhas <slug>`, `--aponta-para <slug>` ou `--capacidade <slug>`, não mais de uma na mesma chamada",
            onde="flag",
            recebido=" ".join(args),
            proximo="ontologia listar shape --filhas <slug>",
        )
    if usadas:
        flag = usadas[0]
        idx = args.index(flag)
        if idx + 1 >= len(args) or args[idx + 1].startswith("--") or not args[idx + 1].strip():
            raise Uso(
                f"`{flag}` exige o slug",
                onde=flag,
                recebido=" ".join(args),
                proximo=f"ontologia listar shape {flag} <slug>",
            )
        alvo = args[idx + 1]
        resto = [_classe_canonica(r) for r in (args[:idx] + args[idx + 2:])]
        if len(resto) != 1 or resto[0] != "shape":
            raise Uso(
                f"`{flag}` só vale em `ontologia listar shape`",
                onde="classe",
                recebido=" ".join(args),
                proximo=f"ontologia listar shape {flag} {alvo}",
            )
        r = cliente.listar(
            "shape",
            filhas=alvo if flag == "--filhas" else None,
            aponta_para=alvo if flag == "--aponta-para" else None,
            capacidade=alvo if flag == "--capacidade" else None,
        )
        return sd.traduzir("listar", r.status, r.corpo, como_json=como_json, aviso_variante=aviso_variante)
    if len(args) > 1:
        raise Uso("listar aceita no máximo a classe", onde="args", recebido=" ".join(args), proximo="ontologia listar")
    classe = _classe_canonica(args[0]) if args else ""
    r = cliente.listar(classe)
    return sd.traduzir("listar", r.status, r.corpo, como_json=como_json, aviso_variante=aviso_variante)


def _ensaiar(cliente: Cliente, args: list, *, como_json: bool = False, aviso_variante: str = "") -> Saida:
    if any(a.startswith("--") for a in args):
        flag = next(a for a in args if a.startswith("--"))
        raise Uso(f"ensaiar: opção desconhecida {flag}", onde="flag", recebido=flag,
                  proximo="ontologia ensaiar <arquivo.yaml>")
    if not args:
        raise Uso("ensaiar quer `[<criar|trocar|recompor>] ... <arquivo.yaml>`",
                  onde="args", recebido="", proximo="ontologia ensaiar <arquivo.yaml>")
    ato_alvo: str | None = None
    versao: str | None = None
    resto = list(args)
    if resto[0] in ("criar", "trocar", "recompor"):
        ato_alvo = resto.pop(0)
        if not resto:
            raise Uso(f"ensaiar {ato_alvo} quer os argumentos de {ato_alvo} ou `<arquivo.yaml>`",
                      onde="args", recebido=ato_alvo, proximo=f"ontologia ensaiar {ato_alvo} <arquivo.yaml>")
    arquivos = [a for a in resto if _e_entrada_yaml(a)]
    if ato_alvo is None and not arquivos:
        alvo = resto[0] if resto else ""
        proximo = f"conferir ontologia {alvo}".strip() if alvo else "conferir ontologia"
        raise Uso(
            "Use `conferir ontologia` para conferir capacidade, estrato ou classe já gravada; `ontologia ensaiar` pede um arquivo `.yaml`.",
            codigo="uso-invalido",
            onde="args",
            recebido=" ".join(resto),
            regra="O ato `ensaiar` do verbo `ontologia` confere uma mudança em YAML; o gravado se confere com `conferir ontologia`.",
            proximo=proximo,
        )
    if len(arquivos) > 1:
        raise Uso("passe apenas um arquivo `.yaml` em ensaiar", onde="args", recebido=" ".join(resto),
                  proximo="ontologia ensaiar <arquivo.yaml>")
    if ato_alvo in ("trocar", "recompor"):
        for a in resto:
            if not _e_entrada_yaml(a) and e_uuid7(a):
                versao = a
                break
    caminho = arquivos[0] if arquivos else None
    _, texto = _ler_entrada_yaml(caminho, proximo=f"ontologia ensaiar {ato_alvo or 'criar'} <arquivo.yaml>")
    # DT 667: ensaiar sem ato ensaia criar, para acusar ficha-chave-ja-existe como criar acusa.
    r = cliente.ensaiar(texto, ato=ato_alvo or "criar", versao=versao)
    return sd.traduzir("ensaiar", r.status, r.corpo, como_json=como_json, aviso_variante=aviso_variante)


def _criar(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    if any(a.startswith("--") for a in args):
        flag = next(a for a in args if a.startswith("--"))
        raise Uso(f"criar: opção desconhecida {flag}", onde="flag", recebido=flag,
                  proximo="ontologia criar <arquivo.yaml>")
    if len(args) > 2:
        raise Uso("criar aceita `[<classe>] [<arquivo.yaml>]`", onde="args", recebido=" ".join(args),
                  proximo="ontologia criar <arquivo.yaml>")
    caminho: str | None = None
    if len(args) == 1:
        if _e_entrada_yaml(args[0]):
            caminho = args[0]
    elif len(args) == 2:
        if not _e_entrada_yaml(args[1]):
            raise Uso("o segundo argumento posicional de criar precisa ser `.yaml`", onde="arquivo", recebido=args[1],
                      proximo=f"ontologia criar {_classe_canonica(args[0])} <arquivo.yaml>")
        caminho = args[1]
    _, texto = _ler_entrada_yaml(caminho, proximo="ontologia criar <arquivo.yaml>")
    _recusar_parte(texto, "ontologia ler <classe> --fichas")
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    pedido_id = pedido or novo_id()
    try:
        r = cliente.criar(texto, pedido_id)
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("criar", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("criar", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _trocar(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    if any(a.startswith("--") for a in args):
        flag = next(a for a in args if a.startswith("--"))
        raise Uso(f"trocar: opção desconhecida {flag}", onde="flag", recebido=flag,
                  proximo="ontologia trocar <classe> <chave> <versao> <arquivo.yaml>")
    if len(args) == 1 and _e_entrada_yaml(args[0]):
        classe, chave, versao, caminho = None, None, None, args[0]
        _, texto = _ler_entrada_yaml(caminho, proximo="ontologia trocar <arquivo.yaml>")
        _recusar_parte(texto, "ontologia ler <classe> <chave>")
    else:
        if len(args) < 3 or len(args) > 4:
            classe_sug = _classe_canonica(args[0]) if args and not _e_entrada_yaml(args[0]) else "<classe>"
            chave_sug = args[1] if len(args) >= 2 and not _e_entrada_yaml(args[1]) else "<chave>"
            raise Uso(
                "trocar exige `<classe> <chave> <versao> [<arquivo.yaml>]` em posição, ou `<arquivo.yaml>` com `versao` em cada item.",
                codigo="versao-ausente",
                onde="versao",
                recebido=" ".join(args) or "(vazio)",
                regra="Chamada a `trocar` sem `<versao>` em posição (salvo lote em `<arquivo.yaml>` com `versao` por item), ou com `<versao>` que não é uuid v7, para antes da Olaria.",
                proximo=f"ontologia ler {classe_sug} {chave_sug}",
            )
        classe, chave, versao = _classe_canonica(args[0]), args[1], args[2]
        if not e_uuid7(versao):
            raise Uso(
                f"`{versao}` não é um uuid v7 de versão lida.",
                codigo="versao-invalida",
                onde="versao",
                recebido=versao,
                regra="Chamada a `trocar` sem `<versao>` em posição, ou com `<versao>` que não é uuid v7, para antes da Olaria.",
                proximo=f"ontologia ler {classe} {chave}",
            )
        caminho = args[3] if len(args) == 4 else None
        if caminho is not None and not _e_entrada_yaml(caminho):
            raise Uso("o caminho da mudança em trocar precisa ser `.yaml`", onde="arquivo", recebido=caminho,
                      proximo=f"ontologia trocar {classe} {chave} {versao} <arquivo.yaml>")
        _, texto = _ler_entrada_yaml(caminho, proximo=f"ontologia trocar {classe} {chave} {versao} <arquivo.yaml>")
        _recusar_parte(texto, f"ontologia ler {classe} {chave}")
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    pedido_id = pedido or novo_id()
    try:
        r = cliente.trocar(texto, versao, pedido_id, classe=classe, chave=chave)
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("trocar", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("trocar", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _recompor(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    if any(a.startswith("--") for a in args):
        flag = next(a for a in args if a.startswith("--"))
        raise Uso(f"recompor: opção desconhecida {flag}", onde="flag", recebido=flag,
                  proximo="ontologia recompor <classe> <versao> <arquivo.yaml>")
    if len(args) < 2 or len(args) > 3:
        classe_sug = _classe_canonica(args[0]) if args and not _e_entrada_yaml(args[0]) else "<classe>"
        raise Uso(
            "recompor exige `<classe> <versao> [<arquivo.yaml>]` em posição.",
            codigo="versao-ausente",
            onde="versao",
            recebido=" ".join(args) or "(vazio)",
            regra="Chamada a `recompor` sem `<versao>` em posição, ou com `<versao>` que não é uuid v7, para antes da Olaria.",
            proximo=f"ontologia ler {classe_sug} --fichas",
        )
    classe, versao = _classe_canonica(args[0]), args[1]
    if not e_uuid7(versao):
        raise Uso(
            f"`{versao}` não é um uuid v7 de versão lida.",
            codigo="versao-invalida",
            onde="versao",
            recebido=versao,
            regra="Chamada a `recompor` sem `<versao>` em posição, ou com `<versao>` que não é uuid v7, para antes da Olaria.",
            proximo=f"ontologia ler {classe} --fichas",
        )
    caminho = args[2] if len(args) == 3 else None
    if caminho is not None and not _e_entrada_yaml(caminho):
        raise Uso("o caminho da mudança em recompor precisa ser `.yaml`", onde="arquivo", recebido=caminho,
                  proximo=f"ontologia recompor {classe} {versao} <arquivo.yaml>")
    _, texto = _ler_entrada_yaml(caminho, proximo=f"ontologia recompor {classe} {versao} <arquivo.yaml>")
    _recusar_parte(texto, f"ontologia ler {classe} --fichas")
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    pedido_id = pedido or novo_id()
    try:
        r = cliente.recompor(texto, versao, pedido_id)
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("recompor", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("recompor", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _renomear(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    classe, pos = None, []
    i = 0
    while i < len(args):
        if args[i] == "--classe":
            if i + 1 >= len(args) or not args[i + 1].strip():
                raise Uso("--classe quer o slug da classe", onde="classe", recebido="",
                          proximo="ontologia renomear <classe> <chave> <nova_chave>")
            classe = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            raise Uso(f"renomear: opção desconhecida {args[i]}", onde="flag", recebido=args[i],
                      proximo="ontologia renomear <classe> <chave> <nova_chave>")
        else:
            pos.append(args[i])
            i += 1
    if len(pos) == 3 and classe is None:
        classe, chave, nova_chave = pos[0], pos[1], pos[2]
    elif len(pos) == 2 and classe:
        chave, nova_chave = pos[0], pos[1]
    else:
        raise Uso("renomear exige `<classe> <chave> <nova_chave>`", onde="args", recebido=" ".join(args),
                  proximo="ontologia renomear <classe> <chave> <nova_chave>")
    if not all(x.strip() for x in (classe, chave, nova_chave)):
        raise Uso("classe, chave e nova_chave não podem ser vazias", onde="args", recebido=" ".join(args),
                  proximo="ontologia renomear <classe> <chave> <nova_chave>")
    classe = _classe_canonica(classe)
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    pedido_id = pedido or novo_id()
    try:
        r = cliente.renomear(chave, nova_chave, pedido_id, origem="ontologia renomear", classe=classe)
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("renomear", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("renomear", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _apagar(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    forma = "ontologia apagar <classe> <chave> <motivo> [--com <classe> <chave>]..."
    # O motivo vai até o primeiro `--com`; cada `--com` leva a classe e a chave de mais uma ficha do mesmo descarte.
    corte = args.index("--com") if "--com" in args else len(args)
    cabeca, resto = args[:corte], args[corte:]
    outra = next((a for a in cabeca if a.startswith("--")), None) or next(
        (a for a in resto if a.startswith("--") and a != "--com"), None)
    if outra:
        raise Uso(f"apagar: opção desconhecida {outra}", onde="flag", recebido=outra, proximo=forma)
    if len(cabeca) < 3 or not cabeca[0].strip() or not cabeca[1].strip() or not " ".join(cabeca[2:]).strip():
        raise Uso("apagar exige `<classe> <chave> <motivo>`, com o motivo antes de qualquer `--com`", onde="args",
                  recebido=" ".join(args), proximo=forma)
    com: list = []
    i = 0
    while i < len(resto):
        grupo = resto[i + 1:i + 3]
        if resto[i] != "--com" or len(grupo) < 2 or any(not x.strip() or x.startswith("--") for x in grupo):
            raise Uso("`--com` leva `<classe> <chave>`", onde="--com", recebido=" ".join(resto[i:i + 3]), proximo=forma)
        com.append((_classe_canonica(grupo[0]), grupo[1]))
        i += 3
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    classe, chave, motivo = _classe_canonica(cabeca[0]), cabeca[1], " ".join(cabeca[2:]).strip()
    pedido_id = pedido or novo_id()
    try:
        r = cliente.apagar(chave, motivo, pedido_id, origem="ontologia apagar", classe=classe, com=com)
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("apagar", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("apagar", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _transitar(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    forma = "ontologia transitar <classe> <chave> <estado>"
    outra = next((a for a in args if a.startswith("--")), None)
    if outra:
        raise Uso(f"transitar: opção desconhecida {outra}", onde="flag", recebido=outra, proximo=forma)
    if len(args) != 3 or not all(a.strip() for a in args):
        raise Uso("transitar exige `<classe> <chave> <estado>`", onde="args", recebido=" ".join(args), proximo=forma)
    classe, chave, para = _classe_canonica(args[0]), args[1], args[2]
    if not cliente.sujeito:
        return sd.ambiente_incompleto("PF_CADEIRA")
    pedido_id = pedido or novo_id()
    try:
        r = cliente.transitar(classe, chave, para, pedido_id, origem="ontologia transitar")
    except PrazoAcabou:
        return sd.desfecho_indeterminavel("transitar", cliente.prazo_s, pedido_id, como_json=como_json)
    return sd.traduzir("transitar", r.status, r.corpo, como_json=como_json, fornada=pedido_id)


def _gerar(cliente: Cliente, args: list, *, como_json: bool = False, aviso_variante: str = "") -> Saida:
    if args:
        raise Uso("gerar não recebe argumento", onde="args", recebido=" ".join(args), proximo="ontologia gerar")
    r = cliente.gerar()
    return sd.traduzir("gerar", r.status, r.corpo, como_json=como_json, aviso_variante=aviso_variante)


def _proximo_para_gravar(args: list, env: dict) -> str:
    limpos = [a for a in args if not a.startswith("--") and a != "--json"]
    if len(limpos) >= 2 and not _e_entrada_yaml(limpos[0]) and not _e_entrada_yaml(limpos[1]):
        classe, chave = _classe_canonica(limpos[0]), limpos[1]
        try:
            r = Cliente.do_ambiente(env).ler(classe, [chave])
            if r.status == 200 and r.corpo.get("versao"):
                return f"ontologia trocar {classe} {chave} {r.corpo['versao']}"
        except Exception:
            pass
        return f"ontologia trocar {classe} {chave} <versao>  |  ontologia criar {classe} <arquivo.yaml>"
    arq = next((a for a in limpos if _e_entrada_yaml(a)), "<arquivo.yaml>")
    return f"ontologia criar {arq}  |  ontologia trocar <classe> <chave> <versao> {arq}"


def _proximo_para_destruicao(args: list) -> str:
    """O verbo ontologia não tem `retirar`: a palavra de destruição leva à leitura do objeto, nunca a `apagar`."""
    limpos = [a for a in args if not a.startswith("--") and not _e_entrada_yaml(a)
              and a.lower() not in VARIANTES_DESTRUICAO]
    if len(limpos) >= 2:
        return f"ontologia ler {_classe_canonica(limpos[0])} {limpos[1]}"
    if limpos:
        return f"ontologia listar {_classe_canonica(limpos[0])}"
    return "ontologia listar"


def _checar_gates_de_uso(ato: str, args: list, *, prog: str, como_json: bool, env: dict) -> Saida | None:
    if any(t.lower() in VARIANTES_DESTRUICAO for t in [ato, *args]):
        ruim = next(t for t in [ato, *args] if t.lower() in VARIANTES_DESTRUICAO)
        return sd.erro_de_uso(
            "termo-de-destruicao", "ato", ruim,
            "O verbo ontologia não tem `retirar`: palavra de destruição não executa e leva à leitura do objeto, nunca a `apagar`.",
            "Leia o objeto antes de decidir; tirar a ficha de vez é `apagar`, escrita que não volta e que vai ao dono antes do ato.",
            _proximo_para_destruicao(args),
            como_json=como_json,
        )
    if any(f in FLAGS_DE_ENSAIO for f in args):
        flag = next(f for f in args if f in FLAGS_DE_ENSAIO)
        sem_flag = [a for a in args if a not in FLAGS_DE_ENSAIO]
        ato_alvo = ato if ato in ("criar", "trocar", "recompor") else ""
        sug = " ".join(x for x in ["ontologia", "ensaiar", ato_alvo, *sem_flag] if x)
        return sd.erro_de_uso(
            "variante-de-flag", "flag", flag,
            "As flags `--dry-run` e `--ensaio` não executam escrita: o ensaio usa o ato `ensaiar`.",
            "Use `ontologia ensaiar` em vez de flag de simulação.",
            sug,
            como_json=como_json,
        )
    if ato == "sonda":
        alvo = args[0] if args and not args[0].startswith("--") else ""
        proximo = f"conferir ontologia {alvo}".strip() if alvo else "conferir ontologia"
        return sd.erro_de_uso(
            "uso-invalido", "ato", "sonda",
            "A conferência do que já está gravado saiu de `ontologia` e mora em `conferir ontologia`.",
            "Use `conferir ontologia <estrato:slug|capacidade:slug|classe>` para conferir o gravado.",
            proximo,
            como_json=como_json,
        )
    if ato == "gravar":
        proximo = _proximo_para_gravar(args, env)
        return sd.erro_de_uso(
            "ato-recusado", "ato", "gravar",
            "Toda classe da ontologia opera como classe guardada: `gravar` é recusado e substituído por `criar` ou `trocar`.",
            "Use `ontologia criar` para objeto novo ou `ontologia trocar <classe> <chave> <versao>` para objeto existente.",
            proximo,
            como_json=como_json,
        )
    if prog in VARIANTES_VERBO and ato in ATOS_ESCRITA:
        return sd.erro_de_uso(
            "variante-em-escrita", "verbo", f"{prog} {ato}",
            "Variante de verbo (`olaria`, `gerador`) só executa em leitura; na escrita recusa sem tocar no banco.",
            f"Chame a forma canônica `ontologia {ato}`.",
            f"ontologia {ato} {' '.join(args)}".strip(),
            como_json=como_json,
        )
    return None


def _ler_lote_nomes(caminho: str, sub: str) -> list[dict]:
    import json
    proximo = f"ontologia nomes {sub} --help"
    if caminho == "-":
        texto = sys.stdin.read()
    else:
        texto = _arquivo(caminho, proximo=proximo)
    if not texto.strip():
        raise Uso("entrada de nomes vazia", codigo="uso-invalido", onde="entrada", recebido="(vazio)", proximo=proximo)
    dados = None
    try:
        dados = json.loads(texto)
    except ValueError:
        try:
            import yaml  # type: ignore[import-not-found]
            dados = yaml.safe_load(texto)
        except (ImportError, ValueError, OSError) as erro:
            raise Uso(f"não consegui ler o lote de nomes: {erro}", codigo="uso-invalido", onde="entrada",
                      recebido=caminho, proximo=proximo) from erro
    if isinstance(dados, dict) and isinstance(dados.get("nomes"), list):
        dados = dados["nomes"]
    if not isinstance(dados, list) or not dados or not all(isinstance(x, dict) for x in dados):
        raise Uso("o lote de nomes deve ser uma lista não vazia de objetos", codigo="uso-invalido",
                  onde="entrada", recebido=caminho, proximo=proximo)
    return dados


def _nomes(cliente: Cliente, args: list, *, pedido: str = "", como_json: bool = False) -> Saida:
    if not args or args[0] not in ("abrir", "encerrar"):
        raise Uso(
            "nomes exige o sub-ato `abrir` ou `encerrar`",
            onde="sub-ato",
            recebido=args[0] if args else "",
            proximo="ontologia nomes abrir <termo> <chave> <origem>",
        )
    sub, resto = args[0], args[1:]
    if any(a.startswith("--") for a in resto):
        flag = next(a for a in resto if a.startswith("--"))
        raise Uso(f"nomes {sub}: opção desconhecida {flag}", onde="flag", recebido=flag,
                  proximo=f"ontologia nomes {sub} --help")
    if len(resto) == 1 and (resto[0] == "-" or resto[0].endswith((".json", ".yaml", ".yml"))):
        itens = _ler_lote_nomes(resto[0], sub)
    elif sub == "abrir":
        if len(resto) != 3:
            raise Uso(
                "nomes abrir exige `<termo> <chave> <origem>` (ou um arquivo .json/.yaml ou `-`)",
                onde="args",
                recebido=" ".join(resto),
                proximo="ontologia nomes abrir <termo> <chave> <origem>",
            )
        itens = [{"termo": resto[0], "chave": resto[1], "origem": resto[2]}]
    else:
        if len(resto) != 2:
            raise Uso(
                "nomes encerrar exige `<termo> <chave>` (ou um arquivo .json/.yaml ou `-`)",
                onde="args",
                recebido=" ".join(resto),
                proximo="ontologia nomes encerrar <termo> <chave>",
            )
        itens = [{"termo": resto[0], "chave": resto[1]}]
    fornada_id = pedido or novo_id()
    r = cliente.nomes(sub, itens, fornada_id, origem=f"ontologia nomes {sub}")
    return sd.traduzir("nomes", r.status, r.corpo, como_json=como_json, fornada=fornada_id)


def executar(argv: list, env: dict | None = None, *, prog: str | None = None) -> Saida:
    """Roda uma chamada e devolve a saída, sem escrever nada."""
    env = dict(os.environ if env is None else env)
    prog = prog or env.get("PF_PECA") or "ontologia"
    if any(a in PEDIDOS_DE_AJUDA for a in argv):
        try:
            cliente = Cliente.do_ambiente(env)
        except AmbienteIncompleto as erro:
            return ajuda_.ajuda(None, f"{erro} não está no ambiente")
        return ajuda_.ajuda(cliente)
    if not argv:
        return sd.erro_de_uso(
            "uso-invalido", "chamada", "",
            "A chamada ao verbo `ontologia` exige um ato.",
            "Consulte as 12 formas da ajuda com `ontologia --help`.",
            "ontologia --help",
        )
    ato, resto = argv[0], list(argv[1:])
    args, como_json = _separar_json(resto)
    gate = _checar_gates_de_uso(ato, args, prog=prog, como_json=como_json, env=env)
    if gate is not None:
        return gate
    todos_atos = ATOS_LEITURA | ATOS_ESCRITA
    if ato not in todos_atos:
        return sd.erro_de_uso(
            "ato-inexistente", "ato", ato,
            f"Os atos de `ontologia` são {', '.join(sorted(todos_atos - {'preparar'}))}.",
            "Escolha um ato válido do verbo `ontologia`.",
            "ontologia --help",
            como_json=como_json,
        )
    aviso_var = ""
    if prog in VARIANTES_VERBO or ato == "preparar":
        canonico = "ler" if ato == "preparar" else ato
        aviso_var = f"aviso: forma canônica ontologia {canonico}"
    try:
        pedido = ""
        if ato in ATOS_ESCRITA:
            args, pedido = _extrair_pedido(args, ato)
        elif "--pedido" in args or "--fornada" in args:
            flag = "--pedido" if "--pedido" in args else "--fornada"
            raise Uso(f"`{flag}` só vale em escrita", codigo="uso-invalido", onde="flag", recebido=flag,
                      proximo=f"ontologia {ato} --help")
        cliente = Cliente.do_ambiente(env)
        if ato == "ler":
            return _ler(cliente, args, como_json=como_json, aviso_variante=aviso_var)
        if ato == "preparar":
            return _preparar(cliente, args, como_json=como_json, aviso_variante=aviso_var)
        if ato == "listar":
            return _listar(cliente, args, como_json=como_json, aviso_variante=aviso_var)
        if ato == "ensaiar":
            return _ensaiar(cliente, args, como_json=como_json, aviso_variante=aviso_var)
        if ato == "gerar":
            return _gerar(cliente, args, como_json=como_json, aviso_variante=aviso_var)
        if ato == "criar":
            return _criar(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "trocar":
            return _trocar(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "recompor":
            return _recompor(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "renomear":
            return _renomear(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "apagar":
            return _apagar(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "transitar":
            return _transitar(cliente, args, pedido=pedido, como_json=como_json)
        if ato == "nomes":
            return _nomes(cliente, args, pedido=pedido, como_json=como_json)
    except Uso as erro:
        return sd.erro_de_uso(erro.codigo, erro.onde, erro.recebido, erro.regra, str(erro), erro.proximo,
                              como_json=como_json)
    except AmbienteIncompleto as erro:
        return sd.ambiente_incompleto(str(erro))
    except SemConexao as erro:
        return sd.sem_conexao(env.get("OLARIA_URL", ""), str(erro))
    except SemResposta as erro:
        if ato in ATOS_ESCRITA:
            return sd.desfecho_indeterminavel(ato, Cliente.do_ambiente(env).prazo_s, pedido or "", como_json=como_json)
        return sd.sem_resposta(str(erro))
    except PrazoAcabou:
        if ato in ATOS_ESCRITA:
            return sd.desfecho_indeterminavel(ato, Cliente.do_ambiente(env).prazo_s, pedido or "", como_json=como_json)
        return sd.sem_resposta(f"prazo de {Cliente.do_ambiente(env).prazo_s:g} s acabou")
    return sd.erro_de_uso("uso-invalido", "chamada", ato, "Chamada inválida.", "Veja a ajuda.", "ontologia --help")


def main(argv: list | None = None, *, prog: str | None = None) -> int:
    saida = executar(list(sys.argv[1:] if argv is None else argv), prog=prog)
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    if saida.stdout:
        sys.stdout.write(saida.stdout)
        sys.stdout.flush()
    if saida.stderr:
        sys.stderr.write(saida.stderr)
        sys.stderr.flush()
    return saida.codigo


if __name__ == "__main__":
    raise SystemExit(main())
