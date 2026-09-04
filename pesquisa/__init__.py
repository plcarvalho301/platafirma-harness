"""Harness de pesquisa web soberana — verbo `pesquisar`.

spec: platafirma-arquitetura/docs/specs/spec_pesquisa-web.md
capacidade: pesquisa-web  ·  dono: claudinha-inteligencia
engenharia do verbo e do loop: ia (chapéu engenharia-de-harness)

Camadas: SearXNG (metabusca, §3.1) + Crawl4AI (leitura, §3.2), com manifesto por
trabalho (§4.8). Rota de máquina é o default: JSON estável, erro como `causa`
legível, idempotência declarada por ato (§2.2).

Import de crawl4ai é preguiçoso (só em `extrator`): a suíte de contrato roda sem a
biblioteca e sem rede, com coletores/transportes falsos. Conformidade contra os
reais pula com motivo (spec §8.6).
"""

from .envelope import FalhaFonte, UsoInvalido, envelope, erro_json

__all__ = ["FalhaFonte", "UsoInvalido", "envelope", "erro_json"]
