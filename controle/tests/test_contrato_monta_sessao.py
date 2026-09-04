"""Contrato de `bin/monta-sessao --json` / `--sem-atualizar` (card #204, item 2).

Reescrito para o modelo de árvore única `abertura/` (arq:0073): persona, chapéu,
ferramental e caderno moram em `abertura/<cadeira>[/<slug>]/`; o nome canônico vem
do ledger de vínculo (`registro/eventos-org.jsonl`), não mais da linha 1 da persona
— a persona nova traz o ALIAS ali, não o slug. As peças de chapéu (chapeu, ferramental,
caderno-chapeu) só entram na 2ª chamada (`--chapeu <slug>`), servidas por catálogo.

Contrato: `{cadeira, nome_canonico, morada, pacote, pecas, chapeu, roteador, avisos}`,
peças em envelope uniforme. `fila` não é peça de abertura (verbo on-demand, ordem do
dono) — test_fila_nao_e_peca_de_abertura é o guarda de regressão.

arq:0097 (runtime não lê working tree git): a abertura vem da MORADA PUBLICADA em
`$PF_ABERTURA_DIR/current/abertura`, e a chave `repos` do pacote deu lugar a `morada`.
O fixture publica a morada E mantém o clone git — de propósito: o clone existe para
provar que o montador NÃO o lê, e é ele que sustenta os dois guardas do ADR
(test_commit_local_nao_empurrado_nao_trava_o_boot,
test_nenhum_git_no_caminho_de_servico).

Isolamento: catálogo, morada e repositório vivem sob um `PF_RAIZ` hermético. O verbo
`mesa` entra por subprocess; `env_verbo()` prepende `{PF_RAIZ}/bin` no PATH, então o
stub mora em `<raiz>/bin/mesa` — e o stub de `git`, ao lado dele.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "monta-sessao"

MESA_STUB = """#!/bin/sh
set -eu
sub="${1:-}"
case "$sub" in
  ver)
    case "${MESA_STUB_MODO:-ok}" in
      ok) printf '[abertura] escrito ha 3 min\\\\nresumo da fita anterior\\\\n' ;;
      falha) echo "mesa: msg-mem fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  caderno)
    case "${CADERNO_STUB_MODO:-ok}" in
      ok) printf 'caderno %s (stub)\\\\n' "${2:-<indice>}" ;;
      falha) echo "mesa: caderno fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub mesa: subcomando nao coberto: $sub" 1>&2
    exit 2
    ;;
esac
"""

# Delator, não bloqueador: registra a chamada e ainda assim falha, para que um `git`
# que voltasse ao caminho de serviço apareça como linha no log E como pacote quebrado.
GIT_STUB = """#!/bin/sh
echo "$@" >> "${PF_GIT_LOG:?}"
echo "git nao pode ser chamado no caminho de servico (arq:0097)" 1>&2
exit 99
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _escreve(base: Path, rel: str, texto: str) -> Path:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def _peca(id_, artefato, *, evento="abertura", volatilidade="estavel"):
    return {
        "id": id_,
        "dono": "fixture",
        "artefato": artefato,
        "regime": "valor",
        "gatilho": {"evento": evento, "condicao": "fixture"},
        "volatilidade": volatilidade,
    }


def morada_de(raiz: Path) -> Path:
    """A morada publicada da raiz hermética — o contrato de `publicar-abertura`."""
    return raiz / "var" / "abertura-publicada"


def publicado(raiz: Path, rel: str) -> Path:
    """Caminho de um arquivo de abertura DENTRO da morada.

    Os testes que exercitam ausência apagam aqui, não no clone: apagar no clone não
    mudaria nada — que é justamente o ponto do arq:0097.
    """
    return morada_de(raiz) / "current" / "abertura" / rel


def _publica(raiz: Path, sha: str = "0" * 40, publicado_em: str | None = None) -> None:
    """Publica a árvore do clone na morada, no formato de `publicar-abertura`.

    Cópia, não git: o contrato que este teste guarda é o de LEITURA da morada. Que a
    árvore saia de um commit imutável por `git archive` é contrato do publicador, e
    tem teste próprio — repetí-lo aqui só acoplaria este arquivo ao git de novo.
    """
    origem = raiz / "platafirma-harness" / "abertura"
    ref = morada_de(raiz) / "refs" / sha
    if ref.exists():
        shutil.rmtree(ref)
    ref.mkdir(parents=True)
    shutil.copytree(origem, ref / "abertura")
    arquivos = [p for p in (ref / "abertura").rglob("*") if p.is_file()]
    (ref / "MANIFEST.json").write_text(json.dumps({
        "sha": sha,
        "sha_curto": sha[:7],
        "ref": "origin/main",
        "tree_sha": "t" * 40,
        "publicado_em": publicado_em or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "publicado_por": "publicar-abertura",
        "n_arquivos": len(arquivos),
        "n_bytes": sum(p.stat().st_size for p in arquivos),
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    current = morada_de(raiz) / "current"
    if current.is_symlink() or current.exists():
        current.unlink()
    current.symlink_to(Path("refs") / sha)


def _monta_raiz(tmp_path: Path) -> Path:
    """Raiz hermética no modelo abertura/: árvore + ledger + git + morada publicada."""
    raiz = tmp_path / "raiz"
    harness = raiz / "platafirma-harness"


    # persona NOVA: alias na linha 1, sem FERRAMENTAL. O canônico sai do ledger.
    _escreve(harness, "abertura/teste/persona.md",
             "Você é Testildo Testonildo, a persona fixture do contrato de monta-sessao.\n\n"
             "Resto do corpo, irrelevante para o contrato --json.\n")
    _escreve(harness, "abertura/fabrica/persona.md",
             "Você é Fabrildo Forasteiro, persona fixture fora do quadro.\n")
    _escreve(harness, "abertura/oficio.md", "# ofício comum\n\nfixture.\n")
    _escreve(harness, "abertura/dono.md", "# conduta do dono\n\nfixture.\n")
    _escreve(harness, "abertura/antirreabertura.md", "# antirreabertura\n\nfixture.\n")
    _escreve(harness, "abertura/teste/caderno.md", "# caderno head\n\nfixture.\n")
    # perna 2 (chapéu rh da cadeira teste)
    _escreve(harness, "abertura/teste/rh/chapeu.md", "# chapéu rh\n\nfixture.\n")
    _escreve(harness, "abertura/teste/rh/ferramental.md", "# ferramental rh\n\nfixture.\n")

    # ledger de vínculo: golden do canônico (arq:0073 §1). Schema real tem "tipo"
    # (nao "evento") e "alias" — #2438 deriva o mapa alias-cadeiras destes campos.
    _escreve(harness, "registro/eventos-org.jsonl",
             json.dumps({"cadeira": "claudinho-teste", "tipo": "PROVIMENTO",
                        "alias": "Testildo Testonildo"}) + "\n" +
             json.dumps({"cadeira": "claudinho-engenharia", "tipo": "PROVIMENTO"}) + "\n")

    # Fonte VIVA de identidade (arq:0073 §1, incidente/ordem do dono): a árvore
    # abertura/ e o aliases.json. O ledger acima permanece como HISTÓRICO (consulta),
    # NÃO é lido para resolver identidade. `teste` tem alias; `engenharia` é cadeira
    # viva sem alias, para exercitar a nota de omissão declarada.
    _escreve(harness, "abertura/engenharia/persona.md", "# engenharia\n\nfixture.\n")
    _escreve(harness, "abertura/aliases.json",
             json.dumps({"teste": "Testildo Testonildo"}, ensure_ascii=False) + "\n")

    _executavel(_escreve(raiz, "bin/mesa", MESA_STUB))
    _executavel(_escreve(raiz, "bin/git", GIT_STUB))

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)],
                   check=True, capture_output=True, text=True)
    _git(harness, "init", "-q", "-b", "main")
    _git(harness, "config", "user.email", "fixture@test.local")
    _git(harness, "config", "user.name", "fixture")
    _git(harness, "add", "-A")
    _git(harness, "commit", "-q", "-m", "fixture inicial")
    _git(harness, "remote", "add", "origin", str(origin))
    _git(harness, "push", "-q", "-u", "origin", "main")

    _publica(raiz)
    return raiz


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    return _monta_raiz(tmp_path)


def _run(args, raiz: Path, *, mesa_modo: str = "ok",
         caderno_modo: str = "ok") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PF_RAIZ"] = str(raiz)
    # `git` do stub à frente do real: no caminho de serviço não deve haver git nenhum,
    # e o que houver fica registrado em PF_GIT_LOG.
    env["PATH"] = f"{raiz / 'bin'}{os.pathsep}" + env.get("PATH", "")
    env["PF_GIT_LOG"] = str(raiz / "git-chamado.log")
    env["MESA_STUB_MODO"] = mesa_modo
    env["CADERNO_STUB_MODO"] = caderno_modo
    env.pop("PF_FITA", None)
    env.pop("PF_FORA_DO_QUADRO", None)
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20, check=False)


ENVELOPE_CHAVES = {"peca", "dono", "ref", "regime", "volatilidade",
                   "sha", "tokens", "frescor", "motivo", "conteudo"}


# --- formato e caminho feliz ------------------------------------------------


def test_json_pacote_e_objeto_unico_com_envelope_uniforme(raiz):
    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 0
    assert proc.stdout.count("\n") == 1
    dados = json.loads(proc.stdout)

    assert dados["cadeira"] == "teste"
    assert dados["nome_canonico"] == "teste"  # slug puro da árvore (incidente/expurgo do prefixo)
    assert "fila" not in dados

    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert ENVELOPE_CHAVES <= por_id["oficio"].keys()
    assert por_id["oficio"]["frescor"] == "fresco"
    assert por_id["oficio"]["conteudo"]
    # o `ref` continua na forma citável <repo>@<path>, mesmo lido da morada
    assert por_id["persona"]["ref"].endswith("abertura/teste/persona.md")

    assert dados["pacote"]["pecas"] == len(dados["pecas"])
    assert dados["pacote"]["tokens"] == sum(p["tokens"] for p in dados["pecas"])
    assert dados["pacote"]["metodo_tokens"]
    assert dados["pacote"]["registro"] == {
        "registrado": False, "motivo": "sem PF_FITA — sessao de mao nao tem fita"}


def test_pacote_traz_morada_publicada_no_lugar_de_repos(raiz):
    """arq:0097: quem data o pacote é o ref publicado, não o SHA de um clone. A chave
    `repos` sai inteira — manter um campo com nome de working tree seria justamente o
    falso-verde que o ADR fecha."""
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert "repos" not in dados
    m = dados["morada"]
    assert m["frescor"] == "publicado"
    assert m["motivo"] is None
    assert m["sha"] == "0" * 7
    assert m["abertura"].endswith("current/abertura")
    assert m["atualiza_por"] == "publicar-abertura"
    # o pacote é datado pelo ref publicado
    assert dados["pacote"]["montador_sha"] == m["sha"]


def test_nome_canonico_e_o_slug_puro_da_arvore(raiz):
    """O nome canônico é o SLUG PURO minúsculo (arq:0073 §2, expurgo do prefixo/
    incidente ordem do dono) — o próprio nome do diretório em abertura/, sem
    claudinho-/claudinha- e sem o alias da linha 1."""
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert dados["nome_canonico"] == "teste"
    assert "Testildo" not in (dados["nome_canonico"] or "")
    assert "claudinho-" not in (dados["nome_canonico"] or "")


def test_fila_nao_e_peca_de_abertura(raiz):
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert "fila" not in dados
    assert "fila" not in {p["peca"] for p in dados["pecas"]}
    assert "mesa" in {p["peca"] for p in dados["pecas"]}


def test_segunda_chamada_serve_pecas_do_chapeu(raiz):
    """`--chapeu rh` roteia por comando e traz chapeu + ferramental + caderno-chapeu,
    todas frescas e com conteúdo. Convivem com a abertura; a ausência da abertura é o
    caso `--so-chapeu`, coberto em test_so_chapeu_nao_reenvia_abertura."""
    dados = json.loads(_run(["teste", "--chapeu", "rh", "--json"], raiz).stdout)
    assert dados["chapeu"] == "rh"
    assert dados["roteador"]["slug"] == "rh"
    # peças de chapéu vêm rotuladas <id>:<slug> e carregam o campo slug
    do_chapeu = {p["peca"].split(":", 1)[0]: p
                 for p in dados["pecas"] if p.get("slug") == "rh"}
    for pid in ("chapeu", "ferramental", "caderno-chapeu"):
        assert do_chapeu[pid]["frescor"] == "fresco", pid
        assert do_chapeu[pid]["conteudo"], pid


def test_sem_atualizar_e_aceito_e_sem_efeito(raiz):
    """A flag sobrevive por compatibilidade de chamada e não muda mais nada: não há o
    que atualizar no caminho de serviço (arq:0097). Guarda contra alguém a reanimar
    ligando de novo o pull na abertura — quem atualiza é `publicar-abertura`."""
    com = json.loads(_run(["teste", "--json"], raiz).stdout)
    sem = json.loads(_run(["teste", "--json", "--sem-atualizar"], raiz).stdout)
    assert com["morada"] == sem["morada"]
    assert [p["peca"] for p in com["pecas"]] == [p["peca"] for p in sem["pecas"]]
    assert com["pacote"]["tokens"] == sem["pacote"]["tokens"]


# --- arq:0097: nada de working tree no caminho de serviço --------------------


def test_nenhum_git_no_caminho_de_servico(raiz):
    """Critério de pronto do arq:0097, medido e não declarado: com `git` sequestrado
    por um stub delator no PATH, uma abertura completa não deixa uma linha no log."""
    log = raiz / "git-chamado.log"
    proc = _run(["teste", "--chapeu", "rh", "--json"], raiz)
    assert proc.returncode == 0
    assert not log.exists(), f"git chamado no caminho de serviço: {log.read_text()}"


def test_commit_local_nao_empurrado_nao_trava_o_boot(raiz):
    """O defeito que o ADR fecha: um commit local ausente no remoto punha o clone na
    classe `divergente` e a sessão de TODA cadeira não abria (a cura seria reset --hard,
    destrutiva). Publicada a morada, o clone pode divergir à vontade — ninguém o lê."""
    harness = raiz / "platafirma-harness"
    _escreve(harness, "abertura/teste/persona.md", "persona reescrita, commitada, não empurrada\n")
    _git(harness, "add", "-A")
    _git(harness, "commit", "-q", "-m", "trabalho local nao empurrado")

    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert "erro" not in dados
    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert por_id["persona"]["frescor"] == "fresco"
    # e o que se serve é o PUBLICADO, não o commit local
    assert "Testildo" in por_id["persona"]["conteudo"]


def test_morada_nao_publicada_e_erro_com_a_cura_nomeada(raiz):
    """Ausência se declara. Sem morada a sessão não abre — e o erro traz o ato que a
    cura, não um diagnóstico de cadeira desconhecida (o gate vem antes da validação
    de cadeira justamente por isso)."""
    (morada_de(raiz) / "current").unlink()
    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 1
    dados = json.loads(proc.stdout)
    assert "nao publicado" in dados["erro"]
    assert "desconhecida" not in dados["erro"]
    assert dados["morada"]["frescor"] == "indisponivel"
    assert dados["morada"]["motivo"]
    assert any("publicar-abertura" in a for a in dados["avisos"])


def test_morada_declara_a_propria_idade(raiz):
    """Publicada agora, a idade é ~0 e nenhum aviso de atraso aparece."""
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert dados["morada"]["idade_h"] is not None
    assert dados["morada"]["idade_h"] < 1
    assert not any("morada publicada ha" in a for a in dados["avisos"])


def test_morada_velha_sai_avisada_na_abertura(tmp_path):
    """Morada não envelhece sozinha: `publicar-abertura` é ato deliberado, e entre dois
    atos ela serve texto de ontem calada — foi o que se mediu em 04/09 (27 commits
    atrás, sem sinal). Medir 'atrás do main' exigiria git, proibido neste caminho; a
    idade, não. Acima de 24h a abertura avisa, e nomeia o ato que republica."""
    raiz = _monta_raiz(tmp_path)
    _publica(raiz, publicado_em="2020-01-01T00:00:00Z")
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert dados["morada"]["idade_h"] > 24
    aviso = [a for a in dados["avisos"] if "morada publicada ha" in a]
    assert aviso, dados["avisos"]
    assert "publicar-abertura" in aviso[0]
    # avisa, não bloqueia: servir texto de ontem com sinal é melhor que não abrir
    assert "erro" not in dados
    assert dados["pacote"]["pecas"] > 0


def test_publicado_em_ilegivel_vira_idade_desconhecida_nao_zero(tmp_path):
    """Idade desconhecida se declara como desconhecida. Carimbo ilegível virando 0.0
    seria o falso-verde 'acabou de publicar' — pior que a ausência."""
    raiz = _monta_raiz(tmp_path)
    _publica(raiz, publicado_em="ontem de manhã")
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert dados["morada"]["idade_h"] is None
    assert not any("morada publicada ha" in a for a in dados["avisos"])


# --- resto do contrato ------------------------------------------------------


def test_fora_do_quadro_nao_recebe_antirreabertura(raiz):
    """Cadeira fora do quadro (#161 opção A): antirreabertura sai (mecânica de
    montagem de quem está dentro da casa). org/tool-manifest-geral não existem mais
    como peça — a poda que resta é a da antirreabertura."""
    dados = json.loads(_run(["fabrica", "--json"], raiz).stdout)
    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert "antirreabertura" not in por_id
    assert "oficio" in por_id  # o comum continua
    assert "persona" in por_id


def test_prefixo_claudinho_e_descartado(raiz):
    """Prefixo fóssil na ENTRADA é tolerado e descartado; o canônico servido nunca
    volta com prefixo — é o slug puro."""
    dados = json.loads(_run(["claudinho-teste", "--json"], raiz).stdout)
    assert dados["cadeira"] == "teste"
    assert dados["nome_canonico"] == "teste"


def test_cadeira_desconhecida_vira_objeto_de_erro_nunca_stdout_vazio(raiz):
    proc = _run(["fantasma", "--json"], raiz)
    assert proc.returncode == 1
    assert proc.stdout.count("\n") == 1
    dados = json.loads(proc.stdout)
    assert dados["erro"]
    assert "teste" in dados["cadeiras_validas"]
    assert "fabrica" in dados["cadeiras_validas"]


def test_sem_cadeira_e_uso_incorreto_exit_2(raiz):
    proc = _run(["--json"], raiz)
    assert proc.returncode == 2
    dados = json.loads(proc.stdout)
    assert dados["erro"]


def test_persona_ausente_nao_derruba_o_pacote(tmp_path):
    """Cadeira cujo diretório existe em abertura/ mas cujo persona.md ainda não foi
    redigido (backfill pendente): persona sai indisponível-declarada, o pacote
    continua válido — nunca erro. O diretório é o que mantém a cadeira pedível."""
    raiz = _monta_raiz(tmp_path)
    publicado(raiz, "teste/persona.md").unlink()
    # o diretório permanece: a cadeira segue pedível, só a peça persona fica ausente.
    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert por_id["persona"]["frescor"] == "indisponivel"
    assert por_id["persona"]["conteudo"] is None
    assert "oficio" in por_id and por_id["oficio"]["frescor"] == "fresco"


# --- indisponibilidade parcial ----------------------------------------------


def test_peca_verbo_indisponivel_nao_derruba_o_pacote(raiz):
    dados = json.loads(_run(["teste", "--json"], raiz, mesa_modo="falha").stdout)
    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert por_id["mesa"]["frescor"] == "indisponivel"
    assert por_id["mesa"]["motivo"]
    assert por_id["mesa"]["conteudo"] is None
    assert por_id["oficio"]["frescor"] == "fresco"
    assert dados["pacote"]["pecas"] == len(dados["pecas"])
    assert any("mesa" in a and "indisponível" in a for a in dados["avisos"])


# --- regressão do texto sem --json ------------------------------------------


def test_sem_json_mantem_marcadores_de_texto(raiz):
    proc = _run(["teste"], raiz)
    assert proc.returncode == 0
    linhas = proc.stdout.splitlines()
    assert linhas[0] == "== cadeira: teste =="
    assert any(l.startswith("===== oficio: platafirma-harness@abertura/oficio.md")
               for l in linhas)
    assert "{" not in proc.stdout


def test_so_chapeu_nao_reenvia_abertura(raiz):
    """Régua da Carla: na troca de chapéu mid-sessão, reenviar a abertura já servida é
    desperdício, então `--so-chapeu` devolve SÓ o chapéu, nenhuma peça de abertura.
    Antes acionado por inferência ('tem pergunta/chapéu'); agora por flag explícita —
    a inferência quebrava a abertura no fallback do #249 (ver os dois testes abaixo)."""
    dados = json.loads(_run(["teste", "--chapeu", "rh", "--so-chapeu", "--json"], raiz).stdout)
    ids = {p["peca"].split(":", 1)[0] for p in dados["pecas"]}
    assert ids == {"chapeu", "ferramental", "caderno-chapeu"}, f"so-chapeu vazou/omitiu: {ids}"
    assert dados["pacote"]["pecas"] == len(dados["pecas"])


def test_abertura_com_pergunta_que_nao_casa_serve_abertura(raiz):
    """Regressão #402 (colisão perna_dois × #249): pergunta que NÃO casa nenhum chapéu
    cai no fallback do roteador, mas a abertura-base tem de vir mesmo assim. O defeito
    era `pecas: []` sem `erro` — abertura pulada por inferência e chapéu ausente por
    fallback, a ambiguidade 'peça vazia × cadeira sem peça' que o contrato proíbe."""
    dados = json.loads(_run(
        ["teste", "--pergunta", "xyzzy nao casa nenhum rotulo", "--json"], raiz).stdout)
    assert dados["roteador"]["slug"] is None
    ids = {p["peca"] for p in dados["pecas"]}
    assert {"persona", "oficio", "conduta-dono"} <= ids, f"abertura sumiu no fallback: {ids}"
    assert dados["pacote"]["pecas"] > 0


def test_abertura_com_chapeu_serve_abertura_mais_chapeu(raiz):
    """Abrir com chapéu (sem --so-chapeu) é ADITIVO: abertura + chapéu, não só chapéu.
    É o que a persona faz na abertura (monta_sessao(cadeira, chapeu=slug)). Guarda que a
    persona (abertura) E as peças de chapéu convivam no mesmo pacote."""
    dados = json.loads(_run(["teste", "--chapeu", "rh", "--json"], raiz).stdout)
    ids = {p["peca"].split(":", 1)[0] for p in dados["pecas"]}
    assert "persona" in ids, f"abertura sumiu: {ids}"
    assert {"chapeu", "ferramental", "caderno-chapeu"} <= ids, f"chapeu sumiu: {ids}"
    assert dados["chapeu"] == "rh"


# --- alias-cadeiras (card #2438) ---------------------------------------------


def test_alias_cadeiras_serve_toda_cadeira_nao_so_fora_do_quadro(raiz):
    """Regressão do bug original: `por_id.get("alias-cadeiras")` nunca casava porque
    a peça não existia no catálogo (#189 partiu o catálogo, fase 5 não rodou). Agora
    é peça de catálogo com gatilho abertura — entra para QUALQUER cadeira, dentro ou
    fora do quadro (comentário #379: decisão do dono, servir a TODA cadeira)."""
    for alvo in ("teste", "fabrica"):
        dados = json.loads(_run([alvo, "--json"], raiz).stdout)
        por_id = {p["peca"]: p for p in dados["pecas"]}
        assert "alias-cadeiras" in por_id, alvo
        env = por_id["alias-cadeiras"]
        assert env["frescor"] == "fresco", (alvo, env)
        assert "Testildo Testonildo -> teste" in env["conteudo"]


def test_alias_cadeiras_so_endereco_sem_prefixo_e_omissao_declarada(raiz):
    """Conteúdo é 'Nome -> slug', slug sem claudinho-/claudinha- (mesma forma do
    diretório em abertura/), e PROVIMENTO sem alias (aqui: engenharia) sai como nota
    de omissão declarada — nunca silenciosamente ausente."""
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    env = {p["peca"]: p for p in dados["pecas"]}["alias-cadeiras"]
    assert "claudinho-" not in env["conteudo"]
    assert "claudinha-" not in env["conteudo"]
    assert "-> engenharia" not in env["conteudo"]  # sem alias, nao vira linha do mapa
    assert "omitido" in env["conteudo"] and "engenharia" in env["conteudo"]
    assert "engenharia" in (env["motivo"] or "")


def test_alias_cadeiras_indisponivel_sem_aliases_nao_derruba_pacote(tmp_path):
    """aliases.json ausente é indisponibilidade declarada, não crash do montador.
    (O ledger de vínculo não é mais lido para isto — incidente/ordem do dono.)"""
    raiz = _monta_raiz(tmp_path)
    publicado(raiz, "aliases.json").unlink()
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    env = {p["peca"]: p for p in dados["pecas"]}["alias-cadeiras"]
    assert env["frescor"] == "indisponivel"
    assert env["conteudo"] is None
    assert any("alias-cadeiras" in a for a in dados["avisos"])
