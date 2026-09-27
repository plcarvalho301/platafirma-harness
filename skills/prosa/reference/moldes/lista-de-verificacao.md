# molde — lista de verificação

Régua fina: anexo de moldes §6 (fonte: `acervo ler casa padrao styleguide-moldes-por-tipo`).
Estrutura: `acervo.especie_estrato` (Derivação e objeto · Critérios). Exemplar no ar:
`acervo ler casa lista-de-verificacao checklist-antipadroes-organizacao-documental`.

Distintivo: cada critério passa ou falha sem julgamento de mérito, ou declara que depende
de leitura. Dois leitores: a máquina (`lint`, teste do portão) e a pessoa que confere o
que a máquina não detecta. Não é padrão (como se faz) nem parecer (o que se recomenda).

## Contrato com a máquina — não improvise

`bin/_lint/lista.py` lê a lista pelo acervo e reconhece a coluna pelo nome do cabeçalho.
Nome fora desta lista faz a coluna sumir para a máquina:

| campo | nomes aceitos |
|---|---|
| id | `#`, `id` |
| o que falha | `critério`, `antipadrão`, `o que fere` |
| fonte | `lei da casa`, `fonte`, `deriva de` |
| detector | `detector` |
| severidade | `severidade`, `classe` |
| cura | `cura` |

- A tabela só é lida se tiver `detector` ou `severidade` no cabeçalho.
- `severidade` vale `bloqueante` ou `aviso`, e nada mais.
- `Rev:` sai das linhas de metadado antes do primeiro `##`; é número inteiro.
- Lista retirada some para a máquina; critério retirado fica na tabela, marcado.

## Estratos

1. **Derivação e objeto** — a primeira frase diz o que se confere e onde. Depois: quem
   roda (teste do portão, `lint <classe>`, leitura), onde não se aplica, e a legenda das
   colunas e da severidade. Sem histórico da deliberação.
2. **Critérios** — a tabela, um critério por linha.
   - `critério`: nome curto do que falha, mesma polaridade na lista inteira.
   - `detector`: o predicado literal; se a máquina não detecta, «leitura».
   - `severidade`: bloqueante só com lei citada e detector mecânico; o resto é aviso.
   - `cura`: imperativo.
   - O `#` não muda nunca; renumerar quebra quem cita.

Opcionais, depois: **Contrapontos** (falsos positivos que o detector respeita) e
**Mudança** (uma linha por rev). Prova de origem vai a rodapé, não à célula.

## Esqueleto

```
# <o que se confere, em palavras comuns>

Espécie: lista-de-verificacao
Rev: 1
Dono: <cadeira>
Sobre: <classe> <chave>; <classe> <chave>
Deriva de: <lei>; <lei>

<Uma frase: o que se confere e onde.> <Quem roda: teste do portão, `lint <classe>`, leitura.>
<Onde não se aplica.>

## Como se lê

- **Bloqueante:** <quando reprova>.
- **Aviso:** <quando só relata>.
- **Detector** é o predicado que a máquina roda; «leitura» quer dizer que ela não detecta.
- **Cura** é o que se faz para o apontamento sumir.

## Critérios

| # | critério | lei da casa | detector | severidade | cura |
|---|---|---|---|---|---|
| <PFX>1 | <o que falha> | <lei, ou «sem lei direta»> | <predicado, ou «leitura»> | <bloqueante ou aviso> | <o que fazer> |

## Contrapontos

- <falso positivo que o detector já respeita>.

## Mudança

- rev 1 (<dd/mm/aaaa>): <o que entrou>.

[^<n>]: <de onde veio o critério>.
```
