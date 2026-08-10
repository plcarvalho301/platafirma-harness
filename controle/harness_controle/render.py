# render — HTML por bloco, fiel às classes CSS dos wireframes de
# claudinha-produto (design/wireframes/harness-{recepcao,cadeira}.html),
# consumindo só design/tokens.css.
# capacidade: expediente
# dono: claudinho-TI
"""Sem framework de front, sem build, sem bundler, sem JavaScript — igual aos
wireframes. Revalidação de 60s é `<meta http-equiv="refresh">`, não fetch/poll;
"Atualizar" é um link comum pro próprio path. As duas ações (despachar recado,
reiniciar) são `<form method="post">` puros, POST-redirect-GET.

Princípio que governa cada função de render (spec §3): ausência de dado se
desenha como ausência, nunca como saúde. `0` e `—` nunca colapsam.
"""

from __future__ import annotations

import html
import time
from typing import Any

TOKENS_HREF = "/estatico/tokens.css"
# Camada 2: tokens.css nao conhece classe de superficie; sozinho, renderiza HTML nu.
TELA_HREF = "/estatico/tela.css"

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
<link rel="stylesheet" href="{TOKENS_HREF}">
<link rel="stylesheet" href="{TELA_HREF}">
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


# --- rodapé e recepção ------------------------------------------------------


def rodape() -> str:
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
        '<div class="folha">'
        + bloco_sinal(estado.get("infra_estado", {}), estado.get("infra_saude", {}))
        + bloco_caixas(estado.get("fila_status", {}))
        + bloco_cadeiras(estado.get("cadeiras", {}))
        + bloco_procedencia(
            estado.get("conferir_servico", {}), estado.get("conferir_verbo", {}),
            estado.get("skills", {}), estado.get("conferir_repo", {}),
        )
        + rodape()
        + "</div>"
    )
    return pagina("harness.platafirma.org — recepção", "recepcao", direita, corpo)


# --- /cadeira/<slug> ---------------------------------------------------


def render_cadeira(estado: dict, slug: str) -> str:
    bloco = estado.get("cadeiras", {})
    itens = {i.get("cadeira"): i for i in (bloco.get("itens") or [])}
    todas = sorted(itens)

    esquerda = "<ul class='cadeiras'>" + "".join(
        f'<li><a href="/cadeira/{_esc(c)}"{" aria-current=\"page\"" if c == slug else ""}>'
        f'{_esc(c)}</a> '
        + chip(
            "indisponível" if itens[c].get("estado") != "ok" else "ok",
            "caveat" if itens[c].get("estado") != "ok" else "calmo",
        )
        + "</li>"
        for c in todas
    ) + "</ul>"

    item = itens.get(slug)
    if item is None:
        centro = f'<p class="indisponivel">Cadeira {_esc(slug)} não encontrada nesta leitura.</p>'
        direita = ""
    elif item.get("estado") != "ok":
        centro = f'<p class="indisponivel">Sem leitura. {_esc(item.get("motivo"))}.</p>'
        direita = ""
    else:
        d = item.get("dados") or {}
        persona = d.get("persona") or {}
        manifesto = d.get("manifesto") or {}
        org = d.get("org") or {}
        mesa = d.get("mesa") or {}
        cadernos = d.get("cadernos") or {}
        fila = d.get("fila") or {}

        # Corpo dos documentos (persona/manifesto/GERAL/org) fica sob demanda
        # numa iteração futura — v1 mostra o que o retrato periódico já dá:
        # caminho e presença de cada um, carimbados, sem fingir seletor
        # interativo que não existiria sem JavaScript.
        docs_linhas = "".join(
            f"<tr><td>{rotulo}</td><td class='mono'>{_esc(caminho) if caminho else '—'}</td>"
            f"<td>{chip('presente' if presente else 'AUSENTE', 'calmo' if presente else 'alert')}</td></tr>"
            for rotulo, caminho, presente in (
                ("Persona", persona.get("caminho"), persona.get("presente")),
                ("Manifesto da cadeira", manifesto.get("caminho"), manifesto.get("presente")),
                ("Org canônico", org.get("caminho"), org.get("presente")),
            )
        )
        centro = (
            f'<div class="cartao cab"><h1>{_esc(slug)}</h1>'
            f'<p class="proc">fonte {_esc(persona.get("caminho"))} · '
            f'{"atualizado nesta leitura" if d.get("atualizado") else "leitura sem git pull"}</p>'
            "</div>"
            '<div class="cartao"><h2>Documentos</h2>'
            f"<table><tbody>{docs_linhas}</tbody></table>"
            "</div>"
        )
        direita = (
            '<div class="cartao"><h2>Agora</h2><dl>'
            f'<div class="par"><dt>Mesa</dt><dd>{"em dia" if mesa.get("disponivel") else "sem leitura"}'
            f' · {_esc(mesa.get("resumo") or "—")}</dd></div>'
            f'<div class="par"><dt>Cadernos</dt><dd>{"em dia" if cadernos.get("disponivel") else "sem leitura"}'
            f' · {_esc(cadernos.get("resumo") or "—")}</dd></div>'
            f'<div class="par"><dt>Caixa</dt><dd>{"em dia" if fila.get("disponivel") else "sem leitura"}'
            f' · {_esc(fila.get("resumo") or "—")}</dd></div>'
            "</dl></div>"
            '<div class="cartao"><h2>Integridade</h2><dl>'
            f'<div class="par"><dt>Persona</dt><dd>{chip("no head" if persona.get("presente") else "AUSENTE", "calmo" if persona.get("presente") else "alert")}</dd></div>'
            f'<div class="par"><dt>Manifesto</dt><dd>{chip("no head" if manifesto.get("presente") else "AUSENTE", "calmo" if manifesto.get("presente") else "alert")}</dd></div>'
            f'<div class="par"><dt>Org canônico</dt><dd>{chip("no head" if org.get("presente") else "AUSENTE", "calmo" if org.get("presente") else "alert")}</dd></div>'
            "</dl></div>"
        )

    corpo = f'<div class="grade"><aside>{esquerda}</aside><main>{centro}</main><aside>{direita}</aside></div>'
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
