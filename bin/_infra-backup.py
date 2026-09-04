#!/usr/bin/env python3
# _infra-backup.py — corpo de `infra backup`. Mede o declarado em registro/backups.json.
# capacidade: infra
# dono: claudinho-TI
"""Mede backup; nao faz backup e nao propoe rotina.

Tres estados existem para nao mentir por omissao: `sem-backup` e alvo declarado sem
cobertura, que fica na lista de proposito; `nao-medivel-daqui` e alvo cuja rotina roda
em conta que este usuario nao alcanca; `vazio` e diretorio declarado sem nenhum arquivo
do padrao OU cujo conteudo real soma zero bytes (mirror que espelhou nada). Alvo com
`log` declarado tem a idade medida pelo log, nao pelo arquivo mais novo: espelho com
--remove nao toca mtime quando nada mudou, e a copia continua em dia. Reportar zero nos
tres casos seria dizer a mesma coisa sobre situacoes diferentes.

O tamanho e medido pelo CONTEUDO real, recursivo: o mirror do minio guarda os objetos em
subdirs por bucket, entao somar so a entrada de topo (o diretorio) media ~0 e assinava
"ok, 0 MB" para um backup que podia estar vazio. `_bytes` desce na arvore; conteudo real
zero cai em `vazio` e falha ruidoso, em vez de assinar ok. Card #2987 / DT #2861.
"""
import glob
import json
import os
import sys
import time


def _bytes(p):
    """Bytes reais de conteudo. Diretorio soma recursivo; arquivo e o proprio tamanho.
    Mede o que foi COPIADO, nao a entrada de diretorio."""
    if os.path.isdir(p):
        t = 0
        for raiz, _dirs, arquivos in os.walk(p):
            for f in arquivos:
                try:
                    t += os.path.getsize(os.path.join(raiz, f))
                except OSError:
                    pass
        return t
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


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
        total = sum(_bytes(f) for f in arqs)
        if not arqs or total == 0:
            item["estado"] = "vazio"
            ruim += 1
        else:
            prova = os.path.expanduser(a["log"]) if a.get("log") else arqs[-1]
            if not os.path.exists(prova):
                prova = arqs[-1]
            idade = (agora - os.path.getmtime(prova)) / 86400
            item.update(geracoes=len(arqs), idade_dias=round(idade, 1),
                        ultimo=os.path.basename(arqs[-1]),
                        bytes=total)
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
            det = "diretorio declarado sem arquivo do padrao ou com conteudo real de 0 bytes"
        print("{:<18} {:<16} {}".format(estado, i["alvo"], det))

sys.exit(1 if ruim else 0)
