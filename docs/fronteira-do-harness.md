# Fronteira do harness

O que o harness serve a quem abre sessão, e o que fica de fora. `conferir
procedencia` mede a fronteira do *caminho de execução*; esta aqui é a fronteira do
*contexto*: o que uma sessão recebe ao abrir, e por que a resposta depende de quem
pergunta.

## As duas classes de sessão

- **Cadeira** — persona do reino, com caixa, mesa, caderno e alcance amplo declarado
  em `seg:0006`. Abre por `monta_sessao(cadeira=…)`, tool MCP, e o cliente é o
  Claude Code ou o app. Recebe repos, manifesto de cadeira e o manifesto comum.
- **Externo** — colaboração em modelo DMZ: persona e conta próprias, sem cadeira,
  sem roteamento, sem shell. Abre por `GET /sessao`, HTTP puro, e o cliente é
  qualquer modelo com um cliente HTTP. Recebe persona e o ofício (`abertura/oficio.md`),
  memória, caixa e o catálogo de ações permitidas.

A diferença não é de tamanho de pacote: é de **superfície**. A cadeira alcança o
host por tool; o externo alcança quatro rotas e nada mais.

## O resolvedor

Não há tabela de "quem recebe o quê". O pacote se resolve do sujeito do token, em
três passos, e o terceiro é o que importa:

1. **Sujeito** — `preferred_username` do JWT, projetado em papel e domínios por
   `politica-acesso/sujeitos.yaml`. Sujeito ausente da projeção não abre sessão.
2. **Persona** — `personas/persona-<sujeito>.md`. Ausente, o pacote declara
   `persona.ausente` e segue; ausência declarada nunca vira omissão silenciosa.
3. **Ações** — o catálogo NÃO é escrito à mão. Cada ato candidato é submetido ao
   PDP com o sujeito real, e só entra no pacote o que a política permite naquele
   instante. Conceder acesso por merge no PAP muda o manifesto do externo sem
   tocar em uma linha de documentação.

O terceiro passo é a resposta ao contexto tácito: o que o modelo pode fazer ele lê,
não deduz. E a lista não pode divergir da política porque é a própria política
consultada.

## O que NÃO atravessa a fronteira para o externo

- Tool nenhuma: `run_command`, `read_file`, `write_file` e `monta_sessao` são
  negadas por interseção de domínio, antes de qualquer regra.
- Credencial de infraestrutura: o broker da malha `msg` nunca vê o externo. Quem
  escreve na caixa é o PEP, em nome dele.
- Caixa de terceiro: `GET /msg` lê a caixa do próprio chamador e não aceita
  parâmetro de caixa — caixa alheia não se lê por engano de query string.
- Acervo: leitura é concessão nomeada com prazo, nunca default.

## Verificar

```
curl -s -H "Authorization: Bearer $JWT" https://ops.platafirma.org/sessao | jq .acoes
acesso decidir --papel pesquisador-externo --dominio mensageria --acao msg_enviar --recurso "caixa:claudinho-IA"
```
