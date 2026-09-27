"""alcance — os 5 saltos da cadeia de acesso sujeito->fonte (card #3153).

Modulo unico: `lint alcance` e `conferir alcance` chamam `cadeia_de_alcance` daqui e so
diferem na forma de dizer. MEDIDOR, nao validador: onde o alvo nao tem ACL canonica
(portao paralelo que nao conhece papel nem dominio), DECLARA — nao presume um canon
inexistente. As 5 fontes-de-verdade (claudinho-seguranca, card #2452 sob #191):
  identidade -> politica-acesso/sujeitos.yaml
  credencial -> politica-acesso/sujeitos.yaml (client/conta/usuario/segredos) [+ realm]
  PDP        -> politica-acesso/politica.yaml
  rede       -> politica-acesso/superficies.yaml::ingress
  ACL        -> politica-acesso/superficies.yaml::portao
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from .resultado import Apontamento


def _carrega_yaml(caminho: str) -> tuple[Optional[dict], Optional[str]]:
    try:
        import yaml
    except Exception as e:  # noqa: BLE001
        return None, f"pyyaml ausente: {e}"
    try:
        with open(caminho, encoding="utf-8") as fh:
            return (yaml.safe_load(fh) or {}), None
    except OSError as e:
        return None, str(e)


def politica_dir_padrao() -> str:
    """Onde a politica de acesso mora: PDP_DIR, senao <bancada>/var/politica-acesso
    (dados fora da worktree de fabrica, #2956)."""
    if os.environ.get("PDP_DIR"):
        return os.environ["PDP_DIR"]
    bancada = os.environ.get("PLATAFIRMA_BANCADA") or os.path.expanduser("~/AI")
    return os.path.join(bancada, "var", "politica-acesso")


def cadeia_de_alcance(
    sujeito: str, fonte: str, harness_dir: str, politica_dir: str
) -> dict[str, Any]:
    """Mede a cadeia e devolve um dict:
      estado  : conforme | divergente | indeterminavel
      motivo  : por que (None quando conforme)
      saltos  : [(salto, valor, detalhe, fonte-de-verdade)]
      elo     : (salto, motivo) do elo mais fraco, ou None
      nota    : aviso de imposicao (ACL fraca / a medir), ou None
      fechou  : False quando a fonte nao esta no catalogo de superficies
    """
    for p in (harness_dir, politica_dir):
        if p and p not in sys.path:
            sys.path.insert(0, p)
    try:
        from recuperacao.pep import PEP
        from recuperacao.fontes import Fonte
    except Exception as e:  # noqa: BLE001
        return {"estado": "indeterminavel",
                "motivo": f"maquinario de acesso ilegivel — {type(e).__name__}: {e}",
                "saltos": [], "elo": None, "nota": None, "fechou": False}
    try:
        f = Fonte(fonte)
    except ValueError:
        validas = ", ".join(x.value for x in Fonte)
        return {"estado": "indeterminavel",
                "motivo": f"fonte {fonte!r} nao existe — validas: {validas}",
                "saltos": [], "elo": None, "nota": None, "fechou": False}

    suj_doc, _ = _carrega_yaml(os.path.join(politica_dir, "sujeitos.yaml"))
    atrib = ((suj_doc or {}).get("sujeitos") or {}).get(sujeito) or {}
    cat_doc, _ = _carrega_yaml(os.path.join(politica_dir, "superficies.yaml"))
    sup = ((cat_doc or {}).get("superficies") or {}).get(fonte)

    pep = PEP()
    neg = pep.autoriza_fonte(sujeito, f)
    acao = pep.acao(f)

    saltos = []

    # 1 identidade
    if atrib:
        papeis = ",".join(atrib.get("papeis") or ()) or "(sem papel)"
        saltos.append(("identidade", "PASSA",
                       f"projetado em sujeitos.yaml (natureza={atrib.get('natureza', '?')}, papeis={papeis})",
                       "politica-acesso/sujeitos.yaml"))
        id_ok = True
    else:
        saltos.append(("identidade", "QUEBRA",
                       f"sujeito {sujeito!r} ausente da projecao — fail-closed; o PDP nega por atributo ausente",
                       "politica-acesso/sujeitos.yaml"))
        id_ok = False

    # 2 credencial
    locus = [f"{k}={atrib[k]}" for k in ("client", "conta", "usuario", "segredos") if atrib.get(k)]
    if not atrib:
        saltos.append(("credencial", "n/a", "sujeito nao projetado — nada onde ancorar credencial",
                       "politica-acesso/sujeitos.yaml (+ realm keycloak)"))
        cred_ok = False
    elif locus:
        saltos.append(("credencial", "PASSA",
                       "locus: " + ", ".join(locus) + " [realm keycloak: declarado, nao medido aqui]",
                       "politica-acesso/sujeitos.yaml (+ realm keycloak)"))
        cred_ok = True
    else:
        saltos.append(("credencial", "QUEBRA",
                       "projetado sem client/conta/usuario/segredos — sem credencial para autenticar",
                       "politica-acesso/sujeitos.yaml (+ realm keycloak)"))
        cred_ok = False

    # 3 PDP
    if neg is None:
        saltos.append(("PDP", "PERMITE", f"a regra permite; acao={acao}", "politica-acesso/politica.yaml"))
        pdp_estado = "PERMITE"
    elif neg.regra in ("projecao", "identidade"):
        saltos.append(("PDP", "nao avaliado",
                       f"sujeito ausente da projecao ({neg.regra}) — a decisao nem chega ao PDP",
                       "politica-acesso/politica.yaml"))
        pdp_estado = "nao avaliado"
    else:
        saltos.append(("PDP", "NEGA", f"regra={neg.regra}, acao={acao} — {neg.motivo}",
                       "politica-acesso/politica.yaml"))
        pdp_estado = "NEGA"

    # 4 rede + 5 ACL do alvo
    if sup is None:
        saltos.append(("rede", "indeterminavel", f"fonte {fonte!r} ausente de superficies.yaml — a medir",
                       "politica-acesso/superficies.yaml"))
        saltos.append(("ACL do alvo", "indeterminavel", "sem entrada no catalogo de superficies",
                       "politica-acesso/superficies.yaml"))
        rede_ok = None
        acl: Any = "faltando"
    else:
        alc = sup.get("alcancavel")
        detalhe_rede = f"{sup.get('ingress', '?')} — {sup.get('rede', '')}"
        if alc is True or alc == "loopback":
            marca = "ALCANCA (loopback)" if alc == "loopback" else "ALCANCA"
            saltos.append(("rede", marca, detalhe_rede, "politica-acesso/superficies.yaml::ingress"))
            rede_ok = True
        else:
            saltos.append(("rede", "BLOQUEIA", detalhe_rede, "politica-acesso/superficies.yaml::ingress"))
            rede_ok = False
        acl = sup.get("acl_canonica")
        portao = sup.get("portao", "")
        if acl is True:
            saltos.append(("ACL do alvo", "CANONICA", portao, "politica-acesso/superficies.yaml::portao"))
        elif acl is False:
            saltos.append(("ACL do alvo", "FRACA", "portao paralelo, NAO impoe o PDP — " + portao,
                           "politica-acesso/superficies.yaml::portao"))
        else:
            saltos.append(("ACL do alvo", "A MEDIR", portao, "politica-acesso/superficies.yaml::portao"))

    # elo mais fraco da cadeia modelada: identidade -> credencial -> PDP -> rede
    elo = None
    if not id_ok:
        elo = ("identidade", "sujeito ausente da projecao")
    elif not cred_ok:
        elo = ("credencial", "sem credencial declarada")
    elif pdp_estado == "NEGA":
        elo = ("PDP", f"regra {neg.regra} nega")
    elif rede_ok is False:
        elo = ("rede", "fonte nao alcancavel")

    if rede_ok is None:
        estado, motivo = "indeterminavel", f"{fonte!r} nao esta no catalogo de superficies; a cadeia nao fecha."
    elif elo is None:
        estado, motivo = "conforme", None
    else:
        estado, motivo = "divergente", f"elo mais fraco: {elo[0]} — {elo[1]}"

    # nota de imposicao: divergencia entre o veredito do PDP e o que o portao impoe
    nota = None
    if acl is False:
        if pdp_estado == "NEGA":
            nota = ("[RISCO] o PDP NEGA mas a ACL do alvo e FRACA (portao paralelo): a negativa "
                    "pode NAO ser imposta no alvo — possivel bypass. Achado do #191.")
        else:
            nota = ("[AVISO] ACL do alvo FRACA: o portao nao impoe o PDP; o veredito acima nao e "
                    "garantido pelo alvo. Achado do #191.")
    elif acl is None:
        nota = "[AVISO] ACL do alvo A MEDIR: o gate do alvo existe mas nao foi lido (#191)."

    return {"estado": estado, "motivo": motivo, "saltos": saltos, "elo": elo,
            "nota": nota, "fechou": rede_ok is not None}


def verificar_alcance(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """`lint alcance <repo> "<sujeito> <fonte>"`: um apontamento por salto que quebra, e
    um pela nota de imposicao. Relata, nao reprova: severidade aviso."""
    if not alvo:
        return []
    tokens = alvo.split()
    if len(tokens) < 2:
        return [Apontamento(
            "politica-acesso", 1,
            f"alvo de alcance deve ser '<sujeito> <fonte>', recebido: '{alvo}'",
            "informar sujeito e fonte validos (ex: ti board)",
            severidade="aviso",
        )]
    sujeito, fonte = tokens[0], tokens[1]
    c = cadeia_de_alcance(sujeito, fonte, str(raiz), politica_dir_padrao())
    apontamentos: list[Apontamento] = []
    if not c["saltos"]:
        apontamentos.append(Apontamento(
            "politica-acesso", 1, f"alcance {sujeito} -> {fonte}: {c['motivo']}",
            "conferir o maquinario de acesso e o nome da fonte", severidade="aviso", id="ALCANCE",
        ))
        return apontamentos
    for salto, valor, detalhe, fonte_verdade in c["saltos"]:
        if valor in ("QUEBRA", "NEGA", "BLOQUEIA", "FRACA", "indeterminavel"):
            apontamentos.append(Apontamento(
                fonte_verdade.split(" ", 1)[0], 1,
                f"alcance {sujeito} -> {fonte}, salto {salto}: {valor} — {detalhe}",
                f"corrigir em {fonte_verdade}", severidade="aviso", id="ALCANCE",
            ))
    if c["nota"]:
        apontamentos.append(Apontamento(
            "politica-acesso/superficies.yaml", 1, c["nota"],
            "impor o PDP no portao do alvo", severidade="aviso", id="ALCANCE",
        ))
    return apontamentos
