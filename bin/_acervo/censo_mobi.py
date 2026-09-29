"""card #3189, ato temporário: lê os cabeçalhos de um MOBI (PalmDB, PalmDOC, MOBI, EXTH) só com struct.

Sem biblioteca de terceiros: a única biblioteca de MOBI conhecida é GPL. Não descomprime o texto
nem lê índices; só o que os cabeçalhos dizem. Nunca levanta: o que não dá para ler fica None e o
motivo vai em lacunas.
"""

import codecs
import struct
import time
from datetime import datetime, timedelta, timezone

_TAM_PALMDB = 78  # cabeçalho PalmDB, antes da lista de registros
_SEM_VALOR = 0xFFFFFFFF  # offset de DRM / limite KF8 "ausente"
_FLAG_EXTH = 0x40  # bit "há bloco EXTH" nos flags do cabeçalho MOBI
_LIMITE_TEXTO = 2000  # corte dos textos do EXTH dentro do bloco
_TIPOS_PALMDB = (("BOOK", "MOBI"), ("TEXt", "REAd"))  # tipo, criador; a caixa importa
_A_CADA = 1024  # de quantas em quantas voltas de laço se confere o prazo

# EXTH: tipo -> campo do bloco
_EXTH_TEXTO = {
    100: "autor",
    101: "editora",
    103: "descricao",
    104: "isbn",
    106: "data_publicacao",
    113: "asin",
    501: "cdetype",
    503: "titulo_atualizado",
    524: "lingua",
}
_EXTH_INTEIRO = {121: "boundary", 125: "n_recursos", 201: "capa_offset", 204: "criador_software_codigo"}
_EXTH_VERSAO = (205, 206, 207)  # versão maior, menor e build do criador

# código EXTH 204; as tabelas públicas divergem quanto ao sistema do kindlegen, então só a família
_CRIADORES = {1: "mobigen", 2: "Mobipocket Creator"}
_FAIXA_KINDLEGEN = range(200, 204)


def ler(dados, ctx):
    """Lê os cabeçalhos do MOBI em `dados` e devolve a ficha do formato; nunca levanta."""
    ficha = _ficha_vazia()
    try:
        _ler_cabecalhos(dados, ctx, ficha)
        _envelope(ficha)
    except Exception as exc:  # falha inesperada vai em erro; o parcial fica na ficha
        ficha["erro"] = _uma_linha("%s: %s" % (type(exc).__name__, exc))
    return ficha


def _ficha_vazia():
    return {
        "mobi": {
            "palmdb": {
                "nome": None,
                "atributos": None,
                "tipo": None,
                "criador": None,
                "versao": None,
                "n_registros": None,
                "criacao": None,
                "modificacao": None,
                "backup": None,
            },
            "palmdoc": {
                "compressao": None,
                "tamanho_texto": None,
                "registros_texto": None,
                "tamanho_registro": None,
                "criptografia": None,
            },
            "mobi": {
                "presente": None,
                "tamanho_cabecalho": None,
                "tipo_mobi": None,
                "encoding_texto": None,
                "uid": None,
                "versao": None,
                "familia": None,
                "combinado": None,
                "locale": None,
            },
            "drm": {"presente": None, "offset": None, "criptografia_palmdoc": None},
            "exth": {
                "presente": None,
                "n_registros": None,
                "autor": None,
                "editora": None,
                "isbn": None,
                "lingua": None,
                "criador_software_codigo": None,
                "criador_software_versao": None,
                "cdetype": None,
                "boundary": None,
                "descricao": None,
                "data_publicacao": None,
                "asin": None,
                "n_recursos": None,
                "capa_offset": None,
                "titulo_atualizado": None,
                "tipos_vistos": [],
            },
        },
        "aplicacoes_criadoras": [],
        "inibidor": None,
        "lingua_declarada": None,
        "estrutura_declarada": [],
        "encoding": None,
        "_texto": None,
        "_paginas": None,
        "lacunas": {
            "biblioteca": "sem biblioteca livre de MOBI de licença permissiva; leitor próprio de cabeçalho",
            "estrutura": "índice/NCX do MOBI não lido no censo",
            "texto": "texto MOBI (LZ77/HUFF) não descomprimido no censo: sem conversão",
        },
        "bibliotecas": {"struct-proprio": "censo-3189"},
        "erro": None,
    }


# ---------- leitura de bytes ----------


def _u16(b, pos):
    """Inteiro de 16 bits (big-endian) em b[pos]; None se não cabe."""
    if pos + 2 > len(b):
        return None
    return struct.unpack_from(">H", b, pos)[0]


def _u32(b, pos):
    """Inteiro de 32 bits (big-endian) em b[pos]; None se não cabe."""
    if pos + 4 > len(b):
        return None
    return struct.unpack_from(">I", b, pos)[0]


def _ascii(b, pos, tam):
    """Texto ASCII de b[pos:pos+tam] com a caixa original; byte não imprimível vira '?'."""
    if pos + tam > len(b):
        return None
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b[pos:pos + tam])


def _decodificar(bruto, encoding_texto, truncado=False):
    """Texto de bytes do MOBI: cp1252 se o cabeçalho diz 1252, senão UTF-8 com cp1252 de reserva."""
    if encoding_texto == 1252:
        return bruto.decode("cp1252", "replace")
    decodificador = codecs.getincrementaldecoder("utf-8")()
    try:
        return decodificador.decode(bruto, final=not truncado)  # truncado: aceita char cortado no fim
    except UnicodeDecodeError:
        return bruto.decode("cp1252", "replace")


def _inteiro(dado):
    """Inteiro big-endian de 1 a 8 bytes; None fora disso."""
    if 1 <= len(dado) <= 8:
        return int.from_bytes(dado, "big")
    return None


def _data_palm(segundos):
    """Data PalmDB em ISO 8601 (UTC). 0 = sem data. Bit alto ligado: época 1904; senão 1970."""
    if not segundos:
        return None
    ano_base = 1904 if segundos >= 2**31 else 1970
    base = datetime(ano_base, 1, 1, tzinfo=timezone.utc)
    try:
        return (base + timedelta(seconds=segundos)).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, ValueError):
        return None


def _uma_linha(texto):
    return " ".join(str(texto).split())[:300]


# ---------- prazo ----------


def _relogio(prazo_s):
    """Função que diz se o prazo do `ler` acabou; sem prazo válido, nunca acaba."""
    try:
        limite = time.monotonic() + float(prazo_s)
    except (TypeError, ValueError):
        return lambda: False
    return lambda: time.monotonic() >= limite


def _marcar_prazo(lacunas, etapa):
    """Registra (uma vez) que o prazo acabou em `etapa`; o resultado é parcial."""
    lacunas.setdefault("prazo", "prazo de leitura estourado em: %s; resultado parcial" % etapa)


def _prazo_antes(lacunas, estourou, etapa):
    """True (e registra a lacuna) se o prazo já acabou antes de `etapa`."""
    if not estourou():
        return False
    _marcar_prazo(lacunas, etapa)
    return True


# ---------- PalmDB ----------


def _ler_palmdb(dados, pal):
    """Cabeçalho PalmDB (78 bytes); campo que não cabe nos bytes fica None."""
    if len(dados) >= 32:
        bruto = dados[:32].split(bytes(1), 1)[0]  # nome vai até o primeiro NUL
        pal["nome"] = _decodificar(bruto, None, truncado=True)
    pal["atributos"] = _u16(dados, 32)
    pal["versao"] = _u16(dados, 34)
    pal["criacao"] = _data_palm(_u32(dados, 36))
    pal["modificacao"] = _data_palm(_u32(dados, 40))
    pal["backup"] = _data_palm(_u32(dados, 44))
    pal["tipo"] = _ascii(dados, 60, 4)
    pal["criador"] = _ascii(dados, 64, 4)
    pal["n_registros"] = _u16(dados, 76)


def _erro_palmdb(dados, pal):
    """Uma linha de erro se os bytes não têm cara de PalmDB de MOBI/PalmDOC; senão None."""
    if len(dados) < _TAM_PALMDB:
        return "arquivo com %d bytes: menor que o cabecalho PalmDB (%d)" % (len(dados), _TAM_PALMDB)
    if (pal["tipo"], pal["criador"]) not in _TIPOS_PALMDB:
        return "PalmDB com tipo/criador nao reconhecido: %r/%r (bytes 60-67: %s)" % (
            pal["tipo"],
            pal["criador"],
            dados[60:68].hex(),
        )
    return None


def _registros(dados, n, lacunas, estourou):
    """Offsets dos registros da lista, até o primeiro problema (fora do arquivo ou decrescente)."""
    total = len(dados)
    offs = []
    for i in range(n):
        if i % _A_CADA == _A_CADA - 1 and _prazo_antes(lacunas, estourou, "lista de registros"):
            break
        pos = _TAM_PALMDB + 8 * i
        off = _u32(dados, pos) if pos + 8 <= total else None
        if off is None:
            motivo = "lista passa do fim do arquivo (%d declarados, %d cabem)" % (n, i)
        elif off > total:
            motivo = "registro %d começa em %d, depois do fim do arquivo (%d bytes)" % (i, off, total)
        elif offs and off < offs[-1]:
            motivo = "offset do registro %d (%d) menor que o do anterior (%d)" % (i, off, offs[-1])
        else:
            offs.append(off)
            continue
        lacunas["registros"] = "%s; lidos %d" % (motivo, len(offs))
        break
    return offs


def _fim(offs, i, total):
    """Fim do registro i: começo do seguinte, ou o fim do arquivo."""
    return offs[i + 1] if i + 1 < len(offs) else total


def _tem_boundary(dados, offs, estourou):
    """True se algum registro é exatamente BOUNDARY; None se o prazo acabou no meio."""
    total = len(dados)
    for i, ini in enumerate(offs):
        if i % _A_CADA == _A_CADA - 1 and estourou():
            return None
        if _fim(offs, i, total) - ini == 8 and dados[ini:ini + 8] == b"BOUNDARY":
            return True
    return False


# ---------- registro 0: PalmDOC e MOBI ----------


def _campo_mobi(r0, pos, tam_cab, lacunas, campo):
    """Inteiro do cabeçalho MOBI em r0[pos]; None (com lacuna) se o cabeçalho ou o registro não cobrem."""
    if pos + 4 > 16 + tam_cab:
        lacunas[campo] = "cabecalho MOBI de %d bytes nao cobre o campo (offset %d)" % (tam_cab, pos)
        return None
    valor = _u32(r0, pos)
    if valor is None:
        lacunas[campo] = "registro 0 (%d bytes) acaba antes do campo (offset %d)" % (len(r0), pos)
    return valor


def _ler_mobi(r0, m, lacunas):
    """Cabeçalho MOBI (a partir do offset 16 do registro 0). Devolve (flags EXTH, offset de DRM)."""
    if len(r0) < 20:
        lacunas["mobi"] = "registro 0 com %d bytes: curto demais para a assinatura MOBI" % len(r0)
        return None, None
    if r0[16:20] != b"MOBI":
        m["presente"] = False
        lacunas["mobi"] = "assinatura MOBI ausente no offset 16 do registro 0"
        return None, None
    m["presente"] = True
    tam = _u32(r0, 20)
    m["tamanho_cabecalho"] = tam
    if tam is None:
        lacunas["mobi.tamanho_cabecalho"] = "registro 0 acaba antes do tamanho do cabecalho"
        return None, None
    if 16 + tam > len(r0):
        lacunas["mobi.tamanho_cabecalho"] = "declara %d bytes; o registro 0 tem %d depois do offset 16" % (
            tam,
            len(r0) - 16,
        )
    for campo, pos in (("tipo_mobi", 24), ("encoding_texto", 28), ("uid", 32), ("versao", 36), ("locale", 92)):
        m[campo] = _campo_mobi(r0, pos, tam, lacunas, "mobi." + campo)
    flags = _campo_mobi(r0, 128, tam, lacunas, "mobi.flags_exth")
    offset_drm = _campo_mobi(r0, 168, tam, lacunas, "drm.offset")
    return flags, offset_drm


def _ler_palmdoc(r0, pd, tem_mobi, lacunas):
    """Cabeçalho PalmDOC (16 bytes do registro 0). O offset 12 só é criptografia se há cabeçalho MOBI."""
    pd["compressao"] = _u16(r0, 0)
    pd["tamanho_texto"] = _u32(r0, 4)
    pd["registros_texto"] = _u16(r0, 8)
    pd["tamanho_registro"] = _u16(r0, 10)
    if tem_mobi:
        pd["criptografia"] = _u16(r0, 12)
    elif tem_mobi is False:
        lacunas["palmdoc.criptografia"] = "sem cabecalho MOBI, o offset 12 e a posicao de leitura, nao criptografia"
    else:
        lacunas["palmdoc.criptografia"] = "registro 0 curto demais para dizer se ha cabecalho MOBI"


# ---------- EXTH ----------


def _varrer_exth(r0, ini, n, estourou):
    """Registros (tipo, dados) do EXTH e o motivo de parar antes de n (None se leu todos; 'prazo')."""
    regs = []
    pos = ini
    while len(regs) < n:
        if pos + 8 > len(r0):
            return regs, "registro %d comeca depois do fim do registro 0" % (len(regs) + 1)
        tipo, tam = struct.unpack_from(">II", r0, pos)
        if tam < 8 or pos + tam > len(r0):
            return regs, "registro %d (tipo %d) com tamanho invalido (%d)" % (len(regs) + 1, tipo, tam)
        regs.append((tipo, r0[pos + 8:pos + tam]))
        pos += tam
        if len(regs) % _A_CADA == 0 and estourou():
            return regs, "prazo"
    return regs, None


def _resumir_exth(regs, encoding_texto):
    """Textos (lista por tipo, na ordem), inteiros (primeiro por tipo) e tipos vistos (ordenados)."""
    textos, inteiros, vistos = {}, {}, set()
    for tipo, dado in regs:
        vistos.add(tipo)
        if tipo in _EXTH_TEXTO:
            valor = _decodificar(dado, encoding_texto).replace(chr(0), "").strip()
            if valor and valor not in textos.setdefault(tipo, []):
                textos[tipo].append(valor)
        elif tipo in _EXTH_INTEIRO or tipo in _EXTH_VERSAO:
            valor = _inteiro(dado)
            if valor is not None and tipo not in inteiros:
                inteiros[tipo] = valor
    return textos, inteiros, sorted(vistos)


def _preencher_exth(ex, textos, inteiros, vistos):
    for tipo, campo in _EXTH_TEXTO.items():
        if tipo in textos:
            ex[campo] = "; ".join(textos[tipo])[:_LIMITE_TEXTO]  # vários autores etc. juntos por "; "
    for tipo, campo in _EXTH_INTEIRO.items():
        if tipo in inteiros:
            ex[campo] = inteiros[tipo]
    if ex["boundary"] == _SEM_VALOR:
        ex["boundary"] = None  # 0xFFFFFFFF = sem limite KF8
    if all(t in inteiros for t in _EXTH_VERSAO):
        ex["criador_software_versao"] = ".".join(str(inteiros[t]) for t in _EXTH_VERSAO)
    ex["tipos_vistos"] = vistos


def _ler_exth(r0, pos, encoding_texto, ex, lacunas, estourou):
    """Bloco EXTH em r0[pos:]; preenche `ex` com o que houver."""
    if pos + 12 > len(r0) or r0[pos:pos + 4] != b"EXTH":
        ex["presente"] = False
        lacunas["exth"] = "flag 0x40 ligado, mas sem bloco EXTH no offset %d do registro 0" % pos
        return
    n = _u32(r0, pos + 8)
    ex["presente"] = True
    ex["n_registros"] = n
    regs, motivo = _varrer_exth(r0, pos + 12, n, estourou)
    if motivo == "prazo":
        _marcar_prazo(lacunas, "leitura dos registros do EXTH")
    elif motivo:
        lacunas["exth"] = "EXTH declara %d registros, %d lidos: %s" % (n, len(regs), motivo)
    _preencher_exth(ex, *_resumir_exth(regs, encoding_texto))


# ---------- decisões sobre o conjunto ----------


def _familia(versao, combinado):
    """KF7 (versão 6), KF8 (versão 8) ou KF7+KF8 (versão 6 com KF8 junto); outra versão: None."""
    if versao == 8:
        return "KF8"
    if versao == 6 and combinado is not None:
        return "KF7+KF8" if combinado else "KF7"
    return None


def _leitura_incompleta(ex, lacunas):
    """True se a lista de registros ou o EXTH não foram lidos por inteiro (o KF8 junto pode estar no que faltou)."""
    return any(k in lacunas for k in ("registros", "exth", "prazo")) or ex["presente"] is None


def _ler_combinado(dados, offs, m, ex, lacunas, estourou):
    """KF8 junto do KF7: EXTH 121 válido ou algum registro BOUNDARY. Sem achar e com leitura incompleta: None."""
    if ex["boundary"] is not None:
        if ex["boundary"] >= len(offs):
            lacunas["exth.boundary"] = "EXTH 121 aponta o registro %d; a lista lida tem %d" % (
                ex["boundary"],
                len(offs),
            )
        m["combinado"] = True
    elif _prazo_antes(lacunas, estourou, "busca de BOUNDARY"):
        m["combinado"] = None
    else:
        m["combinado"] = _tem_boundary(dados, offs, estourou)
        if m["combinado"] is None:
            _marcar_prazo(lacunas, "busca de BOUNDARY")
        elif not m["combinado"] and _leitura_incompleta(ex, lacunas):
            m["combinado"] = None
            lacunas["combinado"] = "sem EXTH 121 nem BOUNDARY no que foi lido; a leitura ficou incompleta"
    m["familia"] = _familia(m["versao"], m["combinado"])


def _ler_drm(bloco, offset_drm, lacunas):
    """DRM: presente se a criptografia PalmDOC é diferente de 0 ou há offset de DRM (0xFFFFFFFF = sem)."""
    drm = bloco["drm"]
    cripto = bloco["palmdoc"]["criptografia"]
    drm["criptografia_palmdoc"] = cripto
    drm["offset"] = None if offset_drm in (None, _SEM_VALOR) else offset_drm
    sinais = []
    if cripto is not None:
        sinais.append(cripto != 0)
    if offset_drm is not None:
        sinais.append(offset_drm != _SEM_VALOR)
    if sinais:
        drm["presente"] = any(sinais)
    else:
        lacunas["drm"] = "nem criptografia PalmDOC nem offset de DRM legiveis"


def _ler_cabecalhos(dados, ctx, ficha):
    estourou = _relogio(ctx.get("prazo_s"))
    lacunas = ficha["lacunas"]
    bloco = ficha["mobi"]
    pal = bloco["palmdb"]
    _ler_palmdb(dados, pal)
    ficha["erro"] = _erro_palmdb(dados, pal)
    if pal["n_registros"] is None:
        lacunas["mobi"] = "cabecalho PalmDB incompleto: nada a ler alem dele"
        return
    offs = _registros(dados, pal["n_registros"], lacunas, estourou)
    if not offs or offs[0] >= len(dados):
        lacunas["mobi"] = "registro 0 ausente ou fora do arquivo"
        return
    r0 = dados[offs[0]:_fim(offs, 0, len(dados))]
    m, ex = bloco["mobi"], bloco["exth"]
    flags, offset_drm = _ler_mobi(r0, m, lacunas)
    _ler_palmdoc(r0, bloco["palmdoc"], m["presente"], lacunas)
    if m["presente"] is False:
        ex["presente"] = False
    elif m["presente"] and flags is not None:
        if not flags & _FLAG_EXTH:
            ex["presente"] = False
        elif not _prazo_antes(lacunas, estourou, "EXTH"):
            _ler_exth(r0, 16 + m["tamanho_cabecalho"], m["encoding_texto"], ex, lacunas, estourou)
    if m["presente"]:
        _ler_combinado(dados, offs, m, ex, lacunas, estourou)
    _ler_drm(bloco, offset_drm, lacunas)


# ---------- envelope ----------


def _nome_criador(codigo):
    if codigo in _CRIADORES:
        return _CRIADORES[codigo]
    if codigo in _FAIXA_KINDLEGEN:
        return "kindlegen"
    return "codigo-204=%d" % codigo


def _inibidor(drm):
    cripto = drm["criptografia_palmdoc"]
    if cripto:
        return {"tipo": "DRM", "alvo": "palmdoc.criptografia=%d" % cripto}
    if drm["offset"] is not None:
        return {"tipo": "DRM", "alvo": "mobi.drm_offset=%d" % drm["offset"]}
    return None


def _envelope(ficha):
    """Campos do envelope do contrato, derivados do bloco."""
    bloco = ficha["mobi"]
    ex = bloco["exth"]
    ficha["lingua_declarada"] = ex["lingua"]
    ficha["inibidor"] = _inibidor(bloco["drm"])
    codigo = ex["criador_software_codigo"]
    if codigo is not None:
        ficha["aplicacoes_criadoras"] = [
            {"nome": _nome_criador(codigo), "versao": ex["criador_software_versao"], "data": None, "fonte": "exth"}
        ]
