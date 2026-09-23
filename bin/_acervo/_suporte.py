#!/usr/bin/env python3
# _suporte.py — o espelho bare do suporte da partição casa (arq:0115 §1.2, §8.1).
#
# O suporte de documento de casa é o repositório `platafirma-casa`. Ele NÃO é unidade de
# release (arq:0115 §1.2): não mora em /opt/platafirma, e a bancada nunca é fonte de
# produção (card #3010, lib/raizes.py). A ingestão lê o objeto git pelo sha num espelho
# bare na INSTÂNCIA, no mesmo padrão do `.repo.git` de bin/release: git absoluto, a
# credencial da própria conta (config do git no HOME dela), fetch só de refs/remotes/origin/*
# e refs/tags/*, refs/heads/* do espelho expurgado (referência fóssil, arq:0074).
#
# Quem usa: _acervo/casa-ingerir (fetch + leitura por sha) e _acervo/casa (só lê o
# origin/main já buscado, para o campo `servido`; leitura não busca no forge).
#
# ambiente:
#   PLATAFIRMA_INSTANCIA[=/srv/platafirma/casa]  raiz da instância (lib/raizes.py)
#   PF_SUPORTE_ESPELHO  override do caminho do espelho (teste)
#   PF_SUPORTE_URL      override da URL do forge do suporte (teste)
import os
import pwd
import subprocess
import sys

SUPORTE = "platafirma-casa"
URL_PADRAO = "https://github.com/plcarvalho301/platafirma-casa.git"

# git ABSOLUTO: sob a porta não há PATH confiável (mesmo padrão de bin/release e bin/repo).
GIT = next((p for p in ("/usr/bin/git", "/bin/git") if os.path.exists(p)), "git")


def _raizes():
    lib = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    import raizes  # noqa: E402
    return raizes


def espelho():
    """<instancia>/var/acervo/suporte/platafirma-casa.git, ou PF_SUPORTE_ESPELHO."""
    v = os.environ.get("PF_SUPORTE_ESPELHO", "").strip()
    if v:
        return v
    return os.path.join(str(_raizes().instancia()), "var", "acervo", "suporte", SUPORTE + ".git")


def url():
    return os.environ.get("PF_SUPORTE_URL", "").strip() or URL_PADRAO


def _env():
    """Ambiente do git: a credencial é a da conta (HOME dela); nunca pergunta no terminal."""
    env = dict(os.environ)
    if not env.get("HOME"):
        try:
            env["HOME"] = pwd.getpwuid(os.getuid()).pw_dir
        except KeyError:
            pass
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def git(esp, *args, entrada=None):
    """git --git-dir=<esp> <args>; saída em BYTES (caminho e corpo são UTF-8, o locale da
    porta pode não ser). Nunca levanta: quem chama lê returncode."""
    return subprocess.run([GIT, f"--git-dir={esp}", *args], input=entrada,
                          capture_output=True, env=_env())


def git_sem_dir(*args):
    return subprocess.run([GIT, *args], capture_output=True, env=_env())


def texto(b):
    return (b or b"").decode("utf-8", "replace").strip()


def main_do_espelho(esp=None):
    """(sha, None) do refs/remotes/origin/main JÁ buscado, ou (None, motivo). Não busca."""
    esp = esp or espelho()
    if not os.path.isdir(esp):
        return None, f"espelho ausente em {esp}"
    r = git(esp, "rev-parse", "--verify", "-q", "refs/remotes/origin/main^{commit}")
    sha = texto(r.stdout)
    if r.returncode != 0 or not sha:
        return None, f"espelho {esp} sem refs/remotes/origin/main"
    return sha, None
