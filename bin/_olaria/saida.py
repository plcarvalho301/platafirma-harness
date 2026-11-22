"""A tradução da resposta do serviço em saída do verbo `ontologia` (cards #4214 e #4254).

Faixa de códigos de saída:
- 0: fez (inclusive listar vazio e repetição de --pedido com mesmo YAML)
- 1: não (recusa semântica da régua, do raciocinador, versão diferente, pedido com conteúdo diferente, lote em parte)
- 2: uso (ato, flag ou chave fora da gramática, gravar/variante em escrita, parte, falta de <versao>, YAML ilegível)
- 3: dependência (Olaria, banco ou raciocinador fora antes de escrita, falta de variável de ambiente)
- 4: recusa (política de acesso negou)
- 5: indeterminável (prazo estourado ou queda após envio; leva o pedido e aponta `conferir` em `proximo`)

Todo erro sai na saída padrão no formato padrão de 6 campos (`codigo`, `onde`, `recebido`, `regra`, `cura`, `proximo`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

SEPARADOR = " · "
TETO_RECEBIDO = 160

OK, RECUSOU, ILEGIVEL, FORA, SEM_PERMISSAO, INDETERMINAVEL = 0, 1, 2, 3, 4, 5


@dataclass
class Saida:
    codigo: int
    stdout: str = ""
    stderr: str = ""


def _limpar(texto: object) -> str:
    return " ".join(str(texto).replace(SEPARADOR, " ; ").splitlines()).strip()


def limitar_recebido(valor: object, teto: int = TETO_RECEBIDO) -> str:
    if valor is None:
        return "(ausente)"
    texto = _limpar(valor if isinstance(valor, str) else repr(valor))
    if not texto:
        return "(vazio)"
    return texto if len(texto) <= teto else texto[: teto - 1] + "…"


def erro_6(codigo: str, onde: str, recebido: object, regra: str, cura: str, proximo: str) -> dict:
    return {
        "codigo": codigo,
        "onde": onde,
        "recebido": limitar_recebido(recebido),
        "regra": regra,
        "cura": cura,
        "proximo": proximo or "ontologia --help",
    }


def linha_de_erro(erro: dict) -> str:
    """O erro numa linha fixa de 6 campos: codigo · onde · recebido · regra · cura · proximo."""
    onde = erro.get("onde") if erro.get("onde") is not None else erro.get("caminho", "")
    recebido = erro["recebido"] if "recebido" in erro else limitar_recebido(erro.get("valor"))
    proximo = erro.get("proximo") or "ontologia --help"
    return SEPARADOR.join([
        _limpar(erro.get("codigo", "?")),
        _limpar(onde),
        f"recebido: {_limpar(recebido)}",
        f"regra: {_limpar(erro.get('regra', ''))}",
        f"cura: {_limpar(erro.get('cura', ''))}",
        f"proximo: {_limpar(proximo)}",
    ])


def erro_de_uso(codigo: str, onde: str, recebido: object, regra: str, cura: str, proximo: str, *,
                como_json: bool = False) -> Saida:
    d = erro_6(codigo, onde, recebido, regra, cura, proximo)
    if como_json:
        return Saida(ILEGIVEL, _json({"erros": [d], "total": 1}))
    return Saida(ILEGIVEL, _linhas(linha_de_erro(d)))


def _linhas(*partes: str) -> str:
    return "".join(p if p.endswith("\n") else p + "\n" for p in partes if p)


def _json(objeto: dict) -> str:
    return json.dumps(objeto, ensure_ascii=False, default=str, indent=2) + "\n"


def _relatorio(corpo: dict) -> dict:
    """O relatório da fornada: no corpo da gravação ele vem aberto, e na resposta «já gravada» vem em `relatorio`."""
    interno = corpo.get("relatorio")
    return interno if isinstance(interno, dict) else corpo


def _recusadas(corpo: dict) -> int:
    valor = _relatorio(corpo).get("recusadas", 0)
    return len(valor) if isinstance(valor, (list, tuple)) else int(valor or 0)


def traduzir(ato: str, status: int, corpo: dict, *, como_json: bool = False, fornada: str = "",
             aviso_variante: str = "") -> Saida:
    if status == 200:
        return _fez(ato, corpo, como_json, fornada, aviso_variante)
    if status == 422:
        return _recusou(ato, corpo, como_json, fornada)
    erro = corpo.get("erro") or corpo.get("estado") or corpo
    if status == 400:
        return erro_de_uso(
            "pedido-ilegivel", ato, erro,
            "O pedido recebido pelo serviço tem forma válida de YAML, identificador e parâmetros.",
            str(corpo.get("cura") or "Confira os argumentos e o arquivo YAML na ajuda do verbo."),
            str(corpo.get("proximo") or f"ontologia {ato} --help"),
            como_json=como_json,
        )
    if status == 403:
        return Saida(SEM_PERMISSAO, _linhas(linha_de_erro(erro_6(
            "sem-permissao", ato, "chave/autorizacao",
            "O serviço recusa chamadas sem chave de serviço válida ou sem autorização no par (ato, classe).",
            "Confira a chave de serviço (OLARIA_CHAVE) e a permissão da cadeira para o ato.",
            "ontologia --help",
        ))))
    if status == 503:
        motivos = corpo.get("motivos") or []
        if ato == "raciocinar" and any("teto" in str(m) or "prazo" in str(m) for m in motivos):
            alvo = str(corpo.get("alvo") or "ontologia")
            d = erro_6(
                "prazo-estourado", alvo, "; ".join(map(str, motivos)),
                "A conferência da ontologia tem de terminar dentro do prazo do verbo e do serviço.",
                "Divida o escopo conferindo uma classe por vez ou confira a saúde da Olaria.",
                f"conferir ontologia {alvo}",
            )
            if como_json:
                return Saida(INDETERMINAVEL, _json({"estado": "indeterminavel", "alvo": alvo, "erros": [d], "total": 1}))
            return Saida(INDETERMINAVEL, _linhas(linha_de_erro(d)),
                         stderr=f"conferir ontologia: prazo estourado em {alvo}\n")
        if ato == "raciocinar":
            detalhe = "; ".join(map(str, motivos)) if motivos else str(erro)
            if como_json:
                return Saida(FORA, _json(corpo), stderr=f"conferir ontologia: indisponível: {detalhe}\n")
            return Saida(FORA, stderr=f"conferir ontologia: o banco ou o raciocinador não responderam: {detalhe}\n")
        depois = f"; o pedido {fornada} está desfeito, e o mesmo --pedido pode ser reenviado" if fornada else ""
        return Saida(FORA, stderr=f"ontologia: o banco ou o raciocinador não responderam: {erro}{depois}\n")
    return Saida(FORA, stderr=f"ontologia: o serviço respondeu {status}: {erro}\n")


def _comentarios_da_shape(corpo: dict) -> list[str]:
    linhas: list[str] = []
    linhagem = corpo.get("linhagem")
    if isinstance(linhagem, list) and linhagem:
        linhas.append(f"# linhagem: {', '.join(map(str, linhagem))}")
    herdadas = corpo.get("herdadas")
    if isinstance(herdadas, list) and herdadas:
        linhas.append("# herdadas:")
        for r in herdadas:
            if not isinstance(r, dict):
                continue
            origem = r.get("classe") or r.get("de") or "?"
            prop = r.get("propriedade", "?")
            tipo = r.get("tipo_de_valor", "?")
            detalhes = [f"tipo_de_valor: {tipo}", f"minimo: {r.get('minimo', 0)}", f"sentido: {r.get('sentido', 'saida')}"]
            if r.get("maximo") is not None:
                detalhes.append(f"maximo: {r['maximo']}")
            if r.get("dicionario"):
                detalhes.append(f"dicionario: {r['dicionario']}")
            if r.get("destinos"):
                detalhes.append(f"destinos: [{', '.join(map(str, r['destinos']))}]")
            if r.get("categorias_de_destino"):
                detalhes.append(f"categorias_de_destino: [{', '.join(map(str, r['categorias_de_destino']))}]")
            linhas.append(f"# - classe: {origem} · propriedade: {prop} ({', '.join(detalhes)})")
    return linhas


def _fez(ato: str, corpo: dict, como_json: bool, fornada: str, aviso_variante: str = "") -> Saida:
    codigo = RECUSOU if _recusadas(corpo) else OK
    if ato in ("ler", "preparar"):
        conteudo_yaml = str(corpo.get("yaml", ""))
        if corpo.get("parte") and not conteudo_yaml.lstrip().startswith("# parte"):
            conteudo_yaml = "# parte\n" + conteudo_yaml
            corpo = {**corpo, "yaml": conteudo_yaml}
    if como_json:
        return Saida(codigo, _json(corpo))
    nota_var = f"{SEPARADOR}{aviso_variante}" if aviso_variante else ""
    if ato in ("ler", "preparar"):
        classe = corpo.get("classe") or "classe"
        versao = corpo.get("versao") or "sem-fornada"
        recorte = corpo.get("recorte") or ("parte" if corpo.get("parte") else "completo")
        parte = f"{SEPARADOR}parte" if corpo.get("parte") else ""
        cabecalho = f"{classe} · fornada {versao} · {recorte}{parte}{nota_var}"
        comentarios = _comentarios_da_shape(corpo)
        return Saida(codigo, _linhas(cabecalho, *comentarios, str(corpo.get("yaml", ""))))
    if ato == "listar":
        classe = corpo.get("classe") or "shape"
        versao = corpo.get("versao") or "sem-fornada"
        chaves = [str(c) for c in corpo.get("chaves") or []]
        recorte = corpo.get("recorte") or f"fichas 1 a {len(chaves)} de {len(chaves)}"
        cabecalho = f"{classe} · fornada {versao} · {recorte}{nota_var}"
        return Saida(codigo, _linhas(cabecalho, *chaves))
    if ato == "gerar":
        fornada_id = corpo.get("fornada", "?")
        cabecalho = f"# shape · fornada {fornada_id} · modelo{nota_var}"
        return Saida(codigo, _linhas(cabecalho, str(corpo.get("modelo", ""))))
    if ato == "raciocinar":
        versao = corpo.get("versao") or "sem-fornada"
        alvo = corpo.get("alvo") or "ontologia"
        classes = corpo.get("classes") or []
        cabecalho = f"ontologia · fornada {versao} · conforme · {alvo} ({len(classes)} classe(s)){nota_var}"
        return Saida(OK, _linhas(cabecalho))
    if ato == "renomear":
        id_ = str(fornada or corpo.get("fornada") or "")
        if corpo.get("estado") == "ja-gravada":
            return Saida(codigo, _linhas(id_, "já gravada"))
        ren = corpo.get("renomeada") or {}
        return Saida(codigo, _linhas(id_, f"renomeada: {ren.get('de', '?')} -> {ren.get('para', '?')} ({ren.get('classe', '?')})"))
    if ato == "transitar":
        id_ = str(fornada or corpo.get("fornada") or "")
        if corpo.get("estado") == "ja-gravada":
            return Saida(codigo, _linhas(id_, "já gravada"))
        tr = corpo.get("transicao") or {}
        de = tr.get("de") or "(inicial)"
        return Saida(codigo, _linhas(
            id_,
            f"transicao: {tr.get('chave', '?')} ({tr.get('classe', '?')}) · {de} -> {tr.get('para', '?')} · {tr.get('evento', '?')}",
        ))
    if ato == "nomes":
        id_ = str(fornada or corpo.get("fornada") or "")
        if corpo.get("estado") == "ja-gravada":
            return Saida(codigo, _linhas(id_, "já gravada"))
        linhas_resp = [id_]
        for item in corpo.get("abertas") or []:
            linhas_resp.append(f"aberta: {item.get('termo', '?')} -> {item.get('chave', '?')} ({item.get('origem', '?')})")
        for item in corpo.get("encerradas") or []:
            linhas_resp.append(f"encerrada: {item.get('termo', '?')} -> {item.get('chave', '?')}")
        return Saida(codigo, _linhas(*linhas_resp))
    if ato == "apagar":
        id_ = str(fornada or corpo.get("fornada") or "")
        if corpo.get("estado") == "ja-gravada":
            return Saida(codigo, _linhas(id_, "já gravada"))
        apagadas = corpo.get("apagadas") or []
        if len(apagadas) > 1:
            return Saida(codigo, _linhas(id_, "apagadas: " + ", ".join(
                f"{a.get('chave', '?')} ({a.get('classe', '?')})" for a in apagadas)))
        apagada = corpo.get("apagada") or {}
        return Saida(codigo, _linhas(id_, f"apagada: {apagada.get('chave', '?')} ({apagada.get('classe', '?')})"))
    if ato in ("gravar", "criar", "trocar", "recompor"):
        return Saida(codigo, _linhas(str(fornada or corpo.get("fornada") or ""), _resumo_da_gravacao(ato, corpo)))
    if ato == "ensaiar-capacidades":
        classes = corpo.get("classes") or []
        return Saida(codigo, _linhas("conforme: a régua não recusa nada no que está gravado"
                                     + (f", nas classes {', '.join(map(str, classes))}" if classes else "")))
    return Saida(codigo, _linhas(_resumo_do_ensaio(corpo)))


def _resumo_do_ensaio(corpo: dict) -> str:
    """O que a gravação faria, com as removidas pela chave: o ensaio que remove não sai igual ao que só acrescenta
    (débito 713)."""
    r = _relatorio(corpo)
    gravadas, removidas = r.get("gravadas") or [], r.get("removidas") or []
    partes = ["ensaio: nenhum erro; nada gravado", str(r.get("uso", "?")), f"gravaria {len(gravadas)} fichas",
              f"removeria {len(removidas)}" + (f": {', '.join(map(str, removidas))}" if removidas else "")]
    return SEPARADOR.join(partes)


def _resumo_da_gravacao(ato: str, corpo: dict) -> str:
    if corpo.get("estado") == "ja-gravada":
        return "já gravada: mesmo YAML"
    r = _relatorio(corpo)
    gravadas, removidas = r.get("gravadas") or [], r.get("removidas") or []
    acao = {"criar": "criadas", "trocar": "trocadas", "recompor": "recompostas"}.get(ato, corpo.get("estado", "fez"))
    return f"{acao}: {r.get('uso', '?')} · {len(gravadas)} fichas gravadas · {len(removidas)} removidas"


def _recusou(ato: str, corpo: dict, como_json: bool, fornada: str) -> Saida:
    erros = [e for e in corpo.get("erros") or [] if isinstance(e, dict)]
    total = corpo.get("total", len(erros))
    if como_json:
        objeto = {**corpo, "erros": erros, "total": total}
        if fornada or corpo.get("fornada"):
            objeto["fornada"] = fornada or corpo.get("fornada")
        return Saida(RECUSOU, _json(objeto))
    linhas = [linha_de_erro(e) for e in erros]
    for d in corpo.get("dependencias") or []:
        if isinstance(d, dict):
            linhas.append(linha_de_erro(erro_6(
                "dependencia-recusada", str(d.get("caminho", "")), d.get("depende_de"),
                "Ficha ligada a item recusado no mesmo lote também fica de fora.",
                f"Corrija a ficha {d.get('depende_de')} e reenvie o lote.",
                f"ontologia ensaiar {ato if ato in ('criar', 'trocar', 'recompor') else 'criar'} <arquivo.yaml>",
            )))
    gravou = ato in ("gravar", "criar", "trocar", "recompor") and corpo.get("estado") == "gravada-em-parte"
    id_info = f"pedido {fornada or corpo.get('fornada')}; " if (fornada or corpo.get("fornada")) and ato != "ensaiar" else ""
    nota = (f"ontologia: {id_info}{total} erro(s)"
            + ("; o lote gravou as fichas que passaram" if gravou
               else "; nada gravado" if ato in ("gravar", "criar", "trocar", "recompor") else ""))
    return Saida(RECUSOU, _linhas(*linhas), stderr=nota + "\n")


def sem_conexao(url: str, motivo: str) -> Saida:
    return Saida(FORA, stderr=f"ontologia: o serviço não responde em {url}: {motivo}\n")


def sem_resposta(motivo: str) -> Saida:
    return Saida(FORA, stderr=f"ontologia: a resposta do serviço não chegou: {motivo}\n")


def desfecho_indeterminavel(ato: str, prazo_s: float, pedido: str, *, como_json: bool = False) -> Saida:
    """Saída 5: envio iniciado perdeu conexão ou estourou prazo; preserva `pedido` e aponta `conferir`."""
    d = erro_6(
        "prazo-estourado",
        ato,
        f"pedido {pedido} após {prazo_s:g} s",
        "Chamada de escrita que perde resposta ou estoura o prazo devolve saída 5 com o pedido para conferência.",
        f"Confira se o pedido {pedido} foi aplicado antes de repetir com --pedido {pedido}.",
        f"conferir ontologia --pedido {pedido}",
    )
    if como_json:
        return Saida(INDETERMINAVEL, _json({"estado": "indeterminavel", "pedido": pedido, "erros": [d], "total": 1}))
    return Saida(INDETERMINAVEL, _linhas(linha_de_erro(d)),
                 stderr=f"ontologia: desfecho indeterminável após envio; pedido {pedido}\n")


def ambiente_incompleto(nome: str) -> Saida:
    return Saida(FORA, stderr=f"ontologia: {nome} não está no ambiente: o verbo não chama o serviço sem ela\n")
