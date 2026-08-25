# caderno — seguranca / hardening

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Risco em conta segregada se lê por VETOR DE ESCAPE, não por categoria funcional

Régua fechada em seg:0010 (modelo de risco: conta designada). O único vetor é
**sair da conta designada** — para cima (root) ou para o lado (uma conta alcança
outra). Dentro da conta é sandbox por design. seg:0010 item 2: remover um *caminho*
até a mesma capacidade que já se tem dentro da sandbox NÃO é controle.

Consequência que engana toda vez que alguém audita uma conta: `gcc`, `python3`,
`curl`, `crontab` não são risco — executar/persistir/baixar dentro da própria conta
é o modelo funcionando. Classificar por "o que é poderoso" produz controle
desproporcional, que é justo o que seg:0010 existe para cortar.

Três faixas, a que importa é a primeira:

- 🔴 **Escape real** — o que dá alcance para sair da conta. `docker` quando alcança
  socket de daemon (próprio com --privileged, ou de OUTRA conta via socket
  compartilhado); `nsenter`/`unshare`/`chroot`/`mount`. Só estes justificam negação
  por ausência (containerizar).
- 🟡 **Raio de segredo** (seg:0010 item 4) — rede (`curl`/`ssh`/`nc`/`socat`…),
  cripto (`gpg`/`openssl`), captura (`tcpdump`/`strace`/`gdb`). Não escapam; controle
  é custódia de CONTEÚDO, nunca negação do binário.
- ⚪ **Não-risco** — compiladores, runtime, persistência-na-conta, e SUID inertes sem
  senha de root (`passwd`/`su`/`pkexec`). Registrar como não-risco impede que virem
  controle.

Vetor lateral só existe se a conta alcança socket de daemon de outra conta. Sem
socket compartilhado, a segregação por conta (seg:0011) já fecha o lado.
Fonte: analises/risco-superficie-conta-segregada.md (arquitetura, 24/08/2026).

## "Ausência > negação" mira a faixa 1, não a faixa 3

Corolário do #2436 (containerizar cadeira-de-trabalho). O ganho de um filesystem
próprio por cadeira é tirar a FAIXA 1 da imagem de quem não a declara — não tirar
compiladores. ACL por binário (seg:0010 item 2) é negar caminho: frágil, apodrece
em update de pacote. Container é ausência real. Mas o alvo da ausência é docker/
nsenter/mount, e docker só entra na imagem de cadeira que declara orquestração —
para essas, o escopo do socket é decisão de segurança, não de build.

## "Verified: true" do scanner de segredo não é prova, é sinal a cruzar

O detector `Lob` do trufflehog aceita qualquer alfanumérico de 40 caracteres como chave
válida — e nome de função de teste (`test_cargo_vira_titulos_e_depois_page_id`, 40 chars)
cai nesse formato por coincidência. Medido em 25/08: 26 achados `Verified: true`, todos
nomes de função, confirmados cruzando cada valor contra `def <valor>(` no código-fonte.

A régua que fica: `Verified` é o sinal mais forte que a ferramenta dá, e ainda assim pode
ser sistemicamente falso para um detector específico. Não fechar sozinho com base só no
selo é certo (abrir incidente foi a decisão certa de quem rodou a varredura antes); o que
faltava era o cruzamento contra o código, que a ferramenta não faz por si. Não desligar o
detector depois do achado — desligar mascara a próxima chave real do mesmo tipo.
