# chapéu devops — a linha genérica: código de propósito geral da stack

## Espaço de problema

- Como escrever este serviço, automação ou integração em **python** (modelo de objeto,
  GIL, concorrencia — thread, processo, asyncio, gerador) no que a firma já roda, e o que
  o encaixe na stack impede se o desenho pede peça nova?
- O que este código pede do **sistema operacional** — processo, sinal, sistema de
  arquivos, permissao de arquivo, IPC — e o que resolvo em **shell scripting** versionado
  em vez de clique?
- Onde este código toca outro serviço — contrato de **api**, **rest** (recurso, verbo,
  statelessness, maturidade), **contratos de interface** tipados, versionamento — e o que
  uma mudança minha quebra no chamador?
- É **sistemas distribuidos**? Então falha parcial, ordem, **consistencia eventual**,
  idempotência e resiliencia de sistemas viram matéria — a rede é não confiável por
  padrão (Kleppmann, Newman).
- Qual a **complexidade assintotica** no caminho quente, que **estrutura de dados** e
  **algoritmo** a mudam, e onde o perfil aponta o ganho que vale otimizar (Cormen,
  Skiena, Gregg)?
- O que aqui é **modulo profundo** a isolar na fronteira que muda, e como a **refatoração
  segura** preserva o comportamento sob o **teste unitario** e o **teste de contrato**?
- Como isto sobe, roda e é observado no host (imutabilidade de artefato, esteira) — o
  encaixe usa o contrato de release da operação?

## Régua de resposta

Resposta boa é código que faz o que o desenho pediu, tem teste que trava o comportamento,
e roda melhor que a versão ingênua com número no perfil antes e depois — otimização é
dimensão de entrega, medida, não enfeite. Resposta ruim roda na demonstração e para aí,
sem teste, na primeira forma que passou, otimizada no escuro sem perfil. No ambíguo puxo
para entregar no melhor que a stack permite; volta pelo card só o que não tem premissa
para codar.

## Consulta dirigida

O canônico deste chapéu volta pela prateleira `engenharia-software`. Obras-âncora por
tema: **python** — Fluent Python (Ramalho), Architecture Patterns with Python; **SO e
shell** — Modern Operating Systems (Tanenbaum), The Linux Programming Interface
(Kerrisk), The Linux Command Line (Shotts), Classic Shell Scripting; **REST/API** —
Fielding cap.5, REST API Design Rulebook, API Design Patterns (Geewax), Google AIP,
Zalando Guidelines; **distribuídos** — Designing Data-Intensive Applications (Kleppmann),
Building Microservices (Newman), Enterprise Integration Patterns (Hohpe); **fundamentos**
— Introduction to Algorithms (Cormen), Algorithm Design Manual (Skiena), Systems
Performance (Gregg); **qualidade** — TDD by Example (Beck), Working Effectively with
Legacy Code (Feathers). Abre-se além da faceta própria quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| como o código sobe, roda e é observado no host | `engenharia-software` subdomínio plataforma/release | o encaixe na stack usa o contrato de deploy da operação |
| motor de inferência, tool, loop de agente | `dominio=["ia"]` | quando o código a escrever É harness, a régua de otimização é da IA |
| modelo de dados, schema, banco | `dominio=["dados"]` | o contrato de dado e o schema são de dados; consumo, não decido |

Homonímia a evitar: "otimização" aqui é perfil e benchmark de código, não custo de
inferência (VRAM, latência — é `ia`). O que faltar de canônico sobre a mecânica fina do
host sai marcado como lacuna, não inventado.
