"""O ajuste do motor, lido e escrito pela geração que serve (card #3513; arq:0121 §7; arq:0124 R4, R6, R7).

Três ajustes moram na geração e não no compose: `aviso_de_cobertura_fraca`, `aviso_com_revisor` e
`veredito_por_conceito` (o registro os marca com o campo `geracao`, a chave dela). Para esses o valor de
verdade é o da geração servindo, lido da rota da #3510; o do compose é só a configuração e aparece como
divergente quando difere. Os outros ajustes seguem pelo compose e pelo env, com o caminho de sempre mais o
fundamento, o histórico e as recusas.

O fundamento é obrigatório em todo ato de escrita e chega por uma de duas vias: da face, `PF_FUNDAMENTO`,
entregue pela porta (#3531); da cadeira, `--fundamento`. As duas caem no bruto da porta. Da face a flag é
recusada, para não haver dois textos. O histórico é um JSONL na instância, uma linha por mexida.

Este módulo não imprime nem sai: devolve dados e levanta `chamada_rag.Falha` com o exit do verbo. Quem
imprime é o `motor`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import chamada_rag
from chamada_rag import Falha

HISTORICO_REL = ("var", "motor", "ajustes-historico.jsonl")
# O que o sinal diz de um serviço que não está de pé. `no-ar` passa; `sem-sinal` e `ausente` não dizem nada
# (não consegui olhar, que não equivale a estar no ar nem a estar fora); o resto recusa.
_SINAL_NAO_DIZ = ("sem-sinal", "ausente")
# O servico do sinal que diz a placa (a spec da face motor, R10: «a placa ou a API do rag fora de no ar»).
SINAL_DA_PLACA = "gpu-host"


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- valores

def tipar(texto: str):
    """`0.61` -> 0.61, `0,61` -> 0.61 (vírgula decimal), `true` -> True, inteiro -> int, o resto é texto."""
    if not isinstance(texto, str):
        return texto
    t = texto.strip()
    if t.lower() in ("true", "false"):
        return t.lower() == "true"
    if re.fullmatch(r"-?\d+,\d+", t):
        t = t.replace(",", ".")
    try:
        return float(t) if "." in t else int(t)
    except ValueError:
        return texto


def br(valor) -> str:
    """O valor como o dono lê: vírgula decimal, `true`/`false`, vazio sem nada."""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if valor is None:
        return ""
    if isinstance(valor, float):
        return repr(valor).replace(".", ",")
    return str(valor)


def mesmo_valor(a, b) -> bool:
    """Igual por número quando os dois são número (0.5 e '0.50'), por texto sem caixa nos outros casos."""
    if isinstance(a, bool) or isinstance(b, bool):
        return str(a).strip().lower() == str(b).strip().lower()
    try:
        return float(str(a).replace(",", ".")) == float(str(b).replace(",", "."))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


# ---------------------------------------------------------------- a geração servindo

def ler_geracao(inst: dict, tok: str, particao: str = "biblioteca") -> tuple[dict | None, str | None]:
    """(resposta da rota, None) ou (None, motivo): ler a geração falhar não derruba a leitura dos ajustes."""
    url = inst.get("ajustes_da_geracao")
    if not url:
        return None, "a instancia nao declara `ajustes_da_geracao` em motor-instancias.json"
    try:
        return chamada_rag.chamar(url, tok, consulta={"particao": particao}), None
    except Falha as f:
        return None, f.mensagem


def mudar_geracao(inst: dict, tok: str, chave: str, valor, sujeito: str, fundamento: str,
                  particao: str = "biblioteca") -> dict:
    url = inst.get("ajustes_da_geracao")
    if not url:
        raise Falha(1, "a instancia nao declara `ajustes_da_geracao` em motor-instancias.json")
    return chamada_rag.chamar(url, tok, {"particao": particao, "chave": chave, "valor": valor,
                                         "sujeito": sujeito, "fundamento": fundamento}, metodo="PUT")


def resolve(b: dict, ger: dict | None, ger_erro: str | None, compose: dict | None, env_ing: dict) -> dict:
    """O valor de um ajuste e de onde ele vem.

    Devolve `valor`, `origem`, `divergente` (o que o compose declara quando difere da geração, ou None) e
    `nao_consegui_olhar` (o motivo de a geração não ter dito o valor, ou None)."""
    if b.get("onde") == "env":
        v = env_ing.get(b["var"])
        return {"valor": v if v is not None else b["codigo"],
                "origem": "env da ingestao" if v is not None else "default do codigo",
                "divergente": None, "nao_consegui_olhar": None}
    declarado = (compose or {}).get(b["var"])
    chave = b.get("geracao")
    nao = None
    if chave and ger and chave in (ger.get("ajustes") or {}):
        v = ger["ajustes"][chave]
        diverge = {"compose": declarado} if declarado is not None and not mesmo_valor(declarado, v) else None
        return {"valor": v, "origem": f"geracao g{ger['geracao']}", "divergente": diverge,
                "nao_consegui_olhar": None}
    if chave and not ger:
        nao = f"nao consegui olhar a geracao: {ger_erro}"
    elif chave:
        nao = f"a geracao g{ger['geracao']} nao carrega {chave}"
    if declarado is not None:
        return {"valor": declarado, "origem": "compose", "divergente": None, "nao_consegui_olhar": nao}
    return {"valor": b["codigo"], "origem": "default do codigo", "divergente": None, "nao_consegui_olhar": nao}


# ---------------------------------------------------------------- fundamento e sujeito

def fundamento_e_origem(da_flag: str | None) -> tuple[str, str]:
    """(texto, origem). Da face vem em PF_FUNDAMENTO e a flag é recusada; da cadeira vem em --fundamento.
    Sem nenhum dos dois o ato de escrita não segue (exit 2)."""
    da_face = (os.environ.get("PF_FUNDAMENTO") or "").strip()
    if da_face:
        if da_flag is not None:
            raise Falha(2, "ajuste: --fundamento nao vale vindo da face; o texto do dono chega pela porta "
                           "(PF_FUNDAMENTO) e dois textos nao se somam")
        return da_face, "face"
    if da_flag is not None and da_flag.strip():
        return da_flag.strip(), "cadeira"
    raise Falha(2, "ajuste: escrita sem fundamento. Diga o porque em --fundamento \"<texto>\" "
                   "(da face, o texto do dono chega pela porta)")


def sujeito() -> str:
    return ((os.environ.get("PF_SUJEITO") or os.environ.get("PF_CADEIRA") or "").strip() or "motor-verbo")


# ---------------------------------------------------------------- recusas

def sinal_do_servico(instancia: Path, nome: str | None) -> tuple[str, str | None]:
    """('no-ar' | 'fora' | 'nao-consegui-olhar', motivo) do serviço no arquivo do `sinal`."""
    caminho = instancia / "var" / "sinal" / "servicos.json"
    try:
        servicos = (json.loads(caminho.read_text(encoding="utf-8")).get("servicos") or {})
    except (OSError, ValueError):
        return "nao-consegui-olhar", f"o arquivo do sinal ({caminho}) nao abriu"
    s = servicos.get(nome or "")
    if not isinstance(s, dict):
        return "nao-consegui-olhar", f"o sinal nao lista o servico {nome}"
    estado = s.get("estado")
    if estado == "no-ar":
        return "no-ar", None
    if estado in _SINAL_NAO_DIZ:
        return "nao-consegui-olhar", s.get("motivo") or f"o sinal diz {estado}"
    return "fora", s.get("motivo") or f"o sinal diz {estado}"


def trabalhos_abertos(inst: dict, tok: str) -> list[dict]:
    """Os trabalhos do rag-api vivos ou indetermináveis (não equivale a parado: pode estar rodando em outra
    réplica). Parado não segura nada; o 409 da API é a rede de baixo."""
    url = inst.get("trabalhos")
    if not url:
        raise Falha(1, "a instancia nao declara `trabalhos` em motor-instancias.json")
    r = chamada_rag.chamar(url, tok)
    return [t for t in (r.get("itens") or []) if t.get("estado") in ("vivo", "indeterminavel")]


def recusar_se_nao_der(inst: dict, tok: str, instancia: Path, *, reinicia: bool = False) -> list[str]:
    """Recusa o ato de escrita com o serviço fora no sinal (exit 3) ou com trabalho aberto (exit 4).

    `reinicia`: o ato derruba o serviço (ajuste do compose promove a stack). Aí o sinal que não deu para olhar
    também recusa: «não conseguir olhar não autoriza reiniciar» (spec da face motor, dependências). O ajuste da
    geração não reinicia nada e segue com a nota.

    Devolve as notas do que não deu para olhar, para o chamador mostrar."""
    notas: list[str] = []
    for nome in (inst.get("container"), SINAL_DA_PLACA):
        estado, motivo = sinal_do_servico(instancia, nome)
        if estado == "fora":
            raise Falha(3, f"ajuste recusado: o sinal diz que {nome} esta fora ({motivo})")
        if estado == "nao-consegui-olhar":
            if reinicia:
                raise Falha(3, f"ajuste recusado: nao consegui olhar o sinal de {nome} ({motivo}) e este ajuste "
                               "reinicia a busca; nao conseguir olhar nao autoriza reiniciar")
            notas.append(f"sinal de {nome}: nao consegui olhar ({motivo})")
    try:
        abertos = trabalhos_abertos(inst, tok)
    except Falha as f:
        if f.codigo == 1:
            raise
        raise Falha(3, f"ajuste recusado: nao consegui olhar os trabalhos do rag-api ({f.mensagem}); "
                       "sem isso nao sei se ha lote aberto") from None
    if abertos:
        t = abertos[0]
        feitos = (t.get("progresso") or {}).get("feitos")
        total = (t.get("progresso") or {}).get("total")
        raise Falha(4, f"ajuste recusado: ha trabalho aberto, o lote de {t.get('tipo')} {t.get('id')} "
                       f"({t.get('estado')}, {feitos}/{total}); acompanhe com `motor rag trabalhos` "
                       "e mexa quando acabar")
    return notas


# ---------------------------------------------------------------- o histórico

def caminho_historico(instancia: Path) -> Path:
    return instancia.joinpath(*HISTORICO_REL)


def grava_historico(instancia: Path, linha: dict) -> Path:
    """Acrescenta a mexida ao JSONL da instância. Uma linha por mexida, nunca reescreve."""
    caminho = caminho_historico(instancia)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return caminho


def ler_historico(instancia: Path, slug: str | None = None, ultimas: int | None = None) -> list[dict]:
    caminho = caminho_historico(instancia)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return []
    linhas = []
    for bruta in texto.splitlines():
        try:
            linha = json.loads(bruta)
        except ValueError:
            continue
        if isinstance(linha, dict) and (slug is None or linha.get("slug") == slug):
            linhas.append(linha)
    return linhas[-ultimas:] if ultimas else linhas


def texto_do_historico(linhas: list[dict]) -> str:
    if not linhas:
        return "historico de ajuste: nenhuma mexida registrada"
    saida = [f"historico de ajuste: {len(linhas)} mexida(s)"]
    for x in linhas:
        saida.append(f"  {x.get('em')}  {x.get('slug')}  {br(x.get('antes'))} -> {br(x.get('depois'))}"
                     f"  ({x.get('origem')}, {x.get('sujeito')}"
                     + (f", geracao g{x['geracao']}" if x.get("geracao") is not None else "") + ")"
                     f"  porque: {x.get('fundamento')}")
    return "\n".join(saida)
