"""A composição das posturas em vigor de uma sessão, uma linha por eixo.

Um dicionário por eixo se preenche em três camadas, cada uma por cima da anterior:

  1. as linhas do perfil, a postura que a ligação postura-preferencial da persona aponta;
  2. a linha da seção Postura do ramo do chapéu vestido;
  3. as linhas do que foi invocado, lidas da memória de trabalho.

Eixo sem linha não entra. A precedência se resolve aqui, e a cadeira recebe só o resultado: cada linha com o rótulo do eixo
e sem a origem, que fica no dado e no log.

Quatro desvios, todos decididos aqui:

  - o perfil não cumpre a forma: a postura da casa (a reserva, sem eixo) entra no lugar dele, e o defeito sai para incidente;
  - um ritual que declara suprimir a postura vigora: o bloco não é servido, as invocações ficam guardadas, e só a invocação
    que o dono fez depois do começo do ritual é servida;
  - a chave da sessão sumiu: o eixo volta ao ramo ou ao perfil, e o aviso diz quais eixos perderam a invocação, pelo último
    evento da sessão no log;
  - um campo da chave traz eixo que saiu da lista: é ignorado, com aviso.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import documentos as doc
from .casa import SemBanco
from .lousa import Fora

_PREFERENCIAL = re.compile(r"^Postura preferencial:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", re.M)


@dataclass
class Vigor:
    eixos: dict = field(default_factory=dict)
    por_eixo: dict = field(default_factory=dict)        # slug do eixo -> Linha em vigor (as três camadas)
    origem: dict = field(default_factory=dict)          # slug do eixo -> perfil | ramo | invocada
    invocadas: dict = field(default_factory=dict)       # slug do eixo -> campo da lousa
    perfil: str | None = None
    reserva: list = field(default_factory=list)         # os itens da postura da casa, quando ela entra no lugar do perfil
    suspenso_por: str | None = None                     # o ritual que suprime a postura
    cenarios: list = field(default_factory=list)        # (slug, título, condição, hora)
    circunstancia: tuple | None = None                  # (slug, título, itens)
    avisos: list = field(default_factory=list)
    defeitos: list = field(default_factory=list)        # doc.Malformado a levar a incidente
    perdidos: list = field(default_factory=list)        # eventos «perdida» a gravar: (evento, campos)
    memoria_fora: bool = False

    def servidas(self) -> list:
        """As linhas que a cadeira recebe, na ordem dos eixos. Com a postura suprimida, só o que o dono invocou depois."""
        linhas = self.por_eixo
        if self.suspenso_por:
            linhas = {e: l for e, l in linhas.items() if self._do_dono_no_ritual(e)}
        return sorted(linhas.values(), key=lambda l: (self.eixos[l.eixo].ordem, l.eixo))

    def _do_dono_no_ritual(self, eixo: str) -> bool:
        campo = self.invocadas.get(eixo) or {}
        return self.origem.get(eixo) == "invocada" and campo.get("motivo") == "dono" and bool(campo.get("no_ritual"))

    def rotulos(self) -> dict:
        """eixo -> «eixo: polo» do que está em vigor, para dizer o que saiu e o que entrou."""
        return {l.eixo: l for l in self.servidas()}

    def bloco(self) -> str:
        """O texto da peça de posturas. Vazio quando não há o que servir."""
        linhas = self.servidas()
        reserva = [] if self.suspenso_por else self.reserva
        if not linhas and not reserva:
            return ""
        if reserva:
            cabeca = "POSTURAS EM VIGOR: a postura da casa, e uma linha por eixo marcado."
        else:
            cabeca = "POSTURAS EM VIGOR: uma linha por eixo, e em cada eixo vale só esta."
        return "\n".join([cabeca, *[f"- {i}" for i in reserva], *[l.marcada() for l in linhas]])

    def bloco_de_cenarios(self) -> str:
        if not self.cenarios:
            return ""
        saida = ["CENÁRIOS PRESENTES"] + [f"- {t}: {c}" for _, t, c, _ in self.cenarios]
        if self.circunstancia:
            _, titulo, itens = self.circunstancia
            saida += [f"CIRCUNSTÂNCIA EM VIGOR: {titulo}", *[f"- {i}" for i in itens]]
        return "\n".join(saida)


def perfil_da_persona(base: Path, cadeira: str, ligacoes, avisos: list) -> str | None:
    """O perfil vem da ligação postura-preferencial. Com o banco fora, vem da linha «Postura preferencial» da persona, que é de
    onde a ingestão grava a ligação, e o aviso diz isso."""
    try:
        return ligacoes.perfil(cadeira)
    except SemBanco as erro:
        try:
            texto, _ = doc.ler_documento(base, "persona", cadeira)
        except doc.Inexistente:
            texto = ""
        achada = _PREFERENCIAL.search(texto[:2000])
        avisos.append(f"banco do acervo fora ({erro}): o perfil veio da linha «Postura preferencial» da persona")
        return achada.group(1) if achada else None


def compor(base: Path, cadeira: str, chapeu: str, sessao_id: str, lousa, log, ligacoes) -> Vigor:
    v = Vigor(eixos=doc.ler_eixos(base))

    # 1. o perfil
    v.perfil = perfil_da_persona(base, cadeira, ligacoes, v.avisos)
    try:
        if v.perfil is None:
            raise doc.Malformado("persona", cadeira, ["a persona não aponta postura preferencial"])
        for linha in doc.postura(base, v.perfil, v.eixos):
            v.por_eixo[linha.eixo], v.origem[linha.eixo] = linha, "perfil"
    except (doc.Malformado, doc.Inexistente) as erro:
        defeito = erro if isinstance(erro, doc.Malformado) else doc.Malformado(
            "postura", v.perfil or "", ["o documento do perfil não está na árvore"])
        v.defeitos.append(defeito)
        v.avisos.append(f"o perfil não cumpre a forma ({defeito}): a postura da casa entrou no lugar dele")
        try:
            v.reserva = doc.itens_sem_marca(base, "postura", doc.RESERVA)[1]
        except (doc.Malformado, doc.Inexistente) as sem_reserva:
            v.avisos.append(f"a postura da casa também não pôde ser lida: {sem_reserva}")

    # 2. o ramo do chapéu vestido
    if chapeu:
        try:
            for linha in doc.ramo(base, chapeu, v.eixos):
                v.por_eixo[linha.eixo], v.origem[linha.eixo] = linha, "ramo"
        except doc.Inexistente:
            v.avisos.append(f"o chapéu {chapeu} não está na árvore da casa nova, e a postura do ramo não entrou")
        except doc.Malformado as defeito:
            v.defeitos.append(defeito)
            v.avisos.append(f"a postura do ramo do chapéu {chapeu} não cumpre a forma e ficou fora: {defeito}")

    if not sessao_id:
        return v

    # 3. o que foi invocado
    ritual, presentes = {}, {}
    try:
        campos = lousa.invocacoes(sessao_id)
        ritual = lousa.ritual(sessao_id)
        presentes = lousa.cenarios(sessao_id)
    except Fora as erro:
        campos, v.memoria_fora = {}, True
        v.avisos.append(f"{erro}: as invocações da sessão não foram lidas, e valem o perfil e o ramo")
    comeco_do_ritual = str(ritual.get("hora") or "")
    antes = dict(v.por_eixo)
    for eixo, campo in campos.items():
        peca = str(campo.get("peca") or "")
        if eixo not in v.eixos:
            v.avisos.append(f"o eixo «{eixo}» saiu da lista dos eixos de postura: a invocação de {peca} nele foi ignorada")
            continue
        try:
            linha = next((l for l in doc.postura(base, peca, v.eixos) if l.eixo == eixo), None)
        except (doc.Malformado, doc.Inexistente) as erro:
            v.avisos.append(f"a invocação de {peca} no eixo «{v.eixos[eixo].rotulo}» foi ignorada: {erro}")
            continue
        if linha is None:
            v.avisos.append(f"a postura {peca} não marca mais o eixo «{v.eixos[eixo].rotulo}»: a invocação foi ignorada")
            continue
        v.invocadas[eixo] = {**campo, "no_ritual": bool(comeco_do_ritual) and str(campo.get("hora") or "") >= comeco_do_ritual}
        v.por_eixo[eixo], v.origem[eixo] = linha, "invocada"

    # a chave que sumiu antes da volta: o último evento do eixo é uma troca, e a lousa já não tem o campo
    ultimos = {"postura": {}, "cenario": {}, "ritual": None}
    if not v.memoria_fora:
        try:
            ultimos = log.ultimos(sessao_id)
        except Exception as erro:      # noqa: BLE001 — o log ilegível tira o aviso, nunca a composição
            v.avisos.append(f"o log da porta não pôde ser lido, e a conferência de invocação perdida não rodou: {erro}")
    for eixo, evento in ultimos["postura"].items():
        if evento.get("acao") != "troca" or eixo in campos or eixo not in v.eixos:
            continue
        volta = antes.get(eixo)
        destino = f"voltou a «{volta.rotulo()}»" if volta else "ficou sem linha"
        v.avisos.append(f"o eixo «{v.eixos[eixo].rotulo}» perdeu a invocação de {evento.get('peca')} "
                        f"(«{evento.get('para')}»): a chave da sessão sumiu da memória de trabalho, e o eixo {destino}")
        v.perdidos.append(("postura", {"acao": "perdida", "eixo": eixo, "de": evento.get("para"),
                                       "para": volta.polo_rotulo if volta else None, "peca": evento.get("peca")}))

    # o ritual que suprime a postura
    if ritual.get("slug") and doc.ritual_suprime_postura(base, str(ritual["slug"])):
        v.suspenso_por = str(ritual["slug"])
    evento = ultimos["ritual"]
    if evento and evento.get("acao") == "comeco" and not ritual and not v.memoria_fora:
        v.avisos.append(f"o ritual {evento.get('ritual')} saiu da memória de trabalho antes do fim: a vaga de ritual esvaziou")
        v.perdidos.append(("ritual", {"acao": "perdido", "ritual": evento.get("ritual")}))

    # os cenários presentes e a circunstância que o mais recente ativa
    for slug, campo in sorted(presentes.items(), key=lambda par: str(par[1].get("hora") or "")):
        try:
            titulo, condicao, _ = doc.cenario(base, slug)
        except doc.Inexistente:
            v.avisos.append(f"o cenário {slug} não está na árvore da casa nova e ficou fora")
            continue
        except doc.Malformado as defeito:
            v.defeitos.append(defeito)
            v.avisos.append(f"o cenário {slug} não cumpre a forma e ficou fora: {defeito}")
            continue
        v.cenarios.append((slug, titulo, condicao, str(campo.get("hora") or "")))
    for slug, evento in ultimos["cenario"].items():
        if evento.get("acao") == "entra" and slug not in presentes and not v.memoria_fora:
            v.avisos.append(f"o cenário {slug} saiu da memória de trabalho antes da saída: a chave da sessão sumiu")
            v.perdidos.append(("cenario", {"acao": "perdido", "cenario": slug}))
    if v.cenarios:
        try:
            ativadas = ligacoes.ativadas([c[0] for c in v.cenarios])
        except SemBanco as erro:
            ativadas = {}
            v.avisos.append(f"banco do acervo fora ({erro}): a circunstância que o cenário ativa não foi lida")
        for slug, *_ in reversed(v.cenarios):      # o cenário presente mais recente que ative uma
            alvo = ativadas.get(slug)
            if not alvo:
                continue
            try:
                titulo, itens, _ = doc.itens_sem_marca(base, "circunstancia", alvo)
                v.circunstancia = (alvo, titulo, itens)
            except doc.Inexistente:
                v.avisos.append(f"a circunstância {alvo} não está na árvore da casa nova e ficou fora")
            except doc.Malformado as defeito:
                v.defeitos.append(defeito)
                v.avisos.append(f"a circunstância {alvo} não cumpre a forma e ficou fora: {defeito}")
            break
    return v
