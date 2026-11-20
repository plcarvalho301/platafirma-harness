---
name: revisao-de-documentos
description: Use SEMPRE que puser em execução uma revisão de documentos para a casa nova (as stories «Revisar os documentos de … na casa nova»), ou voltar a ela para consertar um documento que o dono devolveu. É o fluxo que leva cada documento velho, por um sub-agente, até a decisão que o dono vê e, depois do sim dele, ao documento novo em main e à ficha no schema casa. Siga ANTES de delegar o primeiro documento, mesmo que você ache que já conhece o fluxo pelo card. NÃO dispare para escrever o texto de um documento, que é a prosa-espelho, nem para refinar o recorte da story ou decidir o que é evento.
---

# Revisão de documentos para a casa nova

## Quando serve

A story de revisão entrou em execução, e o Plano dela traz o recorte: os documentos
velhos que ela revisa, a entidade que o título sugere para cada um e os documentos que
devem existir no fim.

A story revisa uma faixa: a lista de eventos que ela cobre, que o Plano traz na ordem,
com o id, o tipo e o texto de cada linha. Faixa é nome do mapa de eventos do dono, não
da ontologia, e não entra em documento novo.

Serve também para voltar a um documento que o dono devolveu com pedido de conserto.

Não serve para refinar o recorte, que se faz antes, no Plano. Também não decide nada
sobre evento: a revisão não trata de como o evento se modela.

O texto de cada documento novo se escreve pela skill prosa-espelho. Quem a carrega é o
sub-agente, na hora de escrever, e não você.

## Os nomes vêm da ontologia nova

Toda revisão se apoia na ontologia nova: o catálogo gravado pela olaria no schema casa do
banco do acervo (`infra rodar ontologia -- ler shape <classe>`). Os tipos de ligação moram no
dicionário `tipo-de-ligacao` do catálogo, e cada classe declara quais ela aceita. O
catálogo é a única fonte de nome. Mudar uma classe ou tipo de ligação pede a autorização
do dono antes.

Todo nome da casa que aparece na revisão se confere contra o catálogo antes de ser
usado. Vale para o caminho, o cabeçalho, o corpo e as ligações de cada documento novo, para
e para o registro da unidade, em qualquer estrato. Duas leituras fazem a
conferência:

- `infra rodar ontologia -- listar shape`:
  o nome existe se a classe está no catálogo; sem ela, os nomes parecidos são os slugs vizinhos.
- `infra rodar ontologia -- ler shape <slug>`:
  a definição, a mãe, a categoria e o caminho do documento da entidade.

Cada saída pede uma coisa:

- **existe:** o slug vai no caminho e no cabeçalho, e o rótulo vai na prosa.
- **não existe, com parecido:** o parecido não é sinônimo. Leia a definição dele e use-o
  só se ela cobre o que o documento diz; se não cobre, o nome não tem encaixe.
- **não existe, sem parecido:** o nome não entra no documento novo. Troque pelo da
  ontologia cuja definição cobre a matéria, ou leve a entidade nova como proposta ao dono.
- **indeterminável (saída 2):** a fonte não respondeu, e isso não é negativa. A unidade
  fica como falhou e se confere de novo.

O nome velho que se trocou por um da ontologia vai ao de-para da revisão (passo 1), para
que todas as unidades troquem o mesmo nome do mesmo jeito.

## Quem faz o quê

Você é a orquestradora. Cada documento velho é uma unidade (um documento velho e os
documentos novos que nascem dele), e cada unidade tem um sub-agente.

O sub-agente é do tipo de uso geral, que escreve arquivo e chama as ferramentas da porta,
e roda em Sonnet, nunca em Opus. A primeira chamada dele abre a própria sessão:
`monta_sessao` no perfil cadeirinha, com a origem igual ao seu sessao_id e a mensagem de
delegação na pergunta, para que o registro de eventos ligue o trabalho dele à sua sessão.
Ele lê o documento velho sozinho, sem passar a leitura a outro agente.

O sub-agente lê, decide e escreve só na pasta da unidade. Escritor só há um, que é você:
só você copia para a árvore do repositório novo, commita em main e grava no schema casa,
um documento por vez.

O sub-agente confere os nomes que usa, mas não confere a si mesmo: você roda de novo a
conferência de nomes sobre o que ele escreveu, no passo 5, sem confiar no que o registro
diz dela.

O dono vê cada decisão antes de você gravar qualquer coisa dela. Nada vai a main nem ao
schema casa antes disso.

## Passos

1. Abra a pasta de trabalho da revisão na bancada, fora da árvore do repositório novo,
   com uma pasta por unidade, o arquivo de andamento e o de-para. O andamento diz, por
   unidade: pendente, em curso, entregue, com o dono, aprovada, gravada, não decidido ou falhou. O
   de-para tem uma linha por nome velho trocado: o nome velho, o slug da ontologia ou
   «proposta», e a unidade e o trecho que o pediram. Nada dessa pasta se commita, porque
   o lint da árvore reprova o que não é documento.

2. Monte o prefixo comum da [mensagem de delegação](mensagem-de-delegacao.md),
   preenchendo os campos marcados nela:
   - o índice das entidades, montado do catálogo (`infra rodar ontologia -- listar shape`): uma linha por entidade que se
     instancia, com o slug e a definição;
   - a lista fechada de tipos de ligação, do catálogo, com as ligações que
     cada entidade candidata declara;
   - a faixa da story inteira, na ordem em que o Plano a traz;
   - o de-para como está;
   - a forma do cabeçalho novo e o teto de giros.

   Confira com `conferir existe entidade` cada entidade que o Plano sugere para o recorte.
   A que não existe não entra como candidata: vai à lista do dono no passo 6.

3. Delegue as unidades em paralelo, um sub-agente em Sonnet por linha do recorte, cada um
   com o prefixo comum e o bloco da unidade. Ponha a unidade em curso no andamento.

4. Quando o sub-agente voltar, ele devolve só o caminho do [registro](registro.md) e o
   estado. Siga pelo estado:

   | o registro diz | o que você faz |
   |---|---|
   | decidido | passe ao passo 5 |
   | falhou | delegue a unidade de novo; as outras não rodam de novo |
   | não decidido, e o que faltou a casa tem | ache o que faltou, ponha no bloco da unidade e delegue de novo |
   | não decidido, e o que faltou só o dono sabe | guarde para o passo 11 |
   | pertence à revisão N | guarde para o passo 6, sem documento |
   | funde com outro documento | cruze as declarações (abaixo) |

   Fusão: o par recíproco vira uma unidade nova, que recebe os dois documentos velhos e
   escreve o fundido. Quando o par está em outra revisão, a troca de revisão vai ao dono
   no passo 6 como decisão. Declaração sem par vai à conferência do fim.

   Junte ao de-para as trocas de nome que o registro traz. Se o mesmo nome velho já tem
   outro destino lá, não escolha: o par vai ao dono no passo 6, e as unidades seguintes
   recebem o de-para sem esse nome até ele decidir.

5. Confira os documentos novos da unidade pela parte «Antes de gravar» da
   [conferência](conferencia.md), que começa pela conferência de nomes. Caminho repetido
   não se resolve por ordem de chegada: nenhum dos dois segue, e o par vai à conferência
   do fim.

6. Leve as decisões ao dono. A mensagem tem duas partes e nada mais:

   - a lista numerada, uma linha por documento velho, na forma «N - documento -
     decisão», com a destinação, a entidade, o caminho novo e o evento da faixa que ele
     serve, ou a revisão para onde ele vai. A lista vem agrupada pelos eventos da faixa,
     na ordem dela, com um grupo final do que não toca evento. A linha diz quando a
     entidade escolhida é provisória no catálogo, como guia e ciclo. Quando o documento pede
     uma ligação que a entidade não declara, a linha traz também a ligação: a
     entidade de origem, o tipo, a de destino e quantas cabem de cada lado. Vale o mesmo
     quando nenhuma entidade ou nenhum tipo de ligação encaixa: a linha traz a entidade ou
     a ligação nova proposta, com origem, destino, quantas cabem de cada lado, quantos
     documentos do recorte pedem o mesmo nome e o encaixe mais próximo ao lado. Ela só
     entra no catálogo com o sim do dono, pelo passo 8. As trocas novas do de-para e os nomes
     com dois destinos entram na lista como itens próprios;
   - um parágrafo sem jargão que explica as decisões em português comum.

   Vá devagar: um assunto por turno, sem empilhar próximo passo nem pedir outra escolha
   junto. Ponha as unidades da lista com o dono no andamento e espere a resposta.

7. Siga pela resposta do dono, item a item. A decisão aprovada passa ao passo 8. A
   decisão que ele corrige volta ao sub-agente com a correção no bloco da unidade e passa
   de novo pelos passos 4 a 6. A troca de revisão aprovada tira a unidade do recorte e
   fica no andamento, com a revisão de destino. A troca de nome aprovada fica no de-para e vai às unidades
   que ainda não rodaram.

8. Copie os documentos novos da unidade aprovada para a pasta da entidade na árvore e
   commite em main. Na linha de skill, o mesmo commit leva o gatilho em
   `instancias/gatilho/<slug>.md` e a cópia em `platafirma-harness@skills/<slug>/`, com o mesmo
   corpo no SKILL.md e os arquivos de apoio no caminho relativo que a skill lê.

   Se a decisão aprovada traz ligação nova, grave antes a alteração da classe pela olaria
   (`infra rodar ontologia -- trocar shape <slug> <versao>`), com o tipo, a classe de destino e o mínimo e o máximo que o dono
   aprovou. Só então passe ao passo 9: o banco recusa a
   ligação que a classe ainda não declara com essa classe ou essa quantidade.

9. Grave a ficha de cada documento novo pelo carregador do schema casa, chamado com o
   caminho dele em main (`infra rodar casa -- documento <caminho> --apply`), e nunca por
   INSERT escrito na fita. A instância de entidade lida em projeção não tem documento,
   como cada viés do gabarito de vieses: grave a ficha dela com
   `infra rodar casa -- ficha criar <entidade> <chave> --apply`. A ficha que o dono mandar
   apagar sai com `infra rodar casa -- ficha apagar <entidade> <chave> --apply`. Entram a
   ficha, o arquivo e as ligações que apontam uma chave já no banco. A ligação que aponta
   outro documento da story espera o passo 10, e a pendente fica no registro. Você grava o
   estado: o de nascimento que a tabela de transições dá, quando a entidade tem ciclo de
   vida, e nulo nas outras. Se o portão do carregador recusar, corrija pelo nome da regra
   que ele deu, com novo commit, e grave de novo. A recusa `ligacao_sem_assinatura`,
   `ligacao_destino_fora_da_assinatura`, `ligacao_acima_do_maximo` ou
   `ligacao_acima_do_maximo_inverso` quer dizer que a ligação contraria o catálogo ou não
   está nela: ela volta ao dono pelo passo 6, e não se contorna. Guarde o relatório do
   portão na fita.

   Ponha a unidade como gravada no andamento.

10. Quando a última unidade estiver gravada, grave as ligações entre documentos da story,
    que agora têm ficha, e rode a parte «No fim do recorte» da conferência.

11. Leve ao dono, na forma do passo 6, o que a conferência do fim não resolveu e as
    unidades que só ele destrava. Ele escolhe o que abre e quando, e a lista não tem
    ordem.

12. Quando o dono devolver um documento com pedido de conserto, corrija por novo commit
    em main, passe o documento de novo pela conferência de nomes e atualize a ficha pelo
    carregador.

## Como se confere

A revisão está pronta para o dono homologar quando:

- toda unidade gravada teve a decisão vista e aprovada pelo dono antes do commit;
- todo nome da casa nos documentos gravados passou por `conferir existe entidade`, rodado
  por você;
- o andamento não tem unidade pendente, em curso, com o dono, aprovada ou falhou;
- o de-para não tem nome velho com dois destinos;
- a conferência do fim passou: o conjunto de caminhos fecha nos dois sentidos, o
  relatório do portão tem zero recusas e o lint nos caminhos da story tem zero
  apontamentos.

O dono homologa na entrega da story, documento a documento. Revisão sem o sim dele em
todos os documentos não está homologada.
