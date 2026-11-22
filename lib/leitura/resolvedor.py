"""resolvedor.py — da chave à ficha, e da ficha ao arquivo na morada (story 4426).

Contrato: platafirma-casa@referencias/instancias/interface-de-verbo/busca.md, «Leitura pela chave»,
e platafirma-casa@referencias/instancias/componente/leitor-universal.md, «As moradas que lê».

- A classe sai da ficha no cadastro (casa.ficha.classe), e não do texto antes dos dois-pontos.
- `<classe>` e `<classe>:` leem a ficha da classe, `shape:<classe>`. No cadastro a ficha de uma
  classe tem a chave humana igual ao slug (`sessao`), e por isso `shape:<x>` também chega nela.
- O caminho sai do molde da classe: o golden de tipo casa antes da referência; o golden de outro
  tipo não é arquivo. O molde se corta na primeira vírgula e só monta caminho quando termina em
  .md e a parte fixa termina na pasta da classe; o resto da chave, depois do primeiro dois-pontos,
  entra no lugar dos marcadores, com os dois-pontos seguintes trocados por barra.
- A morada é a que casa.estrutura_de_documento declara para a classe; sem linha, a referência
  mora em git, que é a release. Só `git` se lê aqui: o arquivo da casa na release servida.
- Sem molde que monte caminho, com morada que não é git ou com o arquivo ausente na release, a
  leitura devolve a ficha inteira, como o cadastro a guarda.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

CLASSE_DAS_CLASSES = "shape"
MORADA_LIDA = "git"

SQL_FICHA = """
SELECT f.uuid::text AS uuid, f.chave_humana AS chave, c.slug AS classe, c.uuid::text AS classe_uuid
  FROM casa.ficha f JOIN casa.shape c ON c.uuid = f.classe
 WHERE f.chave_humana = $1
"""

# O molde do caminho e a morada da classe: o golden, a referência e a estrutura de documento.
SQL_MOLDE = """
SELECT 'golden' AS fonte, g.tipo AS tipo, g.endereco AS endereco
  FROM casa.golden g WHERE g.ficha = $1::uuid
UNION ALL
SELECT 'referencia', NULL, r.endereco
  FROM casa.referencia r WHERE r.ficha = $1::uuid
UNION ALL
SELECT 'estrutura', e.regime, e.morada
  FROM casa.estrutura_de_documento e WHERE e.shape = $1::uuid AND e.encerra_em IS NULL
"""

# A ficha inteira, como o cadastro a guarda: dados vigentes e ligações vigentes por propriedade
# e, quando a ficha é uma classe, a declaração dela em casa.shape.
SQL_FICHA_INTEIRA = """
SELECT jsonb_build_object(
         'chave', f.chave_humana,
         'classe', c.slug,
         'criada_em', f.criada_em,
         'dados', coalesce((
            SELECT jsonb_object_agg(x.slug, x.valores)
              FROM (SELECT p.slug, jsonb_agg(coalesce(d.valor, to_jsonb(d.valor_de_dicionario)) ORDER BY d.id) AS valores
                      FROM casa.dado d
                      JOIN casa.restricao r ON r.id = d.restricao
                      JOIN casa.propriedade p ON p.id = r.propriedade
                     WHERE d.ficha = f.uuid AND d.terminou IS NULL
                     GROUP BY p.slug) x), '{}'::jsonb),
         'ligacoes', coalesce((
            SELECT jsonb_object_agg(y.slug, y.para)
              FROM (SELECT p.slug, jsonb_agg(t.chave_humana ORDER BY l.posicao NULLS LAST, t.chave_humana) AS para
                      FROM casa.ligacao l
                      JOIN casa.propriedade p ON p.id = l.propriedade
                      JOIN casa.ficha t ON t.uuid = l.para
                     WHERE l.de = f.uuid AND l.terminou IS NULL
                     GROUP BY p.slug) y), '{}'::jsonb),
         'declaracao', (SELECT jsonb_strip_nulls(to_jsonb(s) - 'uuid' - 'fornada')
                          FROM casa.shape s WHERE s.uuid = f.uuid)
       ) AS ficha
  FROM casa.ficha f JOIN casa.shape c ON c.uuid = f.classe
 WHERE f.uuid = $1::uuid
"""

_MARCADORES = re.compile(r"<[^<>/]+>(?:[/-]<[^<>/]+>)*")
_SEGMENTO = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Consulta(Protocol):
    def consultar(self, sql: str, *parametros: Any) -> list[dict]: ...


@dataclass(frozen=True)
class Ficha:
    uuid: str
    chave: str
    classe: str
    classe_uuid: str

    @property
    def e_classe(self) -> bool:
        return self.classe == CLASSE_DAS_CLASSES

    @property
    def chave_lida(self) -> str:
        """A chave no cabeçalho: a ficha de uma classe se lê como shape:<classe>."""
        return f"{CLASSE_DAS_CLASSES}:{self.chave}" if self.e_classe else self.chave


@dataclass(frozen=True)
class Alvo:
    ficha: Ficha
    caminho: Path | None      # o arquivo na morada; None: a ficha inteira
    documento: str | None     # o caminho relativo à casa na release
    motivo: str               # por que é arquivo ou ficha inteira


def ficha(retrato: Consulta, chave: str) -> Ficha | None:
    linhas = retrato.consultar(SQL_FICHA, chave)
    return Ficha(**linhas[0]) if linhas else None


def ficha_da_chave(retrato: Consulta, chave: str) -> Ficha | None:
    """A ficha que a chave aponta: a chave humana exata, ou `<classe>:` e `shape:<classe>`."""
    achada = ficha(retrato, chave)
    if achada is not None:
        return achada
    candidata = None
    if chave.endswith(":") and ":" not in chave[:-1]:
        candidata = chave[:-1]
    elif chave.startswith(f"{CLASSE_DAS_CLASSES}:"):
        candidata = chave[len(CLASSE_DAS_CLASSES) + 1:]
    if not candidata:
        return None
    achada = ficha(retrato, candidata)
    return achada if achada is not None and achada.e_classe else None


def caminho_do_molde(molde: str, f: Ficha) -> tuple[str | None, str]:
    """(caminho relativo, motivo); o caminho é None quando o molde não monta arquivo para a chave."""
    m = molde.split(",", 1)[0].strip()
    if not m.endswith(".md") or "<" not in m:
        return None, "molde-sem-arquivo"
    fixo = m[: m.index("<")]
    resto = m[len(fixo): -len(".md")]
    if not fixo.endswith(f"/{f.classe}/") or not _MARCADORES.fullmatch(resto):
        return None, "molde-nao-entendido"
    slug = f.chave.split(":", 1)[1] if ":" in f.chave else f.chave
    partes = slug.split(":")
    if not all(_SEGMENTO.fullmatch(p) and ".." not in p for p in partes):
        return None, "chave-fora-do-molde"
    if len(partes) != resto.count("/") + 1:
        return None, "chave-nao-cabe-no-molde"
    return fixo + "/".join(partes) + ".md", "molde"


def _molde_da_classe(linhas: list[dict]) -> tuple[str | None, str]:
    golden = [ln for ln in linhas if ln["fonte"] == "golden"]
    referencia = [ln for ln in linhas if ln["fonte"] == "referencia"]
    for ln in golden:
        if ln["tipo"] == "casa":
            return ln["endereco"], "golden"
    for ln in referencia:
        return ln["endereco"], "referencia"
    if golden:
        return None, f"golden-de-tipo-{golden[0]['tipo']}"
    return None, "classe-sem-documento"


def casa_na_release(release: Path) -> Path:
    """A casa na release servida: <raiz da release>/current/casa."""
    return Path(release) / "current" / "casa"


def resolver(retrato: Consulta, f: Ficha, release: Path) -> Alvo:
    """O arquivo da ficha na morada que a classe declara, ou a ficha inteira."""
    linhas = retrato.consultar(SQL_MOLDE, f.classe_uuid)
    molde, fonte = _molde_da_classe(linhas)
    if molde is None:
        return Alvo(f, None, None, fonte)
    estrutura = [ln for ln in linhas if ln["fonte"] == "estrutura"]
    morada = estrutura[0]["endereco"] if estrutura else MORADA_LIDA
    if morada != MORADA_LIDA:
        return Alvo(f, None, None, f"morada-{morada}-nao-lida")
    rel, motivo = caminho_do_molde(molde, f)
    if rel is None:
        return Alvo(f, None, None, motivo)
    base = casa_na_release(release)
    alvo = base / rel
    base_real = os.path.realpath(base)
    if not os.path.realpath(alvo).startswith(base_real.rstrip(os.sep) + os.sep):
        return Alvo(f, None, None, "caminho-fora-da-morada")
    if not alvo.is_file():
        return Alvo(f, None, rel, "arquivo-ausente-na-release")
    return Alvo(f, alvo, rel, fonte)


def ficha_inteira(retrato: Consulta, f: Ficha) -> dict:
    linhas = retrato.consultar(SQL_FICHA_INTEIRA, f.uuid)
    return linhas[0]["ficha"] if linhas else {}
