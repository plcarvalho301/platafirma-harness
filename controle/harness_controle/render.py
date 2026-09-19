# render — HTML por bloco, fiel às classes CSS dos wireframes de
# claudinha-produto (design/wireframes/harness-{recepcao,cadeira}.html),
# consumindo o release platafirma/ui (que traz os tokens dentro).
# capacidade: expediente
# dono: claudinho-TI
"""Sem framework de front, sem build, sem bundler. Revalidação de 60s é
`<meta http-equiv="refresh">`, não fetch/poll; "Atualizar" é um link comum pro
próprio path. As duas ações (despachar recado, reiniciar) são
`<form method="post">` puros, POST-redirect-GET.

O único JavaScript da página é o `pf-ui.js` do release, que registra os
primitivos `pf-*` como custom elements. Nada aqui usa esses primitivos ainda:
a tela segue em HTML nu com as classes de `tela.css`, e trocar widget por
widget é outro card (#476 só manda CONSUMIR o release). Carregar o módulo agora
custa um script e prova o caminho: ou o artefato veio na imagem, ou nada
responde.

Princípio que governa cada função de render (spec §3): ausência de dado se
desenha como ausência, nunca como saúde. `0` e `—` nunca colapsam.
"""

from __future__ import annotations

import html
import re
import time
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
import nh3

# Conteudo LIVRE (corpo de mesa, caderno, fila) escrito pela cadeira em
# Markdown. `_esc()` cru despejava esse texto grudado, sem heading nem
# separador — a "linguica" da tela no celular. `md_seguro()` faz parse do
# Markdown e sanitiza o HTML por allowlist ANTES de entrar na pagina.
# So para conteudo livre: rotulo de sistema (nome, chip, caminho, sha, numero)
# segue por `_esc()` cru, que nunca vira Markdown.
_MD = MarkdownIt("commonmark")
_TAGS_OK = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
            "ul", "ol", "li", "strong", "em", "code", "pre", "blockquote", "a"}
_ATTR_OK = {"a": {"href"}}

def md_seguro(texto: Any) -> str:
    """Markdown -> HTML sanitizado. String vazia/None vira vazio, nunca vira
    saude (mesma regra do resto do render: ausencia se desenha como ausencia)."""
    if not texto:
        return ""
    return nh3.clean(_MD.render(str(texto)), tags=_TAGS_OK, attributes=_ATTR_OK)

# Camada 1 — o front da PlataFirma, copiado do release platafirma/ui para
# dentro da imagem em tempo de build (arq:0056, ver Dockerfile). pf-ui.css ja
# traz os tokens inteiros: NAO ha mais tokens.css, e nada mais aqui aponta para
# platafirma-arquitetura. O diretorio e servido inteiro sob PF_UI_BASE porque o
# proprio CSS pede as fontes por caminho relativo (./fontes/...).
PF_UI_DIR = Path(__file__).resolve().parent / "estatico" / "pf-ui"
PF_UI_BASE = "/estatico/pf-ui"
PF_UI_CSS_HREF = f"{PF_UI_BASE}/pf-ui.css"
PF_UI_JS_SRC = f"{PF_UI_BASE}/pf-ui.js"
# Camada 2: os tokens nao conhecem classe de superficie; sozinhos, renderizam
# HTML nu. tela.css vem DEPOIS de pf-ui.css, e nao esta em @layer nenhum — ou
# seja, continua ganhando do que o release traz em camada.
TELA_HREF = "/estatico/tela.css"


def _versao_ui() -> str:
    """Versao do release que veio na imagem, lida do versao.txt que o proprio
    release carrega. Uma vez, no import: o arquivo e imutavel dentro da imagem,
    e ler por requisicao so gastaria syscall. Sem o arquivo (clone de
    desenvolvimento, sem COPY --from) diz “desconhecida” em vez de mentir uma
    versao."""
    try:
        return (PF_UI_DIR / "versao.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return "desconhecida"


VERSAO_UI = _versao_ui()

CLOUDFLARED_OAUTH2PROXY = {"cloudflared", "oauth2-proxy"}


def _esc(s: Any) -> str:
    return html.escape(str(s)) if s is not None else ""


def chip(texto: str, papel: str | None = None) -> str:
    cls = f"chip {papel}" if papel else "chip calmo"
    return f'<span class="{cls}">{_esc(texto)}</span>'


def idade_fmt(segundos: float | None) -> str:
    """`—` é "sem leitura", nunca confundir com "0 s". Zero segundos genuíno
    (leitura literalmente agora) também aparece como valor, não como travessão."""
    if segundos is None:
        return "—"
    segundos = max(0, int(segundos))
    if segundos < 90:
        return f"{segundos} s"
    minutos = segundos // 60
    if minutos < 90:
        return f"{minutos} min"
    horas = minutos // 60
    return f"{horas} h"


def idade_desde(epoch: float | None, agora: float | None = None) -> str:
    if epoch is None:
        return "—"
    agora = time.time() if agora is None else agora
    return idade_fmt(agora - epoch)


def _num(valor: Any) -> str:
    """`0` e `—` nunca colapsam: None vira travessão, 0 vira "0" de verdade."""
    return "—" if valor is None else str(valor)


# --- pacote de cadeira: leitura do que `monta-sessao --json` serve -----------
# A sonda `cadeiras` guarda o pacote CRU de `monta-sessao <c> --json` — uma lista
# `pecas`, cada uma {peca, ref, sha, frescor, tokens, conteudo, motivo}. Nao ha
# "digest" com persona.presente/mesa.disponivel: quem quiser presenca deriva do
# `frescor` da peca. Ler um digest que ninguem produz foi o que pintou toda
# cadeira como ausente/sem-leitura na recepcao.


def _pecas_por_id(pecas: Any) -> dict:
    """Indexa as pecas do pacote por id-base (o trecho antes de `:`; o sufixo
    `:<chapeu>` das pecas de chapeu nao muda o id do documento). Primeira
    ocorrencia vence; peca sem id e ignorada."""
    idx: dict = {}
    for p in pecas or []:
        pid = (p.get("peca") or "").split(":", 1)[0]
        if pid and pid not in idx:
            idx[pid] = p
    return idx


def _fresco(peca: dict | None) -> bool:
    return bool(peca) and peca.get("frescor") == "fresco"


def _acha_peca(idx: dict, candidatos: tuple[str, ...]) -> dict | None:
    for cid in candidatos:
        if cid in idx:
            return idx[cid]
    return None


def _filtra_mesa_por_chapeu(conteudo: str, chapeu: str) -> str:
    """Mantem as linhas da mesa sob o [chapeu] escolhido. Cada item da mesa abre
    com um rotulo `[<chapeu>]`; as linhas seguintes sem rotulo sao continuacao do
    item e vao junto, ate o proximo rotulo. Sem item do chapeu, diz que nao ha —
    ausencia se declara."""
    linhas, saida, mantem = conteudo.split("\n"), [], False
    for linha in linhas:
        m = re.search(r"\[([^\]]+)\]", linha)
        if m:
            mantem = m.group(1) == chapeu
        if mantem:
            saida.append(linha)
    return "\n".join(saida) if saida else f"Nenhum item da mesa para o chapeu [{chapeu}]."


def _render_caixa_doc(estado: dict, slug_l: str) -> str:
    """Documento Caixa: as cartas da caixa da cadeira, lidas a FRIO pelo agregador
    (`fila ler --tudo`), mais nova primeiro. Caixa vazia, sem leitura e
    indisponivel se declaram — nunca somem, nunca viram saude."""
    bloco = estado.get("caixa_conteudo", {})
    item = next((i for i in (bloco.get("itens") or [])
                 if (i.get("persona") or "").lower() == slug_l), None)
    if item is None:
        return ('<div class="leitura"><p class="indisponivel">Caixa sem leitura — o '
                'agregador ainda nao serve o conteudo desta caixa.</p></div>')
    if item.get("estado") != "ok":
        return (f'<div class="leitura"><p class="indisponivel">Caixa indisponível: '
                f'{_esc(item.get("motivo") or "motivo desconhecido")}.</p></div>')
    msgs = item.get("dados") or []
    if not msgs:
        return ('<div class="leitura"><p class="indisponivel">Caixa vazia — nada nos '
                'últimos 7 dias.</p></div>')
    blocos = []
    for m in msgs:
        cab = (
            '<div class="carimbo">'
            f'<span><b>de</b> {_esc(m.get("de") or "?")}</span>'
            f'<span><b>tipo</b> {_esc(m.get("tipo") or "?")}</span>'
            f'<span><b>há</b> {idade_fmt(m.get("idade_seg"))}</span>'
            + (f'<span><b>responde</b> <span class="mono">{_esc(m.get("responde"))}</span></span>'
               if m.get("responde") else "")
            + "</div>"
        )
        assunto = f'<h4>{_esc(m.get("assunto") or "(sem assunto)")}</h4>'
        corpo = f'<div class="corpo">{_esc(m.get("corpo") or "")}</div>'
        blocos.append(f'<article class="msg">{cab}{assunto}{corpo}</article>')
    return f'<div class="leitura caixa-lida">{"".join(blocos)}</div>'


# Documentos que compoem a cadeira, na ordem do seletor da spec (§/cadeira):
# persona · GERAL · org · mesa · cadernos · caixa. Cada entrada e (chave do ?doc=,
# rotulo, ids de peca que a servem — o CLI usa o id do catalogo (`conduta-dono`,
# `cadernos-indice`), a projecao da tool usa o nome curto; aceitam-se os dois).
# Oficio SAIU: a abertura real (expediente montar) nao serve mais essa peca — o
# `bin/monta-sessao` deprecado ainda a lista, entao a tela mostrava um documento
# que a sessao do dono nao recebe. Documento morto nao vira aba.
# `caixa` nao e peca de monta-sessao: vem do bloco `caixa_conteudo` (leitura fria
# `fila ler --tudo`), tratada a parte na leitura — candidatos vazios de proposito.
_DOCS_CADEIRA = [
    ("persona",  "Persona",  ("persona",)),
    ("geral",    "GERAL",    ("conduta-dono", "conduta")),
    ("org",      "Org",      ("alias-cadeiras",)),
    ("mesa",     "Mesa",     ("mesa",)),
    ("cadernos", "Cadernos", ("cadernos-indice", "cadernos")),
    ("caixa",    "Caixa",    ()),
]


# --- casca comum -------------------------------------------------------


def _nav(ativo: str) -> str:
    itens = [("/", "Recepção", "recepcao"), ("/feito", "Feito", "feito")]
    partes = []
    for href, rotulo, chave in itens:
        aria = ' aria-current="page"' if chave == ativo else ""
        partes.append(f'<a href="{href}"{aria}>{rotulo}</a>')
    # "Cadeiras" não tem rota de listagem própria — aponta pro bloco 3 da
    # recepção, âncora simples, sem duplicar dado.
    aria_cadeiras = ' aria-current="page"' if ativo == "cadeira" else ""
    partes.insert(1, f'<a href="/#cadeiras"{aria_cadeiras}>Cadeiras</a>')
    return "<nav>" + "".join(partes) + "</nav>"


def _topo(ativo: str, direita_html: str) -> str:
    return (
        '<header class="topo">'
        '<span class="marca">harness.platafirma.org</span>'
        f"{_nav(ativo)}"
        f'<span class="dir">{direita_html}</span>'
        "</header>"
    )


def pagina(titulo: str, ativo: str, direita_html: str, corpo_html: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>{_esc(titulo)}</title>
<meta name="platafirma-ui" content="{_esc(VERSAO_UI)}">
<link rel="stylesheet" href="{PF_UI_CSS_HREF}">
<link rel="stylesheet" href="{TELA_HREF}">
<script type="module" src="{PF_UI_JS_SRC}"></script>
</head>
<body>
{_topo(ativo, direita_html)}
{corpo_html}
</body>
</html>
"""


# --- bloco 1: Sinal ------------------------------------------------------


def _estado_container(estado_docker: str | None, saude_nativa: str | None) -> tuple[str, str, str]:
    """(rotulo, papel, caminho_exercitado) — três níveis: no ar (calmo) /
    degradado (caveat) / fora (alert), mais "sem sinal" (caveat) quando não
    há dado nenhum pra confiar.

    Dois sinais DISTINTOS, não um substituindo o outro:
    - `estado_docker` (docker inspect .State): "running" ou não — isto o
      Docker já garante HOJE, não depende de trilha C/#254. Container
      parado/morto é "fora", sempre, mesmo sem healthcheck configurado —
      é exatamente o que o aceite 2 do card verifica ("derrubando o
      rag-extractor-api").
    - `saude` (o healthcheck NATIVO do container, quando existe — parte do
      Status entre parênteses): só existe pra container com HEALTHCHECK
      declarado na imagem/compose. Refina "running" em healthy/unhealthy/
      starting; ausência dele não é "sem confiança nenhuma", é "sem
      diagnóstico de aplicação" — sonda externa por serviço é trilha C,
      ainda não construída, e É nesse caso (rodando, sem healthcheck
      próprio) que "sem sinal" se aplica de verdade.
    """
    estado_docker = (estado_docker or "").lower()
    if estado_docker and estado_docker != "running":
        return "fora", "alert", f"docker: {estado_docker}"
    if saude_nativa == "unhealthy":
        return "degradado", "caveat", "healthcheck: unhealthy"
    if saude_nativa == "healthy":
        return "no ar", "calmo", "healthcheck: healthy"
    if saude_nativa:
        return "degradado", "caveat", f"healthcheck: {saude_nativa}"
    if estado_docker == "running":
        return "sem sinal", "caveat", "sem sonda"
    return "sem sinal", "caveat", "sem sonda (estado do container indisponível)"


def bloco_sinal(bloco_estado: dict, bloco_saude: dict) -> str:
    idade = idade_desde(bloco_estado.get("lido_em"))
    linhas = []

    if bloco_estado.get("estado") != "ok" or bloco_saude.get("estado") != "ok":
        motivo = bloco_estado.get("motivo") or bloco_saude.get("motivo") or "sem leitura"
        corpo = f'<p class="indisponivel">Sem leitura. {_esc(motivo)}. Isto não é "tudo no ar".</p>'
    else:
        dados = bloco_estado.get("dados") or {}
        saude = bloco_saude.get("dados") or {}

        for c in dados.get("conteineres", []):
            nome = c.get("nome") or "?"
            excluido = nome in CLOUDFLARED_OAUTH2PROXY
            estado_final, papel_final, caminho = _estado_container(c.get("estado_docker"), c.get("saude"))
            acao = (
                '<span class="motivo">sustenta esta tela</span>' if excluido
                else f'<form method="post" action="/acoes/reiniciar" class="inline">'
                     f'<input type="hidden" name="alvo" value="{_esc(nome)}">'
                     f'<button class="acao" type="submit">Reiniciar {_esc(nome)}</button></form>'
            )
            linhas.append(
                f"<tr><td>{_esc(nome)}</td><td>{chip(estado_final, papel_final)}</td>"
                f"<td class='caminho'>{_esc(caminho)}</td>"
                f"<td class='dir'>{_esc(c.get('desde') or '—')}</td><td>{acao}</td></tr>"
            )

        falhadas = {u["nome"] for u in saude.get("falhadas", []) if u.get("nome")}
        for u in dados.get("units", []):
            nome = u.get("nome") or "?"
            fora = nome in falhadas
            papel = "alert" if fora else "calmo"
            estado_txt = "fora" if fora else "no ar"
            linhas.append(
                f"<tr><td>{_esc(nome)}</td><td>{chip(estado_txt, papel)}</td>"
                f"<td class='caminho'>unit --user</td><td class='dir'>—</td>"
                f"<td><span class='motivo'>sem restart pela tela</span></td></tr>"
            )

        ops = saude.get("ops_health") or {}
        papel_ops = "calmo" if ops.get("ok") else "alert"
        linhas.append(
            f"<tr><td>ops-mcp /health</td><td>{chip('no ar' if ops.get('ok') else 'fora', papel_ops)}</td>"
            f"<td class='caminho'>{_esc(ops.get('motivo') or '/health')}</td>"
            f"<td class='dir'>—</td><td>—</td></tr>"
        )

        corpo = (
            "<table><thead><tr><th>Serviço</th><th>Estado</th><th>Caminho exercitado</th>"
            "<th class='dir'>Idade</th><th>Ação</th></tr></thead><tbody>"
            + "".join(linhas)
            + "</tbody></table>"
        ) if linhas else '<p class="indisponivel">Nenhum serviço encontrado.</p>'

    return (
        '<section class="cartao" id="sinal">'
        '<div class="cab-bloco"><h2>Sinal</h2>'
        '<span class="pergunta">Quebrou alguma coisa?</span>'
        f'<span class="idade num">lido há {idade}</span></div>'
        f"{corpo}</section>"
    )


# --- bloco 2: Caixas -----------------------------------------------------


def bloco_caixas(bloco: dict, limiar_alert_seg: int = 3600) -> str:
    idade = idade_desde(bloco.get("lido_em"))
    # Sem JavaScript (mesma régua dos wireframes): nada de mostrar/esconder
    # formulário por clique — "Despachar recado" é âncora simples pro form,
    # que fica sempre no HTML, visível abaixo da tabela.
    cab = (
        '<div class="cab-bloco"><h2>Caixas</h2>'
        '<span class="pergunta">Tem mensagem parada?</span>'
        '<a class="acao primaria" href="#despachar">Despachar recado</a></div>'
    )
    if bloco.get("estado") != "ok":
        corpo = f'<p class="indisponivel">Sem leitura. {_esc(bloco.get("motivo") or "motivo desconhecido")}.</p>'
    else:
        linhas = []
        for item in bloco.get("dados") or []:
            persona = item.get("persona") or "?"
            estado_caixa = item.get("estado") or "vazia"
            pendentes = item.get("pendentes")
            parada = estado_caixa == "parada" and (item.get("idade_mais_antiga_seg") or 0) > limiar_alert_seg
            if estado_caixa == "vazia":
                papel, rotulo = "calmo", "vazia"
            elif estado_caixa == "em_dia":
                papel, rotulo = "calmo", "em dia"
            elif parada:
                papel, rotulo = "alert", "parada"
            else:
                papel, rotulo = "caveat", "parada"
            linhas.append(
                f"<tr><td><a href='/cadeira/{_esc(persona)}?doc=caixa'>{_esc(persona)}</a></td>"
                f"<td class='dir'>{_num(pendentes)}</td>"
                f"<td class='dir'>{idade_fmt(item.get('idade_mais_antiga_seg'))}</td>"
                f"<td class='dir'>{idade_fmt(item.get('ultima_leitura_seg'))}</td>"
                f"<td>{chip(rotulo, papel)}</td></tr>"
            )
        corpo = (
            "<table><thead><tr><th>Caixa</th><th class='dir'>Pendentes</th>"
            "<th class='dir'>Mensagem mais antiga</th><th class='dir'>Última leitura</th>"
            "<th>Estado</th></tr></thead><tbody>" + "".join(linhas) + "</tbody></table>"
        ) if linhas else '<p class="indisponivel">Nenhuma caixa encontrada.</p>'

    # Seletor fechado, e a fonte e a mesma que o verbo le: as caixas que o
    # proprio bloco acabou de listar. Texto livre aqui daria a tela uma
    # superficie que "fila enviar" nao tem — e um destinatario que so existe na
    # tela nao existe em lugar nenhum. Foi assim que "Claudinho-TI" virou caixa.
    destinos = [i.get("persona") for i in (bloco.get("dados") or []) if i.get("persona")]
    if destinos:
        campo_destino = (
            '<label>Destinatário <select name="destinatario" required>'
            + "".join(f'<option value="{_esc(d)}">{_esc(d)}</option>' for d in destinos)
            + "</select></label>"
        )
    else:
        # Sem leitura de caixa nao ha lista, e sem lista nao se despacha: a acao
        # some declarada, nao vira campo aberto "por enquanto".
        campo_destino = ""

    form = "" if not destinos else (
        '<form method="post" action="/acoes/despachar-recado" id="despachar">'
        + campo_destino
        + '<label>Tipo <select name="tipo" required>'
        + "".join(f'<option value="{t}">{t}</option>' for t in
                   ("decisao", "resposta", "pedido", "minuta", "demanda", "handoff"))
        + "</select></label>"
        '<label>Assunto <input type="text" name="assunto" required></label>'
        '<label>Corpo <textarea name="corpo" required></textarea></label>'
        '<button class="acao primaria" type="submit">Enviar</button>'
        "</form>"
    )
    return (
        f'<section class="cartao" id="caixas">{cab}'
        f'<span class="idade num">lido há {idade}</span>{corpo}{form}</section>'
    )


# --- bloco 3: Cadeiras -----------------------------------------------------


def bloco_cadeiras(bloco: dict) -> str:
    idade = idade_desde(bloco.get("lido_em"))
    cab = (
        '<div class="cab-bloco" id="cadeiras"><h2>Cadeiras</h2>'
        '<span class="pergunta">Meus agentes estão inteiros?</span>'
        f'<span class="idade num">lido há {idade}</span></div>'
    )
    if bloco.get("estado") != "ok":
        corpo = f'<p class="indisponivel">Sem leitura. {_esc(bloco.get("motivo") or "motivo desconhecido")}.</p>'
        return f'<section class="cartao">{cab}{corpo}</section>'

    # Coluna Fila SAIU (spec §bloco 2 nao a lista): a caixa e o bloco Caixas, mesma
    # fonte `fila status`. Duas leituras de fila que discordavam eram o defeito.
    # Presenca e derivada do `frescor` das pecas do pacote cru, nao de um digest
    # inexistente: persona/ofício servidas na abertura sao `fresco`; mesa lida idem.
    linhas = []
    for item in bloco.get("itens") or []:
        cadeira = item.get("cadeira") or "?"
        if item.get("estado") != "ok":
            linhas.append(
                f"<tr><td>{_esc(cadeira)}</td><td colspan='3'>"
                f"{chip('indisponível', 'alert')} <span class='motivo'>{_esc(item.get('motivo'))}</span>"
                f"</td><td class='dir'><a class='acao' href='/cadeira/{_esc(cadeira)}'>Abrir</a></td></tr>"
            )
            continue
        idx = _pecas_por_id((item.get("dados") or {}).get("pecas"))
        persona_ok = _fresco(idx.get("persona"))
        # "Manifesto" da cadeira = a peca ofício, servida na abertura.
        oficio_ok = _fresco(_acha_peca(idx, ("oficio",)))
        mesa_ok = _fresco(idx.get("mesa"))
        linhas.append(
            "<tr>"
            f"<td>{_esc(cadeira)}</td>"
            f"<td>{chip('presente' if persona_ok else 'ausente', 'calmo' if persona_ok else 'alert')}</td>"
            f"<td>{chip('presente' if oficio_ok else 'ausente', 'calmo' if oficio_ok else 'alert')}</td>"
            f"<td>{chip('lida' if mesa_ok else 'sem leitura', 'calmo' if mesa_ok else 'caveat')}</td>"
            f"<td class='dir'><a class='acao' href='/cadeira/{_esc(cadeira)}'>Abrir</a></td>"
            "</tr>"
        )
    corpo = (
        "<table><thead><tr><th>Cadeira</th><th>Persona</th><th>Manifesto</th>"
        "<th>Mesa</th><th></th></tr></thead><tbody>"
        + "".join(linhas) + "</tbody></table>"
    ) if linhas else '<p class="indisponivel">Nenhuma cadeira encontrada.</p>'
    return f'<section class="cartao">{cab}{corpo}</section>'


# --- bloco 4: Procedência --------------------------------------------------


def _predicado(nome_verbo: str, bloco: dict) -> str:
    if bloco.get("estado") != "ok":
        return (
            f'<div class="pred"><span class="verbo mono">{_esc(nome_verbo)}</span>'
            f'<span class="valor mal">—</span>{chip("sem leitura", "caveat")}</div>'
        )
    dados = bloco.get("dados") or {}
    resultado = dados.get("resultado")
    itens = dados.get("servicos") or dados.get("verbos") or dados.get("repos") or []
    n_divergencias = sum(1 for i in itens if _item_diverge(i))
    if resultado == "divergente":
        return (
            f'<div class="pred"><span class="verbo mono">{_esc(nome_verbo)}</span>'
            f'<span class="valor mal num">{n_divergencias}</span>{chip("divergem", "alert")}</div>'
        )
    return (
        f'<div class="pred"><span class="verbo mono">{_esc(nome_verbo)}</span>'
        f'<span class="valor num">0</span>{chip("sem divergência", "calmo")}</div>'
    )


def _item_diverge(item: dict) -> bool:
    if "divergencias" in item:
        return bool(item["divergencias"])
    if "motivos" in item:
        return bool(item["motivos"]) or not item.get("conforme", True)
    if "achados" in item:
        return any(item["achados"].get(k) for k in item["achados"])
    return False


def _predicado_skills(bloco_skills: dict) -> str:
    if bloco_skills.get("estado") != "ok":
        return (
            '<div class="pred"><span class="verbo mono">conferir skill</span>'
            f'<span class="valor mal">—</span>{chip("sem leitura", "caveat")}</div>'
        )
    itens = bloco_skills.get("itens") or []
    indeterminadas = sum(
        1 for i in itens if i.get("estado") == "ok" and (i.get("dados") or {}).get("veredito") == "indeterminado"
    )
    divergentes = sum(
        1 for i in itens if i.get("estado") == "ok" and (i.get("dados") or {}).get("veredito") == "divergente"
    )
    if divergentes:
        return (
            '<div class="pred"><span class="verbo mono">conferir skill</span>'
            f'<span class="valor mal num">{divergentes}</span>{chip("divergem", "alert")}</div>'
        )
    if indeterminadas:
        return (
            '<div class="pred"><span class="verbo mono">conferir skill</span>'
            f'<span class="valor num">{indeterminadas}</span>'
            f'{chip(f"{indeterminadas} indeterminada(s) — sem --servido", "caveat")}</div>'
        )
    return (
        '<div class="pred"><span class="verbo mono">conferir skill</span>'
        '<span class="valor num">0</span>' + chip("sem divergência", "calmo") + "</div>"
    )


def bloco_procedencia(servico: dict, verbo: dict, skills: dict, repo: dict) -> str:
    idade = idade_desde(min(
        (b.get("lido_em") for b in (servico, verbo, skills, repo) if b.get("lido_em") is not None),
        default=None,
    ))
    predicados = (
        _predicado("conferir servico", servico)
        + _predicado("conferir verbo", verbo)
        + _predicado_skills(skills)
        + _predicado("conferir repo", repo)
    )
    return (
        '<section class="cartao">'
        '<div class="cab-bloco"><h2>Procedência</h2>'
        '<span class="pergunta">O módulo está externalizado?</span>'
        f'<span class="idade num">lido há {idade}</span></div>'
        f'<div class="predicados">{predicados}</div>'
        "</section>"
    )


# --- saídas e recepção ------------------------------------------------------


def saidas_bloco() -> str:
    saidas = [
        ("Wiki", "O que vale hoje?", "https://wiki.platafirma.org"),
        ("Git do harness", "Como chegou a ser?", "https://github.com/plcarvalho301/platafirma-harness"),
        ("Rastreador", "O que está prometido?", "https://tarefas.platafirma.org"),
    ]
    itens = "".join(
        f'<a class="saida" href="{href}"><b>{nome}</b>'
        f'<span class="pergunta">{pergunta}</span><span class="url">{href}</span></a>'
        for nome, pergunta, href in saidas
    )
    return f'<div class="saidas">{itens}</div>'


def render_recepcao(estado: dict) -> str:
    direita = '<a href="/">Atualizar</a>'
    corpo = (
        # Ordem invertida por decisão do dono (10/08): saídas, procedência e
        # cadeiras primeiro. Sinal é lista longa de leitura sob demanda e desce
        # para o fim. Reorganização de fato fica para depois do engine (F5).
        '<div class="folha">'
        + saidas_bloco()
        + bloco_procedencia(
            estado.get("conferir_servico", {}), estado.get("conferir_verbo", {}),
            estado.get("skills", {}), estado.get("conferir_repo", {}),
        )
        + bloco_cadeiras(estado.get("cadeiras", {}))
        + bloco_caixas(estado.get("fila_status", {}))
        + bloco_sinal(estado.get("infra_estado", {}), estado.get("infra_saude", {}))
        + "</div>"
    )
    return pagina("harness.platafirma.org — recepção", "recepcao", direita, corpo)


# --- /cadeira/<slug> ---------------------------------------------------


def _painel_vivo(estado: dict, slug_l: str, idx: dict) -> str:
    """Coluna direita: estado vivo (caixa, mesa) + integridade por componente.
    A caixa sai da MESMA fonte do bloco Caixas da recepcao (`fila status`),
    casada pelo slug — fila e caixa deixam de ser duas leituras que discordam."""
    bloco_fila = estado.get("fila_status", {})
    if bloco_fila.get("estado") != "ok":
        caixa = '<div class="par"><dt>Caixa</dt><dd>sem leitura</dd></div>'
    else:
        item_fila = next((i for i in (bloco_fila.get("dados") or [])
                          if (i.get("persona") or "").lower() == slug_l), None)
        if not item_fila:
            caixa = '<div class="par"><dt>Caixa</dt><dd>vazia</dd></div>'
        else:
            caixa = (
                f'<div class="par"><dt>Pendentes</dt><dd class="num">{_num(item_fila.get("pendentes"))}</dd></div>'
                f'<div class="par"><dt>Mais antiga</dt><dd class="num">{idade_fmt(item_fila.get("idade_mais_antiga_seg"))}</dd></div>'
                f'<div class="par"><dt>Última leitura</dt><dd class="num">{idade_fmt(item_fila.get("ultima_leitura_seg"))}</dd></div>'
            )
    mesa_ok = _fresco(idx.get("mesa"))
    mesa = f'<div class="par"><dt>Mesa</dt><dd>{"lida" if mesa_ok else "sem leitura"}</dd></div>'

    def _int(rotulo: str, ok: bool) -> str:
        return (f'<div class="par"><dt>{rotulo}</dt>'
                f'<dd>{chip("OK" if ok else "ausente", "calmo" if ok else "alert")}</dd></div>')

    integridade = (
        _int("Persona", _fresco(idx.get("persona")))
        + _int("Org", _fresco(_acha_peca(idx, ("alias-cadeiras",))))
        + _int("Cadernos", _fresco(_acha_peca(idx, ("cadernos-indice", "cadernos"))))
    )
    return (
        '<aside class="cartao painel-vivo"><h2>Estado vivo</h2>'
        f'<dl>{caixa}{mesa}</dl>'
        '<h3>Integridade</h3>'
        f'<dl>{integridade}</dl></aside>'
    )


def render_cadeira(estado: dict, slug: str | None = None, doc: str | None = None,
                   chapeu: str | None = None) -> str:
    """É "o que este agente e, e o que ele tem na mao agora" (spec §/cadeira): tres
    colunas — as cadeiras, o documento escolhido por seletor (persona · GERAL ·
    org · mesa · cadernos) com um seletor de chapeu que filtra a mesa, e o estado
    vivo. Le o pacote CRU que a sonda `cadeiras` guarda (`monta-sessao --json`),
    nunca um digest. So leitura."""
    bloco = estado.get("cadeiras", {})
    itens = bloco.get("itens") or []
    por_slug: dict = {}
    rotulo_de: dict = {}
    for i in itens:
        c = i.get("cadeira")
        if c:
            por_slug.setdefault(c.lower(), i)
            rotulo_de.setdefault(c.lower(), c)
    todas = sorted(por_slug)
    slug_l = (slug or "").lower()
    if not slug_l and todas:
        slug_l = todas[0]
    slug_disp = rotulo_de.get(slug_l, slug or "")
    item = por_slug.get(slug_l)

    # coluna 1 — as cadeiras, marcada a atual; indisponivel se declara, nao some.
    lis = []
    for c in todas:
        it = por_slug[c]
        aria = ' aria-current="page"' if c == slug_l else ""
        est = "" if it.get("estado") == "ok" else '<span class="est">indisp.</span>'
        lis.append(f'<li><a href="/cadeira/{_esc(rotulo_de[c])}"{aria}>{_esc(rotulo_de[c])}{est}</a></li>')
    col_esq = ('<aside class="cartao"><h2>Cadeiras</h2>'
               f'<ul class="cadeiras">{"".join(lis) or "<li>—</li>"}</ul></aside>')

    revalida = '<span class="revalida num">revalida em até 60 s</span>'

    def _pagina(centro: str, direita: str = "") -> str:
        corpo = f'<div class="grade">{col_esq}{centro}{direita}</div>'
        return pagina(f"cadeira: {slug_disp or '—'}", "cadeira", revalida, corpo)

    if not slug_l:
        return _pagina('<section class="cartao"><p class="indisponivel">Nenhuma cadeira selecionada.</p></section>')
    if not item:
        return _pagina(f'<section class="cartao"><p class="indisponivel">Cadeira {_esc(slug_disp)} não encontrada nas leituras.</p></section>')
    if item.get("estado") != "ok":
        return _pagina(f'<section class="cartao"><p class="indisponivel">Sonda indisponível: {_esc(item.get("motivo"))}</p></section>')

    dados = item.get("dados") or {}
    idx = _pecas_por_id(dados.get("pecas"))
    nome = dados.get("nome_canonico") or slug_disp

    # cabecalho: nome + procedencia da morada (carimbo ao lado do texto, spec §3)
    morada = dados.get("morada") or {}
    proc = ""
    if morada:
        idade_h = morada.get("idade_h")
        proc = (
            '<div class="proc">'
            f'<span><b>morada</b> {_esc(morada.get("frescor") or "—")}</span>'
            f'<span><b>sha</b> <span class="mono">{_esc(morada.get("sha") or "—")}</span></span>'
            + (f'<span><b>publicada há</b> {_esc(idade_h)} h</span>' if idade_h is not None else "")
            + "</div>"
        )
    cab = f'<div class="cab"><h1>{_esc(nome)}</h1>{proc}</div>'

    # chapeus da cadeira: lista COMPLETA vinda do pacote (montador), nao so os que
    # tem mesa/caderno — a mesa sozinha traz so os chapeus com item. Sem a chave
    # (agregador em codigo velho, antes do restart) o seletor some, nao mente.
    chapeus = [c for c in (dados.get("chapeus") or []) if c]
    chapeu_sel = chapeu if chapeu in chapeus else None

    # seletor de documento — abas por link (sem JS): ?doc=<chave>. Com chapeu
    # escolhido, o doc que faz sentido e a mesa (unica com rotulo [chapeu]); senao,
    # default persona.
    docs_validos = {k for k, _r, _c in _DOCS_CADEIRA}
    doc_sel = doc if doc in docs_validos else ("mesa" if chapeu_sel else _DOCS_CADEIRA[0][0])
    tabs = []
    for chave, rotulo, _cands in _DOCS_CADEIRA:
        aria = ' aria-current="page"' if chave == doc_sel else ""
        tabs.append(f'<a href="/cadeira/{_esc(slug_disp)}?doc={chave}"{aria}>{_esc(rotulo)}</a>')
    docs_html = f'<div class="docs">{"".join(tabs)}</div>'

    # seletor de chapeu — filtra a mesa (unico doc com rotulo [chapeu]). Sempre
    # visivel quando a cadeira tem chapeu, pra achar sem garimpar; leva a doc=mesa.
    chapeus_html = ""
    if chapeus:
        links = ['<span class="rotulo">Chapéu (filtra a mesa):</span>']
        aria_todos = ' aria-current="page"' if not chapeu_sel else ""
        links.append(f'<a href="/cadeira/{_esc(slug_disp)}?doc=mesa"{aria_todos}>Todos</a>')
        for c in chapeus:
            aria = ' aria-current="page"' if c == chapeu_sel else ""
            links.append(f'<a href="/cadeira/{_esc(slug_disp)}?doc=mesa&amp;chapeu={_esc(c)}"{aria}>{_esc(c)}</a>')
        chapeus_html = f'<div class="docs chapeus">{"".join(links)}</div>'

    # leitura do documento selecionado, com carimbo de procedencia no topo.
    # A caixa nao e peca de monta-sessao: vem do bloco `caixa_conteudo`, a parte.
    if doc_sel == "caixa":
        leitura = _render_caixa_doc(estado, slug_l)
    else:
        cands = next(c for k, _r, c in _DOCS_CADEIRA if k == doc_sel)
        peca = _acha_peca(idx, cands)
        if peca is None:
            leitura = ('<div class="leitura"><p class="indisponivel">Documento não servido '
                       'nesta abertura (a sonda abre a cadeira sem chapéu).</p></div>')
        elif peca.get("conteudo"):
            corpo = peca.get("conteudo")
            if doc_sel == "mesa" and chapeu_sel:
                corpo = _filtra_mesa_por_chapeu(corpo, chapeu_sel)
            carimbo = (
                '<div class="carimbo">'
                f'<span><b>ref</b> <span class="mono">{_esc(peca.get("ref") or "—")}</span></span>'
                f'<span><b>blob</b> <span class="mono">{_esc(peca.get("sha") or "—")}</span></span>'
                f'<span><b>frescor</b> {_esc(peca.get("frescor") or "—")}</span>'
                + (f'<span><b>chapéu</b> {_esc(chapeu_sel)}</span>'
                   if doc_sel == "mesa" and chapeu_sel
                   else f'<span class="num"><b>tokens</b> {_num(peca.get("tokens"))}</span>')
                + "</div>"
            )
            leitura = f'<div class="leitura">{carimbo}<div class="corpo">{md_seguro(corpo)}</div></div>'
        else:
            leitura = ('<div class="leitura"><p class="indisponivel">'
                       f'Indisponível: {_esc(peca.get("motivo") or "sem conteúdo")}.</p></div>')

    centro = f'<section class="cartao">{cab}{docs_html}{chapeus_html}{leitura}</section>'
    direita = _painel_vivo(estado, slug_l, idx)
    return _pagina(centro, direita)


# --- /feito --------------------------------------------------------------


def render_feito(dias: list[dict]) -> str:
    """`dias`: [{"data": "2026-08-10",
    "cards": [{"id","titulo","commits": [{"sha","mensagem"}, ...]}],
    "commits": [{"sha","mensagem"}, ...]}] — o segundo "commits" é só os
    ÓRFÃOS (sem card associado); o commit ligado a um card aparece aninhado
    nele, não duas vezes. Mais recente primeiro — leitura derivada, sem
    estado próprio (spec)."""
    if not dias:
        corpo = '<div class="folha"><p class="indisponivel">Nada a mostrar ainda.</p></div>'
        return pagina("harness.platafirma.org — feito", "feito", "", corpo)

    def _commit_li(cm: dict) -> str:
        return f"<li><code>{_esc(cm.get('sha'))}</code> {_esc(cm.get('mensagem'))}</li>"

    blocos = []
    for dia in dias:
        itens_card = []
        for c in dia.get("cards", []):
            ligados = c.get("commits") or []
            sub = "".join(_commit_li(cm) for cm in ligados) or "<li class='motivo'>sem commit associado</li>"
            itens_card.append(f"<li>#{_esc(c.get('id'))} {_esc(c.get('titulo'))}<ul>{sub}</ul></li>")
        cards_html = "".join(itens_card) or "<li>—</li>"
        orfaos = dia.get("commits") or []
        orfaos_html = "".join(_commit_li(cm) for cm in orfaos) or "<li>—</li>"
        blocos.append(
            f'<section class="cartao"><h2>{_esc(dia.get("data"))}</h2>'
            f"<h3>Cards fechados</h3><ul>{cards_html}</ul>"
            f"<h3>Commits sem card associado</h3><ul>{orfaos_html}</ul></section>"
        )
    corpo = '<div class="folha">' + "".join(blocos) + "</div>"
    return pagina("harness.platafirma.org — feito", "feito", "", corpo)
