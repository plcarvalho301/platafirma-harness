"""Projecao da conta de SO em que o comando do sujeito executa (story #3007, seg:0013).

Por que existe: ate aqui todo comando despachado pela porta rodava sob o uid do
processo do ops-server (1001/claudinho), qualquer que fosse QUEM pediu. Para uma
cadeira isso e o desenho — a porta E a conta, e o PEP e a fronteira. Para a conta de
PROVIDER nao e: o isolamento que a seg:0013 promete e por uid, e uid compartilhado nao
isola nada no disco. Arquivo escrito pelo provider sai `owner 1001`, legivel e
REGRAVAVEL por toda cadeira; a fronteira existente e a do processo, nao a do disco.

O que este modulo faz, e so isto: dado o dicionario de atributos do sujeito no PAP,
dizer sob qual conta de SO o comando deve rodar, e montar o argv que o leva ate la.
Nenhuma decisao de ACESSO mora aqui — quem decide e o PDP, antes, e um sujeito que
chegou ate este ponto ja passou por ele. Aqui e despacho.

Tres escolhas que nao se deduzem do codigo:

1. `conta_so` AUSENTE e o caminho de hoje, byte por byte: roda sob a conta da porta,
   sem wrapper e sem env novo. Toda cadeira cai aqui, e por isso a mudanca nao tem
   janela de regressao para quem ja funciona.

2. `conta_so` PRESENTE nao degrada. Wrapper que falta, que nega ou que nao esta
   autorizado devolve erro — nunca cai de volta para o uid da porta. Cair calado para
   1001 e exatamente o vazamento que a story fecha, e um fallback silencioso o
   reintroduziria com a aparencia de que foi corrigido.

3. O env atravessa EXPLICITO, por `env -` no meio do argv, e nao por confianca no
   wrapper. `sudo` roda com `env_reset` por default (medido no `sudo -l` desta
   maquina: `Matching Defaults entries: env_reset`), entao o dicionario passado em
   `Popen(env=...)` seria descartado na travessia e o subprocesso herdaria o env do
   sudoers, nao o nosso. Com `env -` a lista e a que esta no argv, o que tambem a
   torna visivel na auditoria e no `ps`.

O modulo e puro de proposito — sem MCP, sem rede, sem disco — para que o teste
(`test_exec_conta.py`) rode sem root e sem as dependencias do servidor.
"""
import shlex

# Wrapper que troca de conta. Default `sudo -n`, e nao `runuser`, porque a porta roda
# sem privilegio: `runuser` exige root (uid 0), enquanto `sudo -n` funciona com uma
# regra NOPASSWD estreita, que e o que se pede ao dono. `-n` para nunca abrir prompt:
# despacho que pede senha trava a thread ate o timeout.
WRAPPER_PADRAO = "sudo -n -u {conta} --"

# Env do processo da porta que NAO pode atravessar para outra conta. Nao e higiene
# generica: cada um destes aponta para um recurso do uid 1001 que o uid de destino nao
# alcanca, e herdado quebra a chamada de um jeito dificil de ler.
#   HOME/USER/LOGNAME  — a casa e a identidade sao da conta nova, e HOME errado faz
#                        git, ssh e pip escreverem no lugar errado (ou falharem no
#                        EACCES, que e o caso bom).
#   XDG_RUNTIME_DIR    — /run/user/1001, modo 0700: o uid de destino leva EACCES.
#   DOCKER_HOST        — socket do daemon rootless do uid da porta. Herdado, a conta
#                        segregada operaria os conteineres da porta, que e o oposto
#                        do que a story faz.
#   SSH_AUTH_SOCK      — agente do uid da porta; credencial nao atravessa fronteira
#                        de conta por heranca de env.
_NAO_ATRAVESSA = ("HOME", "USER", "LOGNAME", "XDG_RUNTIME_DIR", "DOCKER_HOST",
                  "SSH_AUTH_SOCK", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME")


class ContaNaoDespachavel(RuntimeError):
    """Sujeito tem `conta_so` no PAP e o despacho para ela nao pode ser montado.

    E erro de OPERACAO, nao de autorizacao: a politica disse `rode sob a conta X` e o
    host nao tem como obedecer. Quem trata devolve falha, nunca executa sob a conta da
    porta.
    """


def conta_do_sujeito(atrib: dict | None, conta_da_porta: str) -> str | None:
    """Conta de SO sob a qual o comando deste sujeito roda, ou None para 'a da porta'.

    `atrib` e a entrada do sujeito em `politica-acesso/sujeitos.yaml`, ja resolvida
    pelo PEP — este modulo nao le arquivo. Campo lido: `conta_so`.

    Devolve None (= caminho de hoje) em tres casos, e os tres sao deliberados:
      - sujeito sem atributos: nao chega aqui na pratica (o PDP nega por projecao
        ausente antes), mas defensivo e barato;
      - `conta_so` ausente: e o default de toda cadeira;
      - `conta_so` IGUAL a conta da porta: mandar 1001 rodar como 1001 pelo sudo custa
        um fork e uma dependencia de sudoers para nao mudar nada.
    """
    conta = ((atrib or {}).get("conta_so") or "").strip()
    if not conta or conta == conta_da_porta:
        return None
    return conta


def env_sob_conta(env: dict, conta: str, home: str | None = None) -> dict:
    """Env a atravessar para `conta`: o da porta, menos o que e do uid da porta.

    `home` explicito quando a conta nao mora em /home/<conta> — o default cobre o caso
    desta casa (`/home/jaiminho`, uid 1003) sem uma tabela nova para manter.

    PATH: o `<raiz>/bin` da plataforma FICA, porque e o ferramental da casa e e
    legivel; o `~/.local/bin` do uid da porta SAI e vira o da conta nova, senao a
    conta segregada executaria binario instalado na casa alheia.
    """
    casa = home or f"/home/{conta}"
    novo = {k: v for k, v in env.items() if k not in _NAO_ATRAVESSA}
    novo["HOME"] = casa
    novo["USER"] = conta
    novo["LOGNAME"] = conta
    caminhos = [p for p in novo.get("PATH", "").split(":") if p and "/.local/bin" not in p]
    novo["PATH"] = ":".join([f"{casa}/.local/bin", *caminhos])
    return novo


def argv_sob_conta(argv: list[str], conta: str, env: dict,
                   wrapper: str = WRAPPER_PADRAO) -> list[str]:
    """argv que executa `argv` sob `conta`, com `env` atravessando explicito.

    Forma: <wrapper> env - K=V ... <argv>. O `env -` zera o ambiente herdado do
    wrapper e reconstroi so o que esta na linha — ver a escolha 3 do modulo.

    Levanta ContaNaoDespachavel quando o wrapper nao interpola a conta: um wrapper mal
    configurado que rodasse assim mesmo executaria sob a conta da porta com cara de
    sucesso, que e o modo de falha que este modulo existe para nao ter.
    """
    if "{conta}" not in wrapper:
        raise ContaNaoDespachavel(
            f"wrapper de conta sem '{{conta}}': {wrapper!r} — recusado para nao "
            f"executar sob a conta da porta achando que trocou")
    prefixo = shlex.split(wrapper.format(conta=shlex.quote(conta)))
    # Chave sem '=' nao existe em env de processo; valor com '\n' passa inteiro pelo
    # execve (nao ha shell no meio). Ordenado para o argv ser estavel entre chamadas —
    # auditoria comparavel vale mais que os microssegundos do sort.
    pares = [f"{k}={v}" for k, v in sorted(env.items()) if "=" not in k]
    return [*prefixo, "env", "-", *pares, *argv]


def erro_de_conta(exit_code: int, stderr: bytes | str) -> str | None:
    """Mensagem quando a FALHA foi a troca de conta, nao o comando. None se nao foi.

    `sudo -n` sem regra sai 1 com `sudo: a password is required` ou
    `not allowed to execute`; o binario ausente ja estoura OSError antes daqui. A
    distincao importa porque as duas falhas pedem atos diferentes do dono: uma e a
    regra de sudoers que falta, a outra e o comando dele que quebrou.
    """
    if exit_code == 0:
        return None
    texto = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else (stderr or "")
    for marca in ("sudo: a password is required", "is not allowed to execute",
                  "sudo: no tty present", "may not run", "sudo: unable to"):
        if marca in texto:
            return (f"despacho sob a conta do sujeito nao autorizado no host: "
                    f"{texto.strip()[:300]} — falta a regra NOPASSWD de sudoers "
                    f"(ato de root; ver ops-server/README.md, story #3007)")
    return None
