#!/home/claudinho/AI/.venv-harness/bin/python
# prova-guarda-por-id — criterio 18 da minuta 0002: ritual atrasado nao esmaga.
# capacidade: memoria
# dono: claudinho-IA
#
# Encena a corrida que a rotacao produz: o ritual da fita velha termina DEPOIS
# de a fita nova ter anotado a mesa. Sem a guarda, a escrita atrasada sobrescreve
# — e a fita nova acorda com a mesa da anterior. Roda contra a instancia msg-mem
# real, em cadeira ficticia, e limpa o que criou.
import os
import subprocess
import sys

CADEIRA = "prova-449"
MESA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "mesa")
FALHAS = []


def mesa(*args, fita=None, entrada=None):
    env = dict(os.environ, PF_CADEIRA=CADEIRA)
    env.pop("PF_FITA", None)
    if fita:
        env["PF_FITA"] = fita
    r = subprocess.run([MESA, *args], input=entrada, env=env,
                       capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def confere(nome, condicao, detalhe=""):
    print(f"  {'ok  ' if condicao else 'FALHA'} {nome}{'' if condicao else '  <- ' + detalhe}")
    if not condicao:
        FALHAS.append(nome)


print("prova: guarda por id na escrita de mesa")
try:
    _, velha, _ = mesa("fita", "abre")
    confere("abre devolve id", bool(velha), "stdout vazio")

    rc, _, _ = mesa("anota", "contexto", fita=velha, entrada="mesa da fita velha")
    confere("fita corrente escreve", rc == 0, f"rc={rc}")

    # rotacao: fita nova assume o slot, e so entao o ritual da velha termina
    _, nova, _ = mesa("fita", "abre")
    confere("fita nova assume o slot", nova != velha, "id repetido")
    rc, _, _ = mesa("anota", "contexto", fita=nova, entrada="mesa da fita NOVA")
    confere("fita nova escreve", rc == 0, f"rc={rc}")

    rc, _, err = mesa("anota", "contexto", fita=velha, entrada="ritual atrasado da velha")
    confere("ritual atrasado e recusado", rc == 3, f"rc={rc}")
    confere("recusa e declarada, nao silenciosa", "DESCARTADA" in err, err or "stderr vazio")

    _, saida, _ = mesa("ver", "contexto")
    confere("mesa preservou a escrita da fita nova", "fita NOVA" in saida, saida[:80])

    # sem PF_FITA a guarda nao se aplica: sessao de mao nao trava
    rc, _, _ = mesa("anota", "contexto", entrada="sessao de mao, sem fita")
    confere("sem PF_FITA escreve como sempre", rc == 0, f"rc={rc}")

    # fechar so vale para quem e a corrente
    rc, _, _ = mesa("fita", "fecha", "--id", velha)
    confere("fecha de fita velha e recusado", rc == 3, f"rc={rc}")
    rc, _, _ = mesa("fita", "fecha", "--id", nova)
    confere("fecha da corrente funciona", rc == 0, f"rc={rc}")
    _, saida, _ = mesa("fita")
    confere("sem fita, ausencia e declarada", "nenhuma" in saida, saida)
finally:
    mesa("limpa", "contexto")
    mesa("fita", "fecha", "--id", "limpeza")

print(f"\n{len(FALHAS)} falha(s)" if FALHAS else "\ntudo passou")
sys.exit(1 if FALHAS else 0)
