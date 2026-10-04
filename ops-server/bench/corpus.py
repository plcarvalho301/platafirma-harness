"""corpus.py — o corpus do bench de leitura (spec ler-arquivo §16.2, card #3263).

Três partes, e nenhuma lê estado do host:

1. arquivos VERSIONADOS do próprio repositório (`git ls-files -z` na raiz da árvore que se
   promove), por extensão e por faixa de tamanho; até CINCO por célula, na ordem do sha256 do
   caminho; célula vazia vai ao relatório como vazia;
2. as fixtures da §14 (multibyte, linha longa, cp1252, byte inválido, binário, vazio) mais uma
   de 300 KB sem quebra de linha, e a de T5 (arquivo que muda no meio da leitura), geradas em
   diretório temporário, sempre com os mesmos bytes;
3. a árvore de T7, com as quatro formas de erro de caminho da §9 (pai que existe, avô que
   existe, nome parecido no diretório certo, diretório lido como arquivo).

Faixas em bytes, com KB = 1.000 (a mesma conta da página de 40.000 da spec).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

EXTENSOES = (".py", ".md", ".json", ".yaml", ".sh", ".sql", ".txt", ".toml")
# (nome, tamanho máximo incluído). A última não tem teto.
FAIXAS = (("ate-10KB", 10_000), ("10-200KB", 200_000), ("acima-200KB", None))
POR_CELULA = 5


def faixa_de(tamanho: int) -> str:
    for nome, teto in FAIXAS:
        if teto is None or tamanho <= teto:
            return nome
    return FAIXAS[-1][0]


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


@dataclass
class Arquivo:
    nome: str            # caminho relativo à raiz (repo) ou `fixture:<nome>`
    caminho: Path
    origem: str          # "repo" | "fixture"
    tipo: str            # extensão sem ponto (repo) ou `fix:<nome>` (fixture)
    faixa: str
    bytes: int
    sha256: str          # do conteúdo
    texto: bool = True   # entra em T1 e T4; binário e vazio só em T6


@dataclass
class Corpus:
    arquivos: list[Arquivo]                       # repo + fixtures (o que T1 lê)
    fixtures: dict[str, Path]                     # nome -> caminho (inclui `mudanca`)
    arvore_erros: dict[str, Path]                 # forma -> caminho a ler
    arvore_esperado: dict[str, Path]              # forma -> ancestral que deve voltar
    celulas: dict[str, int] = field(default_factory=dict)   # "ext/faixa" -> quantos entraram
    celulas_vazias: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ 1. o repositório
def _chave_sha(caminho: str) -> str:
    return hashlib.sha256(caminho.encode("utf-8")).hexdigest()


def versionados(raiz: Path = RAIZ) -> tuple[list[Arquivo], dict[str, int], list[str]]:
    """(arquivos escolhidos, contagem por célula, células vazias). Ordem de cada célula: sha256
    do caminho relativo, em hexadecimal, crescente. Só arquivo comum (symlink fica de fora)."""
    saida = subprocess.run(["git", "ls-files", "-z"], cwd=raiz, capture_output=True, check=True)
    nomes = sorted(n for n in saida.stdout.decode("utf-8", "surrogateescape").split("\0") if n)
    celulas: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for nome in nomes:
        p = raiz / nome
        ext = p.suffix.lower()
        if ext not in EXTENSOES or p.is_symlink() or not p.is_file():
            continue
        tam = p.stat().st_size
        celulas.setdefault((ext, faixa_de(tam)), []).append((nome, tam))
    escolhidos, contagem, vazias = [], {}, []
    for ext in EXTENSOES:
        for faixa, _teto in FAIXAS:
            ordem = sorted(celulas.get((ext, faixa), []), key=lambda x: _chave_sha(x[0]))
            pegos = ordem[:POR_CELULA]
            chave = f"{ext}/{faixa}"
            contagem[chave] = len(pegos)
            if not pegos:
                vazias.append(chave)
            for nome, tam in pegos:
                p = raiz / nome
                dados = p.read_bytes()
                escolhidos.append(Arquivo(nome=nome, caminho=p, origem="repo",
                                          tipo=ext.lstrip("."), faixa=faixa, bytes=len(dados),
                                          sha256=sha256_bytes(dados)))
    return escolhidos, contagem, vazias


# ------------------------------------------------------------------ 2. as fixtures
def _multibyte() -> bytes:
    # Linhas de 11, 16, 25 e 17 bytes (2, 3 e 4 bytes por caractere): 69 bytes por volta, e
    # 40.000 não é múltiplo de nenhum limite de caractere, então o corte por bytes parte um.
    ciclo = "aé日😀\nç ã õ — ü\n日本語のテキスト\n𝄞𝄢😀🎼\n"
    return (ciclo * 2_000).encode("utf-8")


def _linha_longa() -> bytes:
    itens, n = [], 0
    while True:
        itens.append({"id": n, "nome": f"item-{n:05d}", "valor": n * 7, "ativo": n % 2 == 0})
        n += 1
        dados = json.dumps({"versao": 1, "itens": itens, "meta": {"origem": "bench"}},
                           ensure_ascii=False, separators=(",", ":"))
        if len(dados) >= 60_000:
            return (dados + "\n").encode("utf-8")


def _cp1252() -> bytes:
    return ("coração, ação, não, é só — açúcar e café\n" * 40).replace("—", "-") \
        .encode("cp1252")


def _utf8_com_byte_invalido() -> bytes:
    base = ("Pão de açúcar, café e ônibus — ação e emoção\n" * 2_500).encode("utf-8")
    corte = base.index(b"\n", 70_000) + 1          # começo de linha: não parte caractere
    return base[:corte] + b"\xff" + base[corte:]


def _binario() -> bytes:
    # ELF, e não PDF: desde a emenda de 04/10/2026 (spec §7.4) o PDF se lê pela porta, e o
    # binário que T6 mede é o de tipo fora da tabela, que recusa com `sem_leitor`.
    return b"\x7fELF\x02\x01\x01\x00" + bytes(range(256)) * 8


def _sem_quebra() -> bytes:
    return (b"lorem ipsum dolor sit amet " * 12_000)[:300_000]


def _mudanca() -> bytes:
    # 100 linhas de 990 bytes: a primeira página (40.000) deixa continuação.
    return b"".join(f"{i:04d} ".encode() + b"palavra " * 123 + b"\n" for i in range(1, 101))


# nome -> (conteúdo, entra em T1/T4)
def _definicoes() -> dict[str, tuple[bytes, bool]]:
    return {"multibyte": (_multibyte(), True), "linha_longa": (_linha_longa(), True),
            "cp1252": (_cp1252(), True), "byte_invalido": (_utf8_com_byte_invalido(), True),
            "sem_quebra": (_sem_quebra(), True), "binario": (_binario(), False),
            "vazio": (b"", False), "mudanca": (_mudanca(), False)}


def fixtures(destino: Path) -> tuple[dict[str, Path], list[Arquivo]]:
    destino.mkdir(parents=True, exist_ok=True)
    caminhos, arquivos = {}, []
    for nome, (dados, texto) in _definicoes().items():
        p = destino / f"{nome}.bin" if nome in ("binario", "vazio") else \
            destino / (f"{nome}.json" if nome == "linha_longa" else f"{nome}.txt")
        p.write_bytes(dados)
        caminhos[nome] = p
        if texto:
            arquivos.append(Arquivo(nome=f"fixture:{nome}", caminho=p, origem="fixture",
                                    tipo=f"fix:{nome}", faixa=faixa_de(len(dados)),
                                    bytes=len(dados), sha256=sha256_bytes(dados)))
    return caminhos, arquivos


def conteudo_original(nome: str) -> bytes:
    """Os bytes de origem de uma fixture (T5 a restaura entre as repetições)."""
    return _definicoes()[nome][0]


# ------------------------------------------------------------------ 3. a árvore de T7
def arvore_de_erros(destino: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """(forma -> caminho a ler, forma -> ancestral que `existe_ate` deve nomear)."""
    raiz = destino / "arvore"
    pai = raiz / "pai"
    docs = raiz / "docs"
    pai.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    for nome in ("leitura.py", "poda.py", "notas.txt", "server.py"):
        (pai / nome).write_text(f"# {nome}\n", encoding="utf-8")
    (docs / "readme.md").write_text("# docs\n", encoding="utf-8")
    ler = {"pai_existe": pai / "ausente.py",
           "avo_existe": pai / "inexistente" / "arquivo.py",
           "nome_parecido": pai / "leiture.py",
           "diretorio": docs}
    esperado = {"pai_existe": pai, "avo_existe": pai, "nome_parecido": pai, "diretorio": docs}
    return ler, esperado


def monta(destino: Path, raiz: Path = RAIZ) -> Corpus:
    repo, celulas, vazias = versionados(raiz)
    caminhos, fix = fixtures(destino / "fixtures")
    ler, esperado = arvore_de_erros(destino / "erros")
    return Corpus(arquivos=repo + fix, fixtures=caminhos, arvore_erros=ler,
                  arvore_esperado=esperado, celulas=celulas, celulas_vazias=vazias)
