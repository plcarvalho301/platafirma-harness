# componente: componente:postura
"""A composição por eixo e os atos do verbo persona, sem banco, sem memória de trabalho e sem log: os três entram por dublê,
e a árvore é uma pasta temporária com os documentos mínimos."""

from __future__ import annotations

import pytest

from postura import documentos as doc
from postura.atos import Contexto, ato_cenario, ato_trocar, ato_voltar
from postura.casa import SemBanco
from postura.composicao import compor
from postura.lousa import Fora

EIXOS = """eixos:
  - {slug: horizonte, rotulo: horizonte, ordem: 1, estado: vigente, polos: [{slug: visionario, rotulo: visionário}]}
  - {slug: autoria, rotulo: autoria, ordem: 2, estado: vigente, polos: [{slug: autor, rotulo: autor}, {slug: parecerista, rotulo: parecerista}]}
  - {slug: abertura, rotulo: abertura, ordem: 3, estado: vigente, polos: [{slug: explorador, rotulo: explorador}, {slug: decisor, rotulo: decisor}]}
  - {slug: crenca, rotulo: crença, ordem: 4, estado: vigente, polos: [{slug: cetico, rotulo: cético}]}
  - {slug: leitor, rotulo: leitor, ordem: 5, estado: vigente, polos: [{slug: leigo, rotulo: leigo}]}
  - {slug: risco, rotulo: risco, ordem: 7, estado: retirado, polos: [{slug: guardiao, rotulo: guardião}]}
"""


def _postura(titulo, *itens):
    return f"# {titulo}\n\nEntidade: postura\n\n## Para que lado puxa\n\n" + "".join(f"- {i}\n" for i in itens)


DOCUMENTOS = {
    "postura/postura.md": _postura("Postura da casa", "Diante de A, puxo para B, em vez de C, porque D."),
    "postura/olhar.md": _postura("Olhar", "[autoria: parecerista] Diante de P.", "[leitor: leigo] Diante de L."),
    "postura/cetico.md": _postura("Cético", "[crença: cético] Diante de C."),
    "postura/visionario.md": _postura("Visionário", "[horizonte: visionário] Diante de V."),
    "postura/explorador.md": _postura("Explorador", "[abertura: explorador] Diante de E."),
    "postura/construtor.md": _postura("Construtor", "[autoria: autor] Diante de A.", "[abertura: decisor] Diante de D."),
    "postura/torta.md": _postura("Torta", "Diante de um item sem marca."),
    "chapeu/design.md": "# Design\n\nEntidade: chapeu\n\n## Postura do ramo\n\n- [autoria: autor] Neste chapéu, diante de F.\n",
    "chapeu/jornada.md": "# Jornada\n\nEntidade: chapeu\n\n## Régua de resposta\n\nTexto.\n",
    "ritual/incidente.md": "# Incidente\n\nEntidade: ritual\n\nSuprime postura: sim\n\n## Para que lado puxa\n\n- Diante de X.\n",
    "ritual/da-casa.md": "# Ritual da casa\n\nEntidade: ritual\n\n## Para que lado puxa\n\n- Diante de pedido avulso, fecha no turno.\n",
    "ritual/lapidacao.md": "# Lapidação\n\nEntidade: ritual\n\n## Para que lado puxa\n\n- Diante de Y.\n",
    "cenario/pressa.md": "# Dono com pressa\n\nEntidade: cenario\n\n## Condição\n\nO dono tem pressa.\n\n## Sinais\n\nS.\n\n## Fim\n\nF.\n",
    "circunstancia/pressa-do-dono.md": "# Pressa do dono\n\nEntidade: circunstancia\n\n## Para que lado puxa\n\n- Diante de R.\n",
    "cultura/da-casa.md": "# Cultura da casa nova\n\nEntidade: cultura\n\n## Abertura da sessão\n\n- Primeira premissa da cultura.\n",
}


class LousaDeTeste:
    def __init__(self):
        self.postura, self.rit, self.cen, self.fora = {}, {}, {}, False

    def _vivo(self):
        if self.fora:
            raise Fora("memória de trabalho muda")

    def invocacoes(self, sid):
        self._vivo()
        return {k: dict(v) for k, v in self.postura.items()}

    def ritual(self, sid):
        self._vivo()
        return dict(self.rit)

    def cenarios(self, sid):
        self._vivo()
        return {k: dict(v) for k, v in self.cen.items()}

    def gravar_invocacoes(self, sid, campos, ritual=None):
        self._vivo()
        self.postura.update(campos)
        if ritual:
            self.rit = dict(ritual)

    def apagar_invocacoes(self, sid, eixos, ritual_tambem=False):
        self._vivo()
        for e in eixos:
            self.postura.pop(e, None)
        if ritual_tambem:
            self.rit = {}

    def entrar_cenario(self, sid, slug, valor):
        self.cen[slug] = valor

    def sair_cenario(self, sid, slug):
        self.cen.pop(slug, None)

    def apagar_tudo(self, sid):
        self.postura, self.rit, self.cen = {}, {}, {}


class LogDeTeste:
    def __init__(self):
        self.linhas = []

    def emitir(self, sessao_id, evento, **campos):
        self.linhas.append({"sessao_id": sessao_id, "evento": evento, **campos})

    def eventos(self, sessao_id=None):
        return [e for e in self.linhas if not sessao_id or e["sessao_id"] == sessao_id]

    def ultimos(self, sessao_id):
        saida = {"postura": {}, "cenario": {}, "ritual": None}
        for e in self.eventos(sessao_id):
            if e["evento"] == "postura":
                saida["postura"][e["eixo"]] = e
            elif e["evento"] == "cenario":
                saida["cenario"][e["cenario"]] = e
            elif e["evento"] == "ritual":
                saida["ritual"] = e
        return saida

    def defeito_ja_avisado(self, entidade, slug, sha):
        return any(e["evento"] == "defeito" and e.get("peca") == slug and e.get("sha") == sha for e in self.linhas)


class LigacoesDeTeste:
    def __init__(self, perfil="olhar", banco=True):
        self._perfil, self.banco = perfil, banco

    def perfil(self, cadeira):
        if not self.banco:
            raise SemBanco("fora")
        return self._perfil

    def ativadas(self, cenarios):
        return {c: "pressa-do-dono" for c in cenarios if c == "pressa"}


@pytest.fixture()
def ctx(tmp_path):
    for caminho, texto in DOCUMENTOS.items():
        alvo = tmp_path / doc.PASTA / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")
    (tmp_path / doc.PASTA / "persona").mkdir()
    (tmp_path / doc.PASTA / "persona" / "produto.md").write_text(
        "# Lygia\n\nEntidade: persona\n\nPostura preferencial: olhar\n\nSou a Lygia.\n", encoding="utf-8")
    (tmp_path / doc.EIXOS).parent.mkdir(parents=True)
    (tmp_path / doc.EIXOS).write_text(EIXOS, encoding="utf-8")
    relogio = iter(f"2026-11-10T00:00:{n:02d}" for n in range(60))
    incidentes = []
    c = Contexto(base=tmp_path, cadeira="produto", sessao_id="s1", chapeu="", lousa=LousaDeTeste(), log=LogDeTeste(),
                 ligacoes=LigacoesDeTeste(), incidente=lambda t, corpo: incidentes.append(t) or f"incidente: {t}",
                 agora=lambda: next(relogio))
    c.incidentes = incidentes
    return c


def rotulos(c, sessao=None):
    v = compor(c.base, c.cadeira, c.chapeu, c.sessao_id if sessao is None else sessao, c.lousa, c.log, c.ligacoes)
    return [l.rotulo() for l in v.servidas()], v


def test_sem_invocacao_vale_o_perfil(ctx):
    assert rotulos(ctx)[0] == ["autoria: parecerista", "leitor: leigo"]


def test_o_ramo_do_chapeu_cobre_o_eixo_do_perfil_e_o_chapeu_sem_ramo_nao_muda_nada(ctx):
    ctx.chapeu = "design"
    assert rotulos(ctx)[0] == ["autoria: autor", "leitor: leigo"]
    ctx.chapeu = "jornada"
    assert rotulos(ctx)[0] == ["autoria: parecerista", "leitor: leigo"]


def test_trocar_dois_nomes_ocupa_o_eixo_de_cada_um_e_diz_o_que_entrou(ctx, capsys):
    assert ato_trocar(ctx, ["cético", "e", "visionário"], "", "", "") == 0
    assert rotulos(ctx)[0] == ["horizonte: visionário", "autoria: parecerista", "crença: cético", "leitor: leigo"]
    saida = capsys.readouterr().out
    assert "horizonte: entrou visionário" in saida and "crença: entrou cético" in saida
    assert [(e["acao"], e["eixo"], e["para"]) for e in ctx.log.linhas if e["evento"] == "postura"] == [
        ("troca", "horizonte", "visionário"), ("troca", "crenca", "cético")]
    assert set(ctx.lousa.postura) == {"horizonte", "crenca"}      # perfil e ramo não se gravam
    assert ctx.lousa.postura["crenca"]["peca"] == "cetico" and ctx.lousa.postura["crenca"]["motivo"] == "dono"


def test_construtor_troca_a_autoria_do_perfil_e_diz_o_que_saiu(ctx, capsys):
    assert ato_trocar(ctx, ["construtor"], "", "", "") == 0
    assert rotulos(ctx)[0] == ["autoria: autor", "abertura: decisor", "leitor: leigo"]
    assert "autoria: saiu parecerista, entrou autor" in capsys.readouterr().out


def test_dois_nomes_no_mesmo_eixo_recusam_e_nada_muda(ctx, capsys):
    assert ato_trocar(ctx, ["explorador", "construtor"], "", "", "") == 2
    assert "dois nomes no eixo «abertura»" in capsys.readouterr().err
    assert ctx.lousa.postura == {} and ctx.log.linhas == []
    assert ato_trocar(ctx, ["cetico", "construtor"], "", "", "") == 0


def test_invocar_de_novo_num_eixo_troca_so_aquele_eixo(ctx):
    ato_trocar(ctx, ["construtor"], "", "", "")
    ato_trocar(ctx, ["explorador"], "", "", "")
    assert rotulos(ctx)[0] == ["autoria: autor", "abertura: explorador", "leitor: leigo"]


def test_postura_inexistente_sai_1_e_malformada_sai_4_com_incidente_e_nada_muda(ctx):
    assert ato_trocar(ctx, ["inexistente"], "", "", "") == 1
    assert ato_trocar(ctx, ["torta"], "", "", "") == 4
    assert ctx.incidentes == ["postura torta não cumpre a forma da entidade"]
    assert ato_trocar(ctx, ["torta"], "", "", "") == 4
    assert len(ctx.incidentes) == 1                               # o mesmo sha não abre incidente duas vezes
    assert ato_trocar(ctx, ["postura"], "", "", "") == 2          # a reserva não se invoca
    assert ctx.lousa.postura == {}


def test_voltar_sem_nome_apaga_tudo_e_com_nome_so_os_eixos_do_documento(ctx, capsys):
    ato_trocar(ctx, ["construtor", "cetico"], "", "", "")
    assert ato_voltar(ctx, "construtor", False) == 0
    assert rotulos(ctx)[0] == ["autoria: parecerista", "crença: cético", "leitor: leigo"]
    assert "autoria: saiu autor, voltou parecerista" in capsys.readouterr().out
    assert ato_voltar(ctx, "construtor", False) == 1
    assert ato_voltar(ctx, "", False) == 0
    aviso = rotulos(ctx)
    assert aviso[0] == ["autoria: parecerista", "leitor: leigo"] and not aviso[1].avisos      # a volta não é perda


def test_o_ritual_que_acaba_tira_so_o_que_invocou(ctx):
    ato_trocar(ctx, ["construtor"], "lapidacao", "oc1", "4174")
    ato_trocar(ctx, ["cetico"], "", "", "")
    assert ctx.lousa.postura["autoria"]["motivo"] == "ritual" and ctx.lousa.rit["slug"] == "lapidacao"
    assert ato_voltar(ctx, "", True) == 0
    assert rotulos(ctx)[0] == ["autoria: parecerista", "crença: cético", "leitor: leigo"] and ctx.lousa.rit == {}


def test_o_ritual_que_suprime_cala_o_bloco_e_serve_so_o_que_o_dono_invoca_durante(ctx):
    ato_trocar(ctx, ["cetico"], "", "", "")
    ato_trocar(ctx, [], "incidente", "", "")
    lista, v = rotulos(ctx)
    assert lista == [] and v.bloco() == "" and v.suspenso_por == "incidente"
    ato_trocar(ctx, ["visionario"], "", "", "")
    assert rotulos(ctx)[0] == ["horizonte: visionário"]
    ato_voltar(ctx, "", True)
    assert rotulos(ctx)[0] == ["horizonte: visionário", "autoria: parecerista", "crença: cético", "leitor: leigo"]


def test_perfil_malformado_cede_lugar_a_postura_da_casa_e_vira_incidente(ctx):
    ctx.ligacoes = LigacoesDeTeste(perfil="torta")
    lista, v = rotulos(ctx)
    assert lista == [] and v.reserva == ["Diante de A, puxo para B, em vez de C, porque D."]
    assert v.defeitos and "a postura da casa" in v.bloco()
    ctx.chapeu = "design"
    assert rotulos(ctx)[0] == ["autoria: autor"]                  # o ramo ainda entra, por cima da reserva


def test_chave_perdida_volta_ao_perfil_e_avisa_por_eixo_uma_vez(ctx):
    ato_trocar(ctx, ["construtor"], "", "", "")
    ctx.lousa.apagar_tudo("s1")
    lista, v = rotulos(ctx)
    assert lista == ["autoria: parecerista", "leitor: leigo"]
    perdas = [a for a in v.avisos if "perdeu a invocação" in a]
    assert len(perdas) == 2 and "voltou a «autoria: parecerista»" in perdas[0] and "ficou sem linha" in perdas[1]
    for evento, campos in v.perdidos:
        ctx.log.emitir("s1", evento, **campos)
    assert not rotulos(ctx)[1].avisos


def test_eixo_que_saiu_da_lista_e_ignorado_com_aviso(ctx):
    ctx.lousa.postura["risco"] = {"peca": "cetico", "motivo": "dono", "hora": "x"}
    lista, v = rotulos(ctx)
    assert lista == ["autoria: parecerista", "leitor: leigo"] and any("saiu da lista" in a for a in v.avisos)


def test_sessao_filha_nao_le_a_chave_de_quem_a_chamou(ctx):
    ato_trocar(ctx, ["construtor"], "", "", "")
    filha = LousaDeTeste()
    v = compor(ctx.base, "produto", "", "s1-filha", filha, ctx.log, ctx.ligacoes)
    assert [l.rotulo() for l in v.servidas()] == ["autoria: parecerista", "leitor: leigo"] and not v.avisos


def test_memoria_fora_serve_perfil_com_aviso_e_a_troca_sai_3(ctx):
    ctx.lousa.fora = True
    lista, v = rotulos(ctx)
    assert lista == ["autoria: parecerista", "leitor: leigo"] and v.memoria_fora and v.avisos
    assert ato_trocar(ctx, ["cetico"], "", "", "") == 3


def test_banco_fora_le_o_perfil_da_linha_da_persona(ctx):
    ctx.ligacoes = LigacoesDeTeste(banco=False)
    lista, v = rotulos(ctx)
    assert lista == ["autoria: parecerista", "leitor: leigo"] and any("Postura preferencial" in a for a in v.avisos)


def test_cenario_entra_ativa_a_circunstancia_e_sai(ctx):
    assert ato_cenario(ctx, "pressa", False) == 0
    v = rotulos(ctx)[1]
    assert [c[0] for c in v.cenarios] == ["pressa"] and v.circunstancia[0] == "pressa-do-dono"
    assert "CIRCUNSTÂNCIA EM VIGOR: Pressa do dono" in v.bloco_de_cenarios()
    assert ato_cenario(ctx, "pressa", True) == 0
    v = rotulos(ctx)[1]
    assert v.cenarios == [] and v.circunstancia is None and v.bloco_de_cenarios() == ""
    assert ato_cenario(ctx, "pressa", True) == 1 and ato_cenario(ctx, "nenhum", False) == 1
    assert [(e["acao"], e["cenario"]) for e in ctx.log.linhas if e["evento"] == "cenario"] == [("entra", "pressa"), ("sai", "pressa")]


def test_o_bloco_traz_o_rotulo_do_eixo_e_nao_traz_a_origem(ctx):
    ato_trocar(ctx, ["cetico"], "", "", "")
    bloco = rotulos(ctx)[1].bloco()
    assert "- [crença: cético] Diante de C." in bloco
    assert not any(p in bloco for p in ("perfil", "ramo", "invoca", "dono", "cetico.md"))


def test_ato_cultura_devolve_cultura_sem_titulo_e_sem_entidade(ctx, capsys):
    from postura.atos import ato_cultura
    assert ato_cultura(ctx) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("## Abertura da sessão")
    assert "Primeira premissa da cultura." in saida


def test_ato_apelidos_devolve_lista_ordenada_por_apelido(ctx, capsys):
    from postura.atos import ato_apelidos
    assert ato_apelidos(ctx) == 0
    saida = capsys.readouterr().out.strip().splitlines()
    assert saida == ["Lygia -> produto"]


def test_ato_conduta_desconhecido_sai_2(ctx, capsys):
    from postura.atos import despacha
    assert despacha(ctx, "conduta", []) == 2
    erro = capsys.readouterr().err
    assert "ato desconhecido: conduta · os atos são ler, trocar, voltar, cenario, cultura e apelidos" in erro


def test_remontagem_traz_comportamento_por_valor(ctx):
    from postura.remontagem import remontar
    ato_trocar(ctx, ["construtor"], "", "", "")
    rem = remontar(ctx)
    assert set(rem.rotulos_posturas) == {"autoria: autor", "abertura: decisor"}
    assert rem.cultura.startswith("## Abertura da sessão")
    assert "Sou a Lygia." in rem.persona


def test_ligacoes_casa_consulta_schema_vigente_e_remove_prefixo_da_classe():
    from postura.casa import Ligacoes

    chamadas = []

    class FakeLigacoes(Ligacoes):
        def _consulta(self, sql, parametros):
            chamadas.append((sql, parametros))
            if parametros[0] == "postura-preferencial":
                return [("postura:adaptavel",)]
            return [("cenario:dono-com-pressa", "circunstancia:pressa-do-dono")]

    lig = FakeLigacoes()
    assert lig.perfil("politicas-publicas") == "adaptavel"
    assert lig.ativadas(["dono-com-pressa"]) == {"dono-com-pressa": "pressa-do-dono"}
    assert lig.ativadas([]) == {}
    assert len(chamadas) == 2
    for sql, _ in chamadas:
        assert "o.uuid = l.de" in sql and "d.uuid = l.para" in sql and "l.terminou IS NULL" in sql
        assert "casa.shape" in sql and "casa.propriedade" in sql
    assert chamadas[0][1] == ("postura-preferencial", "persona", "postura", ["politicas-publicas", "persona:politicas-publicas"])
    assert chamadas[1][1] == ("ativa", "cenario", "circunstancia", ["dono-com-pressa", "cenario:dono-com-pressa"])


def test_dsn_postura_aponta_por_padrao_para_casa_db_e_prioriza_casa_pg(monkeypatch):
    from postura.casa import _dsn

    for chave in ("CASA_PG_HOST", "CASA_PG_PORT", "CASA_PG_USER", "CASA_PG_PASSWORD", "CASA_PG_DB",
                  "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(chave, raising=False)
    assert _dsn() == "postgresql://casa:@127.0.0.1:5439/casa"

    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "rag")
    monkeypatch.setenv("POSTGRES_PASSWORD", "a/b")
    monkeypatch.setenv("POSTGRES_DB", "rag_extractor")
    assert _dsn() == "postgresql://rag:a%2Fb@localhost:5432/rag_extractor"

    monkeypatch.setenv("CASA_PG_HOST", "127.0.0.1")
    monkeypatch.setenv("CASA_PG_PORT", "5439")
    monkeypatch.setenv("CASA_PG_USER", "casa")
    monkeypatch.setenv("CASA_PG_PASSWORD", "c@d")
    monkeypatch.setenv("CASA_PG_DB", "casa")
    assert _dsn() == "postgresql://casa:c%40d@127.0.0.1:5439/casa"


def test_ligacoes_construido_de_consulta_join_com_shape():
    from postura.casa import Ligacoes

    chamadas = []

    class FakeLigacoes(Ligacoes):
        def _consulta(self, sql, parametros):
            chamadas.append((sql, parametros))
            return [
                ("persona", "engenharia"),
                ("postura", "cirurgico"),
                ("cultura", "cultura:da-casa"),
            ]

    lig = FakeLigacoes()
    res = lig.construido_de("porta")
    assert res == [
        ("persona", "engenharia"),
        ("postura", "cirurgico"),
        ("cultura", "cultura:da-casa"),
    ]
    assert lig.construido_de("roteiro:porta") == res
    sql, params = chamadas[0]
    assert "JOIN casa.shape sd" in sql and "l.terminou IS NULL" in sql
    assert params == ("construido-de", "roteiro", ["porta", "roteiro:porta"])


def test_ato_ler_partes_separadas_e_json_com_perfil_e_ritual(ctx, capsys):
    import json
    from postura.atos import despacha

    assert ato_cenario(ctx, "pressa", False) == 0
    capsys.readouterr()

    assert despacha(ctx, "ler", ["--parte", "posturas", "--json"]) == 0
    d_pos = json.loads(capsys.readouterr().out)
    assert d_pos["perfil"] == "olhar"
    assert "POSTURAS EM VIGOR" in d_pos["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "cenario", "--json"]) == 0
    d_cen = json.loads(capsys.readouterr().out)
    assert d_cen["cenarios"] == ["pressa"]
    assert "CENÁRIOS PRESENTES" in d_cen["conteudo"]
    assert "CIRCUNSTÂNCIA EM VIGOR" not in d_cen["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "circunstancia", "--json"]) == 0
    d_circ = json.loads(capsys.readouterr().out)
    assert d_circ["circunstancia"] == "pressa-do-dono"
    assert "CIRCUNSTÂNCIA EM VIGOR: Pressa do dono" in d_circ["conteudo"]
    assert "CENÁRIOS PRESENTES" not in d_circ["conteudo"]

    # Ritual sem nada na lousa cai no fallback da-casa
    assert despacha(ctx, "ler", ["--parte", "ritual", "--json"]) == 0
    d_rit = json.loads(capsys.readouterr().out)
    assert d_rit["ritual"] == "da-casa"
    assert "RITUAL EM VIGOR: Ritual da casa" in d_rit["conteudo"]

    # Ritual na lousa prevalece
    ctx.lousa.rit = {"slug": "lapidacao"}
    assert despacha(ctx, "ler", ["--parte", "ritual", "--json"]) == 0
    d_rit_lousa = json.loads(capsys.readouterr().out)
    assert d_rit_lousa["ritual"] == "lapidacao"
    assert "RITUAL EM VIGOR: Lapidação" in d_rit_lousa["conteudo"]


def test_ato_ler_com_chave_serve_instancia_direta_e_sai_1_se_ausente(ctx, capsys):
    import json
    from postura.atos import despacha

    assert despacha(ctx, "ler", ["--parte", "posturas", "--chave", "construtor", "--json"]) == 0
    d_pos = json.loads(capsys.readouterr().out)
    assert d_pos["perfil"] == "construtor"
    assert "autoria: autor" in d_pos["posturas"]
    assert "Diante de A." in d_pos["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "ritual", "--chave", "lapidacao", "--json"]) == 0
    d_rit = json.loads(capsys.readouterr().out)
    assert d_rit["ritual"] == "lapidacao"
    assert "Diante de Y." in d_rit["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "cenario", "--chave", "pressa", "--json"]) == 0
    d_cen = json.loads(capsys.readouterr().out)
    assert d_cen["cenarios"] == ["pressa"]
    assert "O dono tem pressa." in d_cen["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "circunstancia", "--chave", "pressa-do-dono", "--json"]) == 0
    d_circ = json.loads(capsys.readouterr().out)
    assert d_circ["circunstancia"] == "pressa-do-dono"
    assert "Diante de R." in d_circ["conteudo"]

    assert despacha(ctx, "ler", ["--parte", "ritual", "--chave", "inexistente", "--json"]) == 1
    capsys.readouterr()
