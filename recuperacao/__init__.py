"""`recuperacao` — o Recuperador: envelope único de leitura das seis fontes.

Biblioteca importada, nunca subprocess (`arq:0064` §1). Vive no `ops-mcp` e em nenhum
outro consumidor (`arq:0067`, spec §2). O verbo `bin/recuperar` é fino e importa daqui.

F0 (card #2291) entrega o núcleo: envelope, enums, disjuntor e os testes de contrato.
Adaptador, PEP, roteamento, cache e gate são F1–F3 e não moram neste commit.

    from recuperacao import Envelope, Item, Procedencia, Versao, LinhaFonte
    from recuperacao import Cobertura, Casamento, Causa, VersaoTipo, Fonte
    from recuperacao import Painel, Disjuntor
"""

from .disjuntor import Disjuntor, EstadoDisjuntor, Painel
from .envelope import (
    CAMPOS_PROIBIDOS,
    Casamento,
    Causa,
    Cobertura,
    ContratoViolado,
    Envelope,
    Expansao,
    Item,
    LinhaFonte,
    Procedencia,
    Sinal,
    Versao,
    VersaoTipo,
    linha_disjuntor_aberto,
)
from .fontes import CLASSE, PREFIXO_CHAVE, TIMEOUT_MS, Classe, Fonte, classe, timeout_ms

__all__ = [
    "CAMPOS_PROIBIDOS",
    "CLASSE",
    "PREFIXO_CHAVE",
    "TIMEOUT_MS",
    "Casamento",
    "Causa",
    "Classe",
    "Cobertura",
    "ContratoViolado",
    "Disjuntor",
    "Envelope",
    "EstadoDisjuntor",
    "Expansao",
    "Fonte",
    "Item",
    "LinhaFonte",
    "Painel",
    "Procedencia",
    "Sinal",
    "Versao",
    "VersaoTipo",
    "classe",
    "linha_disjuntor_aberto",
    "timeout_ms",
]
