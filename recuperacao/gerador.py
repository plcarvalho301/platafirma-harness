"""Gerador da descrição da tool `recuperar` a partir da tabela de fontes do catálogo.

`spec_recuperador.md` §7: "Um gerador lê essa tabela e emite a descrição da tool no build.
Fonte nova aparece no roteamento; fonte que sai, some. Nenhuma linha se escreve à mão
antes de o gerador existir."
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
from pathlib import Path


class ErroTabelaFontes(ValueError):
    """Erro de validação na tabela de fontes do catálogo."""
    pass


@dataclasses.dataclass(frozen=True)
class FonteInfo:
    slug: str
    capacidade: str
    dono: str
    transporte: str
    classe: str
    contrato_de_leitura: str
    gold: str
    linha_num: int


def _acha_catalogo_padrao() -> Path:
    raiz = Path(__file__).resolve().parent.parent
    cand = raiz / "docs" / "catalogo-de-fontes.md"
    if cand.is_file():
        return cand
    cand_ai = Path(os.path.expanduser("~/AI/platafirma-harness/docs/catalogo-de-fontes.md"))
    if cand_ai.is_file():
        return cand_ai
    return cand


def le_tabela_fontes(caminho: Path | str | None = None, texto: str | None = None) -> list[FonteInfo]:
    """Lê e valida estritamente a tabela `Fontes da plataforma` de docs/catalogo-de-fontes.md.

    Parser estrito: linha malformada, coluna a mais/menos, classe fora de exata|semantica
    falham levantando ErroTabelaFontes com o número da linha e o defeito identificado.
    """
    if texto is None:
        if caminho is None:
            caminho = _acha_catalogo_padrao()
        caminho = Path(caminho)
        if not caminho.is_file():
            raise FileNotFoundError(f"catálogo de verbos não encontrado em {caminho}")
        texto = caminho.read_text(encoding="utf-8")

    linhas = texto.splitlines()

    inicio = -1
    for idx, l in enumerate(linhas):
        if re.match(r"^##\s+Fontes da plataforma", l.strip()):
            inicio = idx
            break

    if inicio == -1:
        return []

    tabela_linhas: list[tuple[int, str]] = []
    for idx in range(inicio + 1, len(linhas)):
        l = linhas[idx]
        if l.startswith("## ") and not l.strip().startswith("## Fontes da plataforma"):
            break
        if l.strip().startswith("|"):
            tabela_linhas.append((idx + 1, l.strip()))

    if not tabela_linhas:
        return []

    num_linha_hdr, hdr_linha = tabela_linhas[0]
    colunas_hdr = [c.strip().lower() for c in hdr_linha.strip("|").split("|")]
    if not colunas_hdr or not any("fonte" in c for c in colunas_hdr):
        raise ErroTabelaFontes(f"linha {num_linha_hdr}: cabeçalho da tabela de fontes inválido: {hdr_linha}")

    num_cols_esperado = len(colunas_hdr)
    if num_cols_esperado != 7:
        raise ErroTabelaFontes(
            f"linha {num_linha_hdr}: esperadas 7 colunas no cabeçalho (fonte, capacidade, dono, transporte, classe, contrato de leitura, gold), encontradas {num_cols_esperado}"
        )

    dados_linhas: list[tuple[int, str]] = []
    for num_l, l in tabela_linhas[1:]:
        celulas = [c.strip() for c in l.strip("|").split("|")]
        if all(re.match(r"^:?-+:?$", c) for c in celulas if c):
            continue
        dados_linhas.append((num_l, l))

    fontes: list[FonteInfo] = []
    for num_l, l in dados_linhas:
        partes = [c.strip() for c in l.strip("|").split("|")]
        if len(partes) != num_cols_esperado:
            raise ErroTabelaFontes(
                f"linha {num_l}: esperadas {num_cols_esperado} colunas, encontradas {len(partes)}"
            )

        raw_fonte, capacidade, dono, transporte, classe, contrato, gold = partes

        if not raw_fonte:
            raise ErroTabelaFontes(f"linha {num_l}: coluna 'fonte' vazia")

        slug = raw_fonte.split("·")[0].split("(")[0].split()[0].strip().lower().replace("`", "")
        if not slug:
            raise ErroTabelaFontes(f"linha {num_l}: slug inválido na coluna fonte: {raw_fonte!r}")

        classe_norm = classe.strip().lower().replace("`", "")
        if classe_norm not in ("exata", "semantica"):
            raise ErroTabelaFontes(
                f"linha {num_l}: classe {classe!r} inválida (deve ser 'exata' ou 'semantica')"
            )

        if not capacidade:
            raise ErroTabelaFontes(f"linha {num_l}: campo 'capacidade' vazio")
        if not dono:
            raise ErroTabelaFontes(f"linha {num_l}: campo 'dono' vazio")
        if not transporte:
            raise ErroTabelaFontes(f"linha {num_l}: campo 'transporte' vazio")
        if not contrato:
            raise ErroTabelaFontes(f"linha {num_l}: campo 'contrato de leitura' vazio")
        if not gold:
            raise ErroTabelaFontes(f"linha {num_l}: campo 'gold' vazio")

        fontes.append(
            FonteInfo(
                slug=slug,
                capacidade=capacidade,
                dono=dono,
                transporte=transporte,
                classe=classe_norm,
                contrato_de_leitura=contrato,
                gold=gold,
                linha_num=num_l,
            )
        )

    return fontes


def gera_descricao_tool(fontes: list[FonteInfo]) -> str:
    """Emite a descrição da tool `recuperar` no build a partir das fontes indexadas.

    spec_recuperador.md §7: Emite o índice das fontes (slug, classe, capacidade, dono, contrato).
    Nenhuma linha pergunta-para-fonte é redigida à mão.
    """
    linhas = [
        "Recupera estado da plataforma consultando fontes declaradas.",
        "Fontes disponíveis:",
    ]
    for f in fontes:
        linhas.append(f"- {f.slug} ({f.classe}): capacidade {f.capacidade}, dono {f.dono} — {f.contrato_de_leitura}")
    return "\n".join(linhas)


def conta_tokens(texto: str) -> int | None:
    """Mede tokens com o tokenizador do harness (qwen2.5.json) se disponível."""
    candidatos = [
        Path(__file__).resolve().parent.parent.parent / "opt" / "tokenizers" / "qwen2.5.json",
        Path(os.path.expanduser("~/AI/opt/tokenizers/qwen2.5.json")),
    ]
    tok_path = next((p for p in candidatos if p.is_file()), None)
    if not tok_path:
        return None
    try:
        from tokenizers import Tokenizer
        return len(Tokenizer.from_file(str(tok_path)).encode(texto).ids)
    except Exception:
        return None


def emite_artefato(
    caminho_catalogo: Path | str | None = None,
    destino_txt: Path | str | None = None,
    destino_json: Path | str | None = None,
) -> tuple[str, dict]:
    """Emite os artefatos de descrição no build."""
    fontes = le_tabela_fontes(caminho=caminho_catalogo)
    desc = gera_descricao_tool(fontes)
    tokens = conta_tokens(desc)

    raiz = Path(__file__).resolve().parent
    if destino_txt is None:
        destino_txt = raiz / "descricao_tool.txt"
    if destino_json is None:
        destino_json = raiz / "descricao.json"

    Path(destino_txt).write_text(desc + "\n", encoding="utf-8")

    dado = {
        "descricao": desc,
        "tokens": tokens,
        "fontes": [
            {
                "slug": f.slug,
                "capacidade": f.capacidade,
                "dono": f.dono,
                "transporte": f.transporte,
                "classe": f.classe,
                "contrato_de_leitura": f.contrato_de_leitura,
                "gold": f.gold,
            }
            for f in fontes
        ],
    }
    Path(destino_json).write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return desc, dado


def _carrega_descricao_estatica() -> str:
    """Lê o artefato versionado gerado no build. Fallback para geração a partir do catálogo."""
    txt_path = Path(__file__).resolve().parent / "descricao_tool.txt"
    if txt_path.is_file():
        return txt_path.read_text(encoding="utf-8").strip()
    try:
        fontes = le_tabela_fontes()
        return gera_descricao_tool(fontes)
    except Exception:
        return "Recupera estado da plataforma consultando fontes declaradas."


DESCRICAO_TOOL = _carrega_descricao_estatica()


if __name__ == "__main__":
    desc, dado = emite_artefato()
    print("Descrição gerada para tool recuperar:")
    print(desc)
    print(f"\nTokens medidos (qwen2.5): {dado.get('tokens')}")
