#!/usr/bin/env python3
# _acesso-desligar — motor dos sub-atos `desligar` e `orfaos` do verbo `acesso`.
# capacidade: acesso
# dono: claudinho-seguranca
#
# Existe porque desligar um sujeito eram quatro operacoes manuais em quatro lugares
# (realm, sujeitos.yaml, PAP, segredo em disco) e nada media resíduo: a entrada tinha
# gate e a saida nao tinha. Regua: seg:0011 item 7.
#
# NAO COMMITA e NAO faz deploy. Edita arquivo do PAP e apaga segredo; o commit e do
# chamador, para que o diff passe por olho humano antes de virar historico.
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

RAIZ = Path(os.environ.get("ACESSO_PDP_DIR", Path.home() / "AI/platafirma-harness/politica-acesso"))
SUJEITOS = RAIZ / "sujeitos.yaml"
POLITICA = RAIZ / "politica.yaml"
HARNESS = RAIZ.parent
PERSONAS = HARNESS / "personas"
SEG = Path.home() / "AI/bin/seg"
VENCE = re.compile(r"vence\s+(\d{4}-\d{2}-\d{2})")


def carrega(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def sujeitos() -> dict:
    return carrega(SUJEITOS).get("sujeitos") or {}


def regras() -> list:
    return carrega(POLITICA).get("regras") or []


# --------------------------------------------------------------------------- órfãos
def kcadm(*args: str) -> tuple[int, str]:
    """kcadm por `seg keycloak`. Credencial nao configurada NAO vira medida — vira
    'nao medido', que e diferente de 'nada encontrado'."""
    try:
        r = subprocess.run([str(SEG), "keycloak", "--", *args],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, f"{type(e).__name__}: {e}"
    return r.returncode, (r.stdout or r.stderr).strip()


def cmd_orfaos(argv: list[str]) -> int:
    achados: list[tuple[str, str]] = []
    suj = sujeitos()
    hoje = date.today()

    # 1. Concessao vencida: o prazo do seg:0009 §7 esta no `motivo`, e ate hoje
    #    ninguem o lia. Vencido, a regra tem de sair por merge.
    for r in regras():
        m = VENCE.search(str(r.get("motivo") or ""))
        if m and date.fromisoformat(m.group(1)) < hoje:
            achados.append(("concessao vencida",
                            f"regra {r['id']} venceu em {m.group(1)} e continua no PAP"))

    # 2. Regra que aponta caixa de quem nao existe (sujeito nem persona).
    # A caixa e `claudinho-<sufixo>`, o arquivo e `persona-<sufixo>.md`: casa por sufixo.
    personas = {p.stem.replace("persona-", "") for p in PERSONAS.glob("persona-*.md")}
    for r in regras():
        for alvo in r.get("sobre") or ():
            if isinstance(alvo, str) and alvo.startswith("caixa:"):
                nome = alvo.split(":", 1)[1]
                if nome not in suj and not any(nome.endswith(f"-{p}") or nome == p
                                               for p in personas):
                    achados.append(("regra sem titular",
                                    f"regra {r['id']} alcanca {alvo}, que nao e sujeito nem persona"))

    # 3. Sujeito que nao se sabe desligar: sem `client` nem `conta`, o desligamento
    #    nao tem alvo, e a falta so apareceria no dia do desligamento.
    for nome, a in suj.items():
        a = a or {}
        if not (a.get("client") or a.get("conta") or a.get("usuario")):
            achados.append(("desligamento sem alvo",
                            f"sujeito {nome} nao declara `client:`, `usuario:` nem `conta:`"))
        for s in a.get("segredos") or ():
            if not Path(os.path.expanduser(s)).exists():
                achados.append(("segredo declarado sem lastro",
                                f"sujeito {nome} aponta {s}, que nao existe"))

    # 4. Conta de SO sem sujeito. uid >= 1000, fora das de sistema.
    try:
        for linha in Path("/etc/passwd").read_text().splitlines():
            c = linha.split(":")
            if len(c) > 5 and c[0] != "nobody" and 1000 <= int(c[2]) < 65000:
                if c[0] not in suj and not any((s or {}).get("conta") == c[0] for s in suj.values()):
                    achados.append(("conta sem sujeito",
                                    f"conta de SO {c[0]} (uid {c[2]}) nao tem sujeito no PAP"))
    except (OSError, ValueError) as e:
        achados.append(("nao medido", f"contas de SO: {e}"))

    # 5. Realm: client habilitado para sujeito que saiu do PAP.
    #    Realm nao alcancado NAO e "nada encontrado": e medicao incompleta, e reprova
    #    duro no fim (exit 2). #163/#418: contagem parcial fechou card falso.
    realm_medido = True
    if "--sem-realm" in argv:
        realm_medido = False
        print("realm: NAO MEDIDO (--sem-realm)")
    else:
        rc, saida = kcadm("get", "clients", "-r", "platafirma",
                          "--fields", "clientId,serviceAccountsEnabled")
        if rc != 0:
            realm_medido = False
            print("realm: NAO MEDIDO — kcadm nao alcancou o realm nesta sessao")
        else:
            # So service account e ATOR, logo sujeito. Client de aplicacao e relying
            # party — o usuario atua atraves dele, e quem responde e o usuario.
            declarados = {(s or {}).get("client") for s in suj.values()}
            import json as _json
            try:
                lista = _json.loads(saida)
            except ValueError:
                lista = []
            for c in lista:
                cid = c.get("clientId")
                if c.get("serviceAccountsEnabled") and cid not in declarados:
                    achados.append(("service account sem sujeito",
                                    f"client {cid} atua no realm e nenhum sujeito o declara"))

    # 6. Auditoria contra projecao: quem ATUOU nos ultimos dias e nao esta declarado,
    #    e credencial declarada que nao atuou nenhuma vez. Os dois sao superficie sem
    #    funcao — um por baixo do PAP, outro sobrando no realm.
    import json as _json
    logs = sorted((Path.home() / "AI/var/log/ops").glob("ops-*.jsonl"))[-int(os.environ.get("ACESSO_DIAS", 7)):]
    vistos_sujeito, vistos_azp = set(), set()
    for arq in logs:
        for linha in arq.read_text(errors="replace").splitlines():
            try:
                d = _json.loads(linha)
            except ValueError:
                continue
            if d.get("sujeito"):
                vistos_sujeito.add(str(d["sujeito"]).lower())
            if d.get("azp"):
                vistos_azp.add(str(d["azp"]))
    declarados = {n.lower() for n in suj}
    for quem in sorted(vistos_sujeito - declarados - {"-", "desconhecido"}):
        achados.append(("sujeito sem projecao",
                        f"{quem} atuou nos ultimos {len(logs)} dia(s) e nao esta em sujeitos.yaml"))
    for nome, a in suj.items():
        cid = (a or {}).get("client")
        if cid and cid not in vistos_azp:
            achados.append(("credencial dormente",
                            f"client {cid} ({nome}) nao atuou nos ultimos {len(logs)} dia(s)"))

    if achados:
        largura = max(len(c) for c, _ in achados)
        for classe, texto in achados:
            print(f"{classe.ljust(largura)}  {texto}")
        print(f"\n{len(achados)} achado(s) — cada um e ato pendente, nao aviso")
    # Veredito no EXIT, nao no meio do relatorio: realm nao medido reprova duro.
    if not realm_medido:
        print("\nREPROVADO: realm NAO medido — resultado INCOMPLETO, nao vale como "
              "'sem orfaos'. exit 2 (medicao incompleta), distinto de 0/1.")
        return 2
    if not achados:
        print("nenhum residuo: sujeito, regra, segredo e conta em dia")
        return 0
    return 1


# --------------------------------------------------------------------------- desligar
def bloco_do_sujeito(texto: str, nome: str) -> tuple[int, int] | None:
    """Linhas do bloco `  <nome>:` dentro de `sujeitos:`, com o comentario colado
    acima. Edicao por texto porque yaml.dump apagaria todo comentario do arquivo."""
    linhas = texto.splitlines(keepends=True)
    ini = None
    for i, l in enumerate(linhas):
        if re.match(rf"^  {re.escape(nome)}:\s*$", l):
            ini = i
            break
    if ini is None:
        return None
    fim = len(linhas)
    for j in range(ini + 1, len(linhas)):
        if re.match(r"^  \S", linhas[j]) or re.match(r"^\S", linhas[j]):
            fim = j
            break
    while ini > 0 and linhas[ini - 1].lstrip().startswith("#"):
        ini -= 1
    while fim > ini and not linhas[fim - 1].strip():
        fim -= 1
    return ini, fim


def bloco_da_regra(texto: str, rid: str) -> tuple[int, int] | None:
    linhas = texto.splitlines(keepends=True)
    ini = None
    for i, l in enumerate(linhas):
        if re.match(rf"^  - id:\s*{re.escape(rid)}\s*$", l):
            ini = i
            break
    if ini is None:
        return None
    fim = len(linhas)
    for j in range(ini + 1, len(linhas)):
        if re.match(r"^  - id:", linhas[j]) or re.match(r"^\S", linhas[j]):
            fim = j
            break
    while fim > ini and not linhas[fim - 1].strip():
        fim -= 1
    return ini, fim


def cmd_desligar(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("uso: acesso desligar <sujeito> [--executar]", file=sys.stderr)
        return 2
    nome, executar = argv[0], "--executar" in argv
    suj = sujeitos()
    if nome not in suj:
        print(f"acesso: {nome} nao e sujeito em sujeitos.yaml", file=sys.stderr)
        return 1
    a = suj[nome] or {}
    client, conta = a.get("client"), a.get("conta")
    segredos = [Path(os.path.expanduser(s)) for s in (a.get("segredos") or ())]
    alvo_regras = [r["id"] for r in regras()
                   if any(isinstance(x, str) and x == f"caixa:{nome}" for x in (r.get("sobre") or ()))]

    plano = [
        ("realm", f"desabilitar client {client}" if client else
                  "NADA A FAZER — sujeito nao declara `client:`"),
        ("sujeitos.yaml", f"remover o bloco `{nome}:`"),
        ("PAP", f"remover regra(s): {', '.join(alvo_regras)}" if alvo_regras else
                "nenhuma regra aponta caixa deste sujeito"),
        ("segredo", "\n            ".join(f"apagar {s}" for s in segredos) if segredos else
                    "NADA DECLARADO — confira `segredos:` antes de confiar nesta linha"),
    ]
    print(f"desligamento de {nome}" + (conta and f" (conta de SO {conta}: ato do dono, fora daqui)" or ""))
    for passo, o_que in plano:
        print(f"  {passo.ljust(14)} {o_que}")
    if not executar:
        print("\nplano medido, nada executado. Repita com --executar.")
        return 0

    falhou = []
    # 1. realm
    if client:
        rc, saida = kcadm("get", "clients", "-r", "platafirma", "-q", f"clientId={client}",
                          "--fields", "id")
        uuid = re.search(r'"id"\s*:\s*"([^"]+)"', saida) if rc == 0 else None
        if not uuid:
            falhou.append(f"realm: client {client} nao resolvido ({saida[:120]})")
        else:
            rc, saida = kcadm("update", f"clients/{uuid.group(1)}", "-r", "platafirma",
                              "-s", "enabled=false")
            print(f"  realm          client {client} desabilitado" if rc == 0
                  else f"  realm          FALHOU: {saida[:160]}")
            if rc != 0:
                falhou.append(f"realm: {saida[:120]}")

    # 2. sujeitos.yaml
    texto = SUJEITOS.read_text(encoding="utf-8")
    faixa = bloco_do_sujeito(texto, nome)
    if faixa:
        linhas = texto.splitlines(keepends=True)
        SUJEITOS.write_text("".join(linhas[:faixa[0]] + linhas[faixa[1]:]), encoding="utf-8")
        print(f"  sujeitos.yaml  bloco `{nome}` removido ({faixa[1] - faixa[0]} linhas)")
    else:
        falhou.append("sujeitos.yaml: bloco nao localizado por texto")

    # 3. PAP
    if alvo_regras:
        texto = POLITICA.read_text(encoding="utf-8")
        for rid in alvo_regras:
            faixa = bloco_da_regra(texto, rid)
            if not faixa:
                falhou.append(f"PAP: regra {rid} nao localizada por texto")
                continue
            linhas = texto.splitlines(keepends=True)
            texto = "".join(linhas[:faixa[0]] + linhas[faixa[1]:])
            print(f"  PAP            regra {rid} removida")
        POLITICA.write_text(texto, encoding="utf-8")

    # 4. segredo
    for s in segredos:
        try:
            s.unlink()
            print(f"  segredo        {s} apagado")
        except OSError as e:
            falhou.append(f"segredo {s}: {e}")

    # 5. o PAP tem de continuar valido depois da cirurgia.
    r = subprocess.run([str(Path.home() / "AI/bin/acesso"), "politica", "conferir"],
                       capture_output=True, text=True)
    print(f"  conferencia    {(r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else 'sem saida'}")
    if r.returncode != 0:
        falhou.append("PAP invalido depois da edicao — reverta pelo git antes de qualquer commit")

    print(f"\n{datetime.now():%Y-%m-%d %H:%M} — desligamento de {nome}")
    if falhou:
        for f in falhou:
            print(f"  PENDENTE  {f}")
        print("  git: NAO commitado. Resolva o pendente antes.")
        return 1
    print("  git: NAO commitado — o diff e seu, o commit tambem.")
    print("  Falta o ato do dono: conta de SO e custodia do segredo fora do host.")
    return 0


if __name__ == "__main__":
    sub = sys.argv[1] if len(sys.argv) > 1 else ""
    if sub == "orfaos":
        sys.exit(cmd_orfaos(sys.argv[2:]))
    if sub == "desligar":
        sys.exit(cmd_desligar(sys.argv[2:]))
    print("uso: _acesso-desligar.py {orfaos|desligar <sujeito> [--executar]}", file=sys.stderr)
    sys.exit(2)
