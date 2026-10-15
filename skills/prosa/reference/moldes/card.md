# molde — corpo de card (épico e feature): o two-pager

Forma: rótulos por nível, da ADR 0096 (padrão de card por nível, de gestão estratégica);
o esqueleto sai de `tarefas modelo <nível>`. Régua fina de cada rótulo: anexo de moldes, §7
(`acervo ler casa padrao styleguide-moldes-por-tipo`). Ciclo e momento de cada rótulo: guia
discovery (`acervo ler casa guia discovery`). Divergiu, a fonte é o anexo.

Leitor: o dono, para validar, e as cadeiras, para procurar onde quebra. Durante o discovery,
o corpo é o único texto que vale: tem um autor, a cadeira que conduz a frente, e uma versão.
Comentário contribui; o corpo é o que vale.

Teste de pronto: quem lê só o Título, a Solução e o Fora sabe o que muda, como se usa e o que
não vem. Os três cabem na primeira tela.

## Esqueleto

```
<Título, até doze palavras: épico, o que passa a ser verdade e para quem; feature, a coisa que vai existir>

Problema:      como é hoje, como quem sofre veria, com um caso; até quatro frases, sem número
Solução:       a solução contada como uso: «Ao <momento>: quem faz o quê, e o que vê»
Peças:         numeradas: o que vai existir (lugar, ato, regra); regra nova diz quem a cobra
Fora:          o que esta frente não entrega e alguém pediria; para onde vai, quando vai
Resultado:     quem passa a conseguir o quê; o outcome vai marcado «não fecha card»
Medida:        escala · medidor · valor hoje · mínimo aceitável — uma linha
Apetite:       quanto vale gastar · o que se corta primeiro — previsão de quem escreve   (opcional)
Aberto:        prosa do autor: o que está por decidir, cada item com quem responde
Produtos documentais: um por linha: ADR, spec da peça, documento, dado, emenda   (feature)
Sai quando:    na lapidação, a frase; na formalização, o comando que prova   (feature)
```

A ordem segue o que o leitor precisa primeiro: logo depois do caso vem a solução, e o Fora
fecha a primeira tela. Resultado e Medida, que a homologação compara, vêm em seguida.

Não há rótulo de fontes nem Continuidade. Fonte entra como comentário `insumo`; o que
sustenta a peça depois da entrega mora na spec dela.

## As três famílias

- **A aposta** (Título, Problema, Fora, Resultado, Medida, Apetite): para de mudar na aposta e
  fica. O Fora ainda cresce com os cortes da entrega.
- **A forma** (Solução, Peças, Aberto): sai do card quando o destino existe. A Solução vira
  link para a spec da peça, no mesmo lugar; as Peças, para as stories, pelo número do card. No lugar
  fica o link com o nome do que aponta e uma linha do que muda para quem usa:
  `Solução: a cadeira valida lendo um texto que descreve a solução · spec do comentário tipado, cenários C1 a C5`.
  Sem spec, a Solução é a única descrição e fica.
- **O índice** (Produtos documentais, Sai quando): completo na formalização.

## A voz, rótulo a rótulo

1. **Título** — palavras comuns, sem metáfora, slogan ou jargão da casa. Desce do resultado
   à entrega (ADR 0096, «O título desce do resultado à entrega»): o épico diz o que passa a
   ser verdade, e para quem; a feature nomeia a coisa que vai existir, com o para quê quando
   couber; a story diz o trabalho e o artefato; a task, o conserto. Lido sozinho na lista,
   abaixo do épico, o título diz o que se está fazendo. «Identificador permanente para
   conceito e coisa do mundo» serve; «apontar conceito por endereço que não muda» é estado
   alcançado, e vai ao Resultado.
2. **Rótulos** — um por linha, linha em branco antes do seguinte. Frases curtas, uma ideia
   por frase, voz ativa.
3. **Problema** — caso, não tema. O número vai à Medida.
4. **Solução** — cada item abre pelo momento ou pela pessoa («Ao lapidar:», «No parecer:»).
   Presente do indicativo. Sem nome de arquivo, campo ou função. Até sete momentos.
5. **Peças** — `1.`, `2.`… uma linha cada. Peça sem momento sobra; momento sem peça é
   promessa sem lugar.
6. **Fora** — lista; não proíbe. O que a casa decide não fazer é comentário `decisão`.
7. **Resultado** — mais de um ganho vira lista.
8. **Apetite** — as duas partes; sem o que se corta, é estimativa, não apetite.
9. **Aberto** — prosa, não lista de comentários: o estado de cada comentário mora no fecho
   dele. Na aposta, linha que sobra diz «fica aberto de propósito:» e o risco.
10. **Produtos documentais**, **Sai quando** — como no esqueleto; na formalização, cada
    linha ganha o link do que foi servido.

No épico, as Peças são as features; a quebra entre elas se lê das filhas, no rastreador.

Tamanho: perto de cinco mil caracteres. Passar muito disso indica solução concreta demais ou
feature que é épico.

Story e task: só o núcleo; quem lê é quem executa, e os rótulos da ADR 0096 já são a forma.
A story que sai de uma formalização tem molde próprio: `story-derivada.md`.

Todo número de card, código de ADR ou seção vem com o nome do que aponta. Parede de texto
sem quebra é falta, por melhor que seja cada frase.
