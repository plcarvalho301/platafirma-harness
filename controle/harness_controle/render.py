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
import time
from pathlib import Path
from typing import Any

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
                f"<tr><td>{_esc(persona)}</td><td class='dir'>{_num(pendentes)}</td>"
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
    else:
        linhas = []
        for item in bloco.get("itens") or []:
            cadeira = item.get("cadeira") or "?"
            if item.get("estado") != "ok":
                linhas.append(
                    f"<tr><td>{_esc(cadeira)}</td><td colspan='4'>"
                    f"{chip('indisponível', 'alert')} <span class='motivo'>{_esc(item.get('motivo'))}</span>"
                    f"</td><td><a class='acao' href='/cadeira/{_esc(cadeira)}'>Abrir</a></td></tr>"
                )
                continue
            d = item.get("dados") or {}
            persona = d.get("persona") or {}
            manifesto = d.get("manifesto") or {}
            defasado = (not persona.get("presente")) or (manifesto.get("caminho") and not manifesto.get("presente"))
            papel_persona = "alert" if not persona.get("presente") else "calmo"
            papel_manifesto = "alert" if defasado else "calmo"
            linhas.append(
                "<tr>"
                f"<td>{_esc(cadeira)}</td>"
                f"<td>{chip('presente' if persona.get('presente') else 'ausente', papel_persona)}</td>"
                f"<td>{chip('presente' if manifesto.get('presente') else 'ausente', papel_manifesto)}</td>"
                f"<td>{chip('em dia' if (d.get('mesa') or {}).get('disponivel') else 'sem leitura', 'calmo' if (d.get('mesa') or {}).get('disponivel') else 'caveat')}</td>"
                f"<td>{chip('em dia' if (d.get('fila') or {}).get('disponivel') else 'sem leitura', 'calmo' if (d.get('fila') or {}).get('disponivel') else 'caveat')}</td>"
                f"<td><a class='acao' href='/cadeira/{_esc(cadeira)}'>Abrir</a></td>"
                "</tr>"
            )
        corpo = (
            "<table><thead><tr><th>Cadeira</th><th>Persona</th><th>Manifesto</th>"
            "<th>Mesa</th><th>Fila</th><th></th></tr></thead><tbody>"
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


def render_cadeira(estado: dict, slug: str | None = None, chapeu: str | None = None) -> str:
    bloco_cadeiras = estado.get("cadeiras", {})
    itens_cadeiras = {i.get("cadeira"): i for i in (bloco_cadeiras.get("itens") or [])}
    todas = sorted(itens_cadeiras)
    if not slug and todas:
        slug = todas[0]

    # --- Topo: Dropdowns ---
    bloco_mesas = estado.get("mesas", {})
    itens_mesas = {i.get("cadeira"): i for i in (bloco_mesas.get("itens") or [])}
    item_mesa = itens_mesas.get(slug)
    
    chapeus_conhecidos = set()
    mesa_dados = {}
    if item_mesa and item_mesa.get("estado") == "ok":
        mesa_dados = item_mesa.get("dados") or {}
        if isinstance(mesa_dados, dict):
            chapeus_conhecidos.update(mesa_dados.get("chapeus") or [])
            if "itens" in mesa_dados:
                for it in mesa_dados["itens"]:
                    if isinstance(it, dict) and it.get("chapeu"):
                        chapeus_conhecidos.add(it["chapeu"])
        elif isinstance(mesa_dados, list):
            for it in mesa_dados:
                if isinstance(it, dict) and it.get("chapeu"):
                    chapeus_conhecidos.add(it["chapeu"])

    if chapeu and chapeu not in chapeus_conhecidos:
        chapeus_conhecidos.add(chapeu)
        
    lista_chapeus = sorted(chapeus_conhecidos)
    
    opts_cadeira = "".join(f'<option value="{_esc(c)}"{" selected" if c == slug else ""}>{_esc(c)}</option>' for c in todas)
    opts_chapeu = '<option value="">(Todos)</option>' + "".join(f'<option value="{_esc(c)}"{" selected" if c == chapeu else ""}>{_esc(c)}</option>' for c in lista_chapeus)
    
    topo = (
        '<div class="cartao cab">'
        '<form method="get" action="/cadeira" class="seletor-cadeira">'
        '<label>Cadeira <select name="cadeira" onchange="this.form.submit()">' + opts_cadeira + '</select></label>'
        '<label>Chapéu <select name="chapeu" onchange="this.form.submit()">' + opts_chapeu + '</select></label>'
        '<noscript><button type="submit" class="acao">Ir</button></noscript>'
        '</form></div>'
    )

    # --- Centro: Estado Vivo (Mesa + Caixa) ---
    centro_html = ""
    if not slug:
        centro_html = '<p class="indisponivel">Nenhuma cadeira selecionada.</p>'
    else:
        if not item_mesa:
            mesa_html = '<p class="indisponivel">Sonda de mesa não encontrou esta cadeira.</p>'
        elif item_mesa.get("estado") != "ok":
            mesa_html = f'<p class="indisponivel">Mesa indisponível: {_esc(item_mesa.get("motivo"))}</p>'
        else:
            if isinstance(mesa_dados, dict):
                corpo = mesa_dados.get("corpo")
                if corpo is None:
                    corpo = json.dumps(mesa_dados, indent=2, ensure_ascii=False)
                sha = mesa_dados.get("sha", "—")
                idade_mesa = idade_fmt(mesa_dados.get("idade_seg"))
            else:
                corpo = json.dumps(mesa_dados, indent=2, ensure_ascii=False)
                sha = "—"
                idade_mesa = "—"
                
            mesa_html = (
                f'<div class="mesa-vivo">'
                f'<div class="meta">sha: {_esc(sha)} | idade: {idade_mesa}</div>'
                f'{_esc(corpo)}</div>'
            )

        bloco_fila = estado.get("fila_status", {})
        if bloco_fila.get("estado") != "ok":
            caixa_html = f'<p class="indisponivel">Caixa indisponível: {_esc(bloco_fila.get("motivo"))}</p>'
        else:
            dados_fila = bloco_fila.get("dados") or []
            item_fila = next((i for i in dados_fila if i.get("persona") == slug), None)
            if not item_fila:
                caixa_html = '<p class="indisponivel">Caixa vazia ou não encontrada.</p>'
            else:
                pendentes = item_fila.get("pendentes", 0)
                idade_msg = idade_fmt(item_fila.get("idade_mais_antiga_seg"))
                ult_leitura = idade_fmt(item_fila.get("ultima_leitura_seg"))
                caixa_html = (
                    f'<div class="caixa-fria">'
                    f'<strong>Caixa:</strong> {pendentes} pendentes | '
                    f'Mais antiga: {idade_msg} | '
                    f'Última leitura: {ult_leitura}'
                    f'</div>'
                )

        centro_html = f'<div class="cartao painel-vivo"><h2>Estado Vivo</h2>{caixa_html}{mesa_html}</div>'

    # --- Rodapé: Integridade ---
    item_cad = itens_cadeiras.get(slug)
    rodape_html = ""
    if item_cad and item_cad.get("estado") == "ok":
        d = item_cad.get("dados") or {}
        persona = d.get("persona") or {}
        manifesto = d.get("manifesto") or {}
        skill_info = d.get("skill") or {} # maybe present
        
        rodape_html = (
            '<div class="cartao rodape-integridade">'
            '<strong>Integridade:</strong> '
            f'Persona {chip("OK" if persona.get("presente") else "AUSENTE", "calmo" if persona.get("presente") else "alert")} | '
            f'Manifesto {chip("OK" if manifesto.get("presente") else "AUSENTE", "calmo" if manifesto.get("presente") else "alert")}'
            '</div>'
        )

    corpo = f'<div class="folha" style="display: flex; flex-direction: column; min-height: 100vh;">{topo}{centro_html}{rodape_html}</div>'
    return pagina(f"cadeira: {slug}", "cadeira", '<span class="revalida num">revalida em até 60 s</span>', corpo)


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
