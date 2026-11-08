"""Testes unitários de lib/topologia.py (DTs 288 e 377).

Garante que a resolução de contêiner para stack da topologia seja única,
desempate pelo projeto do compose ou retorne None em caso de duplicata ambígua.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

import topologia  # noqa: E402

SHA = "c" * 40
TOPOLOGIA = [
    {"slug": "conhecimento", "compose": ["/opt/platafirma/current/conhecimento/docker-compose.yml"]},
    {"slug": "rag", "compose": ["/opt/platafirma/current/conhecimento/rag/docker-compose.yml",
                                "/opt/platafirma/current/conhecimento/rag/docker-compose.gpu.yml"]},
    {"slug": "core", "compose": "/opt/platafirma/current/core/docker-compose.yml"},
]


def test_composes_da_stack():
    assert topologia.composes_da_stack({"compose": "/a/b.yml"}) == ["/a/b.yml"]
    assert topologia.composes_da_stack({"compose": ["/a/b.yml", "/a/c.yml"]}) == ["/a/b.yml", "/a/c.yml"]
    assert topologia.composes_da_stack({"compose": None}) == []
    assert topologia.composes_da_stack({}) == []


def test_stack_do_container_relativo_e_familia():
    cont = {"config_files": f"/opt/platafirma/platafirma-conhecimento/{SHA}/rag/docker-compose.yml"}
    assert topologia.stack_do_container(cont, TOPOLOGIA) == "rag"

    cont_core = {"config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml"}
    assert topologia.stack_do_container(cont_core, TOPOLOGIA) == "core"

    cont_fora = {"config_files": f"/opt/platafirma/platafirma-outro/{SHA}/docker-compose.yml"}
    assert topologia.stack_do_container(cont_fora, TOPOLOGIA) is None


def test_stack_do_container_labels_docker():
    labels = {
        "com.docker.compose.project": "platafirma-core",
        "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml",
    }
    assert topologia.stack_do_container(labels, TOPOLOGIA) == "core"


def test_duas_stacks_mesmo_compose_desempata_por_projeto_ou_retorna_none():
    # DT 288 e DT 377: quando duas stacks têm o mesmo compose, desempata pelo projeto;
    # se não bater ou não houver desempate, retorna None e nunca a primeira que casa.
    duas = [
        {"slug": "borda", "compose": "/opt/platafirma/current/harness/borda/compose.yaml"},
        {"slug": "harness-borda", "compose": "/opt/platafirma/current/harness/borda/compose.yaml"},
    ]
    cont_borda = {
        "config_files": f"/opt/platafirma/platafirma-harness/{SHA}/borda/compose.yaml",
        "projeto": "harness-borda",
    }
    assert topologia.stack_do_container(cont_borda, duas) == "harness-borda"

    cont_outro = dict(cont_borda, projeto="borda")
    assert topologia.stack_do_container(cont_outro, duas) == "borda"

    # Sem projeto ou projeto que não casa nenhuma das duas: None (acusa divergência)
    cont_sem_desempate = dict(cont_borda, projeto="desconhecido")
    assert topologia.stack_do_container(cont_sem_desempate, duas) is None

    cont_sem_projeto = {"config_files": f"/opt/platafirma/platafirma-harness/{SHA}/borda/compose.yaml"}
    assert topologia.stack_do_container(cont_sem_projeto, duas) is None


def test_alias_stack_do_conteiner():
    assert topologia.stack_do_conteiner is topologia.stack_do_container
