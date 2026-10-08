"""oplog — o unico modulo que escreve e le o bruto da porta (card #3344, arq:0123 §3-§5).

O bruto e um arquivo JSONL por dia, `ops-AAAA-MM-DD.jsonl`, so de acrescimo. Aqui moram
as quatro coisas que a ADR poe num lugar so:

  emitir      grava a linha: carimba `evento_id` (uuid v7) e `schema_v`, apara o campo longo
              antes de serializar e lista o que aparou em `aparado`; nunca sai linha cortada
              no meio, e falha de escrita nunca levanta (vai ao stderr, como o `_audit`).
  classificar o desfecho vira `classe`, `causa` e `classe_fonte` pela tabela do arq:0123 §5.
              E a mesma funcao que relê linha antiga sem classe.
  ler         dias, nunca «os N ultimos arquivos»: devolve os eventos e a contagem de
              legiveis e ilegiveis por dia; dia sem arquivo e «ausente», nunca zero.
  corte       o prazo de 35 dias, o que ha no disco, o teto e a unica remocao (card #3354): o
              timer `corte-bruto` apaga o dia que passou no portao; nada mais apaga o bruto.
  CLI         `python3 -m oplog ler <dia> | --desde <d> [--ate <d>] [--sessao <id>] [--tool <t>]`,
              uma linha JSON por evento, para quem e bash (bin/repo). Sai 3 quando nenhum dia da
              janela tem arquivo; dia que falta no meio sai no stderr e a leitura segue (exit 0).

So biblioteca padrao: o modulo roda no venv ops, no venv harness e no python3 do sistema.
Fora daqui ninguem abre o diretorio do bruto (controle/tests/test_oplog_unico_leitor.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCHEMA_V = 1
LIMITE_CAMPO = 7000   # bytes de um campo de texto; acima, apara
LINHA_MAX = 8000      # bytes da linha inteira, ja com o \n

# Campos que a classe, a chave e a juncao dependem: o aparo nunca os toca.
PROTEGIDOS = frozenset({"ts", "evento_id", "schema_v", "tool", "evento", "classe", "causa",
                        "classe_fonte", "aparado", "sessao_id", "ordem_id", "exit_code"})

CLASSES = ("ok", "negativa", "gramatica", "negada", "execucao", "interrompida")
_POR_EXIT = {0: "ok", 1: "negativa", 2: "gramatica", 4: "negada"}
_EVENTO_GRAMATICA = frozenset({"sem_verbo", "cwd_recusado", "escrita_recusada"})
_POR_CLASSE_ERRO = {"gramatica": "gramatica", "faixa": "gramatica", "recusado": "negada",
                    "caminho": "negativa", "binario": "negativa"}
_ABRIR_PROCESSO = ("falha ao abrir", "nao abriu", "não abriu")


# --- onde mora ------------------------------------------------------------------------

def diretorio() -> Path:
    """OPS_LOG_DIR e o nome do diretorio; PF_LOG_OPS e PF_OPS_LOG_DIR seguem lidos so como
    alias antigo; sem nenhum, a instancia (`PLATAFIRMA_INSTANCIA`/var/log/ops)."""
    for nome in ("OPS_LOG_DIR", "PF_LOG_OPS", "PF_OPS_LOG_DIR"):
        valor = os.environ.get(nome)
        if valor:
            return Path(valor)
    instancia = os.environ.get("PLATAFIRMA_INSTANCIA") or "/srv/platafirma/casa"
    return Path(instancia) / "var" / "log" / "ops"


def _dia(d) -> str:
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    texto = str(d).strip()
    date.fromisoformat(texto)          # ValueError para o que nao e AAAA-MM-DD
    return texto


def caminho_do_dia(dia, diretorio_=None) -> Path:
    return Path(diretorio_ or diretorio()) / f"ops-{_dia(dia)}.jsonl"


# --- chave ----------------------------------------------------------------------------

def uuid7(agora_ms: int | None = None) -> str:
    """uuid v7 (RFC 9562) montado a mao: 48 bits de milissegundo, versao 7, variante 10 e
    74 bits aleatorios. Ordena por tempo; `uuid.uuid7` so existe no Python 3.14."""
    ms = int(time.time() * 1000) if agora_ms is None else int(agora_ms)
    aleatorio = int.from_bytes(os.urandom(10), "big")
    rand_a = (aleatorio >> 68) & 0xFFF
    rand_b = aleatorio & ((1 << 62) - 1)
    valor = ((ms & ((1 << 48) - 1)) << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return str(uuid.UUID(int=valor))


# --- aparo ----------------------------------------------------------------------------

def _bytes(texto: str) -> int:
    return len(texto.encode("utf-8"))


def _corta(texto: str, n: int) -> str:
    """Os primeiros `n` bytes de UTF-8, sem partir caractere no meio."""
    return texto.encode("utf-8")[:max(0, n)].decode("utf-8", "ignore")


def _serializa(reg: dict) -> str:
    return json.dumps(reg, ensure_ascii=False)


def aparar(reg: dict) -> dict:
    """Devolve a copia do registro com todo campo longo aparado e a linha abaixo de
    `LINHA_MAX`. Os campos aparados saem listados em `aparado`. Valor que nao e texto
    (lista, dicionario) e serializado antes de ser aparado, e passa a ser texto."""
    saida = dict(reg)
    aparado: list[str] = list(saida.pop("aparado", None) or [])

    def marca(nome):
        if nome not in aparado:
            aparado.append(nome)

    for nome, valor in list(saida.items()):
        if nome in PROTEGIDOS:
            continue
        texto = valor if isinstance(valor, str) else (
            _serializa(valor) if isinstance(valor, (list, dict)) else None)
        if texto is not None and _bytes(texto) > LIMITE_CAMPO:
            saida[nome] = _corta(texto, LIMITE_CAMPO)
            marca(nome)

    def tamanho():
        return _bytes(_serializa({**saida, "aparado": aparado} if aparado else saida)) + 1

    # A linha inteira ainda estoura (muitos campos grandes): apara o maior de cada vez.
    while tamanho() > LINHA_MAX:
        excesso = tamanho() - LINHA_MAX
        candidatos = [(n, _bytes(v if isinstance(v, str) else _serializa(v)))
                      for n, v in saida.items()
                      if n not in PROTEGIDOS and v not in (None, "", [], {})]
        if not candidatos:
            saida = {c: saida[c] for c in ("ts", "evento_id", "schema_v", "tool", "evento")
                     if c in saida}
            aparado.append("*")
            break
        nome, tam = max(candidatos, key=lambda kv: kv[1])
        valor = saida[nome]
        texto = valor if isinstance(valor, str) else _serializa(valor)
        saida[nome] = _corta(texto, tam - excesso - 32)
        marca(nome)
    if aparado:
        saida["aparado"] = aparado
    return saida


# --- classe ---------------------------------------------------------------------------

def classificar(desfecho: dict, *, declara_exit: bool | None = None) -> dict:
    """O desfecho que a porta observa vira `{classe, causa, classe_fonte}` (arq:0123 §5).

    Le do desfecho: `exit_code`, `erro`, `evento`, `cancelado`. `classe_fonte` e `verbo`
    quando o verbo declara a tabela de exit (`declara_exit`), `tabela` quando a porta deduz.
    A mesma funcao relê a linha antiga, que nao tem `classe`: passa o proprio registro."""
    fonte = "verbo" if (declara_exit if declara_exit is not None
                        else desfecho.get("classe_fonte") == "verbo") else "tabela"
    evento = str(desfecho.get("evento") or "")
    erro = desfecho.get("erro")
    exit_code = desfecho.get("exit_code")

    def r(classe, causa=None):
        out = {"classe": classe, "classe_fonte": fonte}
        if causa:
            out["causa"] = causa
        return out

    if desfecho.get("cancelado") or evento == "interrompida":
        return r("interrompida")
    if evento.startswith("pep_negou") or evento == "auth_negada":
        return r("negada")
    if evento == "pep_indisponivel":
        return r("execucao", "pep_indisponivel")
    if evento in _EVENTO_GRAMATICA or desfecho.get("recusado"):
        return r("gramatica")
    if isinstance(exit_code, int) and not isinstance(exit_code, bool):
        if exit_code in _POR_EXIT:
            return r(_POR_EXIT[exit_code])
        return r("execucao", f"exit_{exit_code}" if exit_code in (3, 5) else "exit_fora_da_tabela")
    # As tools de leitura gravam `classe_erro` no erro (caminho, faixa, binario, gramatica,
    # recusado): argumento torto e gramatica, recusa de morada e negada, o que nao existe e
    # resposta negativa. Execucao e so o que a porta nao soube explicar (conta contra o SLO).
    por_classe_erro = _POR_CLASSE_ERRO.get(str(desfecho.get("classe_erro") or ""))
    if por_classe_erro:
        return r(por_classe_erro)          # `causa` so existe na execucao (CHECK de acervo.log_giro)
    if erro:
        texto = str(erro).lower()
        if texto.startswith("timeout"):
            return r("execucao", "timeout")
        if texto.startswith(_ABRIR_PROCESSO):
            return r("execucao", "abrir_processo")
        return r("execucao", "erro")
    return r("ok")


def _e_giro(reg: dict) -> bool:
    tool = reg.get("tool")
    return reg.get("evento") != "http_req" and tool not in (None, "", "-")


# --- origem ---------------------------------------------------------------------------

def origem_da_linha(reg: dict) -> str:
    """Quem chamou (spec log-de-negocio §3): `agente` quando a linha tem `origem_sessao`,
    `sonda` quando e a linha da sonda, `cadeira` no resto. A sonda (22 a 26/09/2026, um giro
    por minuto) nao tem token proprio: reconhece-se pelo giro da tool `sessao` sem ato, sem
    cadeira e sem sessao (`metrica eventos 2026-09-23 --sessao -`). A mesma funcao rele a
    linha antiga, que nao tem `origem`."""
    if reg.get("origem_sessao"):
        return "agente"
    if (reg.get("tool") == "sessao" and not reg.get("ato") and not reg.get("cadeira")
            and reg.get("sessao_id") in (None, "", "-")):
        return "sonda"
    return "cadeira"


# --- contrato -------------------------------------------------------------------------

MOTIVOS_NEGACAO = ("sem_token", "nao_jwt", "assinatura", "audience", "emissor", "expirado", "outro")
# Os do CHECK de `acervo.log_fecho.motivo_parada` (spec apis-escrita-acervo §D1).
MOTIVOS_PARADA = ("concluiu", "teto_giros", "orcamento_erro", "interrompida")
FONTES_TURNO = ("declarado", "gap", "runner", "hook", "transcript")
# As duas que o chamador autenticado pode entregar com `turno_texto` (card #3357); as demais a
# porta deduz.
FONTES_ENTREGUES = ("hook", "transcript")
FONTES_TOKENS = ("provedor", "estimado")
ORIGENS = ("cadeira", "agente", "sonda")
IDENTIDADE = ("sujeito", "sub", "username", "azp", "sid", "jti")

# Campo obrigatorio por tipo de linha. A chave tem de existir; o valor so pode ser nulo onde
# `NULAVEL` diz. `capacidade`, `ferramenta` e `mapa_v` saem nulos enquanto a projecao do
# golden record nao existe na release (arq:0123 §7); as demais excecoes sao campos que a
# situacao deixa vazios (giro sem sessao nao tem cadeira nem ordem; so ha exit quando o
# verbo roda).
CONTRATO = {
    "toda": ("ts", "evento_id", "schema_v", "origem", "mapa_v"),
    "giro": ("tool", "sessao_id", "cadeira", "ordem_id", "exit_code", "classe", "classe_fonte",
             "bytes_produzidos", "bytes_servidos", "lavado", "capacidade", "ferramenta", "escopo",
             "turno_id", "turno_fonte") + IDENTIDADE,
    "abertura": ("tool", "sessao_id", "chapeu", "roteador_via", "superficie", "tokens_pecas",
                 "metodo_tokens", "prefixo_sha", "montador_sha", "pergunta", "pergunta_bytes") + IDENTIDADE,
    "fecho": ("tool", "evento", "sessao_id", "cadeira", "motivo_parada"),
    "auth_negada": ("evento", "path", "origem_requisicao", "motivo"),
    "http_req": ("evento", "path", "via") + IDENTIDADE,
    "escopo": ("tool", "evento", "sessao_id", "escopo") + IDENTIDADE,
    "turno": ("tool", "evento", "sessao_id", "turno_id", "turno_fonte") + IDENTIDADE,
    "consulta": ("tool", "evento", "origem_consulta", "particao"),
}
NULAVEL = frozenset({"capacidade", "ferramenta", "mapa_v", "cadeira", "ordem_id", "exit_code",
                     "roteador_via", "particao", "origem_consulta", "chapeu",
                     "bytes_produzidos", "bytes_servidos",         # escrita e recusa nao devolvem corpo
                     "pergunta"})                                   # reabertura sem mensagem nova
# Campo que, presente, e erro. A mensagem do dono (`pergunta` na abertura, `query` na consulta da
# abertura) se grava no bruto e so nele (spec log-de-negocio §0/§3); a resposta da cadeira, o
# pacote montado e o token nunca (arq:0061 §5).
PROIBIDOS = {"abertura": ("resposta", "pacote", "pecas", "conteudo"),
             "turno": ("resposta", "pacote", "pecas", "conteudo", "token", "access_token",
                       "refresh_token", "authorization"),         # `texto` e a mensagem do dono (#3357)
             "giro": ("token", "access_token", "refresh_token", "authorization", "resposta")}


def tipo_da_linha(reg: dict) -> str:
    """Que linha do contrato e esta. `outro` nao tem campo obrigatorio alem de `toda`."""
    evento = reg.get("evento")
    if evento in ("auth_negada", "http_req", "escopo", "consulta", "fecho"):
        return evento
    if evento == "turno":
        return "turno"
    if reg.get("tool") == "monta_sessao" and evento in (None, ""):
        return "abertura" if not reg.get("erro") else "outro"      # abertura recusada nao tem pacote
    return "giro" if _e_giro(reg) and evento in EVENTOS_DE_GIRO else "outro"


# O que e chamada de verbo, de arquivo ou de fallback: leva os campos do giro. As demais linhas com
# `tool` (recusa, negacao do PEP, sessao aberta, fita encerrada, lote encadeado) tem forma propria.
EVENTOS_DE_GIRO = frozenset({None, "", "verbo", "fallback", "verbo_contornado",
                             "escrita", "escrita_recusada"})


def validar(reg: dict) -> list[str]:
    """O que falta (ou sobra) na linha, pelo contrato do tipo dela. Vazio = cumpre."""
    tipo = tipo_da_linha(reg)
    obrigatorios = CONTRATO["toda"] + CONTRATO.get(tipo, ())
    problemas = []
    for campo in obrigatorios:
        if campo not in reg:
            problemas.append(f"falta {campo}")
        elif reg[campo] in (None, "") and campo not in NULAVEL:
            problemas.append(f"{campo} nulo")
    for campo in PROIBIDOS.get(tipo, ()):
        if campo in reg:
            problemas.append(f"nao se grava {campo}")
    if reg.get("origem") not in (None,) + ORIGENS:
        problemas.append(f"origem fora do vocabulario: {reg.get('origem')!r}")
    if tipo == "auth_negada" and reg.get("motivo") not in MOTIVOS_NEGACAO:
        problemas.append(f"motivo fora do vocabulario: {reg.get('motivo')!r}")
    if tipo == "fecho":
        if reg.get("motivo_parada") not in MOTIVOS_PARADA:
            problemas.append(f"motivo_parada fora do vocabulario: {reg.get('motivo_parada')!r}")
        if reg.get("tokens") is not None and reg.get("fonte_tokens") not in FONTES_TOKENS:
            problemas.append("tokens sem fonte_tokens")
    if tipo in ("giro", "turno") and reg.get("turno_fonte") not in FONTES_TURNO:
        problemas.append(f"turno_fonte fora do vocabulario: {reg.get('turno_fonte')!r}")
    if tipo == "consulta" and "query" not in reg:
        problemas.append("falta query")
    return problemas


# --- escrever -------------------------------------------------------------------------

def emitir(evento: dict, *, diretorio_=None, declara_exit: bool | None = None,
           agora: datetime | None = None) -> bool:
    """Grava uma linha no `ops-AAAA-MM-DD.jsonl` do dia, so por acrescimo (O_APPEND).

    Carimba `evento_id` e `schema_v`; giro leva `classe`; apara antes de serializar. Nunca
    levanta: o erro vai ao stderr (journal) e a funcao devolve False. Auditoria que falha
    em silencio e pior que auditoria ausente."""
    try:
        agora = agora or datetime.now().astimezone()
        reg = {k: v for k, v in dict(evento).items() if k not in ("evento_id", "schema_v")}
        carimbo = {"ts": reg.pop("ts", None) or agora.isoformat(timespec="milliseconds"),
                   "evento_id": uuid7(int(agora.timestamp() * 1000)), "schema_v": SCHEMA_V}
        if _e_giro(reg) and "classe" not in reg:
            reg.update(classificar(reg, declara_exit=declara_exit))
        reg.setdefault("origem", origem_da_linha(reg))
        reg.setdefault("mapa_v", None)      # a projecao do golden record nao existe na release (arq:0123 §7)
        linha = (_serializa(aparar({**carimbo, **reg})) + "\n").encode("utf-8")
        alvo = caminho_do_dia(agora.date(), diretorio_)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(alvo, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, linha)
        finally:
            os.close(fd)
        return True
    except Exception as e:                                  # noqa: BLE001
        print(f"[audit] FALHOU: {e!r}", file=sys.stderr, flush=True)
        return False


# --- ler ------------------------------------------------------------------------------

class Dia:
    """O que a leitura sabe de um dia: se o arquivo existe e quantas linhas leu."""
    __slots__ = ("dia", "estado", "legiveis", "ilegiveis")

    def __init__(self, dia: str, presente: bool):
        self.dia = dia
        self.estado = "presente" if presente else "ausente"
        self.legiveis = 0
        self.ilegiveis = 0

    def como_dict(self) -> dict:
        return {"dia": self.dia, "estado": self.estado,
                "legiveis": self.legiveis, "ilegiveis": self.ilegiveis}


class Leitura:
    """Iteravel de eventos, na ordem em que foram escritos, dia a dia. As contagens por dia
    (`dias`) so fecham quando o iterador se esgota. Evento de linha antiga ganha `classe`."""

    def __init__(self, dias: list[str], diretorio_, sessao: str | None, tool: str | None):
        self.diretorio = Path(diretorio_ or diretorio())
        self.dias = {d: Dia(d, caminho_do_dia(d, self.diretorio).is_file()) for d in dias}
        self._sessao, self._tool = sessao, tool

    @property
    def legiveis(self) -> int:
        return sum(d.legiveis for d in self.dias.values())

    @property
    def ilegiveis(self) -> int:
        return sum(d.ilegiveis for d in self.dias.values())

    def ausentes(self) -> list[str]:
        return [d.dia for d in self.dias.values() if d.estado == "ausente"]

    def caminho(self, dia) -> Path:
        return caminho_do_dia(dia, self.diretorio)

    def __iter__(self):
        for dia, info in self.dias.items():
            if info.estado == "ausente":
                continue
            info.legiveis = info.ilegiveis = 0
            with open(self.caminho(dia), encoding="utf-8", errors="replace") as f:
                for bruta in f:
                    bruta = bruta.strip()
                    if not bruta:
                        continue
                    try:
                        reg = json.loads(bruta)
                    except ValueError:
                        reg = None
                    if not isinstance(reg, dict):
                        info.ilegiveis += 1
                        continue
                    info.legiveis += 1
                    if self._tool and reg.get("tool") != self._tool:
                        continue
                    if self._sessao and not str(reg.get("sessao_id") or "").startswith(self._sessao):
                        continue
                    if "classe" not in reg and _e_giro(reg):
                        reg.update(classificar(reg))
                    reg.setdefault("origem", origem_da_linha(reg))
                    yield reg


def ler(desde, ate=None, *, diretorio_=None, sessao: str | None = None,
        tool: str | None = None) -> Leitura:
    """`ler(dia)` le um dia; `ler(desde, ate)` le a janela em dias corridos, os dois
    inclusos. Dia sem arquivo fica `ausente` em `Leitura.dias`: nao e zero, nao e erro."""
    a = date.fromisoformat(_dia(desde))
    b = date.fromisoformat(_dia(ate if ate is not None else desde))
    if b < a:
        raise ValueError(f"janela invertida: {a} depois de {b}")
    dias = [(a + timedelta(days=n)).isoformat() for n in range((b - a).days + 1)]
    return Leitura(dias, diretorio_, sessao, tool)


# --- extração: os bytes do dia e as linhas numeradas (card #3353) -----------------------------

# Namespace fixo do uuid v5 da linha sem chave (arq:0123 regra 4; spec apis-escrita-acervo §D: a linha
# anterior à chave recebe uuid v5 de (dia, número da linha), e a mesma linha relida dá o mesmo evento).
# Mudar este valor muda o evento_id de toda linha antiga: não se muda.
NAMESPACE_LINHA = uuid.uuid5(uuid.NAMESPACE_URL, "https://platafirma.org/log-da-porta/linha-sem-chave")


def evento_id_da_linha(dia, linha_n: int) -> str:
    """O evento_id de uma linha sem chave: uuid v5 de `AAAA-MM-DD:<número físico da linha>`."""
    return str(uuid.uuid5(NAMESPACE_LINHA, f"{_dia(dia)}:{linha_n}"))


def nome_do_dia(dia) -> str:
    """O nome do arquivo do dia, sem a pasta: o que o extrator declara em D5.1 e o corte confere."""
    return caminho_do_dia(dia, ".").name


def conteudo_do_dia(dia, diretorio_=None) -> bytes | None:
    """Os bytes do arquivo do dia, ou None quando o dia não tem arquivo («ausente», nunca zero). O
    extrator tira o sha256 e as linhas DESTES bytes, de uma vez: o arquivo não muda entre uma coisa e a
    outra, e o corte (#3354) confere contra o mesmo cálculo."""
    try:
        return caminho_do_dia(dia, diretorio_).read_bytes()
    except FileNotFoundError:
        return None


def linhas_do_dia(dados: bytes):
    """(n, bruta, reg) de cada linha não vazia: `n` é o número físico da linha no arquivo (base 1, a
    mesma que `sed -n Np` mostra), `bruta` os bytes dela sem o `\\n`, e `reg` o dicionário — ou None na
    linha ilegível. Mesma regra de `Leitura`: linha em branco não conta; legível é JSON de objeto,
    lido com `errors=replace`; o resto é ilegível. O teste confere que as duas contagens batem."""
    for n, bruta in enumerate(dados.split(b"\n"), 1):
        texto = bruta.decode("utf-8", errors="replace").strip()
        if not texto:
            continue
        try:
            reg = json.loads(texto)
        except ValueError:
            reg = None
        yield n, bruta, (reg if isinstance(reg, dict) else None)


# --- o corte: o prazo, o que ha no disco, o teto (card #3354; arq:0123 regras 10 e 12) -----------

CORTE_DIAS = 35                      # o bruto fica 35 dias no disco; depois so a particao guarda
INICIO_DO_BRUTO = date(2026, 9, 15)  # o primeiro dia que o bruto cobre (arq:0123, Contexto)
TETO_SEMANAS = 4                     # a base do teto: as quatro semanas anteriores a hoje
TETO_FOLGA = 1.5
TETO_MIN_DIAS = 7                    # menos que isso nao da base: o teto diz «sem_base», nao chuta
FUSO = timezone(timedelta(hours=-3))  # o dia do arquivo e o dia local da porta (America/Sao_Paulo)
# Como cards e incidentes chamam o bruto. E so o rotulo de um titulo: quem le o arquivo e este modulo.
ROTULO_BRUTO = "var/log/ops"

_NOME_DO_DIA = re.compile(r"ops-(\d{4}-\d{2}-\d{2})\.jsonl")


def hoje_local() -> date:
    """O dia de hoje no fuso da porta; o arquivo do dia e o que esse fuso diz."""
    return datetime.now(timezone.utc).astimezone(FUSO).date()


def dia_local(instante: str) -> str:
    """O dia (AAAA-MM-DD) no fuso da porta de um instante ISO 8601 com fuso (`2026-10-08T20:56:48+00:00`).
    ValueError para o que nao e instante; instante sem fuso e lido como ja local."""
    texto = str(instante).strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO)
    return momento.date().isoformat()


def dias_no_disco(diretorio_=None) -> dict[str, int]:
    """{dia: bytes} de cada arquivo do dia que esta no disco, do mais velho ao mais novo. Nome fora do
    padrao, data impossivel, link e pasta nao contam. Diretorio que nao existe e {}."""
    pasta = Path(diretorio_ or diretorio())
    try:
        entradas = list(pasta.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return {}
    achados: dict[str, int] = {}
    for p in entradas:
        m = _NOME_DO_DIA.fullmatch(p.name)
        if m is None or p.is_symlink() or not p.is_file():
            continue
        try:
            date.fromisoformat(m.group(1))
            achados[m.group(1)] = p.stat().st_size
        except (ValueError, OSError):
            continue
    return dict(sorted(achados.items()))


def idade_em_dias(dia, hoje) -> int:
    """Dias entre o dia do arquivo (pelo nome, nunca pelo mtime) e hoje."""
    return (date.fromisoformat(_dia(hoje)) - date.fromisoformat(_dia(dia))).days


def dias_mais_velhos_que(idade: int, hoje, diretorio_=None) -> list[str]:
    """Os dias no disco com mais de `idade` dias, do mais velho ao mais novo. O corte usa `CORTE_DIAS`."""
    return [d for d in dias_no_disco(diretorio_) if idade_em_dias(d, hoje) > idade]


def cortes_desde(desde, hoje=None, diretorio_=None) -> list[str]:
    """Os dias de `desde` em diante que ja passaram do prazo e nao tem arquivo no disco: ou o corte os
    levou, ou nunca houve giro neles. Quem le o bruto por data (repo commitar) nao pode seguir com um
    conjunto parcial, e na duvida o dia conta como cortado. O bruto so existe desde `INICIO_DO_BRUTO`."""
    h = date.fromisoformat(_dia(hoje if hoje is not None else hoje_local()))
    primeiro = max(date.fromisoformat(_dia(desde)), INICIO_DO_BRUTO)
    ultimo = h - timedelta(days=CORTE_DIAS + 1)         # idade > CORTE_DIAS
    no_disco = dias_no_disco(diretorio_)
    saida = []
    dia = primeiro
    while dia <= ultimo:
        if dia.isoformat() not in no_disco:
            saida.append(dia.isoformat())
        dia += timedelta(days=1)
    return saida


def remover_dia_conferido(dia, sha256: str, diretorio_=None) -> bool:
    """A unica remocao do bruto (arq:0123 regra 12): apaga o arquivo do dia SE os bytes que estao la agora
    tem o `sha256` que o corte conferiu, e so entao. Devolve False, sem apagar, quando o arquivo sumiu ou
    mudou entre a conferencia e a remocao. Quem a chama e o timer `corte-bruto`; verbo servido nao."""
    caminho = caminho_do_dia(dia, diretorio_)
    try:
        dados = caminho.read_bytes()
    except FileNotFoundError:
        return False
    if hashlib.sha256(dados).hexdigest() != sha256:
        return False
    caminho.unlink()
    return True


def teto_do_bruto(hoje=None, diretorio_=None) -> dict:
    """O bruto no disco contra o teto: mediana de bytes por dia dos dias com arquivo nas quatro semanas
    anteriores a `hoje` (hoje fica de fora, esta incompleto) x 35 x 1,5. `estado`: «dentro», «acima» ou
    «sem_base» (menos de `TETO_MIN_DIAS` dias de base: nao ha o que medir, e nao se inventa teto)."""
    h = date.fromisoformat(_dia(hoje if hoje is not None else hoje_local()))
    no_disco = dias_no_disco(diretorio_)
    inicio = h - timedelta(days=7 * TETO_SEMANAS)
    base = [n for d, n in no_disco.items() if inicio <= date.fromisoformat(d) < h]
    r = {"hoje": h.isoformat(), "dias_no_disco": len(no_disco), "bytes": sum(no_disco.values()),
         "dias_na_base": len(base), "mediana_bytes_dia": None, "teto_bytes": None, "estado": "sem_base"}
    if len(base) >= TETO_MIN_DIAS:
        mediana = int(statistics.median(base))
        r["mediana_bytes_dia"] = mediana
        r["teto_bytes"] = int(mediana * CORTE_DIAS * TETO_FOLGA)
        r["estado"] = "acima" if r["bytes"] > r["teto_bytes"] else "dentro"
    return r


# --- CLI ------------------------------------------------------------------------------

def _uso() -> int:
    print("uso: python3 -m oplog ler <AAAA-MM-DD> | --desde <AAAA-MM-DD> [--ate <AAAA-MM-DD>]"
          " [--sessao <id>] [--tool <t>]\n"
          "     python3 -m oplog dia-local <instante ISO 8601>\n"
          "     python3 -m oplog cortes-desde <AAAA-MM-DD> [--hoje <AAAA-MM-DD>]\n"
          "     python3 -m oplog teto [--hoje <AAAA-MM-DD>]", file=sys.stderr)
    return 2


def _main_corte(argv: list[str]) -> int:
    """`dia-local <instante>` · `cortes-desde <dia> [--hoje <dia>]` · `teto [--hoje <dia>]`: o que o `repo` e o
    `infra` (bash) perguntam ao corte. Exit 0 ok, 1 ha dia cortado (`cortes-desde`), 2 uso."""
    ato, args = argv[0], argv[1:]
    hoje = None
    try:
        if "--hoje" in args:
            i = args.index("--hoje")
            hoje = args[i + 1]
            args = args[:i] + args[i + 2:]
        if ato == "dia-local" and len(args) == 1:
            print(dia_local(args[0]))
            return 0
        if ato == "cortes-desde" and len(args) == 1:
            cortados = cortes_desde(args[0], hoje)
            for dia in cortados:
                print(dia)
            return 1 if cortados else 0
        if ato == "teto" and not args:
            print(json.dumps(teto_do_bruto(hoje), ensure_ascii=False, sort_keys=True))
            return 0
    except (IndexError, ValueError) as e:
        print(f"oplog: {e}", file=sys.stderr)
        return 2
    return _uso()


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("dia-local", "cortes-desde", "teto"):
        return _main_corte(argv)
    if not argv or argv[0] != "ler":
        return _uso()
    desde = ate = sessao = tool = None
    args = argv[1:]
    try:
        while args:
            a = args.pop(0)
            if a == "--desde":
                desde = args.pop(0)
            elif a == "--ate":
                ate = args.pop(0)
            elif a == "--sessao":
                sessao = args.pop(0)
            elif a == "--tool":
                tool = args.pop(0)
            elif not a.startswith("-") and desde is None:
                desde = a
            else:
                return _uso()
        if desde is None:
            return _uso()
        leitura = ler(desde, ate, sessao=sessao, tool=tool)
    except (IndexError, ValueError) as e:
        print(f"oplog: {e}", file=sys.stderr)
        return 2
    for reg in leitura:
        print(_serializa(reg))
    ausentes = leitura.ausentes()
    if ausentes:
        print(f"oplog: dia(s) ausente(s): {', '.join(ausentes)}", file=sys.stderr)
    if leitura.ilegiveis:
        print(f"oplog: {leitura.ilegiveis} linha(s) ilegivel(is)", file=sys.stderr)
    # 3 = dependencia fora: a janela inteira sem arquivo e fonte indisponivel, nao «zero eventos».
    return 3 if len(ausentes) == len(leitura.dias) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
