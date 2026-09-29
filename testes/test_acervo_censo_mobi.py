"""card #3189, ato temporário: testes do leitor de MOBI (censo_mobi) com arquivos sintéticos montados com struct."""

import os
import random
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "_acervo"))

import censo_mobi  # noqa: E402

SEM = 0xFFFFFFFF
CHAVES = {
    "mobi",
    "aplicacoes_criadoras",
    "inibidor",
    "lingua_declarada",
    "estrutura_declarada",
    "encoding",
    "_texto",
    "_paginas",
    "lacunas",
    "bibliotecas",
    "erro",
}
CHAVES_BLOCO = {
    "palmdb": {"nome", "atributos", "tipo", "criador", "versao", "n_registros", "criacao", "modificacao", "backup"},
    "palmdoc": {"compressao", "tamanho_texto", "registros_texto", "tamanho_registro", "criptografia"},
    "mobi": {
        "presente",
        "tamanho_cabecalho",
        "tipo_mobi",
        "encoding_texto",
        "uid",
        "versao",
        "familia",
        "combinado",
        "locale",
    },
    "drm": {"presente", "offset", "criptografia_palmdoc"},
    "exth": {
        "presente",
        "n_registros",
        "autor",
        "editora",
        "isbn",
        "lingua",
        "criador_software_codigo",
        "criador_software_versao",
        "cdetype",
        "boundary",
        "descricao",
        "data_publicacao",
        "asin",
        "n_recursos",
        "capa_offset",
        "titulo_atualizado",
        "tipos_vistos",
    },
}


# ---------- montagem de MOBI sintético ----------


def _exth(registros):
    """Bloco EXTH: cabeçalho, registros (tipo, tamanho, dados) e enchimento até múltiplo de 4."""
    corpo = b"".join(struct.pack(">II", tipo, 8 + len(dado)) + dado for tipo, dado in registros)
    bloco = b"EXTH" + struct.pack(">II", 12 + len(corpo), len(registros)) + corpo
    return bloco + bytes((-len(bloco)) % 4)


def _u32(valor):
    return struct.pack(">I", valor)


def _registro0(versao=6, tam_cab=232, exth=None, cripto=0, compressao=2, encoding=65001, drm_offset=SEM,
               locale=0x16, tipo_mobi=2, uid=0xABCD1234, texto=123456, n_texto=30, tam_reg=4096):
    """Registro 0: PalmDOC (16 bytes) + cabeçalho MOBI de `tam_cab` bytes (+ EXTH). Só grava o que cabe."""
    r = bytearray(16 + tam_cab)
    struct.pack_into(">HHIHHHH", r, 0, compressao, 0, texto, n_texto, tam_reg, cripto, 0)
    r[16:20] = b"MOBI"

    def poe(pos, valor):
        if pos + 4 <= len(r):
            struct.pack_into(">I", r, pos, valor)

    poe(20, tam_cab)
    poe(24, tipo_mobi)
    poe(28, encoding)
    poe(32, uid)
    poe(36, versao)
    poe(92, locale)
    poe(128, 0x40 if exth else 0)
    poe(168, drm_offset)
    poe(172, 0 if drm_offset == SEM else 1)
    return bytes(r) + (exth or b"")


def _montar(registros, tipo=b"BOOK", criador=b"MOBI", nome=b"Livro de Teste", criacao=1600000000,
            modificacao=1600003600, backup=0):
    """Contêiner PalmDB: cabeçalho de 78 bytes, lista de registros, 2 bytes de folga e os registros."""
    n = len(registros)
    pos = 78 + 8 * n + 2
    lista = b""
    for i, reg in enumerate(registros):
        lista += struct.pack(">IB3s", pos, 0, i.to_bytes(3, "big"))
        pos += len(reg)
    cab = struct.pack(">32sHHIIIIII4s4sIIH", nome, 0, 0, criacao, modificacao, backup, 0, 0, 0,
                      tipo, criador, 0, 0, n)
    return cab + lista + bytes(2) + b"".join(registros)


def _exth_kf7():
    return _exth([
        (100, "José da Silva".encode("utf-8")),
        (101, "Editora Exemplo".encode("utf-8")),
        (103, "Uma descrição curta".encode("utf-8")),
        (104, b"9788500000000"),
        (106, b"2020-09-13"),
        (113, b"B000TESTE1"),
        (125, _u32(30)),
        (201, _u32(4)),
        (204, _u32(201)),
        (205, _u32(2)),
        (206, _u32(9)),
        (207, _u32(1028)),
        (501, b"EBOK"),
        (503, "Título Atualizado".encode("utf-8")),
        (524, b"pt-BR"),
    ])


def _kf7():
    return _montar([_registro0(versao=6, exth=_exth_kf7()), b"texto um", b"texto dois"])


def _kf8():
    return _montar([_registro0(versao=8, tam_cab=248, exth=_exth([(524, b"en")])), b"texto"])


def _combinado(com_121=True, com_registro=True):
    exth = [(524, b"pt")]
    if com_121:
        exth.append((121, _u32(3)))
    registros = [_registro0(versao=6, exth=_exth(exth)), b"texto kf7"]
    if com_registro:
        registros.append(b"BOUNDARY")
    registros += [_registro0(versao=8, tam_cab=248, exth=_exth([(524, b"pt")])), b"texto kf8"]
    return _montar(registros)


def _ler(dados, prazo_s=30.0):
    return censo_mobi.ler(dados, {"nome_original": "livro.mobi", "formato_id": "mobi", "bytes": len(dados),
                                  "prazo_s": prazo_s})


def _forma_ok(ficha):
    assert set(ficha) == CHAVES
    assert ficha["erro"] is None or ficha["erro"].startswith(("arquivo com", "PalmDB com tipo")), ficha["erro"]
    assert set(ficha["mobi"]) == set(CHAVES_BLOCO)
    for sub, chaves in CHAVES_BLOCO.items():
        assert set(ficha["mobi"][sub]) == chaves, sub
    assert "_texto" not in ficha["mobi"] and "_paginas" not in ficha["mobi"]
    assert ficha["_texto"] is None and ficha["_paginas"] is None and ficha["encoding"] is None
    assert ficha["estrutura_declarada"] == []
    assert ficha["bibliotecas"] == {"struct-proprio": "censo-3189"}
    assert ficha["lacunas"]["biblioteca"] == (
        "sem biblioteca livre de MOBI de licença permissiva; leitor próprio de cabeçalho")
    assert ficha["lacunas"]["estrutura"] == "índice/NCX do MOBI não lido no censo"
    assert ficha["lacunas"]["texto"] == "texto MOBI (LZ77/HUFF) não descomprimido no censo: sem conversão"


# ---------- KF7, KF8, combinado ----------


def test_kf7_versao_6_com_exth():
    f = _ler(_kf7())
    _forma_ok(f)
    assert f["erro"] is None
    b = f["mobi"]
    assert b["palmdb"] == {"nome": "Livro de Teste", "atributos": 0, "tipo": "BOOK", "criador": "MOBI", "versao": 0,
                           "n_registros": 3, "criacao": "2020-09-13T12:26:40Z",
                           "modificacao": "2020-09-13T13:26:40Z", "backup": None}
    assert b["palmdoc"] == {"compressao": 2, "tamanho_texto": 123456, "registros_texto": 30,
                            "tamanho_registro": 4096, "criptografia": 0}
    assert b["mobi"] == {"presente": True, "tamanho_cabecalho": 232, "tipo_mobi": 2, "encoding_texto": 65001,
                         "uid": 0xABCD1234, "versao": 6, "familia": "KF7", "combinado": False, "locale": 0x16}
    assert b["drm"] == {"presente": False, "offset": None, "criptografia_palmdoc": 0}
    ex = b["exth"]
    assert ex["presente"] is True and ex["n_registros"] == 15
    assert ex["autor"] == "José da Silva"
    assert ex["editora"] == "Editora Exemplo"
    assert ex["descricao"] == "Uma descrição curta"
    assert ex["isbn"] == "9788500000000"
    assert ex["data_publicacao"] == "2020-09-13"
    assert ex["asin"] == "B000TESTE1"
    assert ex["n_recursos"] == 30 and ex["capa_offset"] == 4
    assert ex["lingua"] == "pt-BR" and ex["cdetype"] == "EBOK"
    assert ex["titulo_atualizado"] == "Título Atualizado"
    assert ex["criador_software_codigo"] == 201 and ex["criador_software_versao"] == "2.9.1028"
    assert ex["boundary"] is None
    assert ex["tipos_vistos"] == [100, 101, 103, 104, 106, 113, 125, 201, 204, 205, 206, 207, 501, 503, 524]
    assert f["lingua_declarada"] == "pt-BR"
    assert f["aplicacoes_criadoras"] == [{"nome": "kindlegen", "versao": "2.9.1028", "data": None, "fonte": "exth"}]
    assert f["inibidor"] is None
    assert "prazo" not in f["lacunas"] and "registros" not in f["lacunas"]


def test_kf8_versao_8():
    f = _ler(_kf8())
    _forma_ok(f)
    assert f["erro"] is None
    m = f["mobi"]["mobi"]
    assert m["versao"] == 8 and m["familia"] == "KF8" and m["combinado"] is False
    assert m["tamanho_cabecalho"] == 248
    assert f["mobi"]["exth"]["presente"] is True
    assert f["lingua_declarada"] == "en"
    assert f["aplicacoes_criadoras"] == []


def test_combinado_com_exth_121_e_registro_boundary():
    f = _ler(_combinado())
    _forma_ok(f)
    m = f["mobi"]["mobi"]
    assert m["versao"] == 6 and m["combinado"] is True and m["familia"] == "KF7+KF8"
    assert f["mobi"]["exth"]["boundary"] == 3
    assert 121 in f["mobi"]["exth"]["tipos_vistos"]
    assert "exth.boundary" not in f["lacunas"]


def test_combinado_so_com_exth_121():
    f = _ler(_combinado(com_registro=False))
    assert f["mobi"]["mobi"]["combinado"] is True and f["mobi"]["mobi"]["familia"] == "KF7+KF8"


def test_combinado_so_com_registro_boundary():
    f = _ler(_combinado(com_121=False))
    assert f["mobi"]["exth"]["boundary"] is None
    assert f["mobi"]["mobi"]["combinado"] is True and f["mobi"]["mobi"]["familia"] == "KF7+KF8"


def test_exth_121_sem_valor_nao_combina():
    exth = _exth([(121, _u32(SEM))])
    f = _ler(_montar([_registro0(versao=6, exth=exth), b"texto"]))
    assert f["mobi"]["exth"]["boundary"] is None and 121 in f["mobi"]["exth"]["tipos_vistos"]
    assert f["mobi"]["mobi"]["combinado"] is False and f["mobi"]["mobi"]["familia"] == "KF7"


def test_boundary_aponta_para_registro_fora_da_lista_vira_lacuna():
    exth = _exth([(121, _u32(99))])
    f = _ler(_montar([_registro0(versao=6, exth=exth), b"texto"]))
    assert f["mobi"]["mobi"]["combinado"] is True
    assert "exth.boundary" in f["lacunas"]


def test_versao_desconhecida_nao_tem_familia():
    f = _ler(_montar([_registro0(versao=5, exth=_exth([(524, b"en")])), b"texto"]))
    assert f["mobi"]["mobi"]["versao"] == 5 and f["mobi"]["mobi"]["familia"] is None


# ---------- TEXtREAd, tipo estranho, curtos ----------


def test_textread_sem_cabecalho_mobi():
    r0 = struct.pack(">HHIHHI", 2, 0, 5000, 2, 4096, 70000)  # PalmDOC puro: offset 12 é a posição de leitura
    r0 += bytes(40)
    f = _ler(_montar([r0, b"texto"], tipo=b"TEXt", criador=b"REAd"))
    _forma_ok(f)
    assert f["erro"] is None
    b = f["mobi"]
    assert b["palmdb"]["tipo"] == "TEXt" and b["palmdb"]["criador"] == "REAd"
    assert b["palmdoc"]["compressao"] == 2 and b["palmdoc"]["tamanho_texto"] == 5000
    assert b["palmdoc"]["criptografia"] is None and "palmdoc.criptografia" in f["lacunas"]
    assert b["mobi"]["presente"] is False and b["mobi"]["familia"] is None and b["mobi"]["combinado"] is None
    assert "mobi" in f["lacunas"]
    assert b["exth"]["presente"] is False
    assert b["drm"]["presente"] is None and "drm" in f["lacunas"]
    assert f["inibidor"] is None and f["aplicacoes_criadoras"] == [] and f["lingua_declarada"] is None


def test_caixa_do_tipo_importa():
    f = _ler(_montar([_registro0(), b"x"], tipo=b"book", criador=b"mobi"))
    _forma_ok(f)
    assert f["erro"] is not None and chr(10) not in f["erro"]
    assert f["mobi"]["palmdb"]["tipo"] == "book"
    assert f["mobi"]["mobi"]["presente"] is True  # o que os bytes derem


def test_tipo_e_criador_estranhos_dao_erro_mas_lem_o_que_da():
    f = _ler(_montar([bytes(40), b"x"], tipo=b"ABCD", criador=b"EFGH"))
    _forma_ok(f)
    assert f["erro"] is not None and "ABCD" in f["erro"]
    assert f["mobi"]["palmdb"]["n_registros"] == 2
    assert f["mobi"]["mobi"]["presente"] is False


def test_arquivo_de_10_bytes():
    f = _ler(b"0123456789")
    _forma_ok(f)
    assert f["erro"] is not None and "10 bytes" in f["erro"]
    assert all(v is None for v in f["mobi"]["palmdb"].values())
    assert f["mobi"]["mobi"]["presente"] is None and "mobi" in f["lacunas"]
    assert f["inibidor"] is None and f["aplicacoes_criadoras"] == []


def test_arquivo_vazio_e_bytes_quaisquer():
    for dados in (b"", b"A" * 200, bytes(300), b"BOOKMOBI" * 40):
        f = _ler(dados)
        _forma_ok(f)
        assert f["erro"] is not None


def test_palmdb_pela_metade_da_o_que_cabe():
    f = _ler(_kf7()[:66])
    _forma_ok(f)
    p = f["mobi"]["palmdb"]
    assert f["erro"] is not None
    assert p["nome"] == "Livro de Teste" and p["criacao"] == "2020-09-13T12:26:40Z"
    assert p["tipo"] == "BOOK" and p["criador"] is None and p["n_registros"] is None


# ---------- DRM ----------


def test_drm_por_criptografia_palmdoc():
    f = _ler(_montar([_registro0(cripto=2, drm_offset=0x1F0), b"texto"]))
    d = f["mobi"]["drm"]
    assert d == {"presente": True, "offset": 0x1F0, "criptografia_palmdoc": 2}
    assert f["inibidor"] == {"tipo": "DRM", "alvo": "palmdoc.criptografia=2"}


def test_drm_so_pela_criptografia_antiga():
    f = _ler(_montar([_registro0(cripto=1), b"texto"]))
    assert f["mobi"]["drm"] == {"presente": True, "offset": None, "criptografia_palmdoc": 1}
    assert f["inibidor"] == {"tipo": "DRM", "alvo": "palmdoc.criptografia=1"}


def test_drm_so_pelo_offset():
    f = _ler(_montar([_registro0(cripto=0, drm_offset=0x2A0), b"texto"]))
    assert f["mobi"]["drm"] == {"presente": True, "offset": 0x2A0, "criptografia_palmdoc": 0}
    assert f["inibidor"] == {"tipo": "DRM", "alvo": "mobi.drm_offset=672"}


def test_sem_drm_offset_ffffffff():
    f = _ler(_kf7())
    assert f["mobi"]["drm"]["presente"] is False and f["mobi"]["drm"]["offset"] is None
    assert f["inibidor"] is None


# ---------- cabeçalho MOBI curto ----------


def test_cabecalho_de_116_bytes_cobre_flags_mas_nao_drm():
    exth = _exth([(524, b"fr")])
    f = _ler(_montar([_registro0(versao=4, tam_cab=116, exth=exth), b"texto"]))
    m = f["mobi"]["mobi"]
    assert m["tamanho_cabecalho"] == 116 and m["versao"] == 4 and m["locale"] == 0x16
    assert f["mobi"]["exth"]["presente"] is True and f["lingua_declarada"] == "fr"
    assert f["mobi"]["drm"]["offset"] is None and "drm.offset" in f["lacunas"]
    assert f["mobi"]["drm"]["presente"] is False  # só a criptografia PalmDOC (0) foi lida


def test_cabecalho_curto_demais_para_flags_e_locale():
    f = _ler(_montar([_registro0(versao=3, tam_cab=60), b"texto"]))
    m = f["mobi"]["mobi"]
    assert m["versao"] == 3 and m["locale"] is None
    assert "mobi.locale" in f["lacunas"] and "mobi.flags_exth" in f["lacunas"]
    assert f["mobi"]["exth"]["presente"] is None
    assert f["mobi"]["mobi"]["familia"] is None and f["mobi"]["mobi"]["combinado"] is None


def test_flag_exth_ligado_sem_bloco():
    r0 = bytearray(_registro0(versao=6, exth=_exth([(524, b"pt")])))
    r0[248:252] = b"XXXX"  # estraga o identificador EXTH
    f = _ler(_montar([bytes(r0), b"texto"]))
    assert f["mobi"]["exth"]["presente"] is False and "exth" in f["lacunas"]
    assert f["lingua_declarada"] is None


def test_flag_exth_desligado():
    f = _ler(_montar([_registro0(versao=6), b"texto"]))
    assert f["mobi"]["exth"]["presente"] is False and f["lingua_declarada"] is None
    assert f["mobi"]["exth"]["tipos_vistos"] == []


# ---------- EXTH em detalhe ----------


def test_exth_texto_em_cp1252():
    exth = _exth([(100, "José".encode("cp1252")), (524, b"pt")])
    f = _ler(_montar([_registro0(encoding=1252, exth=exth), b"texto"]))
    assert f["mobi"]["mobi"]["encoding_texto"] == 1252
    assert f["mobi"]["exth"]["autor"] == "José"


def test_exth_varios_autores_e_repetidos():
    exth = _exth([(100, b"Ana"), (100, b"Bia"), (100, b"Ana"), (524, b"pt")])
    f = _ler(_montar([_registro0(exth=exth), b"texto"]))
    assert f["mobi"]["exth"]["autor"] == "Ana; Bia"
    assert f["mobi"]["exth"]["tipos_vistos"] == [100, 524]


def test_exth_codigo_de_criador_desconhecido_e_versao_incompleta():
    exth = _exth([(204, _u32(999)), (205, _u32(1)), (207, _u32(5))])
    f = _ler(_montar([_registro0(exth=exth), b"texto"]))
    ex = f["mobi"]["exth"]
    assert ex["criador_software_codigo"] == 999 and ex["criador_software_versao"] is None
    assert f["aplicacoes_criadoras"] == [{"nome": "codigo-204=999", "versao": None, "data": None, "fonte": "exth"}]


def test_exth_sem_204_nao_gera_aplicacao():
    f = _ler(_montar([_registro0(exth=_exth([(205, _u32(2)), (206, _u32(9)), (207, _u32(1))])), b"texto"]))
    assert f["aplicacoes_criadoras"] == []
    assert f["mobi"]["exth"]["criador_software_versao"] == "2.9.1"


def test_exth_tipos_vistos_ordenados_e_sem_repeticao():
    exth = _exth([(524, b"pt"), (999, b"x"), (100, b"A"), (524, b"pt"), (1, b"")])
    f = _ler(_montar([_registro0(exth=exth), b"texto"]))
    assert f["mobi"]["exth"]["tipos_vistos"] == [1, 100, 524, 999]
    assert f["mobi"]["exth"]["n_registros"] == 5


def test_exth_registro_alem_do_fim_vira_lacuna_e_guarda_o_que_leu():
    bom = _exth([(524, b"pt"), (100, b"Ana")])
    cru = bytearray(bom)
    struct.pack_into(">I", cru, 8, 3)  # declara 3 registros; só há 2
    f = _ler(_montar([_registro0(exth=bytes(cru)), b"texto"]))
    assert f["lingua_declarada"] == "pt" and f["mobi"]["exth"]["autor"] == "Ana"
    assert "exth" in f["lacunas"] and "3" in f["lacunas"]["exth"]


def test_exth_registro_com_tamanho_absurdo():
    exth = bytearray(_exth([(524, b"pt"), (100, b"Ana")]))
    struct.pack_into(">I", exth, 12 + 4, 0x7FFFFFF0)  # tamanho do primeiro registro
    f = _ler(_montar([_registro0(exth=bytes(exth)), b"texto"]))
    assert f["lingua_declarada"] is None and "exth" in f["lacunas"]


def test_exth_texto_longo_e_cortado():
    exth = _exth([(103, b"a" * 5000)])
    f = _ler(_montar([_registro0(exth=exth), b"texto"]))
    assert len(f["mobi"]["exth"]["descricao"]) == 2000


# ---------- limites e truncamento ----------


def test_truncado_no_meio_do_registro_0():
    dados = _kf7()
    corte = 78 + 8 * 3 + 2 + 100  # a 100 bytes do começo do registro 0
    f = _ler(dados[:corte])
    _forma_ok(f)
    assert f["mobi"]["palmdb"]["n_registros"] == 3
    assert f["mobi"]["mobi"]["presente"] is True and f["mobi"]["mobi"]["versao"] == 6
    assert f["mobi"]["mobi"]["locale"] == 0x16
    assert f["mobi"]["exth"]["presente"] is None
    assert f["mobi"]["mobi"]["combinado"] is None and f["mobi"]["mobi"]["familia"] is None
    assert "combinado" in f["lacunas"]


def test_truncado_no_meio_do_exth():
    dados = _kf7()
    r0_ini = 78 + 8 * 3 + 2
    f = _ler(dados[:r0_ini + 248 + 60])
    _forma_ok(f)
    assert f["mobi"]["exth"]["presente"] is True
    assert f["mobi"]["exth"]["autor"] == "José da Silva"
    assert "exth" in f["lacunas"]
    assert f["mobi"]["mobi"]["combinado"] is None and f["mobi"]["mobi"]["familia"] is None


def test_truncado_antes_do_registro_0():
    dados = _kf7()
    f = _ler(dados[:78 + 8 * 3])
    _forma_ok(f)
    assert f["mobi"]["palmdb"]["n_registros"] == 3
    assert "mobi" in f["lacunas"]


def test_lista_de_registros_maior_que_o_arquivo():
    dados = bytearray(_kf7())
    struct.pack_into(">H", dados, 76, 5000)
    f = _ler(bytes(dados))
    assert f["mobi"]["palmdb"]["n_registros"] == 5000
    assert "registros" in f["lacunas"]
    assert f["mobi"]["mobi"]["versao"] == 6 and f["mobi"]["mobi"]["combinado"] is None


def test_offsets_decrescentes():
    dados = bytearray(_kf7())
    struct.pack_into(">I", dados, 78 + 8 * 2, 90)  # registro 2 começa antes do 1
    f = _ler(bytes(dados))
    _forma_ok(f)
    assert "registros" in f["lacunas"] and "menor" in f["lacunas"]["registros"]
    assert f["mobi"]["mobi"]["versao"] == 6 and f["mobi"]["mobi"]["combinado"] is None


def test_registro_fora_do_arquivo():
    dados = bytearray(_kf7())
    struct.pack_into(">I", dados, 78 + 8 * 1, len(dados) + 1000)
    f = _ler(bytes(dados))
    assert "registros" in f["lacunas"] and "depois do fim" in f["lacunas"]["registros"]


def test_registro_0_fora_do_arquivo():
    dados = bytearray(_kf7())
    struct.pack_into(">I", dados, 78, len(dados) + 10)
    f = _ler(bytes(dados))
    assert "registros" in f["lacunas"] and "mobi" in f["lacunas"]
    assert f["mobi"]["mobi"]["presente"] is None


def test_palmdb_sem_registros():
    dados = bytearray(_kf7())
    struct.pack_into(">H", dados, 76, 0)
    f = _ler(bytes(dados))
    _forma_ok(f)
    assert f["mobi"]["palmdb"]["n_registros"] == 0 and "mobi" in f["lacunas"]


def test_tamanho_do_cabecalho_maior_que_o_registro():
    r0 = bytearray(_registro0(versao=6, tam_cab=232))
    struct.pack_into(">I", r0, 20, 5000)
    f = _ler(_montar([bytes(r0), b"texto"]))
    assert f["mobi"]["mobi"]["tamanho_cabecalho"] == 5000
    assert "mobi.tamanho_cabecalho" in f["lacunas"]


# ---------- datas ----------


def test_datas_1970_e_1904():
    f = _ler(_montar([_registro0(), b"x"], criacao=1600000000, modificacao=1600000000 + 2082844800, backup=0))
    p = f["mobi"]["palmdb"]
    assert p["criacao"] == "2020-09-13T12:26:40Z"
    assert p["modificacao"] == "2020-09-13T12:26:40Z"
    assert p["backup"] is None


def test_data_zero_e_data_absurda():
    f = _ler(_montar([_registro0(), b"x"], criacao=0, modificacao=SEM))
    assert f["mobi"]["palmdb"]["criacao"] is None
    assert f["mobi"]["palmdb"]["modificacao"] is not None  # 1904 + 2^32 s ainda é uma data válida


def test_nome_palmdb_ate_o_nul_e_utf8_cortado():
    nome = "Título".encode("utf-8") + bytes(3) + b"lixo"
    f = _ler(_montar([_registro0(), b"x"], nome=nome))
    assert f["mobi"]["palmdb"]["nome"] == "Título"
    cheio = ("ab" * 15 + "c" + "é").encode("utf-8")  # 33 bytes: o corte de 32 parte o "é"
    f = _ler(_montar([_registro0(), b"x"], nome=cheio))
    assert f["mobi"]["palmdb"]["nome"] == "ab" * 15 + "c"


# ---------- prazo, determinismo, robustez ----------


def test_prazo_estourado_devolve_parcial_com_lacuna():
    f = _ler(_kf7(), prazo_s=0.0)
    _forma_ok(f)
    assert "prazo" in f["lacunas"]
    assert f["mobi"]["palmdb"]["tipo"] == "BOOK"
    assert f["mobi"]["mobi"]["versao"] == 6
    assert f["mobi"]["exth"]["presente"] is None  # EXTH não chegou a ser lido
    assert f["mobi"]["mobi"]["combinado"] is None and f["mobi"]["mobi"]["familia"] is None


def test_mesma_entrada_mesma_saida():
    dados = _combinado()
    assert _ler(dados) == _ler(dados)
    assert _ler(dados) is not _ler(dados)


def test_contexto_sem_prazo_nao_quebra():
    f = censo_mobi.ler(_kf7(), {"formato_id": "mobi"})
    assert f["erro"] is None and f["mobi"]["mobi"]["versao"] == 6


def test_nunca_levanta_em_nenhum_prefixo():
    dados = _combinado()
    for corte in range(len(dados) + 1):
        _forma_ok(_ler(dados[:corte]))


def test_nunca_levanta_com_bytes_corrompidos():
    base = _kf7()
    sorteio = random.Random(3189)
    for _ in range(300):
        dados = bytearray(base)
        for _ in range(sorteio.randint(1, 6)):
            dados[sorteio.randrange(len(dados))] = sorteio.randrange(256)
        _forma_ok(_ler(bytes(dados)))
