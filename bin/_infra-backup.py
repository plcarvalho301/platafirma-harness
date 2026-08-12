#!/usr/bin/env python3
# _infra-backup.py — corpo de `infra backup`. Mede o declarado em registro/backups.json.
# capacidade: infra
# dono: claudinho-TI
"""Mede backup; nao faz backup e nao propoe rotina.

Tres estados existem para nao mentir por omissao: `sem-backup` e alvo declarado sem
cobertura, que fica na lista de proposito; `nao-medivel-daqui` e alvo cuja rotina roda
em conta que este usuario nao alcanca; `vazio` e diretorio declarado sem nenhum arquivo
do padrao. Alvo com `log` declarado tem a idade medida pelo log, nao pelo arquivo mais
novo: espelho com --remove nao toca mtime quando nada mudou, e a copia continua em dia. Reportar zero nos tres casos seria dizer a mesma coisa sobre situacoes
diferentes.
"""
import glob
import json
import os
import sys
import time

reg = json.load(open(os.environ["INFRA_BACKUPS_REG"], encoding="utf-8"))
como_json = "--json" in sys.argv
saida, ruim, agora = [], 0, time.time()

for nome, a in sorted((reg.get("alvos") or {}).items()):
    item = {"alvo": nome, "o_que": a.get("o_que"), "cobertura": a.get("cobertura")}
    if a.get("cobertura") == "nenhuma":
        item["estado"] = "sem-backup"
    elif a.get("alcance") == "fora":
        item["estado"] = "nao-medivel-daqui"
    else:
        d = os.path.expanduser(a.get("diretorio", ""))
        arqs = sorted(glob.glob(os.path.join(d, a.get("padrao", "*"))), key=os.path.getmtime)
        if not arqs:
            item["estado"] = "vazio"
            ruim += 1
        else:
            prova = os.path.expanduser(a["log"]) if a.get("log") else arqs[-1]
            if not os.path.exists(prova):
                prova = arqs[-1]
            idade = (agora - os.path.getmtime(prova)) / 86400
            item.update(geracoes=len(arqs), idade_dias=round(idade, 1),
                        ultimo=os.path.basename(arqs[-1]),
                        bytes=sum(os.path.getsize(f) for f in arqs))
            item["estado"] = "ok" if idade < 2 else "atrasado"
            if idade >= 2:
                ruim += 1
    saida.append(item)

if como_json:
    print(json.dumps({"alvos": saida}, ensure_ascii=False))
else:
    for i in saida:
        estado = i["estado"]
        if estado in ("ok", "atrasado"):
            mb = i["bytes"] / 1048576
            det = "{} geracoes, ultima ha {}d, {:.0f} MB".format(
                i["geracoes"], i["idade_dias"], mb)
        elif estado == "sem-backup":
            det = "declarado sem cobertura — nao propor rotina, ver card #176"
        elif estado == "nao-medivel-daqui":
            det = "roda em conta que este usuario nao alcanca"
        else:
            det = "diretorio declarado nao tem nenhum arquivo do padrao"
        print("{:<18} {:<16} {}".format(estado, i["alvo"], det))

sys.exit(1 if ruim else 0)
