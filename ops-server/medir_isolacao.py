#!/usr/bin/env python3
"""Medicao da isolacao de conta no host: o ato `seg isolacao medir`.

Sucede `ops-server/test_exec_conta_host.py` (aceite do #3007), tirado da suite do
harness em 27/09/2026 porque teste de codigo nao le estado real do host. A medicao e a
mesma; muda o dono (seguranca, por decisao do dono em 27/09/2026) e a natureza: aqui e
ato contra o host de verdade, com resultado registrado.

Mede pelo MESMO argv da producao (`exec_conta.argv_sob_conta` e `argv_escrita`) e pela
mesma regra de sudoers que a porta ja usa. Nenhum privilegio novo: se o despacho da
porta mudar de forma, esta medicao passa a medir a forma nova junto.

O que mede, por conta:
  uid      o comando sai sob o uid da conta, e nao sob o da porta
  owner    o arquivo que a conta escreve nasce com o owner dela
  casa     a conta NAO escreve na casa da plataforma; a isolacao e de mao unica e,
           se quebrar, quebra calada: tudo continua funcionando
  lateral  a conta NAO escreve na home da porta nem na das outras contas medidas
  env      o env do uid da porta nao atravessa; o da fita (PF_SESSAO) atravessa

Veredito pela regra de exit da casa: 0 tudo medido e conforme; 1 alguma isolacao
quebrou; 5 algo nao foi medido (conta inexistente, travessia negada). 5 nunca vira 0:
verde por vacuidade e a aparencia do controle sem o controle.

Nao e o pentest de `seg:0010` (escape de conta designada, com travessia lateral,
executado e registrado). E a verificacao de configuracao que segura o desenho entre um
pentest e outro, e o registro dela e consultavel em $SEG_LOG_DIR/isolacao-<data>.jsonl.
"""
import datetime
import json
import os
import pwd
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exec_conta import argv_escrita, argv_sob_conta, env_sob_conta, erro_de_conta  # noqa: E402

# As contas de modelo da spec agente §2 (Gemini sob jaiminho, Qwen sob quinzinho). Conta
# segregada nova entra aqui no mesmo ato que a admite (seg:0011 item 6). Medido em
# 30/09/2026: modulo-osint nao existe mais no host.
CONTAS_PADRAO = ("jaiminho", "quinzinho")

OK, FALHA, NAO_MEDIDO = "ok", "FALHA", "NAO MEDIDO"


def _rodar(argv, entrada=None):
    cp = subprocess.run(argv, input=entrada, capture_output=True, timeout=30, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _conta_info(conta):
    try:
        p = pwd.getpwnam(conta)
    except KeyError:
        return None
    return p.pw_uid, p.pw_dir


def _txt(b):
    return (b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")).strip()


def medir(contas, rodar=_rodar, conta_info=_conta_info, raiz_casa=None,
          uid_porta=None, home_porta=None, marca=None):
    """Lista de (estado, conta, verificacao, detalhe). Puro: o host entra por `rodar`
    e `conta_info`, para o teste de contrato rodar sem sudo e sem contas reais."""
    raiz_casa = raiz_casa or os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa")
    uid_porta = os.getuid() if uid_porta is None else uid_porta
    if home_porta is None:
        home_porta = pwd.getpwuid(uid_porta).pw_dir
    marca = marca or "isolacao-%d" % os.getpid()
    env_porta = {"PATH": "/usr/bin:/bin", "PF_SESSAO": marca,
                 "XDG_RUNTIME_DIR": "/run/user/%d" % uid_porta}

    infos = {c: conta_info(c) for c in contas}
    res = []

    for conta in contas:
        info = infos[conta]
        if info is None:
            res.append((NAO_MEDIDO, conta, "conta", "nao existe neste host"))
            continue
        uid, home = info
        if uid == uid_porta:
            res.append((NAO_MEDIDO, conta, "conta", "e a conta da propria porta"))
            continue
        env = env_sob_conta(env_porta, conta, home)

        def sob(argv, entrada=None, _c=conta, _e=env):
            return rodar(argv_sob_conta(argv, _c, _e), entrada)

        rc, out, err = sob(["id", "-u"])
        if rc != 0:
            motivo = erro_de_conta(rc, err) or _txt(err) or "exit %d" % rc
            res.append((NAO_MEDIDO, conta, "travessia", motivo[:200]))
            continue

        # uid
        visto = _txt(out)
        res.append((OK if visto == str(uid) else FALHA, conta, "uid",
                    "saiu sob %s, esperado %d" % (visto, uid)))

        # owner
        dir_probe = "%s/.probe-%s" % (home, marca)
        alvo = "%s/owner.txt" % dir_probe
        rc, _, err = sob(argv_escrita(alvo), b"medicao de isolacao\n")
        if rc != 0:
            res.append((NAO_MEDIDO, conta, "owner",
                        "a conta nao escreveu na propria home: %s" % _txt(err)[:160]))
        else:
            try:
                rc, out, err = sob(["stat", "-c", "%u", alvo])
                visto = _txt(out)
                if rc != 0:
                    res.append((NAO_MEDIDO, conta, "owner", _txt(err)[:160]))
                else:
                    res.append((OK if visto == str(uid) else FALHA, conta, "owner",
                                "owner no disco %s, esperado %d" % (visto, uid)))
            finally:
                sob(["rm", "-rf", dir_probe])

        # casa (mao unica)
        alvo = "%s/.probe-%s-%s" % (raiz_casa, marca, conta)
        rc, _, _ = sob(["touch", alvo])
        if rc == 0 or os.path.exists(alvo):
            res.append((FALHA, conta, "casa", "a conta escreveu em %s" % raiz_casa))
            sob(["rm", "-f", alvo])
        else:
            res.append((OK, conta, "casa", "negado em %s" % raiz_casa))

        # lateral
        vizinhas = [("porta", home_porta)] + [
            (c, infos[c][1]) for c in contas if c != conta and infos[c] is not None]
        for nome, casa_alheia in vizinhas:
            alvo = "%s/.probe-%s-%s" % (casa_alheia, marca, conta)
            rc, _, _ = sob(["touch", alvo])
            if rc == 0:
                res.append((FALHA, conta, "lateral",
                            "a conta escreveu na home de %s (%s)" % (nome, casa_alheia)))
                sob(["rm", "-f", alvo])
            else:
                res.append((OK, conta, "lateral", "negado na home de %s" % nome))

        # env
        rc, out, err = sob(["bash", "-c", 'echo "${XDG_RUNTIME_DIR:-vazio} ${PF_SESSAO:-vazio}"'])
        partes = _txt(out).split()
        if rc != 0 or len(partes) != 2:
            res.append((NAO_MEDIDO, conta, "env", _txt(err)[:160] or "saida inesperada"))
        else:
            xdg, sessao = partes
            if xdg != "vazio":
                res.append((FALHA, conta, "env", "runtime dir do uid da porta atravessou"))
            elif sessao != marca:
                res.append((FALHA, conta, "env", "PF_SESSAO nao atravessou: a auditoria perde a fita"))
            else:
                res.append((OK, conta, "env", "porta nao atravessa, fita atravessa"))

    return res


def veredito(res):
    estados = {r[0] for r in res}
    if FALHA in estados:
        return 1
    if NAO_MEDIDO in estados or not res:
        return 5
    return 0


def _registrar(res, codigo, contas):
    log_dir = os.environ.get("SEG_LOG_DIR") or os.path.join(
        os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"), "var/log/seg")
    try:
        os.makedirs(log_dir, exist_ok=True)
        agora = datetime.datetime.now().astimezone()
        linha = {"em": agora.isoformat(timespec="seconds"), "ato": "isolacao medir",
                 "contas": list(contas), "exit": codigo,
                 "resultados": [dict(zip(("estado", "conta", "verificacao", "detalhe"), r))
                                for r in res]}
        with open(os.path.join(log_dir, "isolacao-%s.jsonl" % agora.date().isoformat()),
                  "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return None
    except OSError as e:
        return "registro nao gravado em %s: %s" % (log_dir, e)


def main(argv):
    contas = argv or tuple(os.environ.get("SEG_CONTAS_ISOLADAS", "").split()) or CONTAS_PADRAO
    res = medir(contas)
    codigo = veredito(res)
    n = {e: sum(1 for r in res if r[0] == e) for e in (OK, FALHA, NAO_MEDIDO)}
    rotulo = {0: "CONFORME", 1: "QUEBRADA", 5: "INCOMPLETA - nao vale como conforme"}[codigo]
    print("isolacao de conta: %s · %d ok, %d falha, %d nao medido · contas: %s"
          % (rotulo, n[OK], n[FALHA], n[NAO_MEDIDO], " ".join(contas)))
    for estado, conta, verif, detalhe in res:
        print("%-10s %-14s %-9s %s" % (estado, conta, verif, detalhe))
    aviso = _registrar(res, codigo, contas)
    if aviso:
        print(aviso, file=sys.stderr)
    return codigo


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
