"""Bootstrap confiável do cálculo dentro do namespace; stdout nunca é servido."""

from __future__ import annotations

import atexit
import os
import runpy
import sys
from pathlib import Path


def main() -> int:
    codigo = sys.argv[1]
    houve_recusa = [False]
    entrada, saida = Path("/entrada"), Path("/saida")
    # O venv da receita entra montado só para leitura no caminho real de sys.prefix,
    # fora de /usr e /opt; sem ele, todo import de pacote do lock seria recusado.
    ambiente = Path(sys.prefix).resolve()

    def recusar() -> None:
        houve_recusa[0] = True
        raise PermissionError("operacao-nao-permitida")

    def auditor(evento: str, args: tuple) -> None:
        if evento.startswith("socket.") or evento in {
            "os.system",
            "os.exec",
            "os.posix_spawn",
        }:
            recusar()
        if evento == "subprocess.Popen" and args[0] not in {
            "/usr/bin/dot",
            "dot",
            sys.executable,
        }:
            recusar()
        if evento == "open":
            nome, modo, flags = args
            if isinstance(nome, (str, bytes)):
                p = Path(os.fsdecode(nome))
                if not p.is_absolute():
                    p = Path.cwd() / p
                resolvido = p.resolve()
                escrita = (
                    isinstance(modo, str) and any(x in modo for x in "wax+")
                ) or (
                    isinstance(flags, int)
                    and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                )
                if escrita and not resolvido.is_relative_to(saida):
                    recusar()
                if not escrita and not any(
                    resolvido.is_relative_to(r)
                    for r in (
                        entrada,
                        saida,
                        Path("/receita"),
                        ambiente,
                        Path("/usr"),
                        Path("/opt"),
                        Path("/lib"),
                        Path("/lib64"),
                    )
                ):
                    recusar()
        if evento in {
            "os.remove",
            "os.rmdir",
            "os.mkdir",
            "os.rename",
            "os.link",
            "os.symlink",
        }:
            for nome in (
                args[:2]
                if evento in {"os.rename", "os.link", "os.symlink"}
                else args[:1]
            ):
                if isinstance(nome, (str, bytes)) and not Path(
                    os.fsdecode(nome)
                ).resolve().is_relative_to(saida):
                    recusar()

    sys.addaudithook(auditor)

    def encerrar() -> None:
        if houve_recusa[0]:
            os._exit(4)

    atexit.register(encerrar)
    status = 0
    try:
        sys.argv = ["/receita/" + codigo]
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as exc:
        status = exc.code if type(exc.code) is int else 4
    except ImportError:
        status = 4
    except PermissionError:
        status = 4
    except BaseException:
        status = 5
    # /proc só contém o namespace desta execução. O PID 1 é o bwrap.
    # A morte do namespace recolhe os filhos, e a tentativa fica como recusa.
    vivos = []
    for pid in Path("/proc").iterdir():
        if pid.name.isdigit() and int(pid.name) not in {1, os.getpid()}:
            vivos.append(pid.name)
    if vivos or houve_recusa[0]:
        status = 4
    return status if status in {0, 1, 3, 4, 5} else 4


if __name__ == "__main__":
    sys.exit(main())
