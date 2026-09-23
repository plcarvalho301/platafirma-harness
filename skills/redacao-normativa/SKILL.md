---
name: redacao-normativa
description: Use sempre que for MINUTAR, REVISAR ou AVALIAR ato normativo de órgão público — portaria, resolução, instrução normativa, política interna, regimento, norma complementar — e com mais razão quando o objeto é capacidade de tecnologia (governança de dados, segurança da informação, classificação, controle de acesso, sistema que executa regra). Dispara também em «quanto detalhe pôr aqui», «regra ou padrão», «isso é exequível?», «o controle vai cobrar isso?», «revisa esta minuta», ou quando uma política do Roadmap de Políticas entra em redação, mesmo que ninguém diga «skill». Dá o gate antes de redigir (competência, problema, inventário de capacidade), o quadro de densidade por dispositivo, a ordem entre os leitores da norma e os critérios de aceite da minuta. NÃO dispare para peça processual, contrato, parecer sobre caso concreto sem norma a escrever, nem para prosa de wiki (aí é `prosa`). Norma que onera terceiros usa esta skill e acrescenta a análise de impacto regulatório.
cadeiras: direito (dona da matéria); qualquer cadeira que minute ato normativo
compatibility: sem verbo próprio. Fonte humana e versão longa na wiki, página «Guia: redação normativa para capacidades de tecnologia». Rende mais com o acervo ao alcance (`motor rag buscar obra`) para ler D12002, LINDB e LC 95 no texto.
---

# Redação normativa para capacidades de tecnologia

Norma é instrução para um executor de capacidade finita. A densidade do texto escolhe
a capacidade que ele vai exigir: regra detalhada exige capacidade de executar; padrão
aberto exige capacidade de julgar. Minutar é decidir, dispositivo por dispositivo, qual
das duas o órgão tem e o que fazer quando não tem nenhuma.

Esta skill segue a própria régua. O que é verificável está em regra (gate, colunas da
matriz, critérios de aceite). O que pede juízo está em padrão, com a razão ao lado,
para você aplicar ao caso que o texto não previu. Os fundamentos estão em `reference/`.

## 1. Gate: antes do primeiro artigo

Não redija com um destes aberto.

1. **Competência.** Quem assina, com que fundamento, e se a matéria está sob reserva de
   lei. Ato sem competência é nulo por mais bem desenhado, então isto vem antes de tudo.
2. **Problema e consequência.** Que problema o ato resolve e o que muda com ele. É o que
   a LINDB (art. 20) cobra de quem decide, e é o primeiro parágrafo da nota que
   acompanha a minuta.
3. **Inventário de capacidade.** Quem executa hoje cada dever, com que pessoas, sistemas
   e registros. Sem inventário o quadro da seção 3 roda no vazio e a minuta vira modelo
   copiado de outro órgão.
4. **Estoque vigente.** As normas do órgão sobre o mesmo objeto e as federais que ele
   cumpre. Em tecnologia, GSI e MGI costumam regular o mesmo objeto com vocabulários
   diferentes; a minuta absorve a colisão, não a repete.

Falta insumo que só o dono tem (política vigente, estrutura, inventário)? Peça: é
insumo, não decisão. Não preencha com suposição sobre o órgão.

## 2. Quebre em dispositivos-tarefa

A unidade de análise é o dispositivo, não a norma. Uma linha por dever: quem faz o
quê. A mesma portaria mistura deveres de natureza diferente (revogar o acesso de quem
saiu; classificar informação), e cada um pede densidade própria.

## 3. O quadro, linha a linha

Cada dispositivo passa pelos quatro eixos e pelo recorte:

| Eixo | Pergunta | Puxa para regra quando | Puxa para padrão quando |
|---|---|---|---|
| Tipo de tarefa | verificar fato ou decidir caso a caso? repete muito? | verificar fato; conduta frequente | juízo caso a caso; conduta rara |
| Quem sabe especificar | quem redige fecha o caso melhor que quem aplica? | sim | não: padrão com julgador nomeado, ou detalhe delegado a ato de nível inferior |
| Fiscalização depois | há quem confira, com registro? | sim | não: crie a verificação antes de detalhar |
| Compromisso do executor | cumpre ou resiste? | resiste: regra, consequência e construção de capacidade | adere: padrão com apoio |
| Recorte de direitos | restringe direito, sanciona ou decide sobre pessoa (inclusive por sistema)? | sempre precisão, ao menos no rito | não se aplica |

Três saídas do quadro que não são escolha de redação:

- **Precisão no rito, padrão no mérito.** Quando o recorte pede precisão e a tarefa
  pede juízo, o procedimento vai em regra (quem decide, prazo, motivação registrada,
  revisão, contestação) e o conteúdo fica em padrão, com julgador nomeado.
- **Medida de implementação.** O órgão não tem capacidade de executar nem de julgar
  aquele dever: a parte final do ato traz a medida, com responsável e prazo (Decreto
  12.002/2024, art. 4º, III, a, 1), e o regime de transição.
- **Não normatizar ainda.** Obrigar sem capacidade é carga prematura. A nota diz por
  que o dever ficou fora e quando volta.

Padrão sem julgador nomeado nunca é saída. Ele isenta o gestor: não há contra o que
cobrar.

## 4. Matriz de densidade

Anexe à nota da minuta. Estas colunas, nesta ordem, nenhuma suprimida. A última guarda
a previsão feita antes da assinatura; sem ela a minuta não serve de caso de pesquisa.

```
dispositivo | dever (quem faz o quê) | frequência | tipo de tarefa | quem sabe especificar |
fiscalização | compromisso | afeta pessoa? | vai a código? | capacidade exigida (executar/julgar) |
existe? | forma escolhida | medida de implementação | o que o controlador acha | previsão
```

Exemplos preenchidos e dois dispositivos reescritos em `reference/exemplos.md`.

## 5. Os leitores e a ordem entre eles

Quatro leituras, entendidas como papéis (na norma interna, sujeito e implementador
costumam ser o mesmo servidor): o sujeito compreende, o implementador navega, o
operador do direito interpreta, o controlador audita. Em tecnologia o implementador tem
dois corpos, o servidor e o sistema, com quem programa no meio.

Quando colidem:

1. Dispositivo que restringe direito, sanciona ou decide sobre pessoa: vence o operador
   do direito. Precisão antes de simplicidade.
2. Nos demais: vence o implementador. A compreensão do sujeito se resolve com material
   de apoio fora da norma.
3. O controlador não disputa a redação, soma exigências: indicador, responsável,
   registro da decisão.
4. O sistema só lê regra. Padrão não vai a código sem ponto de decisão humana nomeado.
   Regra que vai a código indica o dispositivo de origem, para a tradução poder ser
   conferida. Quando afeta pessoa, aviso, razão e contestação estão no texto da norma,
   não deixados à engenharia.

A ordem é proposta da cadeira de direito (23/09/2026), sem teste. Mudou por decisão do
dono, vale a mudança.

## 6. Critérios de aceite

A minuta sobe à validação quando cada item é verificável na minuta ou na nota:

1. Competência e fundamento no preâmbulo; nada sob reserva de lei.
2. Problema e consequência na nota, com as alternativas consideradas e por que foram
   afastadas (LINDB, art. 20, parágrafo único).
3. Matriz completa, anexa.
4. Todo padrão nomeia quem julga.
5. Toda regra detalhada tem executor com capacidade inventariada, ou medida de
   implementação com responsável e prazo.
6. Conduta frequente em regra; padrão só para o raro ou para o que pede juízo.
7. Todo dispositivo que restringe direito, sanciona ou decide sobre pessoa tem o rito em
   regra, mesmo com o mérito em padrão.
8. Todo dispositivo que vai a código indica a regra fechada ou o ponto de decisão humana
   e, quando afeta pessoa, prevê aviso, razão e contestação.
9. Todo dever tem dono. Quem executa, quem verifica e quem audita são diferentes, e o
   controlador acha indicador e registro.
10. Nenhum dispositivo trazido de modelo entra sem a função que cumpre aqui e a
    capacidade que supõe.
11. Norma sigilosa nomeia quem confere o cumprimento no lugar de quem não pode ler a
    regra.
12. A minuta foi percorrida com quem executa, dispositivo por dispositivo (nas minutas
    da Raia 1: segurança e produto).

Relate como lista: item, passa ou falha, e onde. Falha não se dilui em ressalva.

## 7. Sinais de norma que vai falhar

Ao revisar minuta alheia, procure:

- «observar as boas práticas» sem dizer quem julga → padrão sem julgador;
- colegiado que aprova e não monitora → homologação de fachada;
- artigo igual ao de outro órgão → mimetismo; pergunte a função;
- obrigação com prazo e sem pessoa, orçamento ou sistema → carga prematura;
- «o sistema bloqueará» sem via de contestação → regra aplicada por código sem rito;
- procedimento acrescentado para proteger quem assina → apagão das canetas; a cura é
  motivar com a alternativa afastada (LINDB, art. 20, parágrafo único), porque o agente
  só responde por dolo ou erro grosseiro (art. 28), não mais uma etapa;
- dor de execução atribuída ao órgão executor → confira se não é erro de desenho de
  quem legislou.

## 8. A LINDB a favor de quem redige

- **Art. 22.** Norma de gestão se interpreta considerando os obstáculos reais do gestor.
  O julgador de um padrão registra as circunstâncias do caso na motivação.
- **Art. 23.** Interpretação nova de norma de conteúdo indeterminado que imponha dever
  novo pede regime de transição. Todo padrão da minuta fica sujeito a isso quando o
  julgador mudar de entendimento; preveja o rito.
- **Art. 30.** Regulamento, súmula administrativa e resposta a consulta vinculam o órgão
  até revisão. É o caminho do padrão para a regra: o julgador consolida os casos em
  orientação, e a orientação passa a vincular.
- **Art. 29.** A consulta pública exclui ato de mera organização interna. Não a trate
  como obrigação da norma interna.

## 9. O que esta skill não faz

- Não desenha a política. Problema, teoria da mudança e avaliação são de políticas
  públicas; a skill dá a forma jurídica do que foi desenhado.
- Não fecha pela autoridade. A minuta é proposta; quem assina decide.
- Não cita artigo de memória. Norma citada vem do texto, lido no acervo ou na fonte
  oficial; o que não foi lido sai marcado como não conferido.

## Referências, sob demanda

- `reference/estado-da-arte.md` — as quatro teses sobre redação e capacidade, a
  condição da fiscalização, a camada da norma executada por sistema, o que está
  desocupado. Leia ao escrever a nota da minuta ou quando pedirem o porquê.
- `reference/exemplos.md` — matriz preenchida e dois dispositivos reescritos. Leia
  antes da primeira matriz da fita.
- `reference/norma-e-prompt.md` — por que esta skill está escrita assim, e a ponte
  entre redigir norma e instruir modelo. Leia ao revisar a skill ou quando a norma a
  escrever for instrução a sistema de IA.
