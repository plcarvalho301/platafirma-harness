# Rodada 2 — prompt de proposta de conceitos

Texto único e genérico — cola igual em toda sessão, sem editar nada. Cada
cadeira se identifica sozinha pela própria persona ativa.

Cadeiras que respondem: `claudinho-arquiteto`, `claudinho-conhecimento`,
`claudinho-IA`, `claudinha-produto`, `claudinho-TI`, `claudinho-seguranca`,
`claudinha-gestao-estrategica`. `claudinha-fabrica` e `claudinha-osint` não
participam — não são cadeiras.

---

**Rodada 2 da distribuição do acervo. Você é a cadeira desta sessão — sua
própria persona. Proponha os conceitos que as obras do seu lote sustentam.**

**Seu lote.** Repo `platafirma-harness`:

- `distribuicao/rodada-1/reivindicacoes/<sua-persona>.csv` — o que você ganhou,
  **menos** as obras que aparecem em `conflitos.csv`;
- `distribuicao/rodada-1/conflitos.csv` — as obras em que você foi
  reivindicante e **perdeu**: o conceito delas é seu. Quem levou a obra não
  propõe o conceito dela.

Leia os arquivos inteiros antes de responder. Proposta de memória não vale.

**Conceito não tem dono.** Você propõe **régua**, não posse. Não existe campo de
domínio na entrada: o conceito existe sozinho, individuado pela definição, e é o
domínio que declara pertencimento do lado dele. Duas cadeiras propondo a mesma
régua não é conflito — é a mesma entrada, e uma das duas sai.

**Cota — por lastro, sem número.** Cada conceito proposto precisa de **≥2 obras
do seu lote** que a régua classifique. Teto duro de **10** conceitos por cadeira:
o teto existe para forçar seleção, não para ser atingido. Lote pequeno propõe
pouco ou nada, e isso é resultado correto.

## As sete heurísticas

1. **Régua antes de rótulo.** Escreva o mecanismo — a relação que produz o
   veredito — e só depois nomeie. Definição que contém o próprio rótulo, ou a
   fórmula "o que se considera X", volta.
2. **Teste dos três casos.** Aplique a régua a três obras: uma que entra, uma
   que não entra, uma duvidosa. Quem mede é a duvidosa. Se ela não decide só
   com o texto da régua, a régua está frouxa.
3. **Teste de transposição.** Aplique a régua fora do universo da obra de
   origem. Precisou de "é meio como se fosse", é metáfora, não transposição:
   conceito diferente, régua própria.
4. **Caso falseador, uma linha.** Que caso, se aparecesse, mostraria que esta
   régua está errada. Régua que nenhum caso contraria não delimita nada.
5. **Teste do parônimo.** Se dois curadores competentes redigiriam definições
   incompatíveis para o termo nu, ele não vira entrada: quebre em compostos
   (`inteligencia-de-ameacas`, nunca `inteligencia`).
6. **Prateleira não é régua.** Candidato que só agrupa obras é subdomínio —
   devolva ao dono do domínio, não proponha como conceito. Coincidência lexical
   entre rótulo e domínio não infere nada.
7. **Varredura antes de propor.** Leia
   `distribuicao/rodada-2/conceitos-existentes.csv` (205 entradas). Rótulo
   diferente que decide a mesma coisa **é a mesma entrada**: não proponha em
   paralelo. Discordando da régua existente, proponha **substituição** dela, com
   o motivo, em vez de entrada nova.

## Entrega

Crie `distribuicao/rodada-2/propostas/<sua-persona>.md` (nome do arquivo = seu
próprio nome de cadeira), um bloco por conceito, nesta forma:

```
## <slug>
rotulo: <nome legível>
natureza: fenomeno | processo | disposicao | modelo
estatuto: natural | doutrinario | instituido
definicao: <a régua: o mecanismo, em uma a três frases>
obras-ancora: <obra_id>, <obra_id>   # ≥2, UUID literal do CSV
caso-falseador: <o caso que mostraria a régua errada>
pai-proposto: <slug do conceito mais amplo, ou vazio>
linha-de-raiz: <a frase que entra na raiz do domínio e faz querer clicar>
substitui: <slug existente, ou vazio>
```

`pai-proposto` só quando a régua do pai decide todo caso que a do filho decide.
Hierarquia por afinidade temática não vale — deixe vazio.

**Escrita.** `git pull --rebase`, commit e push **só do seu arquivo**. Não toque
em `conceitos-existentes.csv`, nos artefatos da rodada 1 nem no arquivo de outra
cadeira.

**Resposta na conversa, no máximo:** quantos conceitos propôs; um que você
descartou por falhar no teste de transposição; e qual proposta colide com entrada
existente e por quê.

**Não faça agora:** escrever em `acervo.conceito`, criar ou editar página de
wiki, criar subdomínio, declarar relação entre conceitos de cadeiras diferentes.
A reconciliação e a teia são de `claudinho-conhecimento`, depois que todas as
propostas estiverem no repo.
