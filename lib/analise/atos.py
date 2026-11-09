"""Orquestra os atos e mantém separado o contexto confiável do código da receita."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

    from .publicacao import Catalogo
import argparse
import io
import json
import os
import shutil

from . import (
    Falha,
    ambiente,
    comparacao,
    exigir,
    gravar_atomico,
    hash_arquivo,
    json_canonico,
    nome_seguro,
    relativo,
)
from .extrator import conectar, extrair, resolver_corte
from .manifesto import fase, identidade_receita
from .materializacao import materializar
from .publicacao import Catalogo, novo
from .receita import carregar, parametros, pre_voo
from .supervisor import admitir
from .unidade import executar


class MotorAnalise:
    def __init__(
        self,
        *,
        raiz: Path,
        conhecimento: Path,
        registro: dict,
        instancia: Path,
        sujeito: str,
        sessao: str,
        ordem: str,
        conexao: Callable[..., Connection] = conectar,
        autorizar: Callable[..., dict] | None = None,
        construtor: Callable[..., tuple[Path, dict]] = ambiente.construir,
    ) -> None:
        self.raiz, self.conhecimento, self.registro = (
            Path(raiz),
            Path(conhecimento),
            registro,
        )
        self.instancia = Path(instancia)
        self.sujeito, self.sessao, self.ordem = sujeito, sessao, ordem
        self.conexao = conexao
        if autorizar is None:
            from .acesso import autorizar
        self.autorizar = autorizar
        self.construtor = construtor
        self.cache = self.instancia / "var/analise/ambientes"
        self.controle = self.instancia / "var/analise"
        self.tmp = self.instancia / "var/tmp"

    def catalogo(self) -> Catalogo:
        return Catalogo(self.conexao("destino"), self.sujeito)

    def receita(self, slug: str, ato: str) -> tuple[Path, dict, dict]:
        nome_seguro(slug)
        reg = self.registro.get(slug)
        exigir(reg, "receita-fora-do-registro")
        exigir(
            reg["repositorio"] == "platafirma-conhecimento", "repositorio-nao-aceito"
        )
        raiz_receita=self.conhecimento
        import re
        servida=self.conhecimento.resolve()
        if re.fullmatch(r"[0-9a-f]{40}",servida.name):
            versao=reg.get("versao","")
            exigir(re.fullmatch(r"[0-9a-f]{7,40}",versao),"versao-da-receita-invalida")
            candidatas=[p for p in servida.parent.glob(versao+"*") if p.is_dir()]
            exigir(len(candidatas)==1,"versao-da-receita-nao-materializada",3)
            raiz_receita=candidatas[0]
        pasta = relativo(raiz_receita, reg["caminho"])
        r = carregar(pasta, ato)
        exigir(r["tipo"] == reg["tipo"], "tipo-do-registro-diverge")
        if reg.get("arquivos"):
            for nome, sha in reg["arquivos"].items():
                exigir(
                    hash_arquivo(relativo(pasta, nome)) == sha,
                    "receita-diverge-do-registro",
                    5,
                )
        return pasta, r, reg

    def rodar(
        self,
        ato: str,
        slug: str | None = None,
        *,
        base_id: str | None = None,
        corte: datetime | None = None,
        params: list[str] = (),
        origem: str | None = None,
        reler: bool = False,
    ) -> tuple[int, dict]:
        catalogo = None
        ex = novo("ex")
        work = self.tmp / self.ordem / "analise" / ex
        manifesto = {}
        abriu = False
        try:
            original = None
            if origem:
                catalogo = self.catalogo()
                original = catalogo.execucao(origem)
                old = original["manifesto"]
                exigir(not reler or old["ato"] == "preparar", "reler-so-preparacao")
                slug = old["slug"]
                ato = old["ato"]
                base_id = old.get("base_consumida")
                pasta = Path(old["trabalho"]) / "receita"
                exigir(pasta.is_dir(), "receita-guardada-vencida", 5)
                reg = old["receita_registro"]
                r = carregar(pasta, ato)
                exigir(
                    identidade_receita(pasta, reg) == old["receita"],
                    "receita-guardada-adulterada",
                    5,
                )
                parametros_resolvidos = old["parametros"]
                corte = old.get("corte")
            else:
                pasta, r, reg = self.receita(slug, ato)
                parametros_resolvidos = parametros(r, params)
            politica = []
            for t in r.get("tabelas_de_origem", []):
                politica.append(
                    self.autorizar(
                        self.sujeito,
                        ato,
                        "analise:origem/" + t.get("banco", "rag") + "/" + t["tabela"],
                    )
                )
            base = None
            if ato == "montar":
                exigir(base_id, "base-ausente")
                catalogo = catalogo or self.catalogo()
                self.autorizar(self.sujeito, ato, "analise:base/" + base_id)
                base = catalogo.objeto(base_id)
                exigir(
                    base["tipo"] == "base" and base["receita"] in r["base"]["receitas"],
                    "base-nao-aceita",
                )
                pre_voo(r, base["n"])
            else:
                pre_voo(r)
                corte = resolver_corte(r, corte)
            # Construção não vê origem, destino, credencial ou dado.
            amb, amb_ident = self.construtor(pasta, self.cache)
            catalogo = catalogo or self.catalogo()
            with admitir(self.controle, self.tmp):
                from .coleta import recuperar_orfas

                recuperar_orfas(catalogo)
                work.mkdir(parents=True, mode=0o700)
                work.chmod(0o700)
                entrada = work / "entrada"
                entrada.mkdir(mode=0o700)
                saida = work / "saida"
                saida.mkdir(mode=0o700)
                snapshot = work / "receita"
                shutil.copytree(
                    pasta,
                    snapshot,
                    ignore=shutil.ignore_patterns("__pycache__", ".venv", ".git"),
                )
                manifesto = {
                    "versao_formato": 1,
                    "ato": ato,
                    "slug": slug,
                    "execucao_id": ex,
                    "execucao_origem": origem,
                    "unidade": os.getenv("PF_ANALISE_UNIDADE"),
                    "receita": identidade_receita(snapshot, reg),
                    "receita_registro": reg,
                    "pergunta": r["pergunta"],
                    "ambiente": amb_ident,
                    "politica_acesso": politica,
                    "politica_isolamento": "systemd-rede+bwrap-arquivos-v1",
                    "serializacao": r["serializacao"],
                    "versao_serializacao": 1,
                    "parametros": parametros_resolvidos,
                    "semente": r.get("semente"),
                    "populacao": r["populacao"],
                    "sujeito": self.sujeito,
                    "sessao": self.sessao,
                    "ordem": self.ordem,
                    "trabalho": str(work),
                    "corte": str(corte) if corte else None,
                    "base_consumida": base_id,
                    "fases": {},
                }
                catalogo.abrir_execucao(
                    ex, "refazer" if origem else ato, self.sessao, self.ordem, origem
                )
                abriu = True
                with fase(manifesto, "materializar" if base else "extrair") as medida:
                    if base:
                        entradas = materializar(catalogo, base, r, entrada)
                    elif original and not reler:
                        entradas = old["entradas"]
                        anterior = Path(old["trabalho"]) / "entrada"
                        for nome, meta in entradas.items():
                            arq = anterior / (nome + ".csv")
                            exigir(
                                arq.is_file() and hash_arquivo(arq) == meta["sha256"],
                                "extracao-vencida-ou-adulterada",
                                5,
                            )
                            shutil.copy2(arq, entrada / arq.name)
                    else:
                        entradas = extrair(
                            self.conexao("origem"), r, snapshot, entrada, corte
                        )
                    manifesto["entradas"] = entradas
                    medida["bytes"] = sum(m["bytes"] for m in entradas.values())
                gravar_atomico(
                    entrada / "parametros.json", json_canonico(parametros_resolvidos)
                )
                (entrada / "parametros.json").chmod(0o400)
                with fase(manifesto, "calcular") as medida:
                    rc, m = executar(
                        [
                            str(amb / "bin/python"),
                            "-I",
                            "-B",
                            "/executor.py",
                            r["codigo"],
                        ],
                        pasta=snapshot,
                        entrada=entrada,
                        saida=saida,
                        ambiente=amb,
                    )
                    medida.update(m)
                if rc == 1:
                    reprov = saida / "reprovacao"
                    exigir(
                        reprov.is_file()
                        and not reprov.is_symlink()
                        and reprov.stat().st_size <= 128,
                        "reprovacao-invalida",
                        4,
                    )
                    codigo = reprov.read_text().strip()
                    exigir(
                        codigo in {d["codigo"] for d in r.get("reprovacoes", [])},
                        "reprovacao-nao-declarada",
                        4,
                    )
                    raise Falha(1, "dado-reprovado:" + codigo)
                exigir(
                    rc == 0, "calculo-recusado" if rc == 4 else "calculo-incompleto", rc
                )
                if origem:
                    from .serializacao import canonizar

                    esperados = {
                        t["nome"] + ".csv" for t in r["saidas"].get("tabelas", [])
                    }
                    esperados |= {
                        (p if isinstance(p, str) else p["nome"]) + ".png"
                        for p in r["saidas"].get("projecoes", [])
                    }
                    exigir(
                        {p.name for p in saida.iterdir()} == esperados,
                        "saida-nao-declarada",
                        4,
                    )
                    manifesto["saidas"] = {}
                    for t in r["saidas"].get("tabelas", []):
                        arq = saida / (t["nome"] + ".csv")
                        exigir(
                            not arq.is_symlink() and arq.is_file(),
                            "saida-nao-regular",
                            4,
                        )
                        c = canonizar(arq, t, r["serializacao"])
                        manifesto["saidas"][t["nome"]] = {
                            k: v for k, v in c.items() if k != "conteudo"
                        }
                    for p in r["saidas"].get("projecoes", []):
                        nome = p if isinstance(p, str) else p["nome"]
                        from .projecao import canonizar_png
                        arq=saida/(nome+".png")
                        exigir(not arq.is_symlink() and arq.is_file(),"saida-nao-regular",4)
                        imagem=canonizar_png(arq)
                        manifesto["saidas"][nome]={k:v for k,v in imagem.items() if k!="conteudo"}
                    manifesto["expires_at"] = old["expires_at"]
                    manifesto["guarda"] = old["guarda"]
                    rc, camada = comparacao.comparar(old, manifesto)
                    catalogo.concluir(
                        ex, "divergente" if rc else "pronta", manifesto, camada
                    )
                    return rc, {
                        "execucao_id": ex,
                        "estado": "divergente" if rc else "igual",
                        "causa": camada,
                        "expires_at": manifesto["expires_at"],
                    }
                objeto = catalogo.publicar(ex, r, slug, saida, manifesto, base)
                return 0, {
                    "execucao_id": ex,
                    "base_id": objeto if not base else base_id,
                    "resultado_id": objeto if base else None,
                    "estado": "pronta",
                    "expires_at": manifesto["expires_at"],
                    "manifesto": manifesto,
                }
        except Falha as e:
            if abriu:
                catalogo.concluir(
                    ex, "reprovada" if e.exit == 1 else "incompleta", manifesto, e.causa
                )
            return e.exit, {
                "execucao_id": ex if abriu else None,
                "estado": "reprovada" if e.exit == 1 else "incompleta",
                "causa": e.causa,
                "correcao": e.correcao,
            }
        except Exception:
            if abriu:
                catalogo.concluir(ex, "incompleta", manifesto, "executor-incompleto")
            raise
        finally:
            if catalogo is not None:
                catalogo.conn.close()


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Falha(2, "uso-invalido", "analise --ajuda")


def parser() -> Parser:
    p = Parser(add_help=False)
    p.add_argument("ato", nargs="?")
    p.add_argument("alvo", nargs="?")
    p.add_argument("destino", nargs="?")
    p.add_argument("--ajuda", action="store_true")
    p.add_argument("--guia")
    p.add_argument("--base")
    p.add_argument("--corte")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--reler", action="store_true")
    p.add_argument("--bancada")
    p.add_argument("--tabela")
    p.add_argument("--linhas", default="1-50")
    p.add_argument("--projecao")
    return p


AJUDA = """analise bancos [<banco>]        todo Postgres da casa; com <banco>, as tabelas e colunas que a receita declara
analise preparar <receita> [--corte <instante>] [--param nome=valor]
analise montar <receita> --base <base_id> [--param nome=valor]
analise refazer <execucao_id> [--reler]
analise ler <id> [--tabela <nome>] [--linhas <a-b>] [--projecao <nome>]
analise listar [bases|resultados|execucoes]
analise descartar <base_id|resultado_id>
analise entregar <base_id|resultado_id> <sujeito|todos>
analise travar <receita> --bancada <chave>
analise --guia preparacao"""


def runtime() -> MotorAnalise:
    from raizes import instancia, release

    raiz = Path(__file__).resolve().parents[2]
    try:
        reg = json.loads((raiz / "registro/analise-receitas.json").read_text())
    except (OSError, ValueError):
        raise Falha(3, "registro-ausente") from None
    exigir(
        os.getenv("PF_SUJEITO") and os.getenv("PF_SESSAO") and os.getenv("PF_ORDEM_ID"),
        "identidade-ausente",
        4,
    )
    return MotorAnalise(
        raiz=raiz,
        conhecimento=release() / "conhecimento",
        registro=reg,
        instancia=instancia(),
        sujeito=os.environ["PF_SUJEITO"],
        sessao=os.environ["PF_SESSAO"],
        ordem=os.environ["PF_ORDEM_ID"],
    )


def main(argv: list[str] | None = None) -> int:
    ato = None
    bloco = {}
    try:
        a = parser().parse_args(argv)
        ato = a.ato
        if a.ajuda or (not ato and not a.guia):
            print(AJUDA)
            return 0
        if a.guia:
            exigir(a.guia == "preparacao", "guia-desconhecido")
            from .guia import ler

            print(ler(), end="")
            return 0
        exigir(
            ato
            in {
                "preparar",
                "montar",
                "refazer",
                "ler",
                "listar",
                "descartar",
                "entregar",
                "travar",
                "bancos",
            },
            "ato-desconhecido",
        )
        motor = runtime()
        if ato == "bancos":
            from .bancos import listar as listar_bancos

            motor.autorizar(motor.sujeito, "listar", "analise:bancos/" + (a.alvo or "*"))
            rc, bloco = listar_bancos(a.alvo)
        elif ato in {"preparar", "montar"}:
            exigir(a.alvo, "receita-ausente")
            rc, bloco = motor.rodar(
                ato, a.alvo, base_id=a.base, corte=a.corte, params=a.param
            )
        elif ato == "refazer":
            exigir(a.alvo, "execucao-ausente")
            rc, bloco = motor.rodar("refazer", origem=a.alvo, reler=a.reler)
        elif ato == "travar":
            from raizes import bancada

            exigir(a.alvo and a.bancada, "bancada-ou-receita-ausente")
            nome_seguro(a.alvo)
            import re

            exigir(
                re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,80}", a.bancada), "bancada-invalida"
            )
            cadeira = os.environ.get("PF_CADEIRA", "")
            exigir(cadeira, "cadeira-ausente", 4)
            raiz_bancada = bancada() / "wt/platafirma-conhecimento" / cadeira
            candidatos = list(raiz_bancada.glob(a.bancada))
            if not candidatos:
                outras = list(raiz_bancada.parent.glob("*/" + a.bancada))
                exigir(not outras, "bancada-de-outra-cadeira", 4)
            exigir(len(candidatos) == 1, "bancada-desconhecida")
            pasta = relativo(candidatos[0], "analise/" + a.alvo)
            exigir(pasta.is_dir(), "receita-ausente-na-bancada")
            sha = ambiente.travar(pasta, motor.cache)
            rc, bloco = (
                0,
                {
                    "estado": "pronta",
                    "causa": "lock-gravado",
                    "sha256": sha,
                    "caminho": str(pasta / "uv.lock"),
                },
            )
        else:
            cat = motor.catalogo()
            try:
                from .leitura import ler

                if ato == "listar":
                    tipo = a.alvo or "bases"
                    exigir(
                        tipo in {"bases", "resultados", "execucoes"}, "lista-invalida"
                    )
                    motor.autorizar(motor.sujeito, ato, "analise:" + tipo + "/*")
                    bloco = {"estado": "pronta", "itens": cat.listar(tipo)}
                    rc = 0
                elif ato == "descartar":
                    exigir(a.alvo, "objeto-ausente")
                    motor.autorizar(motor.sujeito, ato, "analise:objeto/" + a.alvo)
                    cat.descartar(a.alvo)
                    bloco = {"estado": "descartada"}
                    rc = 0
                elif ato == "entregar":
                    exigir(a.alvo and a.destino, "objeto-ou-destino-ausente")
                    motor.autorizar(motor.sujeito, ato, "analise:objeto/" + a.alvo)
                    bloco = cat.entregar(
                        a.alvo, "*" if a.destino == "todos" else a.destino
                    )
                    rc = 0
                else:
                    exigir(a.alvo, "objeto-ausente")
                    motor.autorizar(motor.sujeito, ato, "analise:objeto/" + a.alvo)
                    bloco = ler(
                        cat,
                        a.alvo,
                        a.tabela,
                        a.linhas,
                        a.projecao,
                        motor.tmp / motor.ordem,
                    )
                    rc = 0
            finally:
                cat.conn.close()
    except Falha as e:
        rc = e.exit
        bloco = {
            "estado": "recusada" if rc == 4 else "incompleta",
            "causa": e.causa,
            "correcao": e.correcao,
        }
    except Exception:
        rc = 5
        bloco = {
            "estado": "incompleta",
            "causa": "dependencia-ou-executor-indisponivel",
        }
    retorno = dict.fromkeys(
        (
            "ato",
            "execucao_id",
            "base_id",
            "resultado_id",
            "estado",
            "exit",
            "causa",
            "correcao",
            "expires_at",
        )
    )
    retorno.update(bloco)
    retorno.update({"ato": ato, "exit": rc})
    print(json_canonico(retorno))
    if rc == 2 and ato in {"preparar", "montar"}:
        print("analise --guia preparacao")
    return rc
