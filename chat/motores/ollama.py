#!/usr/bin/env python3
"""Motor Ollama para o chat da PlataFirma — roda modelo local (qwen3.5:9b etc.)
pela mesma porta que o MotorClaudeCode.

DESENHO (card quinzinho, 01/09/2026)
------------------------------------
O `um_giro` de bin/chat invoca o motor por SUBPROCESS: monta argv com
`motor.comando()`, faz Popen, escreve o corpo em stdin, le stream-json no stdout
e um passo por linha no stderr. O contrato e a fronteira — o worker/recepcao nao
sabem qual motor esta atras.

Este motor NAO reimplementa esse laco. `comando()` devolve um argv que aponta
para o RUNNER ao lado (ollama_runner.py): e ele que fala com o ollama em
localhost:11434, controla a sessao (o ollama nao tem sessao nativa — o historico
e do chamador) e cospe o mesmo stream-json que o Claude Code cospe. Para o
um_giro, um motor e outro sao indistinguiveis.

SESSAO (ponto c do pedido): o runner guarda o historico por id_fita em
~/AI/fitas/ollama/<id>.json e o remonta a cada giro. `--session-id` na fita nova,
`--resume <id>` na existente — mesmos flags que o Code, resolvidos pelo runner.

Persona (ponto d): a persona e injetada no prompt como system, exatamente como
nas cadeiras — o pacote de `monta-sessao` entra no lugar do system message. Qwen
usa as MESMAS personas; so infere com modelo local e alcance escopado.
"""
import os
import shutil
import subprocess

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
RUNNER = os.path.join(RAIZ, "platafirma-harness", "chat", "motores", "ollama_runner.py")


def _agora_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


class MotorOllama:
    """Cumpre o mesmo contrato do MotorClaudeCode: versao_servida, comando,
    passo, compactou, cota_barrada. Modelo local nao tem cota nem compactacao
    de janela como o servico remoto — esses dois retornam vazio por construcao."""

    # Modelo default do motor local. Pode ser trocado por --modelo <alias> da
    # sala ou por PF_CHAT_MODELO. Alias amigavel resolvido em bin/chat.
    # O despachar compara servida != VERSAO_PINADA para avisar deriva de motor.
    # Modelo local nao tem CLI pinada — igualamos pinada a servida no init, entao
    # o aviso so dispara se o ollama ficar mudo (servida=None), que e informacao real.
    VERSAO_PINADA = None
    MODELO_DEFAULT = os.environ.get("PF_OLLAMA_MODELO", "qwen3.5:9b")
    BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    def __init__(self, modelo="", esforco=""):
        self.modelo = modelo or self.MODELO_DEFAULT
        # esforco nao se aplica a modelo local (nao ha nivel de effort no ollama);
        # aceito no construtor para assinatura identica, ignorado no comando.
        self.esforco = esforco
        self.py = shutil.which("python3") or "/usr/bin/python3"
        self.VERSAO_PINADA = self.versao_servida()

    def versao_servida(self):
        """Versao do ollama servida em BASE_URL. None se nao respondeu."""
        try:
            import json as _j
            import urllib.request as _u
            with _u.urlopen(f"{self.BASE_URL}/api/version", timeout=10) as r:
                return _j.loads(r.read()).get("version")
        except Exception:  # noqa: BLE001
            return None

    def comando(self, id_fita, pacote, cwd):
        """argv do giro: chama o runner, que fala com o ollama e emite stream-json.
        Mesma logica de fita do Code — id proprio na fita nova, resume na existente."""
        argv = [self.py, RUNNER,
                "--modelo", self.modelo,
                "--base-url", self.BASE_URL,
                "--cwd", cwd]
        if id_fita:
            argv += ["--resume", id_fita]
        else:
            from importlib import import_module
            # id_fita_novo mora em bin/chat; o runner tambem sabe gerar um se vazio.
            argv += ["--session-id", _novo_id()]
            if pacote:
                argv += ["--sistema", pacote]
        return argv

    def passo(self, ev):
        """Evento do runner -> passo para o stderr. Mesmo shape do Code: metadado,
        nunca conteudo. O runner ja emite eventos com 'type'."""
        tipo = ev.get("type", "?")
        p = {"passo": tipo, "em": _agora_iso()}
        if tipo == "assistant":
            blocos = (ev.get("message") or {}).get("content") or []
            p["blocos"] = [b.get("type") for b in blocos if isinstance(b, dict)]
            p["chars"] = sum(len(b.get("text", "")) for b in blocos if isinstance(b, dict))
        elif tipo == "result":
            p["subtipo"] = ev.get("subtype")
            p["erro"] = bool(ev.get("is_error"))
            u = ev.get("usage") or {}
            p["entrada"] = u.get("prompt_eval_count") or 0
            p["saida"] = u.get("eval_count") or 0
        return p

    def compactou(self, ev):
        """Modelo local nao compacta janela pelo motor — o runner corta historico
        por conta propria e declara no evento se o fizer."""
        return bool(ev.get("compactou"))

    def cota_barrada(self, ev):
        """Nao ha cota em modelo local. Sempre passa."""
        return None


def _novo_id():
    import uuid
    return str(uuid.uuid4())
