"""PEP reutilizável — o mesmo ponto de decisão para qualquer servidor da casa.

Extraído de `jaiminho-server/server.py` (20/08/2026, ordem do dono). Motivo: até
hoje só UM servidor tinha PEP, e por isso só UM bot tinha acesso autorizado por
sujeito. A ordem é outra — a wiki é alcançável por qualquer bot autenticado e
autorizado no PAP, independente de onde ele roda. Autorização é por SUJEITO; conta
de SO e rede não entram nesta conta.

Mora ao lado do `pdp.py` de propósito: quem já monta `PDP_DIR` (bind read-only)
ganha o PEP sem bind novo e sem cópia envelhecendo em dois lugares.

USO

    from pep import Pep
    pep = Pep(servico="wiki-mcp")
    neg = pep.autoriza(authorization_header,
                       acao="wiki_ler", tipo="wiki",
                       dominio="plataforma-wiki", alvos=["wiki:principal/Foo"])
    if neg:
        return neg          # negativa já auditada, pronta para devolver

REGRAS QUE ESTE MÓDULO NÃO NEGOCIA
  - Fail-closed: política ilegível, sujeito ausente ou JWT inválido = negado.
  - Toda decisão é auditada, permitida ou negada. Não é silenciável pelo chamador.
  - Negativa vence permissão — quem decide isso é o `pdp.decide`, não aqui.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["Pep", "Identidade"]


@dataclass(frozen=True)
class Identidade:
    """Quem o servidor enxerga. `sujeito` vazio = não autenticado."""
    sujeito: str = ""
    sub: str = ""
    azp: str = "-"
    via: str = "-"          # `oidc` ou `estatico`; entra na trilha, e é por ele
                            # que se mede quanto ainda passa pela rota de emergência.

    def __bool__(self) -> bool:
        return bool(self.sujeito)


class Pep:
    def __init__(self, servico: str,
                 pdp_dir: str | os.PathLike | None = None,
                 issuer: str | None = None,
                 jwks_url: str | None = None,
                 audience: str | None = None,
                 log_dir: str | os.PathLike | None = None):
        self.servico = servico
        self.pdp_dir = Path(pdp_dir or os.environ.get("PDP_DIR", "/opt/pf/politica-acesso"))
        self.issuer = issuer or os.environ.get(
            "OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
        self.jwks_url = jwks_url or os.environ.get(
            "OIDC_JWKS_URL", f"{self.issuer}/protocol/openid-connect/certs")
        self.audience = audience or os.environ.get("OIDC_AUDIENCE", "ops-mcp")
        self.log_dir = Path(log_dir or os.environ.get(
            "PEP_LOG_DIR", f"/var/log/{servico}"))
        self._jwks_cli = None
        self._cache: dict = {"carimbo": None, "politica": None, "sujeitos": None,
                             "erro": "nao carregada"}

    # --- auditoria ---------------------------------------------------------
    def audit(self, **campos) -> None:
        linha = {"em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "servico": self.servico, **campos}
        texto = json.dumps(linha, ensure_ascii=False, default=str)[:8000]
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            alvo = self.log_dir / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"
            with alvo.open("a", encoding="utf-8") as f:
                f.write(texto + "\n")
        except OSError:
            print(texto, file=sys.stderr)

    # --- identidade --------------------------------------------------------
    def _jwks(self):
        if self._jwks_cli is None:
            from jwt import PyJWKClient
            self._jwks_cli = PyJWKClient(self.jwks_url, cache_keys=True, lifespan=3600)
        return self._jwks_cli

    def identidade(self, authorization: str) -> Identidade:
        """Identidade vazia = não é JWT válido do realm.

        Só o header. Token em query string NÃO é aceito: query vaza em log de
        proxy, em Referer e no histórico do navegador — e o que vaza aqui é
        credencial de portador, que vale enquanto durar.
        """
        if not authorization or not authorization.startswith("Bearer "):
            return Identidade()
        tok = authorization[len("Bearer "):].strip()
        if tok.count(".") != 2:
            return Identidade()
        try:
            import jwt
            claims = jwt.decode(
                tok, self._jwks().get_signing_key_from_jwt(tok).key,
                algorithms=["RS256", "ES256"],
                audience=self.audience, issuer=self.issuer,
                options={"require": ["exp", "iat", "sub"]})
            return Identidade(
                sujeito=claims.get("preferred_username") or claims.get("sub") or "",
                sub=claims.get("sub", ""), azp=claims.get("azp", "-"), via="oidc")
        except Exception as e:                                   # noqa: BLE001
            self.audit(evento="jwt_recusado", motivo=type(e).__name__)
            return Identidade()

    # --- política ----------------------------------------------------------
    def politica(self) -> dict:
        """PAP e projeção de sujeito, relidos quando o mtime de um dos dois muda:
        merge no PAP vale sem restart."""
        pol_f, suj_f = self.pdp_dir / "politica.yaml", self.pdp_dir / "sujeitos.yaml"
        try:
            carimbo = (pol_f.stat().st_mtime_ns, suj_f.stat().st_mtime_ns)
        except OSError as e:
            self._cache.update(carimbo=None, politica=None, sujeitos=None,
                               erro=f"politica ilegivel: {e}")
            return self._cache
        if self._cache["carimbo"] == carimbo:
            return self._cache
        try:
            if str(self.pdp_dir) not in sys.path:
                sys.path.insert(0, str(self.pdp_dir))
            import yaml
            from pdp import Politica
            pol = Politica.de_arquivo(pol_f)
            suj = (yaml.safe_load(suj_f.read_text(encoding="utf-8")) or {}).get("sujeitos") or {}
            self._cache.update(carimbo=carimbo, politica=pol, sujeitos=suj, erro=None)
        except Exception as e:                                   # noqa: BLE001
            self._cache.update(carimbo=carimbo, politica=None, sujeitos=None,
                               erro=f"{type(e).__name__}: {e}")
        return self._cache

    # --- decisão -----------------------------------------------------------
    def autoriza(self, authorization: str, acao: str, tipo: str,
                 dominio: str, alvos: list[str]) -> dict | None:
        """None = pode seguir. dict = negativa auditada, pronta para devolver.

        Um recurso por alvo, e qualquer negativa nega o pedido inteiro: pedido de
        três alvos com concessão de dois não vira meio pedido — vira negativa, e o
        chamador sabe o que pedir de novo.
        """
        est = self.politica()
        if est["erro"]:
            self.audit(evento="pep_sem_politica", motivo=est["erro"])
            return {"erro": "politica de acesso indisponivel", "detalhe": est["erro"]}

        ident = self.identidade(authorization)
        if not ident:
            self.audit(evento="negado", acao=acao, motivo="sem identidade")
            return {"erro": "nao autenticado"}

        from pdp import Recurso, Sujeito, decide
        atrib = (est["sujeitos"] or {}).get(ident.sujeito) or {}
        if not atrib:
            self.audit(evento="negado", sujeito=ident.sujeito, acao=acao,
                       via=ident.via, motivo="sujeito ausente da projecao")
            return {"erro": "negado pela politica de acesso",
                    "motivo": "sujeito sem papel declarado no PAP"}

        s = Sujeito(id=ident.sujeito, natureza=atrib.get("natureza"),
                    papeis=tuple(atrib.get("papeis") or ()),
                    dominios=tuple(atrib.get("dominios") or ()),
                    habilitacao=atrib.get("habilitacao", "publico"))

        for alvo in alvos:
            d = decide(s, acao, Recurso(tipo=tipo, id=alvo, dominio=dominio),
                       est["politica"])
            if not d.permitido:
                self.audit(evento="negado", sujeito=ident.sujeito, acao=acao,
                           sobre=alvo, regra=d.regra, motivo=d.motivo,
                           azp=ident.azp, via=ident.via)
                return {"erro": "negado pela politica de acesso", "sobre": alvo,
                        "regra": d.regra, "motivo": d.motivo}
        self.audit(evento="permitido", sujeito=ident.sujeito, acao=acao,
                   sobre=alvos, azp=ident.azp, via=ident.via)
        return None
