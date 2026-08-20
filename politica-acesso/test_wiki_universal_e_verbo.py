"""Aceite das duas ordens do dono de 20/08/2026.

    uvx --with pyyaml pytest -q politica-acesso/test_wiki_universal_e_verbo.py

(e) A WIKI E SUPERFICIE UNIVERSAL, autorizada por SUJEITO — nao por conta de SO,
    nao por rede, nao por qual servidor MCP o bot usou para entrar. Aqui se confere
    que ler passa para quem tem concessao nominal e que escrever nao passa para
    quem nao tem, com negativa ESCRITA em vez de default.

(d) VERBO NO LUGAR DE STRING. A allowlist de prefixo tinha dois buracos medidos —
    `cat *` cobria `cat > arquivo`, e `git *` cobria `git -c core.pager=<cmd>`.
    Os dois viram teste: sao a razao da mudanca, e razao que nao vira teste volta.

A expectativa e literal, pelo mesmo motivo do `test_matriz_sujeito_fonte`: gerar o
gabarito da politica que ele julga seria escrever a prova com o gabarito aberto.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

from pdp import Politica, Recurso, Sujeito, decide  # noqa: E402

PERMITE, NEGA = True, False

DONO = "megafone"
EXTERNO = "jaiminho"
FABRICA = "jaiminho-fabrica"
ESTRANHO = "cadeira-que-nao-existe"

# (sujeito, acao, tipo, dominio, alvo, esperado, por que)
CASOS = [
    # --- (e) wiki: leitura por sujeito, de qualquer servidor -------------------
    (EXTERNO, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     PERMITE, "jaiminho-le-wiki-conceito"),
    (EXTERNO, "wiki_buscar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "busca entrou na mesma concessao em 20/08"),
    (EXTERNO, "wiki_listar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "idem"),
    (EXTERNO, "wiki_consultar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "idem — cargo le o mesmo namespace"),
    (EXTERNO, "wiki_buscar", "wiki", "plataforma-wiki", "wiki:PlataFirma/*",
     NEGA, "externo-nao-le-wiki-interna, e buscar nao contorna"),

    # --- (e) wiki: escrita nao se concede por portar token ---------------------
    (EXTERNO, "wiki_editar", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "externo-nao-escreve-na-wiki"),
    (EXTERNO, "wiki_enviar_arquivo", "wiki", "plataforma-wiki", "wiki:File/x.png",
     NEGA, "envio de binario e superficie de outra natureza"),
    (FABRICA, "wiki_editar", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "fornecedor-nao-escreve-na-wiki: a entrega da fabrica e commit"),
    (FABRICA, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "nao ha regra de wiki para fornecedor, e o default nega"),
    (DONO, "wiki_editar", "wiki", "plataforma-wiki", "wiki:PlataFirma/Sec",
     PERMITE, "operador-plataforma: a casa por dentro e dele"),
    (ESTRANHO, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "atributo ausente nega"),

    # --- (d) os dois buracos medidos, agora fechados ---------------------------
    (FABRICA, "run_command", "comando", "plataforma", "git -c core.pager=sh log",
     NEGA, "BURACO 1: `git -c` executa comando arbitrario; o glob `git *` o cobria"),
    (FABRICA, "run_command", "comando", "plataforma", "git -c alias.z=!sh z",
     NEGA, "mesmo buraco por alias de shell"),
    (FABRICA, "run_command", "comando", "plataforma", "cat > /tmp/x",
     NEGA, "BURACO 2: `cat *` ESCREVIA; leitura agora e `read_file`, com alvo"),
    (FABRICA, "run_command", "comando", "plataforma", "cat /etc/passwd",
     NEGA, "`cat *` saiu inteiro: nao ha meio-termo por glob"),

    # --- (d) o que a fabrica precisa continua passando -------------------------
    (FABRICA, "run_command", "comando", "plataforma", "git status --short",
     PERMITE, "fornecedor-le-repo, subcomando nomeado"),
    (FABRICA, "run_command", "comando", "plataforma", "git commit -m x",
     PERMITE, "idem"),
    (FABRICA, "run_command", "comando", "plataforma", "git push origin main",
     PERMITE, "idem"),
    (FABRICA, "run_command", "comando", "plataforma", "pytest -q",
     PERMITE, "idem"),
    (FABRICA, "run_command", "comando", "plataforma", "tarefas comentar 2286 x",
     PERMITE, "fornecedor-opera-o-card"),

    # --- (d) o que continua fora, e e o ponto da regra ------------------------
    (FABRICA, "run_command", "comando", "plataforma", "docker ps",
     NEGA, "fornecedor-sem-estado-do-host"),
    (FABRICA, "run_command", "comando", "plataforma", "systemctl --user restart docker",
     NEGA, "idem"),
]


@pytest.fixture(scope="module")
def ambiente():
    pol = Politica.de_arquivo(AQUI / "politica.yaml")
    suj = (yaml.safe_load((AQUI / "sujeitos.yaml").read_text(encoding="utf-8"))
           or {}).get("sujeitos") or {}
    return pol, suj


def _sujeito(nome: str, projecao: dict) -> Sujeito:
    a = projecao.get(nome) or {}
    return Sujeito(id=nome, natureza=a.get("natureza"),
                   papeis=tuple(a.get("papeis") or ()),
                   dominios=tuple(a.get("dominios") or ()),
                   habilitacao=a.get("habilitacao", "publico"))


@pytest.mark.parametrize("sujeito,acao,tipo,dominio,alvo,esperado,porque", CASOS,
                         ids=[f"{c[0]}-{c[1]}-{c[4][:28]}" for c in CASOS])
def test_caso(ambiente, sujeito, acao, tipo, dominio, alvo, esperado, porque):
    pol, proj = ambiente
    d = decide(_sujeito(sujeito, proj), acao,
               Recurso(tipo=tipo, id=alvo, dominio=dominio), pol)
    assert d.permitido is esperado, (
        f"{sujeito} × {acao} × {alvo}: esperado "
        f"{'PERMITE' if esperado else 'NEGA'} ({porque}), "
        f"obtido {'PERMITE' if d.permitido else f'NEGA[{d.regra}: {d.motivo}]'}")


def test_verbo_operacional_declarado_mas_inerte_ate_existir():
    """As regras de verbo estao escritas e NAO valem para o que nao existe.

    Verbo declarado no PAP e alcance pretendido, nao capacidade. Este teste
    guarda a diferenca: no dia em que `repo_commitar` existir de verdade, ele
    passa a permitir — e ate la, nada muda para quem nao tem o tipo `operacao`.
    """
    pol, proj = (Politica.de_arquivo(AQUI / "politica.yaml"),
                 (yaml.safe_load((AQUI / "sujeitos.yaml").read_text(encoding="utf-8"))
                  or {}).get("sujeitos") or {})
    s = _sujeito(FABRICA, proj)
    permitido = decide(s, "repo_commitar",
                       Recurso(tipo="operacao", id="platafirma-harness/x",
                               dominio="plataforma"), pol)
    assert permitido.permitido, "a regra do verbo tem de valer quando o tipo e `operacao`"
    negado = decide(s, "repo_commitar",
                    Recurso(tipo="comando", id="platafirma-harness/x",
                            dominio="plataforma"), pol)
    assert not negado.permitido, "verbo nao pode virar atalho de `run_command`"
