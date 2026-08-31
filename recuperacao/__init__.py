"""`recuperacao` — o Recuperador: envelope único de leitura das seis fontes.

Biblioteca importada, nunca subprocess (`arq:0064` §1). Vive no `ops-mcp` e em nenhum
outro consumidor (`arq:0067`, spec §2). Os verbos `bin/recuperar`, `bin/descobrir` e `bin/situacao`
são finos e importam daqui (arq:0085 §2).

F0 (card #2291) entrega o núcleo: envelope, enums, disjuntor e os testes de contrato.
F1 acrescenta os adaptadores (#2298 e seguintes) e o PEP por fonte (#2303). F2 traz o
cache por fonte e a instrumentação `rec:stat` (#2308). Roteamento derivado (#2304) e gate
(F3) seguem fora.
Verbos de leitura do acervo (#2952, #2953, arq:0085): `descobrir` e `situacao`.

    from recuperacao import Envelope, Item, Procedencia, Versao, LinhaFonte
    from recuperacao import Cobertura, Casamento, Causa, VersaoTipo, Fonte
    from recuperacao import Painel, Disjuntor
    from recuperacao import PEP, Negativa, recusa_por_concessao
    from recuperacao import Cache, busca_com_cache
    from recuperacao import descobrir, situacao
"""

from .cache import Cache, SemCache, busca_com_cache
from .catalogo import Catalogo, Custo, CustoProibido, Leitor, LinhaCatalogo, monta
from .descobrir import EIXOS_PADRAO, EIXOS_VALIDOS, descobrir
from .disparo import Disparo, FonteAlcancada, SemDenominador, delta, serie_disparo
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
from .pep import ACAO, PEP, Negativa, recusa_por_concessao
from .resolvedor import Coordenada, Degrau, EstadoConceito, NaoResolve, Resolvedor, Secao, le_chave
from .situacao import situacao
from .veredito import LinhaVeredito, Serie, SerieFonte, instrumenta, serie

__all__ = [
    "ACAO",
    "CAMPOS_PROIBIDOS",
    "CLASSE",
    "Cache",
    "Casamento",
    "Catalogo",
    "Causa",
    "Classe",
    "Cobertura",
    "ContratoViolado",
    "Coordenada",
    "Custo",
    "CustoProibido",
    "Degrau",
    "Disjuntor",
    "Disparo",
    "EIXOS_PADRAO",
    "EIXOS_VALIDOS",
    "Envelope",
    "EstadoConceito",
    "EstadoDisjuntor",
    "Expansao",
    "Fonte",
    "FonteAlcancada",
    "Gate",
    "Item",
    "Julgamento",
    "Leitor",
    "LinhaCatalogo",
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
    "SemDenominador",
    "Serie",
    "SerieFonte",
    "Sinal",
    "TIMEOUT_MS",
    "Veredito",
    "Versao",
    "VersaoTipo",
    "busca_com_cache",
    "classe",
    "delta",
    "descobrir",
    "extrai_chaves",
    "fontes_citadas",
    "instrumenta",
    "le_chave",
    "linha_disjuntor_aberto",
    "monta",
    "recusa_por_concessao",
    "serie",
    "serie_disparo",
    "situacao",
    "timeout_ms",
]
