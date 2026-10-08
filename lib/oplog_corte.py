"""oplog_corte — o corte do bruto da porta em 35 dias, só pelo timer e só com portão (card #3354; arq:0123 regras 10 e 12).

`bin/_infra/corte-bruto` roda pelo timer `corte-bruto` às 01:20, uma hora depois do `linhagem-ops`, e nunca pela
porta: nenhum verbo servido apaga o bruto. Candidato é o dia que passou de 35 dias PELO NOME do arquivo (nunca pelo
mtime). Para cada um, o portão faz três conferências sobre os MESMOS bytes que vai apagar:

    1. as linhas do arquivo: lidas = legíveis + ilegíveis, e a linhagem do dia (D5.5) diz os mesmos números;
    2. os eventos do dia na partição (D5.6, página a página) são tantos quanto as linhas legíveis;
    3. o sha256 e o tamanho recalculados dos bytes são os da linhagem.

Passou nas três: corta. Sem linhagem (a passada ainda não concluiu): retém, em silêncio, com uma linha em poda.log.
Linhagem que reprova: retém, abre o incidente «<bruto> <dia>: bruto reprovado no portão» para a cadeira `seguranca`
(sem repetir o que já está aberto) e sai 1. API ou banco fora: retém e sai 3; o dia fica, e o teto de `infra saude`
acusa se o atraso crescer. Só `oplog.remover_dia_conferido` apaga, e só se o arquivo ainda tem os bytes conferidos.

Travas do corte, além do portão: no máximo `CORTE_MAX_DIAS` (3) dias por rodada, e nada se corta com o relógio fora
do bruto (arquivo do futuro, ou o dia mais novo parado há mais de 3 dias). `--seco` confere e diz o que faria, sem
apagar, sem gravar poda.log e sem abrir incidente; `--mais-velhos-que N` (só com `--seco`) escolhe os dias de ensaio.
Só biblioteca padrão: o timer roda no python da release, sem modelo.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import oplog
import raizes
from oplog_extracao import Api, Falha

APROVADO, RETIDO, REPROVADO, CORTADO = "aprovado", "retido", "reprovado", "cortado"
ESTADOS_ABERTOS = ("detectado", "em-mitigacao", "mitigado")   # o incidente ainda não terminou (como `bot caidas`)
CADEIRA_DO_INCIDENTE = "seguranca"
PAGINA = 1000                  # o teto de D5.6
MAX_DIAS_POR_RODADA = 3
BRUTO_PARADO_DIAS = 3          # o dia mais novo no disco mais velho que isso: relógio ou porta; não se corta
TABS_DA_LISTAGEM = 2           # `tarefas listar`: id TAB estado TAB título


@dataclass
class Veredito:
    dia: str
    acao: str                  # aprovado · retido · reprovado (a rodada troca aprovado por cortado ao apagar)
    motivo: str
    contas: dict = field(default_factory=dict)


# --- a conferência de um dia ------------------------------------------------------------------

def contas_do_arquivo(dados: bytes) -> dict:
    """O que os bytes dizem de si: linhas não vazias, legíveis, ilegíveis, tamanho e sha256. Mesma regra de
    `oplog.ler` e do extrator (o teste de #3353 confere as duas)."""
    fisicas = sum(1 for linha in dados.split(b"\n") if linha.decode("utf-8", errors="replace").strip())
    legiveis = ilegiveis = 0
    for _, _, reg in oplog.linhas_do_dia(dados):
        if reg is None:
            ilegiveis += 1
        else:
            legiveis += 1
    return {"lidas": fisicas, "legiveis": legiveis, "ilegiveis": ilegiveis, "bytes": len(dados),
            "sha256": hashlib.sha256(dados).hexdigest()}


def _linhagem(api: Api, dia: str) -> dict | None:
    _, corpo = api.chamar("GET", "/acervo/log/dias", params={"desde": dia, "ate": dia})
    for linha in (corpo or {}).get("itens") or []:
        if linha.get("dia") == dia:
            return linha
    return None


def _eventos_na_particao(api: Api, dia: str, esperados: int) -> int:
    """Conta os eventos do dia lendo D5.6 página a página, com o cursor que a própria resposta devolve. O laço
    para na página que não traz `proximo`; o teto de páginas só impede que um cursor que não anda gire para sempre,
    e nesse caso a conta volta -1, que nunca bate com uma contagem de linhas (o portão reprova)."""
    n, cursor = 0, None
    for _ in range(esperados // PAGINA + 3):
        params = {"limite": PAGINA}
        if cursor:
            params["cursor"] = cursor
        _, corpo = api.chamar("GET", f"/acervo/log/dias/{dia}/eventos", params=params)
        n += len((corpo or {}).get("itens") or [])
        cursor = (corpo or {}).get("proximo")
        if not cursor:
            return n
    return -1


def portao(api: Api, dia: str, dados: bytes) -> Veredito:
    """As três conferências. `Falha` (3, 4, 5) sobe: sem poder conferir, o dia fica."""
    linha = _linhagem(api, dia)
    passada = (linha or {}).get("passada")
    if passada is None:
        return Veredito(dia, RETIDO, "sem_linhagem")
    c = contas_do_arquivo(dados)
    eventos = _eventos_na_particao(api, dia, c["legiveis"])
    da_linhagem = {"lidas": passada.get("linhas_lidas"), "legiveis": passada.get("linhas_legiveis"),
                   "ilegiveis": passada.get("linhas_ilegiveis"), "bytes": linha.get("bytes"),
                   "sha256": linha.get("sha256")}
    falhas = []
    if (c["lidas"] != c["legiveis"] + c["ilegiveis"]
            or (da_linhagem["lidas"], da_linhagem["legiveis"], da_linhagem["ilegiveis"])
            != (c["lidas"], c["legiveis"], c["ilegiveis"])):
        falhas.append("linhas")
    if eventos != c["legiveis"]:
        falhas.append("eventos")
    if (c["sha256"], c["bytes"]) != (da_linhagem["sha256"], da_linhagem["bytes"]):
        falhas.append("sha256")
    contas = {"arquivo": c, "linhagem": da_linhagem, "eventos_na_particao": eventos}
    return Veredito(dia, REPROVADO if falhas else APROVADO, ",".join(falhas) or "conferido", contas)


# --- o rastreador: incidente sem duplicar ---------------------------------------------------------

class Tarefas:
    """O `tarefas` do harness, o mesmo que `bot caidas` usa para abrir incidente sem duplicar."""

    def __init__(self, binario: str | os.PathLike | None = None):
        padrao = Path(os.path.realpath(__file__)).parent.parent / "bin" / "tarefas"
        self.binario = str(binario or os.environ.get("PF_TAREFAS_BIN") or padrao)

    def _roda(self, args: list[str], stdin: str | None = None):
        try:
            return subprocess.run([self.binario, *args], input=stdin, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=60, check=False)
        except subprocess.TimeoutExpired:
            raise Falha(5, "tarefas: passou de 60s sem resposta") from None
        except OSError as e:
            raise Falha(3, f"tarefas: não executou ({e})") from None

    def titulos_abertos(self) -> set[str]:
        """Títulos dos incidentes ainda abertos: uma chamada por estado (`--estado` repetido pode ser last-wins)."""
        titulos: set[str] = set()
        for estado in ESTADOS_ABERTOS:
            p = self._roda(["listar", "--estado", estado])
            if p.returncode != 0:
                motivo = (p.stderr.strip().splitlines() or ["sem retorno"])[0]
                raise Falha(5, f"tarefas listar --estado {estado} saiu {p.returncode}: {motivo}")
            titulos |= {linha.split("\t", TABS_DA_LISTAGEM)[TABS_DA_LISTAGEM] for linha in p.stdout.splitlines()
                        if linha.count("\t") >= TABS_DA_LISTAGEM}
        return titulos

    def abrir_incidente(self, titulo: str, corpo: str) -> str:
        p = self._roda(["criar", titulo, "--incidente", "--cadeira", CADEIRA_DO_INCIDENTE, "--desc-stdin"],
                       stdin=corpo)
        if p.returncode != 0:
            motivo = (p.stderr.strip().splitlines() or ["sem retorno"])[0]
            raise Falha(5, f"tarefas criar saiu {p.returncode}: {motivo}")
        return p.stdout.strip() or "incidente aberto"


def titulo_do_incidente(dia: str) -> str:
    return f"{oplog.ROTULO_BRUTO} {dia}: bruto reprovado no portão"


def corpo_do_incidente(v: Veredito) -> str:
    """Só contagem e prefixo de hash: o incidente não leva conteúdo do bruto."""
    a, g = v.contas["arquivo"], v.contas["linhagem"]
    return (f"O bruto de {v.dia} não passou no portão do corte (arq:0123 regra 12): {v.motivo}.\n\n"
            f"Arquivo: lidas={a['lidas']} legíveis={a['legiveis']} ilegíveis={a['ilegiveis']} bytes={a['bytes']} "
            f"sha256={a['sha256'][:12]}\n"
            f"Linhagem: lidas={g['lidas']} legíveis={g['legiveis']} ilegíveis={g['ilegiveis']} bytes={g['bytes']} "
            f"sha256={(g['sha256'] or '-')[:12]}\n"
            f"Eventos do dia na partição: {v.contas['eventos_na_particao']}\n\n"
            f"O arquivo fica no disco: só o timer corta, e só o que passa no portão. Ver `metrica dia {v.dia}`, "
            f"`infra logs corte-bruto` e `infra logs linhagem-ops`. Aberto por `corte-bruto` (timer das 01:20).")


# --- a rodada ------------------------------------------------------------------------------------

def _linha(v: Veredito, idade: int, a: dict | None) -> str:
    detalhe = f"idade={idade}d" + (f" bytes={a['bytes']} sha256={a['sha256'][:12]}" if a else "")
    return f"corte-bruto {v.dia}: {v.acao} — {v.motivo} ({detalhe})"


def _grava_poda(caminho: Path, linhas: list[str]) -> None:
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().astimezone().isoformat(timespec="seconds")
        with open(caminho, "a", encoding="utf-8") as f:
            f.writelines(f"{marca} {linha}\n" for linha in linhas)
    except OSError as e:
        print(f"corte-bruto: poda.log não gravou ({e.strerror})", file=sys.stderr)


USO = """uso: corte-bruto [--seco [--mais-velhos-que N]]
sem argumento: corta todo dia com mais de 35 dias (pelo nome do arquivo) que passa nas três conferências, no
  máximo 3 por rodada, do mais velho ao mais novo. Roda só pelo timer `corte-bruto`; a porta não o despacha.
  --seco              confere e diz o que faria; não apaga, não grava poda.log e não abre incidente
  --mais-velhos-que N só com --seco: ensaio com os dias de mais de N dias (padrão 35)
exit: 0 ok · 1 dia reprovado no portão (retido, incidente aberto) · 2 uso · 3 API ou banco fora · 4 token recusado ·
      5 indeterminável (relógio fora do bruto, incidente que não abriu)"""


def _argumentos(argv: list[str]) -> tuple[bool, int | None]:
    """(seco, idade de ensaio). ValueError ou IndexError para uso errado."""
    seco, idade, args = False, None, list(argv)
    while args:
        a = args.pop(0)
        if a == "--seco":
            seco = True
        elif a == "--mais-velhos-que":
            idade = int(args.pop(0))
        else:
            raise ValueError(a)
    if idade is not None and not seco:
        raise ValueError("--mais-velhos-que só vale com --seco: o corte tem um prazo só")
    return seco, idade


def _relogio_fora_do_bruto(no_disco: dict, hoje: date) -> str | None:
    """Por que não se corta: o dia mais novo do bruto está no futuro ou parado há mais de `BRUTO_PARADO_DIAS`. O
    relógio errado à frente faria todo dia parecer velho; o portão ainda barraria, mas a trava é barata."""
    if not no_disco:
        return None
    recente = max(no_disco)
    if 0 <= oplog.idade_em_dias(recente, hoje) <= BRUTO_PARADO_DIAS:
        return None
    return (f"o dia mais novo do bruto é {recente} e hoje é {hoje.isoformat()}: relógio ou porta fora do normal, "
            "não se corta sem saber")


class Rodada:
    """O placar de uma passada do corte e o que fazer com cada veredito do portão."""

    def __init__(self, api: Api, tarefas: Tarefas | None, *, seco: bool, maximo: int,
                 diretorio_: str | os.PathLike | None = None):
        self.api, self.tarefas, self.seco, self.maximo, self.diretorio = api, tarefas, seco, maximo, diretorio_
        self.cortados = self.retidos = self.reprovados = self.adiados = self.pior = 0
        self.linhas: list[str] = []
        self._abertos: set[str] | None = None

    def processa(self, dia: str, idade: int) -> bool:
        """Confere e decide um dia. False quando a rodada deve parar (a API está fora para todos)."""
        if self.cortados >= self.maximo:
            self.adiados += 1
            return True
        dados = oplog.conteudo_do_dia(dia, self.diretorio)
        if dados is None:
            return True                                 # sumiu entre a listagem e a leitura: nada a cortar
        try:
            v = portao(self.api, dia, dados)
        except Falha as f:
            self.retidos += 1
            self.pior = max(self.pior, f.codigo)
            self.linhas.append(_linha(Veredito(dia, RETIDO, f"linhagem_indisponivel [{f.codigo}]"), idade, None))
            print(f"corte-bruto {dia}: {f}", file=sys.stderr)
            return False
        if v.acao == APROVADO:
            v = self._aprovado(v)
        elif v.acao == RETIDO:
            self.retidos += 1
        else:
            v = self._reprovado(v)
        self.linhas.append(_linha(v, idade, v.contas.get("arquivo")))
        return True

    def _aprovado(self, v: Veredito) -> Veredito:
        if self.seco:
            return Veredito(v.dia, "cortaria", v.motivo, v.contas)
        if oplog.remover_dia_conferido(v.dia, v.contas["arquivo"]["sha256"], self.diretorio):
            self.cortados += 1
            return Veredito(v.dia, CORTADO, v.motivo, v.contas)
        self.retidos += 1
        return Veredito(v.dia, RETIDO, "mudou_durante_a_conferencia", v.contas)

    def _reprovado(self, v: Veredito) -> Veredito:
        self.reprovados += 1
        self.pior = max(self.pior, 1)
        if self.seco:
            return Veredito(v.dia, "reprovaria", v.motivo, v.contas)
        try:
            self.tarefas = self.tarefas or Tarefas()
            if self._abertos is None:
                self._abertos = self.tarefas.titulos_abertos()
            titulo = titulo_do_incidente(v.dia)
            if titulo in self._abertos:
                return Veredito(v.dia, REPROVADO, v.motivo + "; incidente já aberto", v.contas)
            self.tarefas.abrir_incidente(titulo, corpo_do_incidente(v))
            self._abertos.add(titulo)
            return Veredito(v.dia, REPROVADO, v.motivo + "; incidente aberto", v.contas)
        except Falha as f:
            print(f"corte-bruto {v.dia}: incidente não aberto: {f}", file=sys.stderr)
            self.pior = max(self.pior, f.codigo)
            return Veredito(v.dia, REPROVADO, v.motivo + "; incidente NÃO aberto", v.contas)


def main(argv: list[str], api: Api | None = None, hoje: date | None = None, tarefas: Tarefas | None = None,
         saida: Callable[[str], object] = print, diretorio_: str | os.PathLike | None = None,
         poda_log: Path | None = None) -> int:
    if any(a in ("-h", "--help", "--ajuda") for a in argv):
        saida(USO)
        return 0
    try:
        seco, idade_de_ensaio = _argumentos(argv)
    except (IndexError, ValueError) as e:
        print(f"corte-bruto: {e}\n{USO}" if str(e) else USO, file=sys.stderr)
        return 2
    hoje = hoje or oplog.hoje_local()
    no_disco = oplog.dias_no_disco(diretorio_)
    parado = _relogio_fora_do_bruto(no_disco, hoje)
    if parado:
        print(f"corte-bruto: {parado}", file=sys.stderr)
        return 5
    limite = oplog.CORTE_DIAS if idade_de_ensaio is None else idade_de_ensaio
    candidatos = oplog.dias_mais_velhos_que(limite, hoje, diretorio_)
    maximo = int(os.environ.get("CORTE_MAX_DIAS") or MAX_DIAS_POR_RODADA)
    rodada = Rodada(api or Api(), tarefas, seco=seco, maximo=maximo, diretorio_=diretorio_)
    for dia in candidatos:
        if not rodada.processa(dia, oplog.idade_em_dias(dia, hoje)):
            break                                       # API fora para um é fora para todos: a próxima rodada tenta
    linhas = list(rodada.linhas)
    if rodada.adiados:
        linhas.append(f"corte-bruto: {rodada.adiados} dia(s) ficam para a próxima rodada "
                      f"(máximo {maximo} cortes por rodada)")
    # Linha de vida: grava mesmo sem candidato, para «o corte rodou» ser um fato observável, não uma suposição.
    linhas.append(f"corte-bruto {'ensaio' if seco else 'ok'} — candidatos={len(candidatos)} "
                  f"cortados={rodada.cortados} retidos={rodada.retidos} reprovados={rodada.reprovados} · "
                  f"prazo={limite}d · no disco={len(no_disco)} dias")
    for linha in linhas:
        saida(linha)
    if not seco:
        _grava_poda(poda_log or raizes.instancia() / "var" / "log" / "poda.log", linhas)
    return rodada.pior


if __name__ == "__main__":      # pragma: no cover
    sys.exit(main(sys.argv[1:]))
