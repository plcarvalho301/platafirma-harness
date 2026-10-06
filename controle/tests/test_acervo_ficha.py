"""#3305: a ficha do arquivo da obra — `acervo ler biblioteca ficha` e `acervo ingerir biblioteca ficha`.

O verbo é cliente fino das rotas do motor_acervo (arq:0089 §2; spec apis-escrita-acervo §D): nada aqui abre o banco
nem o balde. A rota é de dublê, e o que se prova é o que o cliente decide sozinho: resolver a obra (uuid, prefixo,
título), o texto da ficha, o laço de uma obra por vez, a espera do 409 «todas as réplicas ocupadas», a parada quando o
conversor cai, o autor no corpo e os exits.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FICHA = REPO / "bin" / "_acervo" / "ficha"
BIN = REPO / "bin" / "acervo"

UUID = "0d9fc4f8-c022-44e3-9979-d66e0ccbdbc0"
OUTRO = "0d9fc4ff-ffff-4444-8888-000000000000"
SHA = "a1" * 32


@pytest.fixture
def mod(monkeypatch):
    loader = importlib.machinery.SourceFileLoader("ficha_teste", str(FICHA))
    spec = importlib.util.spec_from_loader("ficha_teste", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    monkeypatch.setenv("PF_CADEIRA", "claudinho-dados")
    m._esperas = []                                   # o que o cliente esperou, em vez de dormir
    monkeypatch.setattr(m, "_dormir", m._esperas.append)
    return m


class Rota:
    """A rota de dublê: responde por (método, caminho), na ordem em que o cliente pergunta, e guarda o que lhe pediram."""

    def __init__(self, mod, **respostas):
        self.mod, self.respostas, self.chamadas = mod, {k: list(v) for k, v in respostas.items()}, []

    def __call__(self, metodo, caminho, *, params=None, corpo=None, timeout=60):
        self.chamadas.append((metodo, caminho, params, corpo))
        chave = f"{metodo} {caminho}"
        fila = self.respostas.get(chave)
        if not fila:
            raise AssertionError(f"chamada que o teste não previu: {chave} {params} {corpo}")
        r = fila.pop(0) if len(fila) > 1 else fila[0]
        if isinstance(r, Exception):
            raise r
        return r if len(r) == 3 else (r[0], r[1], {})

    def posts(self):
        return [c for c in self.chamadas if c[0] == "POST"]


def _obra(obra_id=UUID, titulo="e-ARQ Brasil: Modelo de Requisitos", **kw):
    return {"id": obra_id, "titulo": titulo, "arquivo": "EARQV203MAI2022.pdf", "objeto": f"acervo/{SHA}",
            "retirada": False, **kw}


def _ficha_da_rota(**extra):
    ficha = {"sha256": SHA, "tamanho": 1550572, "tipo": "application/pdf", "identificacao": "identificado",
             "paginas": 225, "encoding": None, "encoding_declarado": None, "lingua_declarada": "pt-BR",
             "lingua_detectada": "pt", "lingua_confianca": 0.9999, "texto_prefixo_sha1": "8ade6e3db7427c5d8a511cb099b184cbf574633f",
             "texto": {"caracteres": 36923, "nfc": True, "substituicao": 0, "uso_privado": 0, "ligaduras": 0},
             "estrutura_declarada": [{"fonte": "pdf_outline", "entradas": 19, "profundidade": 9}],
             "aplicacoes_criadoras": [{"nome": "Acrobat Distiller", "versao": "5.0", "data": "2007-03-13T20:11:43Z"}],
             "inibidores": [], "erro_leitura": None, "lacunas": {"pdf.glifos": "não medido"},
             "caracterizado_por": {"identificador": {"nome": "conversor", "versao": "1"}, "bibliotecas": {"pypdf": "6.19.0"}},
             "caracterizado_em": "2026-10-06T14:50:11.123+00:00", "versao_ficha": 1}
    ficha.update(extra)
    return {"obra": _obra(), "ficha": ficha, "paginas": {"analisadas": 225, "pedem_ocr": 3},
            "formatos": [{"ordem": 0, "nome": "Acrobat PDF 1.7 - Portable Document Format", "versao": "1.7",
                          "registro": "PRONOM", "chave": "fmt/276", "papel": "identificacao", "mime": "application/pdf",
                          "base": "signature (fido)", "aviso": None}]}


def _colecao(*obras):
    return {"itens": [{"obra_id": i, "titulo": t} for i, t in obras], "proximo": None}


def _resumo(sha=SHA, **kw):
    r = {"sha256": sha, "tamanho": 1550572, "formato": "PDF", "versao": "1.7", "tipo": "application/pdf",
         "identificacao": "identificado", "paginas": 225, "paginas_ocr": 3, "erro_leitura": None}
    r.update(kw)
    return r


def _releitura(obra_id=UUID, tinha=False, aplicado=True, **resumo):
    return 200, {"modo": "aplicado" if aplicado else "plano", "obra_id": obra_id, "objeto": f"acervo/{SHA}",
                 "tinha_ficha": tinha, "ficha": _resumo(**resumo)}


def _cobertura(itens=(), **kw):
    c = {"nao_retiradas": 932, "com_arquivo": 930, "com_ficha": 925, "sem_ficha": len(itens), "sem_arquivo": 2,
         "pdf_sem_paginas": 0, "itens": [{"id": i, "titulo": t, "arquivo": f"{t}.pdf", "objeto": f"acervo/{SHA}"} for i, t in itens],
         "proximo": None}
    c.update(kw)
    return c


# --- a obra ----------------------------------------------------------------------------------------

def test_termo_e_uuid_prefixo_de_6_hex_ou_titulo(mod):
    assert mod.classificar_termo(UUID) == ("uuid", UUID)
    assert mod.classificar_termo("0D9FC4F8") == ("prefixo", "0d9fc4f8")
    assert mod.classificar_termo("0d9fc4") == ("prefixo", "0d9fc4")
    assert mod.classificar_termo("0d9fc")[0] == "titulo"            # menos de 6 hex é título
    assert mod.classificar_termo("e-ARQ Brasil")[0] == "titulo"


def test_uuid_inteiro_vale_como_esta_e_nao_consulta_a_colecao(mod, monkeypatch):
    rota = Rota(mod)
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.resolver_obra(UUID) == {"obra_id": UUID} and rota.chamadas == []


def test_prefixo_se_resolve_pela_colecao_das_obras_vivas(mod, monkeypatch):
    rota = Rota(mod, **{"GET /acervo/obras": [(200, _colecao((UUID, "e-ARQ Brasil"), ("fffe0000-0000-0000-0000-000000000000", "Outra")))]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.resolver_obra("0d9fc4f8")["obra_id"] == UUID
    assert rota.chamadas == [("GET", "/acervo/obras", {"campos": "obra_id,titulo"}, None)]


def test_obra_que_so_existe_entre_as_retiradas_cai_na_segunda_consulta(mod, monkeypatch):
    rota = Rota(mod, **{"GET /acervo/obras": [(200, _colecao(("fffe0000-0000-0000-0000-000000000000", "Outra"))),
                                               (200, _colecao((UUID, "e-ARQ Brasil")))]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.resolver_obra("0d9fc4f8")["obra_id"] == UUID
    assert [c[2].get("retiradas") for c in rota.chamadas] == [None, "true"]


def test_titulo_exato_vence_a_substring_e_acento_e_caixa_nao_contam(mod, monkeypatch):
    itens = _colecao((UUID, "Introdução à Governança"), (OUTRO, "Introdução à Governança de Dados"))
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{"GET /acervo/obras": [(200, itens)]}))
    assert mod.resolver_obra("introducao a governanca")["obra_id"] == UUID
    assert mod.resolver_obra("governanca de dados")["obra_id"] == OUTRO


def test_termo_ambiguo_sai_2_e_lista_os_candidatos(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{"GET /acervo/obras": [(200, _colecao((UUID, "A"), (OUTRO, "B")))]}))
    assert mod.main(["ler", "0d9fc4"]) == 2
    err = capsys.readouterr().err
    assert "ambíguo, 2 obra(s)" in err and UUID in err and OUTRO in err


def test_obra_que_nao_casa_sai_1_com_varrido_e_vizinho(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{"GET /acervo/obras": [(200, _colecao())]}))
    assert mod.main(["ler", "ffffffff"]) == 1
    err = capsys.readouterr().err
    assert "obra não encontrada: ffffffff" in err and "varrido:" in err and "vizinho:" in err


def test_colecao_que_responde_5xx_sai_5_e_nunca_diz_que_nao_achou(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{"GET /acervo/obras": [(503, {"title": "FonteIndisponivel", "detail": "banco fora"})]}))
    assert mod.main(["ler", "0d9fc4f8"]) == 5
    assert "FonteIndisponivel: banco fora" in capsys.readouterr().err


# --- ler -------------------------------------------------------------------------------------------

def test_ler_mostra_a_ficha_em_texto(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [(200, _ficha_da_rota())]}))
    assert mod.main(["ler", UUID]) == 0
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[0] == ("ficha do arquivo · application/pdf · 1.5 MB · identificado · lida em 2026-10-06T14:50:11 "
                         "· obra 0d9fc4f8 «e-ARQ Brasil: Modelo de Requisitos»")
    texto = "\n".join(linhas)
    assert f"objeto: acervo/{SHA} · sha256 {SHA} · 1550572 bytes" in texto
    assert "formato[0]: Acrobat PDF 1.7 - Portable Document Format 1.7 · PRONOM fmt/276 · signature (fido)" in texto
    assert "páginas: 225 · camada de texto por página: 225 lida(s), 3 pede(m) OCR" in texto
    assert "língua: declarada pt-BR · detectada pt (0.9999)" in texto and "inibidores: nenhum" in texto
    assert "estrutura declarada: pdf_outline 19 entradas (prof. 9)" in texto
    assert "criado por: Acrobat Distiller 5.0 (2007-03-13T20:11:43Z)" in texto
    assert "lacunas (1, o que não se mediu): pdf.glifos — não medido" in texto
    assert linhas[-1] == "lida por: conversor 1; pypdf 6.19.0"


def test_ler_diz_quando_a_camada_de_texto_por_pagina_ainda_nao_foi_medida(mod, monkeypatch, capsys):
    d = _ficha_da_rota(erro_leitura="pypdf não abriu o arquivo: PdfStreamError")
    d["paginas"] = {"analisadas": 0, "pedem_ocr": 0}
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [(200, d)]}))
    assert mod.main(["ler", UUID]) == 0
    saida = capsys.readouterr().out
    assert "ainda não carregada (a releitura do PDF a traz)" in saida
    assert "erro de leitura: pypdf não abriu o arquivo: PdfStreamError (um leitor que falha não prova que o arquivo não abre)" in saida


def test_ler_json_devolve_o_que_a_rota_devolveu(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [(200, _ficha_da_rota())]}))
    assert mod.main(["ler", UUID, "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert set(j) == {"obra", "ficha", "paginas", "formatos"} and j["ficha"]["sha256"] == SHA


def test_ler_obra_sem_ficha_sai_1_e_diz_a_cura(mod, monkeypatch, capsys):
    resposta = (404, {"title": "FichaNaoEncontrada", "detail": "Obra 0d9fc4f8 não tem ficha do arquivo no catálogo"})
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [resposta]}))
    assert mod.main(["ler", UUID]) == 1
    err = capsys.readouterr().err
    assert "sem ficha: Obra 0d9fc4f8 não tem ficha" in err
    assert f"vizinho:   acervo ler biblioteca obra {UUID}" in err
    assert f"cura:      acervo ingerir biblioteca ficha {UUID} --apply" in err


def test_ler_obra_inexistente_pelo_uuid_sai_1_sem_dizer_sem_ficha(mod, monkeypatch, capsys):
    resposta = (404, {"title": "ObraNaoEncontrada", "detail": f"Obra {UUID} não encontrada"})
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [resposta]}))
    assert mod.main(["ler", UUID]) == 1
    err = capsys.readouterr().err
    assert "ObraNaoEncontrada" in err and "sem ficha" not in err


def test_ler_com_a_rota_fora_sai_3(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_chamar", Rota(mod, **{f"GET /acervo/obras/{UUID}/ficha": [mod.Falha(3, "rota fora: x")]}))
    assert mod.main(["ler", UUID]) == 3
    assert "rota fora" in capsys.readouterr().err


# --- ingerir: o plano ------------------------------------------------------------------------------

def test_plano_de_sem_ficha_lista_as_obras_e_nao_le_nada(mod, monkeypatch, capsys):
    cob = _cobertura([(UUID, "Nova"), (OUTRO, "Outra")], pdf_sem_paginas=4)
    rota = Rota(mod, **{"GET /acervo/fichas/cobertura": [(200, cob)]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha"]) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("plano: 2 obra(s) não retirada(s) sem ficha, de 932 (930 com arquivo, 2 sem arquivo) · 925 já com ficha")
    assert "2 a ler agora · 4 PDF com ficha e sem a camada de texto por página" in saida
    assert "0d9fc4f8 «Nova» (Nova.pdf)" in saida and "plano seco: nada lido nem gravado" in saida
    assert rota.posts() == []


def test_plano_de_uma_obra_mostra_a_ficha_que_a_leitura_daria_sem_gravar(mod, monkeypatch, capsys):
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [_releitura(aplicado=False, tinha=True)]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID]) == 0
    assert rota.posts()[0][3] == {"autor": "dados", "aplicar": False}
    saida = capsys.readouterr().out
    assert "a leitura de 0d9fc4f8 dá application/pdf · 1.5 MB · identificado · 225 págs (3 pedem OCR)" in saida
    assert "já tinha ficha, que a releitura substitui" in saida and "plano seco: nada gravado" in saida


# --- ingerir: o laço -------------------------------------------------------------------------------

def test_apply_le_cada_obra_com_o_autor_da_cadeira_e_mede_a_cobertura_no_fim(mod, monkeypatch, capsys):
    cob = _cobertura([(UUID, "Nova"), (OUTRO, "Outra")])
    rota = Rota(mod, **{
        "GET /acervo/fichas/cobertura": [(200, cob), (200, _cobertura(sem_ficha=0, com_ficha=930))],
        f"POST /acervo/obras/{UUID}/ficha/releitura": [_releitura(UUID)],
        f"POST /acervo/obras/{OUTRO}/ficha/releitura": [_releitura(OUTRO, tipo="text/markdown", paginas=None, paginas_ocr=None)],
    })
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply", "--paralelo", "1"]) == 0
    assert sorted(c[3]["autor"] for c in rota.posts()) == ["dados", "dados"] and all(c[3]["aplicar"] is True for c in rota.posts())
    saida = capsys.readouterr().out
    assert "feita   0d9fc4f8 application/pdf · 1.5 MB · identificado · 225 págs (3 pedem OCR) «Nova»" in saida
    assert "feita   0d9fc4ff text/markdown · 1.5 MB · identificado «Outra»" in saida
    assert saida.rstrip().endswith("carga: 2 obra(s) lida(s) e gravada(s) · 0 falharam · restam 0 sem ficha de 930 com arquivo")


def test_autor_do_comando_vence_o_da_cadeira(mod, monkeypatch):
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [_releitura()]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID, "--apply", "--autor", "ti"]) == 0
    assert rota.posts()[0][3] == {"autor": "ti", "aplicar": True}


def test_todas_as_replicas_ocupadas_espera_o_retry_after_e_repete(mod, monkeypatch):
    ocupada = (409, {"title": "ConversaoOcupada", "detail": "ocupada"}, {"Retry-After": "7"})
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [ocupada, ocupada, _releitura()]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID, "--apply"]) == 0
    assert len(rota.posts()) == 3 and mod._esperas == [7, 7]


def test_espera_pedida_pelo_servico_tem_teto_e_piso(mod, monkeypatch):
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [
        (409, {"title": "ConversaoOcupada"}, {"Retry-After": "600"}), (409, {"title": "ConversaoOcupada"}, {"Retry-After": "0"}),
        (409, {"title": "ConversaoOcupada"}, {}), _releitura()]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID, "--apply"]) == 0
    assert mod._esperas == [mod.ESPERA_MAX_S, 1, mod.ESPERA_PADRAO_S]


def test_esperas_esgotadas_viram_falha_da_obra_exit_5_sem_gravar(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "TENTATIVAS_OCUPADO", 3)
    ocupada = (409, {"title": "ConversaoOcupada", "detail": "ocupada"}, {"Retry-After": "1"})
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [ocupada]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID, "--apply"]) == 5
    assert len(rota.posts()) == 3 and "seguiram ocupadas depois de 3 esperas" in capsys.readouterr().err


def test_fixidez_quebrada_nao_se_repete_e_a_obra_vai_a_lista_de_falhas(mod, monkeypatch, capsys):
    fixidez = (409, {"title": "FixidezQuebrada", "detail": "o balde entregou bytes de outro sha256"})
    rota = Rota(mod, **{
        "GET /acervo/fichas/cobertura": [(200, _cobertura([(UUID, "Quebrada"), (OUTRO, "Boa")])), (200, _cobertura([(UUID, "Quebrada")], com_ficha=929))],
        f"POST /acervo/obras/{UUID}/ficha/releitura": [fixidez],
        f"POST /acervo/obras/{OUTRO}/ficha/releitura": [_releitura(OUTRO)],
    })
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply", "--paralelo", "1"]) == 1
    saida = capsys.readouterr().out
    assert "falhou  0d9fc4f8 FixidezQuebrada: o balde entregou bytes de outro sha256 «Quebrada»" in saida
    assert "feita   0d9fc4ff" in saida
    assert saida.rstrip().endswith("carga: 1 obra(s) lida(s) e gravada(s) · 1 falharam · restam 1 sem ficha de 930 com arquivo")
    assert len([c for c in rota.posts() if UUID in c[1]]) == 1      # 409 de mérito não se repete


def test_tres_quedas_seguidas_param_o_laco_e_as_que_nao_comecaram_nao_sao_lidas(mod, monkeypatch, capsys):
    obras = [(f"0000000{i}-0000-0000-0000-000000000000", f"O{i}") for i in range(6)]
    fora = (503, {"title": "ConversorIndisponivel", "detail": "caiu"})
    respostas = {"GET /acervo/fichas/cobertura": [(200, _cobertura(obras)), (200, _cobertura(obras))]}
    respostas.update({f"POST /acervo/obras/{i}/ficha/releitura": [fora] for i, _ in obras})
    rota = Rota(mod, **respostas)
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply", "--paralelo", "1"]) == 1
    assert len(rota.posts()) == 3
    cap = capsys.readouterr()
    assert "parei: 3 obras seguidas com o conversor ou o catálogo fora" in cap.err
    assert cap.out.count("falhou  ") == 3 and "3 falharam" in cap.out


def test_falha_de_merito_no_meio_nao_conta_como_queda_e_o_laco_segue(mod, monkeypatch, capsys):
    obras = [(f"0000000{i}-0000-0000-0000-000000000000", f"O{i}") for i in range(5)]
    sem_arquivo = (422, {"title": "ObraSemArquivo", "detail": "catalogada sem arquivo"})
    respostas = {"GET /acervo/fichas/cobertura": [(200, _cobertura(obras)), (200, _cobertura(obras[:4]))]}
    respostas.update({f"POST /acervo/obras/{i}/ficha/releitura": [sem_arquivo if n < 4 else _releitura(i)]
                      for n, (i, _) in enumerate(obras)})
    rota = Rota(mod, **respostas)
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply", "--paralelo", "1"]) == 1
    assert len(rota.posts()) == 5 and "parei" not in capsys.readouterr().err


def test_limite_corta_a_lista_e_o_paralelo_atende_varias_ao_mesmo_tempo(mod, monkeypatch, capsys):
    obras = [(f"0000000{i}-0000-0000-0000-000000000000", f"O{i}") for i in range(6)]
    respostas = {"GET /acervo/fichas/cobertura": [(200, _cobertura(obras)), (200, _cobertura(obras[2:]))]}
    respostas.update({f"POST /acervo/obras/{i}/ficha/releitura": [_releitura(i)] for i, _ in obras})
    rota = Rota(mod, **respostas)
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply", "--limite", "2", "--paralelo", "4"]) == 0
    assert sorted(c[1].split("/")[3] for c in rota.posts()) == [obras[0][0], obras[1][0]]
    assert "carga: 2 obra(s) lida(s) e gravada(s) · 0 falharam · restam 4 sem ficha" in capsys.readouterr().out


def test_sem_nada_a_ler_diz_que_ja_esta_tudo_e_nao_chama_a_leitura(mod, monkeypatch, capsys):
    rota = Rota(mod, **{"GET /acervo/fichas/cobertura": [(200, _cobertura([], com_ficha=930))]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", "--sem-ficha", "--apply"]) == 0
    assert "carga: nada a ler · 930 de 930 obras com arquivo já têm ficha" in capsys.readouterr().out and rota.posts() == []


def test_uma_obra_com_apply_grava_e_diz_se_ja_tinha_ficha(mod, monkeypatch, capsys):
    rota = Rota(mod, **{f"POST /acervo/obras/{UUID}/ficha/releitura": [_releitura(tinha=True)]})
    monkeypatch.setattr(mod, "_chamar", rota)
    assert mod.main(["ingerir", UUID, "--apply"]) == 0
    assert capsys.readouterr().out.startswith("gravada: obra 0d9fc4f8 · application/pdf · 1.5 MB · identificado · 225 págs (3 pedem OCR) · já tinha ficha")


@pytest.mark.parametrize("argv", [
    [], ["ler"], ["ler", "--x"], ["ingerir"], ["ingerir", "--sem-ficha", UUID], ["ingerir", UUID, "outra"],
    ["ingerir", "--sem-ficha", "--paralelo", "9"], ["ingerir", "--sem-ficha", "--paralelo", "0"],
    ["ingerir", "--sem-ficha", "--paralelo", "x"], ["ingerir", "--sem-ficha", "--limite", "0"],
    ["ingerir", "--sem-ficha", "--paralelo"], ["ingerir", "--sem-ficha", "--outra"], ["carregar", "x.jsonl"], ["--ajuda"],
])
def test_uso_errado_sai_2_com_a_usage_e_antes_de_chamar_a_rota(mod, monkeypatch, capsys, argv):
    monkeypatch.setattr(mod, "_chamar", lambda *a, **k: pytest.fail("não podia chamar a rota"))
    assert mod.main(argv) == 2
    assert "acervo ler biblioteca ficha <obra>" in capsys.readouterr().err


# --- o verbo é cliente fino (arq:0089) -------------------------------------------------------------

def test_o_verbo_nao_abre_o_banco_nem_o_balde_nem_roda_programa(mod):
    fonte = FICHA.read_text(encoding="utf-8")
    for proibido in ("docker", "psql", "subprocess", "boto3", "minio", "psycopg"):
        assert proibido not in fonte.lower(), f"arq:0089 §2: o verbo é cliente da rota e não usa {proibido}"


# --- o despachante ---------------------------------------------------------------------------------

def _acervo(*args, env=None):
    return subprocess.run([str(BIN), *args], capture_output=True, text=True, env={**os.environ, **(env or {})})


ROTA_FECHADA = {"MOTOR_ACERVO_URL": "http://127.0.0.1:9", "RAG_API_URL": "", "RAG_API_BASE": ""}


def test_a_usage_do_acervo_lista_as_duas_formas_da_ficha():
    r = _acervo("--ajuda")
    assert r.returncode == 2
    assert "acervo ler      biblioteca ficha <obra> [--json]" in r.stderr
    assert "acervo ingerir  biblioteca ficha <obra> | --sem-ficha [--apply]" in r.stderr


@pytest.mark.parametrize("args", [("ler", "biblioteca", "ficha"), ("ingerir", "biblioteca", "ficha")])
def test_as_rotas_da_ficha_sem_argumento_saem_2_com_a_usage_da_ficha(args):
    r = _acervo(*args)
    assert r.returncode == 2 and "acervo ler biblioteca ficha <obra>" in r.stderr


def test_ingerir_biblioteca_ficha_nao_cai_no_ramo_da_pasta_de_ingestao():
    # `ficha` seria lido como raiz de pasta pelo ramo genérico, que ia ao cliente de obra; a rota própria chega no cliente da ficha
    r = _acervo("ingerir", "biblioteca", "ficha", "--ajuda-da-ficha")
    assert r.returncode == 2 and "acervo ingerir biblioteca ficha <obra> | --sem-ficha" in r.stderr


@pytest.mark.parametrize("args", [("ler", "biblioteca", "ficha", UUID), ("ingerir", "biblioteca", "ficha", "--sem-ficha")])
def test_com_a_rota_fora_sai_3_e_nunca_diz_que_nao_ha_ficha(args):
    r = _acervo(*args, env=ROTA_FECHADA)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "sem ficha" not in r.stdout + r.stderr
