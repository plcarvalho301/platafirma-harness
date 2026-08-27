#!/usr/bin/env python3
"""Prova do modelo ator/provider/persona em comum/cadeiras.py.

Roda NO HOST, so com stdlib, contra a arvore de personas real:

    PF_RAIZ=<pai-do-harness> python3 chat/testes/prova-cadeiras-ator-persona.py

Trava o corte que a sessao de 24/08/2026 fixou como canonico:
  - conta    = perimetro de segregacao (usuario do SO)
  - provider = entidade afetiva por tras da conta (jaiminho = Antigravity)
  - persona  = o que a sessao monta (abertura/<persona>/persona.md)

O bug que ela pega: colapsar ator e persona num nome so faz participantes()
procurar abertura/jaiminho/persona.md (removido no revert b871733) e voltar
vazio — o ator some do roster, a sala fica muda. Regressao silenciosa, porque
lista vazia nao levanta erro. Sai 0 se tudo passou.
"""
from __future__ import annotations

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
CHAT = os.path.dirname(AQUI)
sys.path.insert(0, CHAT)

from comum import cadeiras as c  # noqa: E402

falhas = []


def prova(nome, cond):
    if cond:
        print(f"  ok   {nome}")
    else:
        print(f"  FALHA {nome}")
        falhas.append(nome)


# O ator de superficie entra no roster e ganha porta com o dono.
prova("jaiminho e participante com persona resolvida",
      "jaiminho" in c.participantes())
prova("jaiminho esta no roster de atores (MXID, sala)",
      "jaiminho" in c.atores())
prova("eh_participante(jaiminho): gira por rota propria",
      c.eh_participante("jaiminho") is True)

# A sessao dele monta a persona da fabrica, nao uma homonima do ator.
prova("slug_da_cadeira(jaiminho) == fabrica (persona, nao ator)",
      c.slug_da_cadeira("jaiminho") == "fabrica")

# O perimetro (conta/MXID) e do ator e nao se move pela troca de persona.
prova("sufixo_canonico(_pf_jaiminho) == jaiminho (MXID preservado)",
      c.sufixo_canonico("_pf_jaiminho") == "jaiminho")
prova("localpart_da_cadeira(jaiminho) == _pf_jaiminho",
      c.localpart_da_cadeira("jaiminho") == "_pf_jaiminho")

# O roster do org (voto, roteamento entre cadeiras) nao admite o participante.
prova("cadeiras() NAO inclui jaiminho (roster do org intacto)",
      "jaiminho" not in c.cadeiras())

# A persona-fabrica de fato existe onde o mapa aponta — senao o resto e ilusao.
raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
alvo = os.path.join(raiz, "platafirma-harness", "abertura", "fabrica", "persona.md")
prova("abertura/fabrica/persona.md existe (destino do mapa)",
      os.path.isfile(alvo))


# --- #2431 Fase 1: nome humano (alias) resolve para o sufixo canonico -----------
# O bug que fixa: o dono digita o nome do ator ("Oswaldo", "joão") e a resolucao
# de cadeira devolvia None, entao a fila procurava caixa inexistente.
prova("alias inteiro: 'Oswaldo Aranha' -> TI",
      c.sufixo_canonico("Oswaldo Aranha") == "TI")
prova("primeiro nome: 'Oswaldo' -> TI",
      c.sufixo_canonico("Oswaldo") == "TI")
prova("acento dobrado: 'joao' -> arquiteto",
      c.sufixo_canonico("joao") == "arquiteto")
prova("acento + hifen: 'João-de-Barro' -> arquiteto",
      c.sufixo_canonico("João-de-Barro") == "arquiteto")
prova("primeiro nome com til: 'joão' -> arquiteto",
      c.sufixo_canonico("joão") == "arquiteto")
# O alias e a ULTIMA tentativa: sufixo/slug reais continuam vencendo.
prova("sufixo real vence alias: 'TI' -> TI",
      c.sufixo_canonico("TI") == "TI")
prova("slug com prefixo intacto: 'claudinho-TI' -> TI",
      c.sufixo_canonico("claudinho-TI") == "TI")
# Nome que nao e alias de ninguem nao inventa cadeira.
prova("nome desconhecido -> None",
      c.sufixo_canonico("Fulano de Tal") is None)

print("prova do modelo ator/provider/persona em cadeiras.py")
print()
if falhas:
    print(f"FALHOU: {len(falhas)} prova(s)")
    sys.exit(1)
print("tudo passou")
sys.exit(0)
