# componente: componente:diagrama
"""Conjunto de casos de comportamento do componente diagrama: esqueleto, esquemas, medida, tokens, grade, receita, renderização, checagem, lint e juízes."""
from __future__ import annotations

import copy
import itertools
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagrama import checagem, grade, juizes, medida, receita
from diagrama import tokens as tk
from diagrama.__main__ import USO, main as diagrama_main
from diagrama.checagem import checar_plano_svg, checar_svg
from diagrama.lint import lint_plano
from diagrama.renderizar import (
    _caminho_inter,
    _extrair_textos,
    main as renderizar_main,
    para_o_mupdf,
    png_do_svg,
    renderizar_arquivo,
    renderizar_dados,
)

HARNESS_RAIZ = Path(__file__).resolve().parents[2]
RAIZ_ESPELHO = Path(__file__).resolve().parents[4]
BASE_SKILL = HARNESS_RAIZ / "skills" / "diagrama"
BASE_EXEMPLOS = BASE_SKILL / "exemplo"
TIPOS = ["alocacao", "camada", "modulo", "componente-e-conector", "fluxo"]


# ==============================================================================================
# Seção 1 — Esqueleto e registro
# ==============================================================================================


def test_ajuda_lista_cinco_atos():
    assert "lint" in USO
    assert "renderizar" in USO
    assert "checar" in USO
    assert "conferir-plano" in USO
    assert "conferir-figura" in USO
    assert diagrama_main(["--help"]) == 0


def test_registro_declara_diagrama_no_harness():
    registro_py = HARNESS_RAIZ / "bin" / "_release" / "registro.py"
    venvs_json = HARNESS_RAIZ / "registro" / "venvs.json"
    env = {"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(venvs_json)}
    r_diag = subprocess.run(
        ["python3", str(registro_py), "diagrama"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_diag.returncode == 0, r_diag.stderr
    assert r_diag.stdout.strip() == "platafirma-harness\tvenv:rag\tlib/diagrama\tcodigo\tdiagrama\t-"


# ==============================================================================================
# Seção 2 — Esquemas e exemplos
# ==============================================================================================


@pytest.fixture
def plano_schema():
    return json.loads((BASE_SKILL / "plano.schema.json").read_text(encoding="utf-8"))


@pytest.fixture
def fonte_schema():
    return json.loads((BASE_SKILL / "fonte.schema.json").read_text(encoding="utf-8"))


def test_exemplos_de_plano_validam(plano_schema):
    for tipo in TIPOS:
        arq = BASE_EXEMPLOS / f"{tipo}.plano.json"
        assert arq.is_file(), f"faltou {arq}"
        dados = json.loads(arq.read_text(encoding="utf-8"))
        jsonschema.validate(dados, plano_schema)


def test_exemplos_de_fonte_validam(fonte_schema):
    for tipo in TIPOS:
        arq = BASE_EXEMPLOS / f"{tipo}.fonte.json"
        assert arq.is_file(), f"faltou {arq}"
        dados = json.loads(arq.read_text(encoding="utf-8"))
        jsonschema.validate(dados, fonte_schema)


def _uma_caixa(**extra):
    caixa = {"id": "a", "titulo": "Capacidade", "tipo": "capacidade", "faixa": "f", "coluna": 1, "ordem": 1}
    caixa.update(extra)
    return {"tipo": "alocacao", "titulo": "Neutra", "arestas": [], "faixas": [{"id": "f"}], "elementos": [caixa]}


def test_fonte_aceita_caixa_sem_categoria(fonte_schema):
    jsonschema.validate(_uma_caixa(), fonte_schema)


@pytest.mark.parametrize("campo", ["faixa", "coluna", "ordem"])
def test_fonte_recusa_caixa_sem_posicao(fonte_schema, campo):
    dados = _uma_caixa()
    del dados["elementos"][0][campo]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dados, fonte_schema)


def test_fonte_recusa_coluna_zero_e_lado_desconhecido(fonte_schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_uma_caixa(coluna=0), fonte_schema)
    dados = _uma_caixa()
    dados["arestas"] = [{"de": "a", "para": "a", "rotulo": "x", "sai": "norte"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dados, fonte_schema)


def test_so_a_seta_tracejada_dispensa_o_rotulo(fonte_schema):
    dados = _uma_caixa()
    dados["arestas"] = [{"de": "a", "para": "a", "tracejada": True}]
    jsonschema.validate(dados, fonte_schema)
    for seta in ({"de": "a", "para": "a"}, {"de": "a", "para": "a", "tracejada": False}):
        dados["arestas"] = [seta]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(dados, fonte_schema)


def test_fonte_sem_faixas_e_recusada(fonte_schema):
    dados = _uma_caixa()
    del dados["faixas"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dados, fonte_schema)


def test_recusas_falham_no_esquema(plano_schema):
    d1 = json.loads((BASE_EXEMPLOS / "recusa-sem-rotulo.plano.json").read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d1, plano_schema)

    d2 = json.loads((BASE_EXEMPLOS / "recusa-tipo-invalido.plano.json").read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d2, plano_schema)


# ==============================================================================================
# Seção 3 — Medida de texto na Inter
# ==============================================================================================

MEDIDAS = [
    ("Capacidade", 600, 92.43),
    ("Capacidade", 400, 90.53),
    ("Recompensa", 600, 100.38),
    ("fiz do jeito de sempre", 400, 163.57),
    ("Tool na porta ou chamada de processo", 600, 299.31),
]


@pytest.mark.parametrize("texto,peso,real", MEDIDAS)
def test_largura_fica_a_2_por_cento_da_medida_da_fonte(texto, peso, real):
    assert medida.largura(texto, 16, peso) == pytest.approx(real, rel=0.02)


def test_largura_escala_com_o_tamanho():
    assert medida.largura("Busca", 32, 600) == pytest.approx(2 * medida.largura("Busca", 16, 600))


def test_peso_mais_pesado_mede_mais():
    assert medida.largura("Capacidade", 16, 600) > medida.largura("Capacidade", 16, 400)


def test_peso_fora_da_tabela_usa_o_mais_proximo():
    assert medida.largura("Verbo", 16, 650) == medida.largura("Verbo", 16, 600)
    assert medida.largura("Verbo", 16, "500") == medida.largura("Verbo", 16, 500)


def test_caractere_fora_da_tabela_mede_o_n():
    assert medida.largura("中", 16, 400) == medida.largura("n", 16, 400)


def test_texto_vazio_mede_zero():
    assert medida.largura("", 16, 400) == 0


def test_quebrar_respeita_o_maximo():
    texto = "nível 1 · a busca é a nuclear, as outras de suporte"
    linhas = medida.quebrar(texto, 12, 500, 120)
    assert len(linhas) > 1
    assert " ".join(linhas) == texto
    assert all(medida.largura(l, 12, 500) <= 120 for l in linhas)


def test_quebrar_deixa_palavra_longa_sozinha():
    linhas = medida.quebrar("a Supercalifragilístico b", 16, 400, 40)
    assert linhas == ["a", "Supercalifragilístico", "b"]


def test_quebrar_parte_a_palavra_composta_depois_do_hifen():
    assert medida.quebrar("Control-plane", 16, 600, 100) == ["Control-", "plane"]
    assert medida.quebrar("Control-plane", 16, 600, 200) == ["Control-plane"]
    assert medida.quebrar("o Control-plane do core", 16, 600, 100) == ["o Control-", "plane do", "core"]


def test_subida_e_descida_somam_mais_que_o_tamanho():
    assert medida.subida(16) + medida.descida(16) > 16


# ==============================================================================================
# Seção 4 — Tokens e checagens de cor, efeito, fio, família e peso
# ==============================================================================================

CSS = """
:root {
  --platafirma-violet-ink: #5b21b6;
  --platafirma-dark-violet-ink: #c4b5fd;
  --platafirma-gray-900: #111827;
  --platafirma-dark-fg-body: #e5e7eb;
  --platafirma-diagram-stroke: light-dark(var(--platafirma-gray-900), var(--platafirma-dark-fg-body));
  --platafirma-family-1-stroke: light-dark(var(--platafirma-violet-ink), var(--platafirma-dark-violet-ink));
  --platafirma-family-1-glyph: '▲';
  --platafirma-size-250: 0.875rem;
  --platafirma-diagram-label-floor: var(--platafirma-size-250);
  --platafirma-line-strong: 1.5px;
  --platafirma-diagram-border-width: var(--platafirma-line-strong);
  --platafirma-brinde: var(--platafirma-ausente, #abc);
}
"""

PLANO_TOKEN = {"entidades": [{"id": "a", "nome": "Serviço A"}], "relacoes": []}


@pytest.fixture
def tokens(tmp_path):
    css = tmp_path / "tokens.css"
    css.write_text(CSS, encoding="utf-8")
    return tk.carregar(css)


def test_resolve_light_dark_e_var_encadeados(tokens):
    assert tk.cor("diagram-stroke", tokens) == "#111827"
    assert tk.cor("diagram-stroke", tokens, escuro=True) == "#e5e7eb"
    assert tk.cor("family-1-stroke", tokens) == "#5b21b6"


def test_var_com_reserva_e_glifo(tokens):
    assert tk.cor("brinde", tokens) == "#aabbcc"
    assert tk.resolver("family-1-glyph", tokens).strip("'\"") == "▲"


def test_tamanho_em_px(tokens):
    assert tk.px(tk.resolver("diagram-label-floor", tokens)) == 14
    assert tk.px(tk.resolver("diagram-border-width", tokens)) == 1.5


def test_token_que_nao_existe_sai_com_erro(tokens):
    with pytest.raises(KeyError):
        tk.resolver("nao-existe", tokens)


def test_paleta_traz_as_cores_dos_dois_temas(tokens):
    p = tk.paleta(tokens)
    assert {"#111827", "#e5e7eb", "#5b21b6", "#c4b5fd"} <= p


def test_tokens_da_release_resolvem_as_oito_familias():
    t = tk.carregar()
    for n in range(1, 9):
        f = tk.familia(t, n)
        assert f["stroke"].startswith("#") and "glyph" not in f
    assert tk.px(tk.resolver("diagram-label-floor", t)) == 14


@pytest.fixture
def figura(tmp_path):
    t = tk.carregar()
    tinta = tk.cor("diagram-stroke", t)
    plano = tmp_path / "plano.json"
    plano.write_text(json.dumps(PLANO_TOKEN), encoding="utf-8")

    def montar(extra="", rotulo_peso="700"):
        svg = tmp_path / "f.svg"
        svg.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="none" stroke="{tinta}" stroke-width="1.5"/>'
            f'<text x="10" y="20" font-size="16" font-weight="{rotulo_peso}">Serviço A</text>{extra}</svg>',
            encoding="utf-8",
        )
        return plano, svg

    return montar


def test_figura_dentro_dos_tokens_passa(figura):
    assert checar_plano_svg(*figura()) == (0, [])


def test_cor_fora_dos_tokens_e_apontada(figura):
    cod, defeitos = checar_plano_svg(*figura('<rect fill="#123456"/>'))
    assert cod == 1 and any("#123456" in d and "fora dos tokens" in d for d in defeitos)


def test_gradiente_e_sombra_sao_efeito_vedado(figura):
    cod, defeitos = checar_plano_svg(*figura('<defs><linearGradient id="g"/></defs><rect fill="url(#g)"/>'))
    assert cod == 1 and any("efeito vedado" in d for d in defeitos)
    cod, defeitos = checar_plano_svg(*figura('<rect filter="url(#s)"/>'))
    assert cod == 1 and any("efeito vedado" in d for d in defeitos)


def test_fio_mais_grosso_que_o_contorno(figura):
    cod, defeitos = checar_plano_svg(*figura('<rect stroke-width="3"/>'))
    assert cod == 1 and any("mais grosso" in d for d in defeitos)


def test_rotulo_de_caixa_em_peso_regular(figura):
    cod, defeitos = checar_plano_svg(*figura(rotulo_peso="400"))
    assert cod == 1 and any("peso regular" in d for d in defeitos)


def test_mais_de_quatro_familias(figura):
    t = tk.carregar()
    rects = "".join(f'<rect stroke="{tk.familia(t, n)["stroke"]}"/>' for n in range(1, 6))
    cod, defeitos = checar_plano_svg(*figura(rects))
    assert cod == 1 and any("famílias" in d for d in defeitos)


# ==============================================================================================
# Seção 5 — Grade: posição, rota em ângulo reto, rótulo junto da seta e SVG
# ==============================================================================================

NORTE = {
    "tipo": "fluxo",
    "titulo": "Quem sabe vai direto; quem não sabe vai à busca; o verbo é a chamada",
    "faixas": [{"id": "fluxo", "nome": "Fluxo"}, {"id": "negocio", "nome": "Negócio"},
               {"id": "dobradica", "nome": "Dobradiça"}, {"id": "tecnologia", "nome": "Tecnologia"}],
    "zonas": [{"id": "trabalho", "nome": "Trabalho", "faixa": "fluxo"}],
    "elementos": [
        {"id": "sessao", "titulo": "Sessão aberta", "tipo": "inicio", "faixa": "fluxo", "coluna": 1, "ordem": 1},
        {"id": "gatilho", "titulo": "Gatilho", "tipo": "decisao", "faixa": "fluxo", "coluna": 1, "ordem": 2},
        {"id": "processo", "titulo": "Processo", "tipo": "passo", "zona": "trabalho", "faixa": "fluxo", "coluna": 2, "ordem": 1},
        {"id": "busca", "titulo": "Busca", "tipo": "passo", "zona": "trabalho", "faixa": "fluxo", "coluna": 2, "ordem": 2},
        {"id": "rotina", "titulo": "Rotina", "tipo": "passo", "zona": "trabalho", "faixa": "fluxo", "coluna": 2, "ordem": 3},
        {"id": "validacao", "titulo": "Deu certo?", "tipo": "decisao", "faixa": "fluxo", "coluna": 3, "ordem": 1},
        {"id": "recompensa", "titulo": "Recompensa", "tipo": "fim", "faixa": "fluxo", "coluna": 4, "ordem": 1},
        {"id": "deu_ruim", "titulo": "Deu ruim", "tipo": "fim", "faixa": "fluxo", "coluna": 4, "ordem": 2},
        {"id": "capacidade", "titulo": "Capacidade", "subtitulo": "nível 1 · a busca é a nuclear, as outras de suporte",
         "tipo": "coisa", "faixa": "negocio", "coluna": 2, "colunas": 3, "ordem": 1},
        {"id": "verbo", "titulo": "Verbo", "subtitulo": "atos no nível 2 · não precisa estar na porta",
         "tipo": "coisa", "faixa": "dobradica", "coluna": 2, "colunas": 3, "ordem": 1},
        {"id": "tool", "titulo": "Tool na porta ou chamada de processo",
         "subtitulo": "sobre stacks recortadas por custo de transação",
         "tipo": "coisa", "faixa": "tecnologia", "coluna": 2, "colunas": 3, "ordem": 1}],
    "arestas": [
        {"de": "sessao", "para": "gatilho", "rotulo": "dispara", "chega": "esquerda"},
        {"de": "gatilho", "para": "processo", "rotulo": "reconheci a norma", "sai": "cima"},
        {"de": "gatilho", "para": "busca", "rotulo": "não sei", "sai": "direita"},
        {"de": "gatilho", "para": "rotina", "rotulo": "lembrei como faz", "sai": "baixo"},
        {"de": "busca", "para": "processo", "rotulo": "achei a norma"},
        {"de": "busca", "para": "rotina", "rotulo": "lembrei como faz"},
        {"de": "busca", "para": "validacao", "rotulo": "cansei de procurar"},
        {"de": "processo", "para": "validacao", "rotulo": "segui os passos"},
        {"de": "rotina", "para": "validacao", "rotulo": "fiz do jeito de sempre", "chega": "baixo"},
        {"de": "validacao", "para": "recompensa", "rotulo": "sim", "sai": "direita"},
        {"de": "validacao", "para": "deu_ruim", "rotulo": "não", "sai": "direita"},
        {"de": "capacidade", "para": "trabalho", "rotulo": "habilita"},
        {"de": "capacidade", "para": "verbo", "rotulo": "um para um"},
        {"de": "verbo", "para": "tool", "rotulo": "servido por"}],
}

DUAS_COLUNAS = {
    "tipo": "alocacao", "titulo": "Duas colunas",
    "faixas": [{"id": "a", "nome": "Cima"}, {"id": "b", "nome": "Baixo"}],
    "elementos": [
        {"id": "x", "titulo": "Caixa X", "tipo": "coisa", "faixa": "a", "coluna": 1, "ordem": 1},
        {"id": "y", "titulo": "Caixa Y mais comprida", "tipo": "coisa", "faixa": "b", "coluna": 1, "ordem": 1},
        {"id": "z", "titulo": "Z", "tipo": "coisa", "faixa": "b", "coluna": 2, "ordem": 1}],
    "arestas": [{"de": "x", "para": "y", "rotulo": "desce"}, {"de": "y", "para": "z", "rotulo": "segue"}],
}

LARGA = {
    "tipo": "camada", "titulo": "Caixa larga",
    "faixas": [{"id": "cima"}, {"id": "baixo"}],
    "zonas": [{"id": "z", "nome": "Zona de baixo com nome comprido", "faixa": "baixo"}],
    "elementos": [
        {"id": "a", "titulo": "A", "tipo": "coisa", "faixa": "cima", "coluna": 1, "ordem": 1},
        {"id": "b", "titulo": "B", "tipo": "coisa", "faixa": "cima", "coluna": 2, "ordem": 1},
        {"id": "c", "titulo": "C", "tipo": "coisa", "faixa": "cima", "coluna": 3, "ordem": 1},
        {"id": "l", "titulo": "Larga", "tipo": "coisa", "zona": "z", "faixa": "baixo", "coluna": 1, "colunas": 3, "ordem": 1}],
    "arestas": [{"de": "a", "para": "l", "rotulo": "desce"}, {"de": "b", "para": "l", "rotulo": "desce"},
                {"de": "c", "para": "l", "rotulo": "desce"}],
}

CAMADA = {
    "tipo": "fluxo", "titulo": "Camada tracejada",
    "faixas": [{"id": "cima"}, {"id": "baixo"}],
    "zonas": [{"id": "z", "nome": "Camada", "faixa": "baixo", "tracejada": True}],
    "elementos": [
        {"id": "a", "titulo": "Passo", "tipo": "passo", "faixa": "cima", "coluna": 1, "ordem": 1},
        {"id": "b", "titulo": "Busca", "tipo": "passo", "faixa": "cima", "coluna": 2, "ordem": 1, "tracejada": True},
        {"id": "c", "titulo": "Fim", "tipo": "fim", "zona": "z", "faixa": "baixo", "coluna": 1, "ordem": 1}],
    "arestas": [{"de": "a", "para": "c", "rotulo": "deixa"},
                {"de": "a", "para": "b", "tracejada": True}],
}


@pytest.fixture(scope="module")
def norte():
    return grade.montar(copy.deepcopy(NORTE))


def _segmentos(fig):
    return [(s, a, b) for s in fig.setas for a, b in zip(s.pontos, s.pontos[1:])]


def test_caixas_da_mesma_coluna_tem_o_mesmo_x_e_a_mesma_largura(norte):
    por_coluna = {}
    for c in norte.caixas.values():
        por_coluna.setdefault((c.coluna, c.colunas), set()).add((c.x, c.w))
    assert all(len(v) == 1 for v in por_coluna.values()), por_coluna


def test_caixas_da_mesma_pilha_seguem_a_ordem(norte):
    pilha = sorted((norte.caixas[i] for i in ("processo", "busca", "rotina")), key=lambda c: c.ordem)
    assert [c.id for c in sorted(pilha, key=lambda c: c.y)] == ["processo", "busca", "rotina"]


def test_todo_segmento_de_seta_e_horizontal_ou_vertical(norte):
    for s, a, b in _segmentos(norte):
        assert a[0] == b[0] or a[1] == b[1], (s.de, s.para, a, b)


def test_nenhuma_seta_atravessa_caixa(norte):
    for s, a, b in _segmentos(norte):
        for c in norte.caixas.values():
            r = (c.x, c.y, c.x + c.w, c.y + c.h)
            assert not grade._corta(a, b, r), (s.de, s.para, c.id)


def test_a_seta_do_norte_nao_cruza_outra(norte):
    segs = _segmentos(norte)
    for (s1, a1, b1), (s2, a2, b2) in itertools.combinations(segs, 2):
        if s1 is not s2:
            assert not grade._cruza(a1, b1, a2, b2), (s1.de, s1.para, s2.de, s2.para)


def test_rotulo_fica_a_ate_24px_da_propria_seta(norte):
    e = norte.estilo
    for s in norte.setas:
        ax, topo, ancora = s.rotulo_pos
        lw = max(medida.largura(l, e.metadado, e.peso_corpo) for l in s.rotulo_linhas)
        x0 = ax - lw / 2 if ancora == "middle" else ax - lw if ancora == "end" else ax
        r = (x0, topo, x0 + lw, topo + len(s.rotulo_linhas) * e.linha(e.metadado))
        d = min(grade._dist_ret_seg(r, a, b) for a, b in zip(s.pontos, s.pontos[1:]))
        assert d <= grade.DISTANCIA_ROTULO, (s.rotulo, d)


def test_viewbox_tem_ate_760_de_largura(norte):
    svg = grade.svg(norte)
    largura = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
    assert largura <= grade.LARGURA
    assert norte.largura == largura


def test_cada_texto_sai_no_tamanho_do_seu_papel(norte):
    t = tk.carregar()
    papel = {"bloco": "text-section", "texto": "text-body", "metadado": "text-meta"}
    svg = grade.svg(norte)
    achados = re.findall(r'<text data-papel="(\w+)" font-size="([\d.]+)"', svg)
    assert achados
    for nome, tamanho in achados:
        assert float(tamanho) == tk.px(tk.resolver(papel[nome], t)), (nome, tamanho)


def test_largura_de_duas_colunas_encolhe_e_a_caixa_cabe(norte):
    fig = grade.montar(copy.deepcopy(DUAS_COLUNAS))
    assert fig.largura < grade.LARGURA
    assert fig.caixas["x"].x == fig.caixas["y"].x


def test_duas_caixas_na_mesma_celula_sao_recusadas_pelo_nome():
    dados = copy.deepcopy(DUAS_COLUNAS)
    dados["elementos"][2].update(coluna=1)
    with pytest.raises(grade.ErroDeFonte, match=r"'y' e 'z'"):
        grade.montar(dados)


def test_caixa_que_ocupa_colunas_choca_com_a_vizinha():
    dados = copy.deepcopy(DUAS_COLUNAS)
    dados["elementos"][1]["colunas"] = 2
    with pytest.raises(grade.ErroDeFonte, match=r"'y' e 'z'"):
        grade.montar(dados)


@pytest.mark.parametrize("campo", ["faixa", "coluna", "ordem"])
def test_caixa_sem_posicao_e_recusada_pelo_nome(campo):
    dados = copy.deepcopy(DUAS_COLUNAS)
    del dados["elementos"][0][campo]
    with pytest.raises(grade.ErroDeFonte, match=rf"'x' não tem {campo}"):
        grade.montar(dados)


def test_seta_para_caixa_que_nao_existe_e_recusada():
    dados = copy.deepcopy(DUAS_COLUNAS)
    dados["arestas"][0]["para"] = "fantasma"
    with pytest.raises(grade.ErroDeFonte, match="fantasma"):
        grade.montar(dados)


def test_texto_que_nao_cabe_na_coluna_e_recusado_pelo_nome():
    dados = copy.deepcopy(DUAS_COLUNAS)
    dados["elementos"][2]["titulo"] = "Inconstitucionalissimamente"
    with pytest.raises(grade.ErroDeFonte, match="'z' não cabe"):
        grade.montar(dados)


def test_texto_da_fonte_e_escapado_no_svg():
    dados = copy.deepcopy(DUAS_COLUNAS)
    dados["elementos"][0]["titulo"] = 'A <b> & "C"'
    svg = grade.desenhar(dados)
    assert "A &lt;b&gt; &amp; &quot;C&quot;" in svg
    assert "<b>" not in svg


def test_ponta_da_seta_e_forma_desenhada_na_chegada(norte):
    svg = grade.svg(norte)
    assert "marker" not in svg
    pontas = re.findall(r'<path class="ponta" d="M([\d.]+) ([\d.]+)L', svg)
    assert len(pontas) == len(norte.setas)
    for s, (x, y) in zip(norte.setas, pontas):
        assert (float(x), float(y)) == s.pontos[-1], (s.de, s.para)


def test_caixa_larga_tem_uma_porta_por_coluna():
    fig = grade.montar(copy.deepcopy(LARGA))
    for s in fig.setas:
        assert len(s.pontos) == 2 and s.pontos[0][0] == s.pontos[1][0], (s.de, s.pontos)


def test_nome_da_zona_fica_fora_do_caminho_das_setas():
    fig = grade.montar(copy.deepcopy(LARGA))
    h = fig.cabecas[("zona", "z")]
    r = h.retangulo(fig.estilo)
    for s in fig.setas:
        for a, b in zip(s.pontos, s.pontos[1:]):
            assert grade._dist_ret_seg(r, a, b) > 0, (s.de, h.x, h.linhas)


def test_feixe_que_diz_a_mesma_coisa_leva_o_rotulo_uma_vez():
    feixe = {
        "tipo": "camada", "titulo": "Feixe", "faixas": [{"id": "cima"}, {"id": "baixo"}],
        "elementos": [{"id": "s", "titulo": "Fonte", "tipo": "coisa", "faixa": "cima", "coluna": 2, "ordem": 1}]
        + [{"id": f"t{i}", "titulo": f"Alvo {i}", "tipo": "coisa", "faixa": "baixo", "coluna": i, "ordem": 1}
           for i in (1, 2, 3)],
        "arestas": [{"de": "s", "para": f"t{i}", "rotulo": "usa a mesma porta", "sai": "baixo"} for i in (1, 2, 3)],
    }
    fig = grade.montar(feixe)
    assert sum(1 for s in fig.setas if s.rotulo_linhas) == 1
    svg = grade.svg(fig)
    assert svg.count(">usa a mesma porta<") == 1


def test_seta_reta_passa_antes_e_fica_reta(norte):
    validacao = next(s for s in norte.setas if s.de == "busca" and s.para == "validacao")
    assert len(validacao.pontos) == 2


def test_seta_pode_apontar_a_zona(norte):
    habilita = next(s for s in norte.setas if s.rotulo == "habilita")
    z = next(z for z in norte.zonas if z.id == "trabalho")
    fim = habilita.pontos[-1]
    assert z.y + z.h == fim[1] and z.x <= fim[0] <= z.x + z.w


def test_seta_tracejada_dispensa_o_rotulo_e_sai_tracejada():
    fig = grade.montar(copy.deepcopy(CAMADA))
    busca = next(s for s in fig.setas if s.para == "b")
    assert busca.tracejada and not busca.rotulo_linhas
    svg = grade.svg(fig)
    g = re.search(r'<g class="seta tracejada" data-de="a" data-para="b"><path [^>]*stroke-dasharray="([\d.]+) ([\d.]+)"', svg)
    assert g, svg
    e = fig.estilo
    assert (float(g.group(1)), float(g.group(2))) == (e.folga, e.folga / 2)
    cheia = re.search(r'<g class="seta" data-de="a" data-para="c"><path ([^>]*)/>', svg)
    assert cheia and "dasharray" not in cheia.group(1)


def test_caixa_e_zona_tracejadas_saem_com_o_fio_tracejado():
    svg = grade.svg(grade.montar(copy.deepcopy(CAMADA)))
    caixa = re.search(r'<g class="caixa" data-id="b"><rect [^>]*>', svg).group(0)
    zona = re.search(r'<g class="zona" data-id="z"><rect [^>]*>', svg).group(0)
    outra = re.search(r'<g class="caixa" data-id="a"><rect [^>]*>', svg).group(0)
    assert "stroke-dasharray" in caixa and "stroke-dasharray" in zona
    assert "stroke-dasharray" not in outra


def test_caixa_de_familia_nao_leva_glifo():
    fonte = {
        "tipo": "componente-e-conector", "titulo": "Sem glifo", "faixas": [{"id": "f"}],
        "elementos": [{"id": "b", "titulo": "Banco", "tipo": "coisa", "categoria": "persistencia",
                       "faixa": "f", "coluna": 1, "ordem": 1}],
        "arestas": [],
    }
    svg = grade.svg(grade.montar(fonte))
    caixa = re.search(r'<g class="caixa" data-id="b">(.*?)</g>', svg).group(1)
    assert re.findall(r"<tspan[^>]*>([^<]*)</tspan>", caixa) == ["Banco"]


def test_seta_cheia_sem_rotulo_e_recusada():
    fonte = copy.deepcopy(CAMADA)
    fonte["arestas"][1]["tracejada"] = False
    with pytest.raises(grade.ErroDeFonte, match=r"seta 2 \(a → b\).*tracejada"):
        grade.montar(fonte)


# ==============================================================================================
# Seção 6 — Receita embutida no SVG
# ==============================================================================================

SVG_RECEITA = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><?plantuml 1.0?><text x="1" y="1">Caixa</text></svg>'
FONTE_RECEITA = {"tipo": "alocacao", "titulo": "Ação & <teste>", "elementos": [], "arestas": []}
PLANO_RECEITA = {"pergunta": "Onde roda?", "leitor": "dono", "tipo": "alocacao", "fontes": ["a.md"]}


def _arquivos_receita(tmp_path):
    svg = tmp_path / "fig.svg"
    svg.write_text(SVG_RECEITA, encoding="utf-8")
    fonte = tmp_path / "fig.fonte.json"
    fonte.write_text(json.dumps(FONTE_RECEITA, ensure_ascii=False), encoding="utf-8")
    plano = tmp_path / "fig.plano.json"
    plano.write_text(json.dumps(PLANO_RECEITA, ensure_ascii=False), encoding="utf-8")
    return svg, fonte, plano


def test_embutir_e_ler_devolvem_a_mesma_receita(tmp_path):
    svg, fonte, plano = _arquivos_receita(tmp_path)
    receita.embutir(svg, fonte, plano)
    texto = svg.read_text(encoding="utf-8")
    assert receita.ler(texto) == {"fonte": FONTE_RECEITA, "plano": PLANO_RECEITA}
    ET.fromstring(texto)
    assert '<text x="1" y="1">Caixa</text>' in texto


def test_embutir_de_novo_troca_a_receita_sem_duplicar(tmp_path):
    svg, fonte, plano = _arquivos_receita(tmp_path)
    receita.embutir(svg, fonte, plano)
    fonte.write_text(json.dumps({**FONTE_RECEITA, "titulo": "outro"}), encoding="utf-8")
    receita.embutir(svg, fonte, plano)
    texto = svg.read_text(encoding="utf-8")
    assert texto.count("<metadata") == 2
    assert receita.ler(texto)["fonte"]["titulo"] == "outro"


def test_receita_devolve_os_arquivos(tmp_path):
    svg, fonte, plano = _arquivos_receita(tmp_path)
    receita.embutir(svg, fonte, plano)
    saida = tmp_path / "rascunho"
    feitos = receita.extrair(svg, saida)
    assert [p.name for p in feitos] == ["fig.plano.json", "fig.fonte.json"]
    assert json.loads((saida / "fig.fonte.json").read_text(encoding="utf-8")) == FONTE_RECEITA
    assert json.loads((saida / "fig.plano.json").read_text(encoding="utf-8")) == PLANO_RECEITA


def test_svg_sem_receita_sai_1(tmp_path):
    svg = tmp_path / "mao.svg"
    svg.write_text(SVG_RECEITA, encoding="utf-8")
    with pytest.raises(LookupError):
        receita.extrair(svg)
    assert diagrama_main(["receita", str(svg)]) == 1


def test_recusa_texto_que_fecharia_o_bloco():
    with pytest.raises(ValueError):
        receita.embutir_texto(SVG_RECEITA, {"fonte": {"titulo": "a ]]> b"}})


def test_cli_embutir_e_receita(tmp_path):
    svg, fonte, plano = _arquivos_receita(tmp_path)
    assert diagrama_main(["embutir", str(svg), str(fonte), str(plano)]) == 0
    assert diagrama_main(["receita", str(svg), "--saida", str(tmp_path / "r")]) == 0
    assert (tmp_path / "r" / "fig.fonte.json").is_file()
    assert diagrama_main(["embutir", str(svg)]) == 2


# ==============================================================================================
# Seção 7 — Renderização pela grade (SVG e PNG)
# ==============================================================================================


@pytest.mark.parametrize("tipo", TIPOS)
def test_exemplo_sai_em_svg_pela_grade(tipo):
    dados = json.loads((BASE_EXEMPLOS / f"{tipo}.fonte.json").read_text(encoding="utf-8"))
    svg = renderizar_dados(dados)
    largura = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
    assert svg.startswith("<svg") and largura <= 760
    assert "<b>" not in svg and "@startuml" not in svg


def test_renderizar_grava_svg_e_png_do_mesmo_desenho(tmp_path):
    svg_path, png_path = renderizar_arquivo(BASE_EXEMPLOS / "camada.fonte.json", saida_dir=tmp_path)
    assert svg_path.read_text(encoding="utf-8").startswith("<svg")
    png = png_path.read_bytes()
    assert png.startswith(b"\x89PNG")
    w, h = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")
    assert max(w, h) <= 1568


def test_previa_da_ao_texto_a_familia_e_o_peso_que_o_mupdf_pinta():
    dados = json.loads((BASE_EXEMPLOS / "camada.fonte.json").read_text(encoding="utf-8"))
    previa = para_o_mupdf(renderizar_dados(dados))
    textos = re.findall(r"<text\b[^>]*>", previa)
    assert textos and all("sans-serif" in t for t in textos)
    pesos = set(re.findall(r'font-weight="([^"]+)"', previa))
    assert pesos <= {"bold", "normal"} and pesos == {"bold", "normal"}


def test_previa_png_pinta_textos_dos_cinco_exemplos_dentro_de_5_por_cento_da_inter():
    import pymupdf
    assert _caminho_inter(400), "Inter regular deveria estar instalada em /usr/share/fonts"
    desvios = []
    for tipo in TIPOS:
        dados = json.loads((BASE_EXEMPLOS / f"{tipo}.fonte.json").read_text(encoding="utf-8"))
        svg = renderizar_dados(dados)
        for item in _extrair_textos(svg):
            esperada = medida.largura(item["texto"], item["tamanho"], item["peso"])
            if esperada <= 0:
                continue
            fonte = pymupdf.Font(fontfile=_caminho_inter(item["peso"]))
            pintada = fonte.text_length(item["texto"], fontsize=item["tamanho"])
            erro_rel = abs(pintada - esperada) / esperada
            if erro_rel > 0.05:
                desvios.append((tipo, item["texto"], esperada, pintada, erro_rel))
    assert not desvios, f"textos fora de 5% da largura Inter: {desvios}"
    svg_teste = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="60" viewBox="0 0 300 60" '
        'font-family="Inter, system-ui, sans-serif">'
        '<rect width="300" height="60" fill="#FFFFFF"/>'
        '<text font-size="12" font-weight="400" fill="#18181B" text-anchor="start">'
        '<tspan x="20" y="35">1. claudinho-mcp chama o verbo</tspan></text></svg>'
    )
    pix = pymupdf.Pixmap(png_do_svg(svg_teste))
    xs = [x for y in range(pix.height) for x in range(pix.width) if pix.pixel(x, y)[0] < 200]
    largura_px_svg = (max(xs) - min(xs) + 1) / 2.0
    esperada_inter = medida.largura("1. claudinho-mcp chama o verbo", 12, 400)
    assert abs(largura_px_svg - esperada_inter) / esperada_inter <= 0.05, (largura_px_svg, esperada_inter)


def test_previa_png_mostra_tracejadas_a_seta_a_caixa_e_a_zona():
    import pymupdf
    svg_tracejado = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="180" viewBox="0 0 240 180">'
        '<rect width="240" height="180" fill="#FFFFFF"/>'
        '<rect x="20" y="20" width="200" height="50" rx="8" fill="#F4F4F5" stroke="#18181B" '
        'stroke-width="2" stroke-dasharray="8 4"/>'
        '<rect x="20" y="85" width="200" height="45" rx="6" fill="#EFF6FF" stroke="#1D4ED8" '
        'stroke-width="2" stroke-dasharray="8 4"/>'
        '<path d="M 20 155 L 220 155" fill="none" stroke="#18181B" stroke-width="2" stroke-dasharray="8 4"/>'
        '</svg>'
    )
    previa = para_o_mupdf(svg_tracejado)
    assert "stroke-dasharray" not in previa
    pix = pymupdf.Pixmap(png_do_svg(svg_tracejado))

    def transicoes_na_linha(y_svg: int) -> int:
        y_px = y_svg * 2
        escuros = [pix.pixel(x, y_px)[0] < 200 for x in range(60, 420)]
        return sum(1 for a, b in zip(escuros, escuros[1:]) if a != b)

    assert transicoes_na_linha(20) >= 10
    assert transicoes_na_linha(85) >= 10
    assert transicoes_na_linha(155) >= 10


def test_caixa_sem_coluna_sai_1_e_nomeia_a_caixa(tmp_path, capsys):
    dados = json.loads((BASE_EXEMPLOS / "camada.fonte.json").read_text(encoding="utf-8"))
    del dados["elementos"][1]["coluna"]
    f = tmp_path / "sem-coluna.fonte.json"
    f.write_text(json.dumps(dados), encoding="utf-8")
    assert renderizar_main([str(f), "--saida", str(tmp_path)]) == 1
    assert "'api' não tem coluna" in capsys.readouterr().err


def test_duas_caixas_na_mesma_celula_saem_1_com_as_duas(tmp_path, capsys):
    dados = json.loads((BASE_EXEMPLOS / "modulo.fonte.json").read_text(encoding="utf-8"))
    dados["elementos"][1]["ordem"] = 1
    f = tmp_path / "choque.fonte.json"
    f.write_text(json.dumps(dados), encoding="utf-8")
    assert renderizar_main([str(f), "--saida", str(tmp_path)]) == 1
    erro = capsys.readouterr().err
    assert "'mod_diagrama'" in erro and "'mod_agente'" in erro


def test_fonte_fora_do_esquema_sai_1(tmp_path):
    f = tmp_path / "invalido.fonte.json"
    f.write_text(json.dumps({"tipo": "tipo_inexistente", "titulo": "X", "faixas": [{"id": "a"}],
                             "elementos": [], "arestas": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        renderizar_arquivo(f, saida_dir=tmp_path)
    assert renderizar_main([str(f), "--saida", str(tmp_path)]) == 1


def test_cli_diagrama_renderizar(tmp_path):
    assert diagrama_main(["renderizar", str(BASE_EXEMPLOS / "modulo.fonte.json"), "--saida", str(tmp_path)]) == 0
    assert (tmp_path / "modulo.svg").is_file() and (tmp_path / "modulo.png").is_file()


# ==============================================================================================
# Seção 8 — Checagem estrutural do SVG
# ==============================================================================================


def _exemplo(tipo):
    fonte = json.loads((BASE_EXEMPLOS / f"{tipo}.fonte.json").read_text(encoding="utf-8"))
    plano = json.loads((BASE_EXEMPLOS / f"{tipo}.plano.json").read_text(encoding="utf-8"))
    return fonte, plano, grade.desenhar(fonte)


@pytest.mark.parametrize("tipo", TIPOS)
def test_exemplo_desenhado_pela_grade_nao_tem_defeito(tipo):
    _, plano, svg = _exemplo(tipo)
    assert checar_svg(svg, plano) == []


def test_entidade_que_some_dos_textos_e_acusada():
    _, plano, svg = _exemplo("camada")
    svg = svg.replace(">Painel UI<", "><")
    assert any("Painel UI" in d for d in checar_svg(svg, plano))


def test_letra_fora_dos_papeis_e_acusada():
    _, plano, svg = _exemplo("camada")
    svg = svg.replace('font-size="16"', 'font-size="13"', 1)
    assert any("13.0px" in d and "papel" in d for d in checar_svg(svg, plano))


def test_letra_se_mede_na_largura_de_leitura():
    _, plano, svg = _exemplo("camada")
    largo = re.sub(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', lambda m: f'viewBox="0 0 1520 {m.group(2)}"', svg)
    defeitos = checar_svg(largo, plano)
    assert any("8.0px" in d for d in defeitos), defeitos


def test_figura_mais_larga_que_o_dobro_da_altura_e_acusada():
    _, plano, svg = _exemplo("camada")
    baixa = re.sub(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', lambda m: f'viewBox="0 0 {m.group(1)} 100"', svg)
    assert any("dobro da altura" in d for d in checar_svg(baixa, plano))


def test_setas_que_se_cruzam_sao_acusadas():
    _, plano, svg = _exemplo("camada")
    cruz = ('<g class="seta" data-de="a" data-para="b"><path d="M10 50H200" fill="none"/></g>'
            '<g class="seta" data-de="c" data-para="d"><path d="M100 10V90" fill="none"/></g>')
    defeitos = checar_svg(svg.replace("</svg>", cruz + "</svg>"), plano)
    assert any("a → b e c → d se cruzam" in d for d in defeitos), defeitos


def test_setas_que_so_se_encostam_na_ponta_nao_se_cruzam():
    _, plano, svg = _exemplo("camada")
    garfo = ('<g class="seta" data-de="a" data-para="b"><path d="M10 50H100V10" fill="none"/></g>'
             '<g class="seta" data-de="a" data-para="c"><path d="M100 50V90" fill="none"/></g>')
    assert not any("se cruzam" in d for d in checar_svg(svg.replace("</svg>", garfo + "</svg>"), plano))


def test_feixe_que_se_separa_do_tronco_nao_cruza():
    _, plano, svg = _exemplo("camada")
    feixe = ('<g class="seta" data-de="a" data-para="b"><path d="M10 90V50H200" fill="none"/></g>'
             '<g class="seta" data-de="a" data-para="c"><path d="M10 90V50H100V10" fill="none"/></g>'
             '<g class="seta" data-de="d" data-para="c"><path d="M150 90V50H100V10" fill="none"/></g>')
    assert not any("se cruzam" in d for d in checar_svg(svg.replace("</svg>", feixe + "</svg>"), plano))


def test_curva_do_plantuml_entra_no_cruzamento():
    _, plano, svg = _exemplo("camada")
    curvas = ('<g class="link" id="l1"><path d="M0,50 C60,50 140,50 200,50" fill="none"/></g>'
              '<g class="link" id="l2"><path d="M100,0 C100,30 100,70 100,100" fill="none"/></g>')
    assert any("l1 e l2 se cruzam" in d for d in checar_svg(svg.replace("</svg>", curvas + "</svg>"), plano))


def test_rotulo_longe_da_seta_e_acusado():
    _, plano, svg = _exemplo("camada")
    grupo = re.search(r'<g class="seta" data-de="ui".*?</g>', svg).group(0)
    longe = re.sub(r'<tspan x="([\d.]+)"', lambda m: f'<tspan x="{float(m.group(1)) + 80:g}"', grupo)
    defeitos = checar_svg(svg.replace(grupo, longe), plano)
    assert any("consome por HTTPS" in d and "da seta" in d for d in defeitos), defeitos


def test_texto_sobre_caixa_alheia_e_acusado():
    _, plano, svg = _exemplo("camada")
    caixa = re.search(r'<g class="caixa" data-id="api"><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', svg)
    x, y, w = (float(v) for v in caixa.groups())
    intruso = f'<text font-size="12" x="{x + w - 20:g}" y="{y + 20:g}">intruso grande</text>'
    assert any("'intruso grande' invade" in d for d in checar_svg(svg.replace("</svg>", intruso + "</svg>"), plano))


def test_receita_embutida_nao_esconde_a_caixa_que_falta(tmp_path):
    fonte, plano, svg = _exemplo("camada")
    com_receita = receita.embutir_texto(svg, {"plano": plano, "fonte": fonte})
    sem_caixa = re.sub(r'<g class="caixa" data-id="db">.*?</g>', "", com_receita, flags=re.S)
    p_svg, p_plano = tmp_path / "f.svg", tmp_path / "p.json"
    p_svg.write_text(sem_caixa, encoding="utf-8")
    p_plano.write_text(json.dumps(plano), encoding="utf-8")
    cod, defeitos = checar_plano_svg(p_plano, p_svg)
    assert cod == 1
    assert any("Postgres do Acervo" in d for d in defeitos)


def test_cor_fora_dos_tokens_segue_acusada():
    _, plano, svg = _exemplo("camada")
    assert any("#ff00ff" in d for d in checar_svg(svg.replace("</svg>", '<rect fill="#ff00ff"/></svg>'), plano))


def test_cli_diagrama_checar(tmp_path, capsys):
    _, _, svg = _exemplo("camada")
    (tmp_path / "c.svg").write_text(svg, encoding="utf-8")
    assert diagrama_main(["checar", str(BASE_EXEMPLOS / "camada.plano.json"), str(tmp_path / "c.svg")]) == 0
    assert "0 defeitos" in capsys.readouterr().out


def test_pontos_do_path_le_comando_relativo_e_curva():
    tracos = checagem.pontos_do_path("M10 10h20v20l-5 5C0 0 0 0 1 1z")
    assert tracos[0][:4] == [(10, 10), (30, 10), (30, 30), (25, 35)]
    assert tracos[0][-1] == (10, 10)


# ==============================================================================================
# Seção 9 — Lint do plano (tabelado)
# ==============================================================================================


def test_exemplos_passam_no_lint():
    for tipo in ("camada", "modulo", "componente-e-conector", "alocacao", "fluxo"):
        arq = BASE_EXEMPLOS / f"{tipo}.plano.json"
        cod, defeitos = lint_plano(arq)
        assert cod == 0, f"falhou em {arq}: {defeitos}"
        assert len(defeitos) == 0


@pytest.mark.parametrize(
    ("nome_arq", "trechos_esperados"),
    [
        ("recusa-sem-fonte.plano.json", ("fora da lista de fontes",)),
        ("recusa-sem-rotulo.plano.json", ("sem rótulo / nome", "esquema")),
        ("recusa-tipo-invalido.plano.json", ("taxonomia", "esquema")),
    ],
)
def test_recusa_exemplo_invalido_em_tabela(nome_arq: str, trechos_esperados: tuple[str, ...]):
    arq = BASE_EXEMPLOS / nome_arq
    cod, defeitos = lint_plano(arq)
    assert cod == 1
    assert any(any(t in d for t in trechos_esperados) for d in defeitos)


def _fluxo_mutado(tmp_path, cenario: str):
    dados = json.loads((BASE_EXEMPLOS / "fluxo.plano.json").read_text(encoding="utf-8"))
    if cenario == "decisao_sem_pergunta":
        next(e for e in dados["entidades"] if e["id"] == "plano_ok")["nome"] = "Plano passa"
    elif cenario == "forma_fora":
        next(e for e in dados["entidades"] if e["id"] == "produzir")["tipo"] = "servico"
    elif cenario == "elipse_no_meio":
        dados["relacoes"].append({"de": "entregar", "para": "pedido", "rotulo": "recomeça"})
    elif cenario == "decisao_uma_saida":
        dados["relacoes"] = [r for r in dados["relacoes"] if not (r["de"] == "plano_ok" and r["para"] == "planejar")]
    elif cenario == "saidas_iguais":
        for r in dados["relacoes"]:
            if r["de"] == "plano_ok":
                r["rotulo"] = "segue"
    arq = tmp_path / f"{cenario}.plano.json"
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return lint_plano(arq)


@pytest.mark.parametrize(
    ("cenario", "trecho_esperado"),
    [
        ("decisao_sem_pergunta", "tem de ser pergunta"),
        ("forma_fora", "é a forma"),
        ("elipse_no_meio", "a elipse fica só na ponta"),
        ("decisao_uma_saida", "decisão tem duas ou mais"),
        ("saidas_iguais", "mesmo rótulo"),
    ],
)
def test_fluxo_recusa_violacoes_em_tabela(tmp_path, cenario: str, trecho_esperado: str):
    cod, defeitos = _fluxo_mutado(tmp_path, cenario)
    assert cod == 1
    assert any(trecho_esperado in x for x in defeitos)


# ==============================================================================================
# Seção 10 — Juízes da peça diagrama
# ==============================================================================================

FONTE_JUIZ = "docker-compose.yml"
GABARITO_PLANO = "GABARITO-DO-PLANO"
GABARITO_FIGURA = (
    "Abertura do gabarito.\n\n## Em toda figura\n\nITENS-GERAIS\n\n"
    "## Camada\n\nITENS-CAMADA\n\n## Módulo\n\nITENS-MODULO\n\n"
    "## Componente e conector\n\nITENS-COMPONENTE\n\n## Alocação\n\nITENS-ALOCACAO\n"
)
CSV_GALERIA = (
    "arquivo,tipo,endereco,frase\n"
    "a.png,alocação,http://x/a,mostra o host\n"
    "b.png,camada,http://x/b,mostra a pilha\n"
    "c.png,alocacao,http://x/c,outra de host\n"
    "d.png,alocação,http://x/d,terceira de host\n"
)


@pytest.fixture
def mundo(monkeypatch):
    docs = {
        juizes.GABARITO_PLANO: GABARITO_PLANO,
        juizes.GABARITO_FIGURA: GABARITO_FIGURA,
        FONTE_JUIZ: "DOC-DA-FONTE-1",
    }

    def ler_de_main(caminho, raiz=None):
        if caminho not in docs:
            raise juizes.FonteForaDeMain(f"{caminho} não está em origin/main")
        return docs[caminho]

    chamadas = []

    def chamar_agente(slug, tarefa, anexos=None):
        chamadas.append({"slug": slug, "tarefa": tarefa, "anexos": anexos or []})
        return mundo_resposta["rc"], mundo_resposta["retorno"], mundo_resposta["erro"]

    mundo_resposta = {"rc": 0, "retorno": "veredito: 0 — x@abc", "erro": ""}
    monkeypatch.setattr(juizes, "raiz_do_repo", lambda: RAIZ_ESPELHO)
    monkeypatch.setattr(juizes, "ler_de_main", ler_de_main)
    monkeypatch.setattr(juizes, "chamar_agente", chamar_agente)
    # os testes dos juízes medem o caminho que volta com a #4150; o desligado tem os seus abaixo
    monkeypatch.setattr(juizes, "JUIZES_LIGADOS", True)
    return {"docs": docs, "chamadas": chamadas, "resposta": mundo_resposta}


def test_juizes_ficam_desligados_ate_a_4150():
    assert juizes.JUIZES_LIGADOS is False


def test_desligado_conferir_plano_roda_lint_e_fontes_sem_chamar_o_auditor(mundo, monkeypatch, capsys):
    monkeypatch.setattr(juizes, "JUIZES_LIGADOS", False)
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 0
    assert mundo["chamadas"] == []
    assert "auditor: juiz desligado" in capsys.readouterr().out


def test_desligado_fonte_fora_de_main_segue_defeito(mundo, monkeypatch, capsys):
    monkeypatch.setattr(juizes, "JUIZES_LIGADOS", False)
    del mundo["docs"][FONTE_JUIZ]
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 1
    assert mundo["chamadas"] == []
    assert "não está em origin/main" in capsys.readouterr().err


def test_desligado_conferir_figura_roda_a_checagem_sem_chamar_o_critico(mundo, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(juizes, "JUIZES_LIGADOS", False)
    svg, png = tmp_path / "f.svg", tmp_path / "f.png"
    svg.write_text("<svg/>", encoding="utf-8")
    png.write_bytes(b"\x89PNG-dados")
    monkeypatch.setattr(juizes, "checar_plano_svg", lambda p, s: (0, []))
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 0
    assert mundo["chamadas"] == []
    assert "crítico: juiz desligado" in capsys.readouterr().out


def test_desligado_checagem_que_reprova_segue_reprovando(mundo, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(juizes, "JUIZES_LIGADOS", False)
    svg, png = tmp_path / "f.svg", tmp_path / "f.png"
    svg.write_text("<svg/>", encoding="utf-8")
    png.write_bytes(b"\x89PNG-dados")
    monkeypatch.setattr(juizes, "checar_plano_svg", lambda p, s: (1, ["entidade 'X' do plano ausente no SVG"]))
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 1
    assert "ausente no SVG" in capsys.readouterr().err


def test_recorta_gabarito_com_o_geral_e_a_secao_do_tipo():
    r = juizes.recortar_gabarito(GABARITO_FIGURA, "alocacao")
    assert "Abertura do gabarito." in r and "ITENS-GERAIS" in r and "ITENS-ALOCACAO" in r
    assert "ITENS-CAMADA" not in r and "ITENS-MODULO" not in r and "ITENS-COMPONENTE" not in r


def test_gabarito_do_espelho_tem_a_secao_de_cada_tipo():
    gabarito = RAIZ_ESPELHO / juizes.GABARITO_FIGURA
    if not gabarito.is_file():
        pytest.skip("gabarito da casa ausente fora da arvore da casa")
    texto = gabarito.read_text(encoding="utf-8")
    for tipo in juizes.SECAO_DO_TIPO:
        assert juizes.recortar_gabarito(texto, tipo)


def test_galeria_escolhe_ate_duas_do_tipo_na_ordem_da_lista():
    r = juizes.escolher_galeria(CSV_GALERIA, "alocacao")
    assert [f["arquivo"] for f in r] == ["a.png", "c.png"]
    assert r[0]["frase"] == "mostra o host"


def test_galeria_sem_figura_do_tipo_volta_vazia():
    assert juizes.escolher_galeria(CSV_GALERIA, "modulo") == []
    assert juizes.escolher_galeria("", "camada") == []


def test_conferir_plano_recusado_pelo_lint_nao_chama_o_auditor(mundo, tmp_path):
    plano = tmp_path / "plano.json"
    plano.write_text(json.dumps({"pergunta": "x"}), encoding="utf-8")
    assert juizes.conferir_plano(str(plano)) == 1
    assert mundo["chamadas"] == []


def test_conferir_plano_monta_a_entrada_na_ordem(mundo):
    plano = BASE_EXEMPLOS / "alocacao.plano.json"
    assert juizes.conferir_plano(str(plano)) == 0
    (c,) = mundo["chamadas"]
    t = c["tarefa"]
    assert c["slug"] == "auditor-de-plano" and c["anexos"] == []
    ordem = [t.index(x) for x in (GABARITO_PLANO, "DOC-DA-FONTE-1", '"pergunta"')]
    assert ordem == sorted(ordem)
    assert "plano@" in t


def test_conferir_plano_veredito_um_sai_um(mundo, capsys):
    mundo["resposta"]["retorno"] = "veredito: 1 — plano@abc\nfalta a fronteira (linha 3)"
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 1
    assert "falta a fronteira" in capsys.readouterr().out


def test_conferir_plano_fonte_fora_de_main_e_defeito_do_plano(mundo, capsys):
    del mundo["docs"][FONTE_JUIZ]
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 1
    assert mundo["chamadas"] == []
    assert "não está em origin/main" in capsys.readouterr().err


def test_resposta_sem_linha_de_veredito_sai_cinco(mundo):
    mundo["resposta"]["retorno"] = "acho que está bom"
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 5


def test_agente_que_falha_sai_cinco(mundo):
    mundo["resposta"].update(rc=3, retorno="", erro="conta fora")
    assert juizes.conferir_plano(str(BASE_EXEMPLOS / "alocacao.plano.json")) == 5


def _figura_juiz(tmp_path, monkeypatch, defeitos=()):
    svg, png = tmp_path / "f.svg", tmp_path / "f.png"
    svg.write_text("<svg/>", encoding="utf-8")
    png.write_bytes(b"\x89PNG-dados")
    monkeypatch.setattr(juizes, "checar_plano_svg", lambda p, s: (1 if defeitos else 0, list(defeitos)))
    return svg, png


def test_conferir_figura_recusada_pela_checagem_nao_chama_o_critico(mundo, tmp_path, monkeypatch, capsys):
    svg, png = _figura_juiz(tmp_path, monkeypatch, defeitos=["entidade 'X' do plano ausente no SVG"])
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 1
    assert mundo["chamadas"] == []
    assert "ausente no SVG" in capsys.readouterr().err


def test_conferir_figura_poe_gabarito_galeria_plano_e_png_nessa_ordem(mundo, tmp_path, monkeypatch, capsys):
    mundo["docs"][juizes.GALERIA_CSV] = CSV_GALERIA
    svg, png = _figura_juiz(tmp_path, monkeypatch)
    copias = {"a.png": tmp_path / "ga.png", "c.png": tmp_path / "gc.png"}
    monkeypatch.setattr(juizes, "baixar_figura", lambda titulo, pasta: copias[titulo])
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 0
    (c,) = mundo["chamadas"]
    t = c["tarefa"]
    assert c["slug"] == "critico-de-figura"
    assert c["anexos"] == [str(tmp_path / "ga.png"), str(tmp_path / "gc.png"), str(png)]
    ordem = [t.index(x) for x in ("ITENS-ALOCACAO", "[[anexo:1]]", "[[anexo:2]]", '"pergunta"', "[[anexo:3]]")]
    assert ordem == sorted(ordem)
    assert "ITENS-CAMADA" not in t
    assert "rodou sem referência" not in capsys.readouterr().out


def test_conferir_figura_sem_galeria_roda_so_com_o_gabarito_e_diz(mundo, tmp_path, monkeypatch, capsys):
    svg, png = _figura_juiz(tmp_path, monkeypatch)
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 0
    (c,) = mundo["chamadas"]
    assert c["anexos"] == [str(png)] and "[[anexo:1]]" in c["tarefa"]
    assert "rodou sem referência" in capsys.readouterr().out


def test_veredito_da_figura_um_sai_um(mundo, tmp_path, monkeypatch):
    mundo["resposta"]["retorno"] = "veredito: 1 — figura@abc\nforma: seta sem rótulo legível"
    svg, png = _figura_juiz(tmp_path, monkeypatch)
    assert juizes.conferir_figura(str(BASE_EXEMPLOS / "alocacao.plano.json"), str(svg), str(png)) == 1


def test_chamar_agente_preserva_stdin_quando_subprocesso_drena_fd0(tmp_path, monkeypatch):
    pf_bin = tmp_path / "bin"
    pf_bin.mkdir()
    agente_stub = pf_bin / "agente"
    agente_stub.write_text(
        f"#!{sys.executable}\n"
        "import json, subprocess, sys\n"
        "subprocess.run([sys.executable, '-c', 'import os; os.read(0, 100000)'], check=True)\n"
        "tarefa = sys.stdin.read() if not sys.stdin.isatty() else ''\n"
        "if not tarefa.strip():\n"
        "    print('agente: a tarefa vem em stdin: agente rodar <slug> < tarefa', file=sys.stderr)\n"
        "    sys.exit(2)\n"
        "print(json.dumps({'retorno': f'veredito: 0 — recebido:{len(tarefa)}'}))\n",
        encoding="utf-8",
    )
    agente_stub.chmod(0o755)
    monkeypatch.setenv("PF_BIN", str(pf_bin))
    rc, retorno, erro = juizes.chamar_agente("auditor-de-plano", "TAREFA-DO-AUDITOR\n")
    assert rc == 0, erro
    assert retorno == "veredito: 0 — recebido:18"
