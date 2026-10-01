"""units — a unit systemd --user que o bot gera e os declarantes que `conferir jobs` lê (card #3186).

Contrato (bin/bot e `release conferir jobs` leem este arquivo; a interface é esta):
  CABECALHO_GERADO          1ª linha de todo .service/.timer gerado pelo bot
  eh_unit_do_bot(texto)     True só se a 1ª linha do texto é CABECALHO_GERADO, inteira
  duracao_para_iso(texto)   '1d' '6h' '30m' '90s' '1d12h' ou ISO 8601 pronto -> ISO 8601
                            ('P1D', 'PT6H', 'P1DT12H'); zero, negativo ou lixo -> ValueError
  nomes_da_unit(slug)       ('<slug>.service', '<slug>.timer'); ValueError se o slug não casa SLUG
  gera_unit(declaracao)     (texto_service, texto_timer) de uma declaração com trigger timer
                            (dict com slug e trigger_arg, como o serviço devolve); puro e
                            byte a byte determinístico; ValueError se o slug não casa SLUG,
                            o gatilho não é timer ou o calendário é vazio ou tem quebra de linha,
                            caractere de controle, barra invertida ou % (injeção no texto da unit)
  dir_units()               Path onde se gravam as units: PF_UNITS_DIR (só teste) >
                            ~/.config/systemd/user se gravável > $XDG_DATA_HOME/systemd/user
                            (padrão ~/.local/share/systemd/user); quem grava diz a morada usada
  dirs_candidatas()         lista de Path de todas as moradas possíveis (PF_UNITS_DIR, ~/.config e
                            $XDG_DATA_HOME, em systemd/user); quem desfaz procura em todas
  dir_wants(alvo)           Path do <alvo>.wants (padrão timers.target) onde o symlink habilita
                            a unit: ~/.config/systemd/user/<alvo>.wants, ou PF_UNITS_DIR/<alvo>.wants
                            sob o override de teste; só o .wants de ~/.config conta como enabled
  sh(args, timeout=None)    (rc, stdout, stderr) sem shell; rc 127 se não executa, 124 no timeout
  systemctl_show(unit, props)
                            ({prop: valor}, None) ou (None, motivo); lê `systemctl --user show`
  declarantes_de_jobs(release)
                            (decl, esperados, faltas) dos registros servidos da release
  le_unit(caminho)          texto do arquivo da unit, ou '' se não lê
  fichas_do_bot(bin_irmaos) ({slug: ficha}, None) das fichas ativas por `bot listar --json`, ou
                            ({}, motivo) se o serviço não responde; verbo ausente = sem fichas
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

CABECALHO_GERADO = "# GERADO por bot — não editar"

ENV_OPS = "/home/claudinho/.config/ops/env"
UNIT_SISTEMA = ("/usr/lib/systemd/user/", "/lib/systemd/user/")

RELEASE_HARNESS = "/opt/platafirma/current/harness"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_CURTA = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")
_ISO = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def sh(args, timeout=None):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"{os.path.basename(args[0])} passou de {timeout}s sem resposta"
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        return 127, "", f"nao consegui executar {args[0]}: {e}"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def eh_unit_do_bot(texto):
    return texto.splitlines()[:1] == [CABECALHO_GERADO]


def duracao_para_iso(texto):
    t = texto.strip()
    if t.upper().startswith("P"):
        m = _ISO.match(t.upper())
        horas_sem_valor = "T" in t.upper() and not any(m.groups()[1:]) if m else False
        if not m or not any(m.groups()) or horas_sem_valor or not sum(int(g or 0) for g in m.groups()):
            raise ValueError(f"duracao invalida: {texto!r} (ISO 8601 como P1D, PT6H, maior que zero)")
        return t.upper()
    m = _CURTA.match(t.lower())
    if not m or not any(m.groups()) or not sum(int(g or 0) for g in m.groups()):
        raise ValueError(f"duracao invalida: {texto!r} (use 1d, 6h, 30m, 90s, 1d12h ou ISO 8601 como P1D)")
    d, h, mi, s = (int(g) if g else 0 for g in m.groups())
    tempo = "".join(f"{v}{u}" for v, u in ((h, "H"), (mi, "M"), (s, "S")) if v)
    return "P" + (f"{d}D" if d else "") + (f"T{tempo}" if tempo else "")


def nomes_da_unit(slug):
    if not SLUG.fullmatch(slug):
        raise ValueError(f"slug invalido: {slug!r} (minusculas, digitos e hifen entre eles)")
    return f"{slug}.service", f"{slug}.timer"


def gera_unit(declaracao):
    """Forma de deploy-harness/sinal.service e sinal.timer: Type=oneshot, release e nunca
    clone, mesmo ambiente do ops-mcp (sem o EnvironmentFile o verbo toma 401). Sem
    SuccessExitStatus: exit != 0 do job deixa a unit failed, e é isso que `bot caidas` vê."""
    slug = declaracao["slug"]
    servico, _ = nomes_da_unit(slug)
    if declaracao.get("trigger_tipo", "timer") != "timer":
        raise ValueError(f"unit so existe para trigger timer, nao {declaracao.get('trigger_tipo')!r}")
    cal = declaracao.get("trigger_arg") or ""
    if not cal.strip() or any(ord(c) < 32 or ord(c) == 127 or c in "\\%" for c in cal):
        raise ValueError(f"calendario invalido: {cal!r} (vazio, quebra de linha, caractere de controle, "
                         "barra invertida ou %: o systemd os le como continuacao de linha e especificador)")
    fonte = f'# fonte: ficha de automacao "{slug}" no acervo; desfazer: bot desligar {slug}'
    service = "\n".join([
        CABECALHO_GERADO,
        fonte,
        "[Unit]",
        f"Description=bot — {slug}",
        "",
        "[Service]",
        "Type=oneshot",
        f"WorkingDirectory={RELEASE_HARNESS}",
        f"Environment=PATH={RELEASE_HARNESS}/bin:/usr/local/bin:/usr/bin:/bin",
        f"EnvironmentFile={ENV_OPS}",
        f"ExecStart={RELEASE_HARNESS}/bin/bot rodar {slug}",
        "",
    ])
    timer = "\n".join([
        CABECALHO_GERADO,
        fonte,
        "[Unit]",
        f"Description=bot — {slug} (agenda)",
        "",
        "[Timer]",
        f"OnCalendar={cal}",
        f"Unit={servico}",
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])
    return service, timer


def _conf_systemd():
    return Path.home() / ".config" / "systemd" / "user"


def dir_units():
    forcado = os.environ.get("PF_UNITS_DIR", "").strip()
    if forcado:
        return Path(forcado)
    if os.access(_conf_systemd(), os.W_OK):
        return _conf_systemd()
    dados = os.environ.get("XDG_DATA_HOME", "").strip() or str(Path.home() / ".local" / "share")
    return Path(dados) / "systemd" / "user"


def dirs_candidatas():
    """Todas as pastas onde uma unit do bot pode ter caido: PF_UNITS_DIR (so teste), ~/.config/systemd/user e
    $XDG_DATA_HOME/systemd/user. A morada muda com a permissao do ~/.config; quem desfaz procura em todas."""
    dados = os.environ.get("XDG_DATA_HOME", "").strip() or str(Path.home() / ".local" / "share")
    forcado = os.environ.get("PF_UNITS_DIR", "").strip()
    achadas = [Path(forcado)] if forcado else []
    for d in (_conf_systemd(), Path(dados) / "systemd" / "user"):
        if d not in achadas:
            achadas.append(d)
    return achadas


def dir_wants(alvo="timers.target"):
    forcado = os.environ.get("PF_UNITS_DIR", "").strip()
    return (Path(forcado) if forcado else _conf_systemd()) / f"{alvo}.wants"


def le_unit(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError):
        return ""


def systemctl_show(unit, props):
    rc, out, err = sh(["systemctl", "--user", "show", unit, "-p", ",".join(props)], timeout=30)
    if rc != 0:
        return None, (err or out or f"systemctl saiu {rc}").splitlines()[0]
    d = {}
    for linha in out.splitlines():
        k, _, v = linha.partition("=")
        d[k] = v
    return d, None


def declarantes_de_jobs(release):
    """{unit: declarante} dos registros servidos e o conjunto de timers que um
    instalador por symlink promete ligar. Registro ilegivel volta em `faltas`."""
    decl, esperados, faltas = {}, set(), []
    instalar = os.path.join(release, "harness", "deploy-harness", "instalar")
    try:
        with open(instalar, encoding="utf-8") as f:
            texto = f.read()
        bloco = re.search(r"^UNITS=\((.*?)^\)", texto, re.S | re.M)
        for rel in re.findall(r'"([^"|]+)\|', bloco.group(1) if bloco else ""):
            nome = os.path.basename(rel)
            decl[nome] = "harness@deploy-harness/instalar"
            if nome.endswith(".timer"):
                esperados.add(nome)
    except OSError as e:
        faltas.append(f"harness@deploy-harness/instalar ilegivel: {e}")
    reg = os.path.join(release, "core", "deploy", "units-da-instancia.json")
    try:
        with open(reg, encoding="utf-8") as f:
            d = json.load(f)
        for nome in d.get("units", {}):
            decl.setdefault(nome, "core@deploy/instala-units.sh")
            if nome.endswith(".timer"):
                esperados.add(nome)
        for chave, onde in d.get("_fora_deste_instalador", {}).items():
            for nome in (n.strip() for n in chave.split(",")):
                decl.setdefault(nome, "core@deploy/units-da-instancia.json: " + onde.split(" — ")[0])
    except (OSError, ValueError) as e:
        faltas.append(f"core@deploy/units-da-instancia.json ilegivel: {e}")
    return decl, esperados, faltas


def fichas_do_bot(bin_irmaos):
    """Fichas ativas de automacao por `bot listar --json` (a ficha mora no acervo, o bot e o
    leitor). Sem o verbo na release nao ha ficha que sustente unit: ({}, None)."""
    bot = os.path.join(bin_irmaos, "bot")
    if not os.path.isfile(bot):
        return {}, None
    rc, out, err = sh([bot, "listar", "--json"], timeout=60)
    if rc != 0:
        return {}, f"bot listar --json saiu {rc}: {(err or out or 'sem saida').splitlines()[0]}"
    try:
        lista = json.loads(out)
    except ValueError:
        return {}, "bot listar --json nao devolveu JSON"
    if isinstance(lista, dict):
        lista = lista.get("itens")
    if not isinstance(lista, list):
        return {}, "bot listar --json nao devolveu uma lista de fichas"
    return {f["slug"]: f for f in lista
            if isinstance(f, dict) and f.get("slug") and f.get("ciclo", "ativa") == "ativa"}, None
