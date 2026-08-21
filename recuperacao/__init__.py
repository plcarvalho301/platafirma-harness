"""`recuperacao` — o Recuperador: envelope único de leitura das seis fontes.

Biblioteca importada, nunca subprocess (`arq:0064` §1). Vive no `ops-mcp` e em nenhum
outro consumidor (`arq:0067`, spec §2). O verbo `bin/recuperar` é fino e importa daqui.

F0 (card #2291) entrega o núcleo: envelope, enums, disjuntor e os testes de contrato.
F1 acrescenta os adaptadores (#2298 e seguintes) e o PEP por fonte (#2303). F2 traz o
cache por fonte e a instrumentação `rec:stat` (#2308). Roteamento derivado (#2304) e gate
(F3) seguem fora.

    from recuperacao import Envelope, Item, Procedencia, Versao, LinhaFonte
    from recuperacao import Cobertura, Casamento, Causa, VersaoTipo, Fonte
    from recuperacao import Painel, Disjuntor
    from recuperacao import PEP, Negativa, recusa_por_concessao
    from recuperacao import Cache, busca_com_cache
"""

from .cache import Cache, SemCache, busca_com_cache
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
from .gate import Gate, Julgamento, Parecer, Veredito, extrai_chaves, fontes_citadas
from .veredito import LinhaVeredito, Serie, SerieFonte, instrumenta, serie
from .resolvedor import Coordenada, Degrau, EstadoConceito, NaoResolve, Resolvedor, Secao, le_chave
from .pep import ACAO, PEP, Negativa, recusa_por_concessao

__all__ = [
    "ACAO",
    "CAMPOS_PROIBIDOS",
    "CLASSE",
    "Cache",
    "Casamento",
    "Causa",
    "Classe",
    "Cobertura",
    "ContratoViolado",
    "Coordenada",
    "Degrau",
    "Disjuntor",
    "Envelope",
    "EstadoConceito",
    "EstadoDisjuntor",
    "Expansao",
    "Fonte",
    "Gate",
    "Item",
    "Julgamento",
    "LinhaFonte",
    "LinhaVeredito",
    "NaoResolve",
    "Negativa",
    "PEP",
    "PREFIXO_CHAVE",
    "Painel",
    "Parecer",
    "Procedencia",
    "Resolvedor",
    "Secao",
    "SemCache",
    "Serie",
    "SerieFonte",
    "Sinal",
    "TIMEOUT_MS",
    "Veredito",
    "Versao",
    "VersaoTipo",
    "busca_com_cache",
    "classe",
    "extrai_chaves",
    "fontes_citadas",
    "instrumenta",
    "le_chave",
    "linha_disjuntor_aberto",
    "recusa_por_concessao",
    "serie",
    "timeout_ms",
]
