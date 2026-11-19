"""Os eventos do verbo persona no log da porta: cada troca e cada volta, por eixo, cada entrada e saída de cenário, cada
começo e fim de ritual, cada invocação perdida e cada defeito de forma.

A lousa guarda só o agora; o histórico mora aqui. É deste log que a composição tira o aviso de invocação perdida: o último
evento da sessão num eixo foi uma troca, e a memória de trabalho já não tem o campo. Escreve e lê pelo oplog, o único módulo
que abre o bruto da porta.
"""

from __future__ import annotations

from datetime import date, timedelta

TOOL = "persona"
JANELA_DIAS = 2          # a chave da sessão vive 48 horas; evento mais velho que isso não diz nada de sessão viva


class Log:
    def __init__(self, diretorio=None):
        self.diretorio = diretorio

    def emitir(self, sessao_id: str, evento: str, **campos) -> None:
        import oplog
        oplog.emitir({"tool": TOOL, "evento": evento, "sessao_id": sessao_id,
                      **{k: v for k, v in campos.items() if v is not None}}, diretorio_=self.diretorio)

    def eventos(self, sessao_id: str | None = None) -> list[dict]:
        """Os eventos do verbo na janela, na ordem em que foram escritos; com `sessao_id`, só os dela."""
        import oplog
        hoje = date.today()
        leitura = oplog.ler(hoje - timedelta(days=JANELA_DIAS), hoje, diretorio_=self.diretorio, sessao=sessao_id, tool=TOOL)
        return [e for e in leitura if not sessao_id or e.get("sessao_id") == sessao_id]

    def ultimos(self, sessao_id: str) -> dict:
        """O último evento da sessão por eixo, por cenário e do ritual: {"postura": {eixo: ev}, "cenario": {slug: ev},
        "ritual": ev ou None}."""
        saida = {"postura": {}, "cenario": {}, "ritual": None}
        for e in self.eventos(sessao_id):
            if e.get("evento") == "postura" and e.get("eixo"):
                saida["postura"][e["eixo"]] = e
            elif e.get("evento") == "cenario" and e.get("cenario"):
                saida["cenario"][e["cenario"]] = e
            elif e.get("evento") == "ritual":
                saida["ritual"] = e
        return saida

    def defeito_ja_avisado(self, entidade: str, slug: str, sha: str) -> bool:
        """O mesmo documento, no mesmo sha, já teve o defeito levado a incidente nesta janela: não se abre outro."""
        return any(e.get("evento") == "defeito" and e.get("entidade") == entidade and e.get("peca") == slug
                   and e.get("sha") == sha for e in self.eventos())
