# Brief de integração para provedor de inferência

**Dono:** produto (Lygia). **Estado:** v4, congelada em 06/09/2026. **Idioma do brief:** inglês, por ser lido por modelos de qualquer vendor.

## O que é

Um one-pager que se cola no prompt de um modelo candidato com a instrução "leia e dê seu parecer". Ele explica o que a PlataFirma é, o papel de provedor de inferência (o modelo rodando em conta isolada, como engine intercambiável de uma cadeira), e pergunta ao candidato os fatos técnicos que a casa precisa para integrá-lo: regime de acesso por assinatura, tooling (MCP, instrução persistente, hooks), identidade e credencial dupla, e dados comerciais e de retenção.

Nada no questionário é requisito. Soberania, retenção e opt-out entram como fato coletado; quem classifica o provedor é a política de segurança da casa (ISP, #2978, comentário #650), não este brief.

## Como usar

1. Cole o bloco abaixo, inteiro, no prompt do candidato.
2. Peça: "Read this and give your assessment."
3. Guarde a resposta como insumo do benchmark de provedores. Fato afirmado pelo candidato só vira fato da casa depois de medido em POC: na validação, o mesmo modelo deu respostas diferentes em duas rodadas.

## Histórico

- v1 (06/09): PT, perguntas de tooling/identidade/comercial.
- v2: EN; pergunta-raiz de viabilidade (CLI sob assinatura).
- v3: tese da casa (centraliza a externalidade coletiva, descentraliza o instrumental); bootstrap; credencial dupla.
- v4: cadeira acionada por turno, não daemon; enforcement do bootstrap é da casa; franquia dedicada × compartilhada; inventário de hooks com comportamento em falha; pesos abertos; bloco C reenquadrado como coleta de fato.

Validada contra ChatGPT/Codex CLI e Kimi Code CLI (duas rodadas cada).

---

```markdown
# PlataFirma — Integration brief for an inference provider

You are a candidate model. Read this, then answer the questionnaire at the end and
give your assessment. If you are unsure what your own product supports, say so plainly —
do not guess. Nothing in this questionnaire is a pass/fail requirement: we are collecting
the technical facts our own policies need in order to integrate you correctly.

## What PlataFirma is
A working organization run by AI personas ("seats" — *cadeiras*), each a specialist in one
domain (product, data, security, law, and so on), operating over a document corpus, a
wiki, and a set of code repositories. A seat is not a fixed-flow app: it is an instance of
an inference model that, at the start of every session, loads a persona plus its working
context and then operates the house through "verbs" — tools that read the corpus, move
task cards, check state, and publish to git and to the wiki.

The design principle: PlataFirma **centralizes what has collective externality** — the
corpus, institutional memory, decisions, tasks and responsibilities, provenance and audit,
and who is allowed to know what — and **decentralizes what is instrumental**: which model,
which subscription, which CLI, which personal workflow. The seat is the stable object; the
model is an interchangeable engine attached to it. A participant brings their own
inference; the house provides the world it operates in.

## The provider's role
You are the engine a participant brings to a seat — not the product. "Provider" means the
inference model running in an isolated system account, as the base of the security
architecture: the full set of verbs exposed over an API, policy enforcement at the endpoint
of every resource (a policy decision point on the path of every call), its own OS user, a
short-lived credential for house resources, and an audit trail of everything invoked. Any
competent runtime that honors this contract can hold a seat; a working integration with
you is proof of that architecture, not a dependency on you.

The house has its own harness (*platafirma-harness*). In the target regime it does not
replace your official client — it plugs into it: your CLI is the runtime, our harness
supplies the MCP server (the verbs), the persistent instruction (the persona), and the
session bootstrap.

## How it operates, in practice
A seat is **driven by the participant's turns**: it wakes when the participant opens a
session, works, and goes quiet when the session ends. It is not a daemon and does not run
continuously. The first action of every session is a call to the `monta_sessao` verb
("assemble session"), which returns the persona, its charter, a working desk (open items),
and the slice of corpus relevant to the turn. From there the model receives the remaining
verbs as tools and works. Anything that touches the host goes through an endpoint with
policy on the path — nothing is run through a free command string. Enforcement of this
sequence lives on **our** side: house verbs refuse to run without a valid session. Anything
your runtime offers on top of that is a second layer, not the barrier.

What goes **into** your prompt is also governed by house policy: content is classified by
provider class (sovereign / enterprise API with zero retention / consumer subscription),
and each class receives what it may receive. That is why block C asks about retention and
region — to place you in a class, not to disqualify you.

**Target access regime:** your official command-line client, authenticated with a
subscription plan (fixed price), serving as the runtime of a seat — not a metered
pay-per-token API and not a harness we build against your API. Question A1 asks whether
that is possible; answer it before the rest of block A.

## What we need you to tell us about yourself
Answer point by point. Where something does not apply, say so.

**A. Access regime and tooling**
1. Does your **official CLI, authenticated with a subscription plan**, accept external MCP
   servers and an external persistent instruction, and serve as the runtime of an agent
   session driven by our harness — **without the house owning or administering the
   account**? If tool use under a subscription is available only inside your own product
   surface, or only through the paid API, say so. Is the subscription allowance for CLI
   use **dedicated**, or **shared** with the participant's personal use of your other
   products (web, mobile, IDE)? What are the rate-limit windows?
2. Name and version of that CLI/agent runtime; how fast it changes; what you would not pin.
3. MCP: which transports (stdio, HTTP/SSE, streamable HTTP)? Any limit on number of tools,
   schema size, or naming? Reconnection behavior on a long session?
4. If not MCP, what is your tooling model (native function calling, proprietary format)?
5. Persistent instruction: which files or settings (e.g. an `AGENTS.md`-style project
   instruction, a system-prompt override, a global config) can pin a seat's persona across
   the session? Give paths and formats.
6. Hooks: which lifecycle hooks exist (session start, before tool call, after tool call,
   session end)? Which of them can **block**? What happens when a hook script errors or
   times out — does the runtime fail open (allow) or fail closed (deny)?
7. Long sessions: context window, state between calls, resume mechanism,
   compaction/checkpoint behavior, or must we resend the full history each turn? Can the
   CLI be driven headless / non-interactively (one-shot prompt, agent protocol)?

**B. Access, identity, and deployment**
8. How is access configured on your side: your own console, CLI configuration, a file
   (which format, which path)?
9. **Two credentials.** The inference login (your account) belongs to the participant; the
   house never holds it. Credentials for house resources are issued by the house as
   short-lived tokens and never reach the model — it receives only tools. Confirm your
   runtime needs nothing beyond the MCP tools to operate, and describe how your own login
   is stored and rotated on the participant's machine.
10. Call endpoints and the region where inference runs. If region controls exist only on
    the API and not under a subscription, say so.
11. Are your model weights available for **self-hosting** (license, sizes, hardware
    envelope)? If so, does your official CLI work against a self-hosted or third-party
    endpoint, and how is that configured?

**C. Commercial and data governance (facts for classification, not requirements)**
12. Pricing model: subscription tiers and their usage allowances, versus API pricing.
13. Link to your privacy policy.
14. Data capture and retention, **under a subscription specifically**: is training opt-out
    available, and is it self-serve? Is zero retention available, or only on the API? What
    is retained of prompts and responses, and for how long? Where the answer differs
    between subscription, API, and self-hosted, say so for each.
```
