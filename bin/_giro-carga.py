#!/home/claudinho/AI/.venv-harness/bin/python
# _giro-carga.py — deprecado: 2026-09-12 sucessor: bin/_sessao/giro-carga.py (arq:0110 §1/§11).
# A porta em execucao ainda chama ~/AI/bin/_giro-carga.py no encerrar; o codigo commitado
# ja aponta ao sucessor. Este shim fica so ate o restart da porta e se retira nesse ato.
import os, runpy
runpy.run_path(os.path.join(os.path.dirname(os.path.realpath(__file__)), "_sessao", "giro-carga.py"),
               run_name="__main__")
