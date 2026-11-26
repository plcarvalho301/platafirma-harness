#!/usr/bin/env python3
# _infra-backup.py — corpo de `infra backup`. Mede, dispara sob demanda e restaura
# o declarado em registro/backups.json.
# capacidade: infra
# dono: ti
"""Mede, dispara e restaura backups declarados em registro/backups.json.

Sub-atos:
  infra backup [--json]
      Mede presença, idade, piso e gerações de cada alvo declarado.
  infra backup rodar <alvo> [--json]
      Executa o script de backup declarado do alvo na release e confere a geração nova.
  infra backup restaurar <alvo> [<geracao>] [--ensaio] [--json]
      Confere integridade da geração escolhida (default: última), repõe o alvo e confere o conteúdo.
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


def _bytes(p: str) -> int:
    """Bytes reais de conteudo. Diretorio soma recursivo; arquivo e o proprio tamanho."""
    if os.path.isdir(p):
        t = 0
        for raiz, _dirs, arquivos in os.walk(p):
            for f in arquivos:
                try:
                    t += os.path.getsize(os.path.join(raiz, f))
                except OSError:
                    pass
        return t
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


def _h(n: float) -> str:
    """Tamanho legivel (320 B, 4.5 MiB)."""
    for u in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or u == "GiB":
            return "{:.0f} B".format(n) if u == "B" else "{:.1f} {}".format(n, u)
        n /= 1024
    return "{:.1f} GiB".format(n)


def _carregar_registro() -> dict:
    return json.load(open(os.environ["INFRA_BACKUPS_REG"], encoding="utf-8"))


def _medir_alvo(nome: str, a: dict, agora: float | None = None) -> tuple[dict, bool]:
    agora = time.time() if agora is None else agora
    item = {"alvo": nome, "o_que": a.get("o_que"), "cobertura": a.get("cobertura")}
    ruim = False
    if a.get("cobertura") == "nenhuma":
        item["estado"] = "sem-backup"
    elif a.get("alcance") == "fora":
        item["estado"] = "nao-medivel-daqui"
    else:
        d = os.path.expanduser(a.get("diretorio", ""))
        arqs = sorted(glob.glob(os.path.join(d, a.get("padrao", "*"))), key=os.path.getmtime)
        total = sum(_bytes(f) for f in arqs)
        if not arqs or total == 0:
            item["estado"] = "vazio"
            ruim = True
        else:
            prova = os.path.expanduser(a["log"]) if a.get("log") else arqs[-1]
            if not os.path.exists(prova):
                prova = arqs[-1]
            idade = (agora - os.path.getmtime(prova)) / 86400
            ultimo_bytes = _bytes(arqs[-1])
            piso = int(a.get("piso_bytes") or 0)
            item.update(
                geracoes=len(arqs),
                idade_dias=round(idade, 1),
                ultimo=os.path.basename(arqs[-1]),
                ultimo_caminho=arqs[-1],
                ultimo_mtime=os.path.getmtime(prova),
                bytes=total,
                ultimo_bytes=ultimo_bytes,
            )
            if piso:
                item["piso_bytes"] = piso
            if piso and ultimo_bytes < piso:
                item["estado"] = "abaixo-do-piso"
                ruim = True
            elif idade >= 2:
                item["estado"] = "atrasado"
                ruim = True
            else:
                item["estado"] = "ok"
    return item, ruim


def _cmd_medir(reg: dict, como_json: bool) -> int:
    saida, ruim, agora = [], 0, time.time()
    for nome, a in sorted((reg.get("alvos") or {}).items()):
        item, eh_ruim = _medir_alvo(nome, a, agora)
        item.pop("ultimo_caminho", None)
        item.pop("ultimo_mtime", None)
        if eh_ruim:
            ruim += 1
        saida.append(item)
    if como_json:
        print(json.dumps({"alvos": saida}, ensure_ascii=False))
    else:
        for i in saida:
            estado = i["estado"]
            if estado in ("ok", "atrasado"):
                det = "{} geracoes, ultima ha {}d com {} (soma {})".format(
                    i["geracoes"], i["idade_dias"], _h(i["ultimo_bytes"]), _h(i["bytes"])
                )
            elif estado == "abaixo-do-piso":
                det = "ultima geracao {} com {}, abaixo do piso de {}".format(
                    i["ultimo"], _h(i["ultimo_bytes"]), _h(i["piso_bytes"])
                )
            elif estado == "sem-backup":
                det = "declarado sem cobertura — nao propor rotina"
            elif estado == "nao-medivel-daqui":
                det = "roda em conta que este usuario nao alcanca"
            else:
                det = "diretorio declarado sem arquivo do padrao ou com conteudo real de 0 bytes"
            print("{:<18} {:<16} {}".format(estado, i["alvo"], det))
    return 1 if ruim else 0


def _alvos_com(reg: dict, campo: str) -> list[str]:
    return sorted(
        nome
        for nome, a in (reg.get("alvos") or {}).items()
        if a.get(campo) and a.get("cobertura") != "nenhuma" and a.get("alcance") != "fora"
    )


def _cmd_rodar(reg: dict, args: list[str], como_json: bool) -> int:
    alvos = reg.get("alvos") or {}
    pos = [a for a in args if not a.startswith("--")]
    flags = [a for a in args if a.startswith("--")]
    if flags or len(pos) != 1:
        disp = ", ".join(_alvos_com(reg, "script"))
        print(f"uso: infra backup rodar <alvo> [--json]\nalvos com script: {disp}", file=sys.stderr)
        return 2
    nome = pos[0]
    if nome not in alvos:
        disp = ", ".join(_alvos_com(reg, "script"))
        print(f"infra backup rodar: alvo desconhecido: {nome}\nalvos com script: {disp}", file=sys.stderr)
        return 1
    alvo = alvos[nome]
    if alvo.get("cobertura") == "nenhuma" or alvo.get("alcance") == "fora" or not alvo.get("script"):
        print(
            f"infra backup rodar: alvo '{nome}' nao tem script local executavel (cobertura={alvo.get('cobertura')}, alcance={alvo.get('alcance')})",
            file=sys.stderr,
        )
        return 4

    release_raiz = os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current")
    script_rel = alvo["script"]
    script_abs = script_rel if os.path.isabs(script_rel) else os.path.join(release_raiz, script_rel)
    if not os.path.isfile(script_abs):
        print(f"infra backup rodar: script declarado ausente: {script_abs}", file=sys.stderr)
        return 3

    antes, _ = _medir_alvo(nome, alvo)
    antes_ultimo = antes.get("ultimo")
    antes_mtime = antes.get("ultimo_mtime") or 0.0
    inicio = time.time()

    cmd = [script_abs] if os.access(script_abs, os.X_OK) else ["bash", script_abs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        det = (proc.stderr or proc.stdout or "").strip()
        if como_json:
            print(
                json.dumps(
                    {
                        "alvo": nome,
                        "estado": "falhou",
                        "exit_script": proc.returncode,
                        "script": script_abs,
                        "saida": det,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"infra backup rodar: script de '{nome}' saiu {proc.returncode}: {det}", file=sys.stderr)
        return 1

    # Para alvos com log (espelho), grava o log quando rodado sob demanda para atualizar a prova de idade
    if alvo.get("log"):
        log_path = os.path.expanduser(alvo["log"])
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as lf:
                if proc.stdout:
                    lf.write(proc.stdout)
                if proc.stderr:
                    lf.write(proc.stderr)
        except OSError:
            pass

    depois, ruim = _medir_alvo(nome, alvo)
    geracao_nova = (
        depois.get("ultimo") != antes_ultimo
        or (depois.get("ultimo_mtime") or 0.0) > antes_mtime
        or (depois.get("ultimo_mtime") or 0.0) >= inicio - 1.0
    )
    ok = (not ruim) and depois.get("estado") == "ok" and geracao_nova
    resultado = {
        "alvo": nome,
        "estado": "ok" if ok else depois.get("estado", "falhou"),
        "script": script_abs,
        "geracao_nova": geracao_nova,
        "ultimo": depois.get("ultimo"),
        "ultimo_bytes": depois.get("ultimo_bytes"),
        "geracoes": depois.get("geracoes"),
        "saida": (proc.stdout or "").strip(),
    }
    if como_json:
        print(json.dumps(resultado, ensure_ascii=False))
    else:
        if ok:
            print(
                f"ok  {nome}  geracao={resultado['ultimo']}  "
                f"tamanho={_h(resultado['ultimo_bytes'] or 0)}  geracoes={resultado['geracoes']}"
            )
        else:
            print(
                f"falhou  {nome}  estado={resultado['estado']}  geracao_nova={geracao_nova}  "
                f"ultimo={resultado['ultimo']}",
                file=sys.stderr,
            )
    return 0 if ok else 1


def _conferir_dump_gz(caminho: str, piso: int, rodape_prefixo: str) -> tuple[bool, str, int]:
    if not os.path.isfile(caminho):
        return False, f"arquivo ausente: {caminho}", 0
    tamanho = os.path.getsize(caminho)
    if piso and tamanho < piso:
        return False, f"dump com {tamanho} bytes, abaixo do piso de {piso}", tamanho
    ultimas: list[str] = []
    try:
        with gzip.open(caminho, "rt", encoding="utf-8", errors="replace") as gz:
            for linha in gz:
                ultimas.append(linha.rstrip("\r\n"))
                if len(ultimas) > 5:
                    ultimas.pop(0)
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        return False, f"gzip corrompido: {exc}", tamanho
    if not any(l.startswith(rodape_prefixo) for l in ultimas):
        return False, f"dump sem o rodape esperado ({rodape_prefixo})", tamanho
    return True, "ok", tamanho


def _conferir_arquivo_gz_jsonl(caminho: str) -> tuple[bool, str, int, bytes]:
    if not os.path.isfile(caminho):
        return False, f"arquivo ausente: {caminho}", 0, b""
    try:
        with gzip.open(caminho, "rb") as gz:
            bruto = gz.read()
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        return False, f"gzip corrompido: {exc}", 0, b""
    linhas = 0
    for idx, raw in enumerate(bruto.splitlines(), start=1):
        txt = raw.decode("utf-8", errors="strict").strip()
        if not txt:
            continue
        try:
            json.loads(txt)
        except ValueError as exc:
            return False, f"linha {idx} invalida no jsonl: {exc}", len(bruto), b""
        linhas += 1
    return True, f"{linhas} linha(s) jsonl", len(bruto), bruto


def _docker_cmd(args: list[str], stdin_bytes: bytes | None = None, stdin_file=None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    if stdin_file is not None:
        return subprocess.run(["docker", *args], stdin=stdin_file, capture_output=True, env=env, timeout=600)
    return subprocess.run(
        ["docker", *args], input=stdin_bytes, capture_output=True, env=env, timeout=600
    )


def _resolver_conteiner(rest: dict) -> tuple[str | None, str]:
    if rest.get("conteiner"):
        nome = rest["conteiner"]
        p = _docker_cmd(["ps", "-q", "--filter", f"name=^/{nome}$"])
        if p.returncode != 0:
            return None, f"docker indisponivel: {p.stderr.decode(errors='replace').strip()}"
        cid = p.stdout.decode().strip()
        if not cid:
            return None, f"conteiner '{nome}' nao esta de pe"
        return nome, ""
    proj, svc = rest.get("projeto"), rest.get("servico")
    p = _docker_cmd(
        [
            "ps",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={proj}",
            "--filter",
            f"label=com.docker.compose.service={svc}",
        ]
    )
    if p.returncode != 0:
        return None, f"docker indisponivel: {p.stderr.decode(errors='replace').strip()}"
    linhas = [l for l in p.stdout.decode().splitlines() if l.strip()]
    if not linhas:
        return None, f"conteiner {proj}/{svc} nao esta de pe"
    if len(linhas) > 1:
        return None, f"mais de um conteiner {proj}/{svc} — nao escolho"
    return linhas[0], ""


def _resolver_geracao(alvo: dict, geracao: str | None) -> tuple[str | None, str]:
    d = os.path.expanduser(alvo.get("diretorio", ""))
    padrao = alvo.get("padrao", "*")
    if not geracao or geracao == "ultima":
        arqs = sorted(glob.glob(os.path.join(d, padrao)), key=os.path.getmtime)
        if not arqs:
            return None, f"nenhuma geracao encontrada em {d} ({padrao})"
        return arqs[-1], ""
    if "/" in geracao or "\\" in geracao or geracao in (".", "..") or ".." in geracao:
        return None, "nome de geracao invalido (nao aceita caminho)"
    caminho = os.path.join(d, geracao)
    if not os.path.exists(caminho):
        return None, f"geracao nao encontrada: {caminho}"
    return caminho, ""


def _cmd_restaurar(reg: dict, args: list[str], como_json: bool) -> int:
    alvos = reg.get("alvos") or {}
    ensaio = "--ensaio" in args
    pos = [a for a in args if a != "--ensaio" and not a.startswith("--")]
    outras_flags = [a for a in args if a.startswith("--") and a != "--ensaio"]
    if outras_flags or len(pos) < 1 or len(pos) > 2:
        disp = ", ".join(_alvos_com(reg, "restauracao"))
        print(
            f"uso: infra backup restaurar <alvo> [<geracao>|ultima] [--ensaio] [--json]\n"
            f"alvos restauraveis: {disp}",
            file=sys.stderr,
        )
        return 2
    nome = pos[0]
    geracao_pedida = pos[1] if len(pos) == 2 else "ultima"
    if nome not in alvos:
        disp = ", ".join(_alvos_com(reg, "restauracao"))
        print(f"infra backup restaurar: alvo desconhecido: {nome}\nalvos restauraveis: {disp}", file=sys.stderr)
        return 1
    alvo = alvos[nome]
    rest = alvo.get("restauracao")
    if alvo.get("cobertura") == "nenhuma" or alvo.get("alcance") == "fora" or not isinstance(rest, dict):
        print(f"infra backup restaurar: alvo '{nome}' nao tem restauracao local declarada", file=sys.stderr)
        return 4

    if not ensaio and not os.environ.get("PF_SUJEITO"):
        print("infra backup restaurar: PF_SUJEITO ausente — mutacao exige identidade", file=sys.stderr)
        return 3

    tipo = rest.get("tipo")
    piso = int(alvo.get("piso_bytes") or 0)
    d = os.path.expanduser(alvo.get("diretorio", ""))

    # 1. Selecionar e conferir a geracao antes de tocar no destino
    if tipo in ("postgres", "mariadb"):
        caminho, err = _resolver_geracao(alvo, geracao_pedida)
        if not caminho:
            print(f"infra backup restaurar: {err}", file=sys.stderr)
            return 4 if "nao aceita caminho" in err else 1
        rodape = "-- PostgreSQL database dump complete" if tipo == "postgres" else "-- Dump completed"
        ok_dump, mot, tam = _conferir_dump_gz(caminho, piso, rodape)
        if not ok_dump:
            print(f"infra backup restaurar: geracao recusada ({os.path.basename(caminho)}): {mot}", file=sys.stderr)
            return 1
        ctr, err_ctr = _resolver_conteiner(rest)
        if not ctr:
            print(f"infra backup restaurar: {err_ctr}", file=sys.stderr)
            return 3
        if ensaio:
            res = {
                "alvo": nome,
                "estado": "ensaio-ok",
                "tipo": tipo,
                "geracao": os.path.basename(caminho),
                "bytes": tam,
                "conteiner": ctr,
            }
            print(json.dumps(res, ensure_ascii=False) if como_json else f"ensaio-ok  {nome}  geracao={res['geracao']} ({_h(tam)}) -> conteiner={ctr}")
            return 0
        # Restaurar
        with gzip.open(caminho, "rb") as gz:
            if tipo == "postgres":
                cmd = ["exec", "-i", ctr, "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
            else:
                cmd = ["exec", "-i", ctr, "sh", "-c", 'exec mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE"']
            p_rest = _docker_cmd(cmd, stdin_bytes=gz.read())
        if p_rest.returncode != 0:
            det = p_rest.stderr.decode(errors="replace").strip() or p_rest.stdout.decode(errors="replace").strip()
            print(f"infra backup restaurar: restauracao de '{nome}' falhou (exit {p_rest.returncode}): {det}", file=sys.stderr)
            return 1
        # Conferencia pos-restauracao
        if tipo == "postgres":
            schema = rest.get("schema")
            sql_q = (
                f"SELECT count(*) FROM information_schema.tables WHERE table_schema = '{schema}'"
                if schema
                else "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')"
            )
            p_chk = _docker_cmd(["exec", ctr, "sh", "-c", f'psql -tAc "{sql_q}" -U "$POSTGRES_USER" -d "$POSTGRES_DB"'])
        else:
            p_chk = _docker_cmd(
                [
                    "exec",
                    ctr,
                    "sh",
                    "-c",
                    'mariadb -Nse "SELECT count(*) FROM information_schema.tables WHERE table_schema = DATABASE()" -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE"',
                ]
            )
        tabelas = int((p_chk.stdout.decode().strip() or "0").splitlines()[-1]) if p_chk.returncode == 0 else 0
        if p_chk.returncode != 0 or tabelas <= 0:
            print(
                f"infra backup restaurar: conferencia pos-restauracao reprovou em '{nome}' (tabelas={tabelas})",
                file=sys.stderr,
            )
            return 1
        res = {
            "alvo": nome,
            "estado": "restaurado",
            "tipo": tipo,
            "geracao": os.path.basename(caminho),
            "bytes": tam,
            "tabelas": tabelas,
        }
        print(json.dumps(res, ensure_ascii=False) if como_json else f"restaurado  {nome}  geracao={res['geracao']} ({_h(tam)})  tabelas={tabelas}")
        return 0

    if tipo == "minio-mirror":
        buckets = list(rest.get("buckets") or [])
        if geracao_pedida not in ("ultima", "") and geracao_pedida not in buckets:
            print(f"infra backup restaurar: bucket desconhecido '{geracao_pedida}' (declarados: {', '.join(buckets)})", file=sys.stderr)
            return 1
        buckets_alvo = [geracao_pedida] if geracao_pedida in buckets else buckets
        presentes = [b for b in buckets_alvo if os.path.isdir(os.path.join(d, b)) and _bytes(os.path.join(d, b)) > 0]
        if not presentes:
            print(f"infra backup restaurar: espelho vazio em {d} para buckets {buckets_alvo}", file=sys.stderr)
            return 1
        mc = os.environ.get("MC_BIN") or shutil.which("mc") or os.path.expanduser("~/.local/bin/mc")
        alias = os.environ.get("MC_ALIAS", "platafirma")
        if not (shutil.which(mc) or os.path.isfile(mc)):
            print(f"infra backup restaurar: cliente mc nao encontrado: {mc}", file=sys.stderr)
            return 3
        total_b = sum(_bytes(os.path.join(d, b)) for b in presentes)
        if ensaio:
            res = {"alvo": nome, "estado": "ensaio-ok", "tipo": tipo, "buckets": presentes, "bytes": total_b}
            print(json.dumps(res, ensure_ascii=False) if como_json else f"ensaio-ok  {nome}  buckets={','.join(presentes)} ({_h(total_b)})")
            return 0
        contagens = {}
        for b in presentes:
            src = os.path.join(d, b)
            p_m = subprocess.run([mc, "mirror", "--overwrite", src, f"{alias}/{b}"], capture_output=True, text=True, timeout=600)
            if p_m.returncode != 0:
                print(f"infra backup restaurar: mc mirror falhou em {b}: {p_m.stderr.strip()}", file=sys.stderr)
                return 1
            p_ls = subprocess.run([mc, "ls", "--recursive", f"{alias}/{b}"], capture_output=True, text=True, timeout=120)
            n_obj = len([l for l in p_ls.stdout.splitlines() if l.strip()]) if p_ls.returncode == 0 else 0
            if p_ls.returncode != 0 or n_obj <= 0:
                print(f"infra backup restaurar: conferencia pos-restauracao reprovou no bucket '{b}'", file=sys.stderr)
                return 1
            contagens[b] = n_obj
        res = {"alvo": nome, "estado": "restaurado", "tipo": tipo, "buckets": contagens, "bytes": total_b}
        print(json.dumps(res, ensure_ascii=False) if como_json else f"restaurado  {nome}  buckets={contagens} ({_h(total_b)})")
        return 0

    if tipo == "arquivo-gz":
        caminho, err = _resolver_geracao(alvo, geracao_pedida)
        if not caminho:
            print(f"infra backup restaurar: {err}", file=sys.stderr)
            return 4 if "nao aceita caminho" in err else 1
        ok_a, mot, tam_desc, bruto = _conferir_arquivo_gz_jsonl(caminho)
        if not ok_a:
            print(f"infra backup restaurar: geracao recusada ({os.path.basename(caminho)}): {mot}", file=sys.stderr)
            return 1
        instancia = os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa")
        dest_rel = rest["destino"]
        destino = dest_rel if os.path.isabs(dest_rel) else os.path.join(instancia, dest_rel)
        if ensaio:
            res = {
                "alvo": nome,
                "estado": "ensaio-ok",
                "tipo": tipo,
                "geracao": os.path.basename(caminho),
                "bytes_descomprimidos": tam_desc,
                "destino": destino,
                "detalhe": mot,
            }
            print(json.dumps(res, ensure_ascii=False) if como_json else f"ensaio-ok  {nome}  geracao={res['geracao']} ({mot}) -> {destino}")
            return 0
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(destino), prefix=".restore-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(bruto)
            os.replace(tmp, destino)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        sha_esperado = hashlib.sha256(bruto).hexdigest()
        sha_gravado = hashlib.sha256(open(destino, "rb").read()).hexdigest()
        if sha_gravado != sha_esperado:
            print(f"infra backup restaurar: divergencia de sha256 apos restaurar {destino}", file=sys.stderr)
            return 1
        res = {
            "alvo": nome,
            "estado": "restaurado",
            "tipo": tipo,
            "geracao": os.path.basename(caminho),
            "bytes_descomprimidos": tam_desc,
            "destino": destino,
            "sha256": sha_gravado,
        }
        print(json.dumps(res, ensure_ascii=False) if como_json else f"restaurado  {nome}  geracao={res['geracao']} ({mot}) -> {destino}")
        return 0

    print(f"infra backup restaurar: tipo de restauracao desconhecido: {tipo}", file=sys.stderr)
    return 5


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    como_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    reg = _carregar_registro()
    if not args:
        return _cmd_medir(reg, como_json)
    sub, resto = args[0], args[1:]
    if sub == "rodar":
        return _cmd_rodar(reg, resto, como_json)
    if sub == "restaurar":
        return _cmd_restaurar(reg, resto, como_json)
    print(
        "uso: infra backup [--json] | infra backup rodar <alvo> [--json] | "
        "infra backup restaurar <alvo> [<geracao>] [--ensaio] [--json]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
