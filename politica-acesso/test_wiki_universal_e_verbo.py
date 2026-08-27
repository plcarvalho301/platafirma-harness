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
    # jaiminho carrega agora o papel `dev` (card #2899, ordem do dono 27/08/2026): faz
    # tudo que a cadeira faz, menos publicar em producao. Varias linhas de EXTERNO que
    # eram NEGA no modelo DMZ viraram PERMITE — escritas A MAO, como o gabarito literal
    # exige. jaiminho-fabrica (FABRICA) segue `fornecedor` ate o teardown do split.

    # --- (e) wiki: dev le e escreve como cadeira -------------------------------
    (EXTERNO, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     PERMITE, "dev-faz-tudo-menos-publicar"),
    (EXTERNO, "wiki_buscar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "idem"),
    (EXTERNO, "wiki_listar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "idem"),
    (EXTERNO, "wiki_consultar", "wiki", "plataforma-wiki", "wiki:principal/*",
     PERMITE, "idem"),
    (EXTERNO, "wiki_buscar", "wiki", "plataforma-wiki", "wiki:PlataFirma/*",
     PERMITE, "dev le a casa por dentro; a contencao e a conta segregada, nao o PAP"),
    (EXTERNO, "wiki_editar", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     PERMITE, "dev escreve wiki como cadeira"),
    (EXTERNO, "wiki_enviar_arquivo", "wiki", "plataforma-wiki", "wiki:File/x.png",
     PERMITE, "idem"),

    # --- (e) FABRICA/fornecedor segue como antes ------------------------------
    (FABRICA, "wiki_editar", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "fornecedor-nao-escreve-na-wiki: a entrega da fabrica e commit"),
    (FABRICA, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "nao ha regra de wiki para fornecedor, e o default nega"),
    (DONO, "wiki_editar", "wiki", "plataforma-wiki", "wiki:PlataFirma/Sec",
     PERMITE, "operador-plataforma: a casa por dentro e dele"),
    (ESTRANHO, "wiki_ler", "wiki", "plataforma-wiki", "wiki:principal/Ontologia",
     NEGA, "atributo ausente nega"),

    # --- (d) FABRICA/fornecedor: os dois buracos medidos seguem fechados -------
    (FABRICA, "run_command", "comando", "plataforma", "git -c core.pager=sh log",
     NEGA, "BURACO 1: `git -c` executa comando arbitrario; o glob `git *` o cobria"),
    (FABRICA, "run_command", "comando", "plataforma", "git -c alias.z=!sh z",
     NEGA, "mesmo buraco por alias de shell"),
    (FABRICA, "run_command", "comando", "plataforma", "cat > /tmp/x",
     NEGA, "BURACO 2: `cat *` ESCREVIA; leitura agora e `read_file`, com alvo"),
    (FABRICA, "run_command", "comando", "plataforma", "cat /etc/passwd",
     NEGA, "`cat *` saiu inteiro: nao ha meio-termo por glob"),
    (FABRICA, "run_command", "comando", "plataforma", "git status --short",
     PERMITE, "fornecedor-le-repo, subcomando nomeado"),
    (FABRICA, "run_command", "comando", "plataforma", "git push origin main",
     PERMITE, "fornecedor tambem: o PAP nao trava push; a credencial trava"),
    (FABRICA, "run_command", "comando", "plataforma", "docker ps",
     NEGA, "fornecedor-sem-estado-do-host"),

    # --- (d) dev (jaiminho): run_command AMPLO, publicar-em-prod recortado -----
    # O recorte do dev e por ALVO, nao por allowlist de git subcomando a subcomando:
    # o proprio PAP diz que prefixo de string e mitigacao, nao controle. A contencao
    # do dev e a CONTA segregada; por isso o mesmo `git -c ...` que a fabrica nega,
    # o dev permite — a diferenca de modelo esta escrita aqui de proposito.
    (EXTERNO, "run_command", "comando", "plataforma", "git status --short",
     PERMITE, "dev-faz-tudo-menos-publicar"),
    (EXTERNO, "run_command", "comando", "plataforma", "pytest -q",
     PERMITE, "dev roda teste e build"),
    (EXTERNO, "run_command", "comando", "plataforma", "git -c alias.z=!sh z",
     PERMITE, "dev tem run_command amplo por desenho; o vetor de contencao do dev e a conta, nao o filtro de string"),
    # PONTO CRITICO: o PAP NAO impede o dev de dar push no branch default.
    (EXTERNO, "run_command", "comando", "plataforma", "git push origin main",
     PERMITE, "o PAP libera push; a trava de publicar-no-git e a credencial escopada da conta, nao o PAP"),
    # O que o PAP TRAVA e o RUNTIME de producao (a outra metade de publicar):
    (EXTERNO, "run_command", "comando", "plataforma", "docker compose up -d",
     NEGA, "dev-nao-publica-em-producao"),
    (EXTERNO, "run_command", "comando", "plataforma", "systemctl --user restart ops",
     NEGA, "idem: runtime de prod"),
    (EXTERNO, "run_command", "comando", "plataforma", "deploy prod",
     NEGA, "idem"),
    (EXTERNO, "run_command", "comando", "plataforma", "cat prod.env",
     NEGA, "idem: `*.env*` e segredo de ambiente"),
    (EXTERNO, "run_command", "comando", "plataforma", "seg conceder x",
     NEGA, "idem: administracao de acesso nao e do dev"),
    (EXTERNO, "run_command", "comando", "plataforma", "acesso desligar x",
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
