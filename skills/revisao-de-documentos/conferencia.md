# Conferência da revisão

A conferência roda em dois momentos: antes de gravar cada unidade, e no fim do recorte.
Quem roda é a orquestradora, sobre os registros e a árvore.

## Antes de gravar

Sobre cada unidade decidida, antes de levá-la ao dono:

| confira | se falhar |
|---|---|
| cada nome da casa nos documentos novos, no caminho, no cabeçalho, nas ligações e na entidade do registro está no catálogo (`infra rodar ontologia -- ler shape <classe>`), conferida por você e não lida da lista termos | delegue a unidade de novo, com o nome e a saída que ele teve |
| todo nome que você conferiu está na lista termos do registro, com a mesma saída | delegue de novo, com o nome que faltou ou divergiu |
| o registro tem os campos que o estado e a destinação pedem | delegue a unidade de novo, com o campo que faltou |
| nenhum caminho novo se repete entre unidades nem já existe em main | não grave nenhum dos dois; o par vai ao fim do recorte |
| o caminho é o da entidade escolhida no catálogo (`golden` ou `referencia`) | delegue de novo, com o apontamento |
| no partido, toda parte que não fica com a linha tem cinde-de para a que fica | delegue de novo, com o apontamento |
| a seção obrigatória da entidade está no texto (no gatilho, O que aciona) | delegue de novo, com o apontamento |
| o lint da árvore, rodado só nos caminhos desta unidade com o comando do Plano, dá zero apontamentos | corrija o apontamento no documento e rode de novo |

No corpo de observação, o nome sem encaixe fica como está e só precisa estar na lista
termos. Saída 2 da conferência não reprova nem aprova: confira de novo quando a fonte
voltar.

Aprovada, a unidade segue para o dono, e só vai ao commit depois do sim dele. O lint não
se roda na árvore inteira, porque herda o que outras revisões deixaram.

## No fim do recorte

Quando a última unidade estiver gravada:

1. Confira o conjunto. Os caminhos que a story criou em main são iguais, nos dois
   sentidos, aos caminhos das fichas que o carregador gravou. Documento em main sem ficha,
   ou ficha sem documento em main, reprova.
2. Confira a carga. O relatório do portão guardado na fita tem zero recusas e zero avisos
   de ficha sem arquivo.
3. Confira os nomes de novo, em lote, sobre os documentos da story em main: a
   ontologia pode ter mudado enquanto a revisão corria. Nome que deixou de existir volta
   ao passo da skill que o gravou.
4. Liste o que fica com o dono, sem ordem:
   - duas unidades com entidades diferentes para a mesma matéria, inclusive quando uma
     entidade é mãe da outra;
   - o mesmo nome velho com dois destinos no de-para;
   - fusão declarada sem par;
   - caminho disputado por duas unidades;
   - unidade não decidida pelo que só o dono sabe;
   - ligações pendentes, com o destino em texto, para a revisão que tiver a ficha.

Conjunto, carga e nomes aprovados, a revisão vai ao dono com a lista. Reprovado, corrija
pelo passo da skill que falhou e confira de novo.
