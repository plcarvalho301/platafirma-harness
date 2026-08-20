"""`recuperacao` — o Recuperador: envelope único de leitura das seis fontes.

Biblioteca importada, nunca subprocess (`arq:0064` §1). Vive no `ops-mcp` e em nenhum
outro consumidor (`arq:0067`, spec §2). O verbo `bin/recuperar` é fino e importa daqui.

F0 (card #2291) entrega o núcleo: envelope, enums, disjuntor e os testes de contrato.
F1 acrescenta os adaptadores (#2298 e seguintes) e o PEP por fonte (#2303). Roteamento
derivado (#2304), cache (F2) e gate (F3) seguem fora.

    from recuperacao import Envelope, Item, Procedencia, Versao, LinhaFonte
    from recuperacao import Cobertura, Casamento, Causa, VersaoTipo, Fonte
    from recuperacao import Painel, Disjuntor
    from recuperacao import PEP, Negativa, recusa_por_concessao
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
from .pep import ACAO, PEP, Negativa, recusa_por_concessao

__all__ = [
    "ACAO",
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
    "Negativa",
    "PEP",
    "Painel",
    "Procedencia",
    "Sinal",
    "Versao",
    "VersaoTipo",
    "classe",
    "linha_disjuntor_aberto",
    "recusa_por_concessao",
    "timeout_ms",
]
