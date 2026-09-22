# caderno dados/recuperação

## Endereços canônicos

- Livros a ingerir — pasta canônica no Google Drive: https://drive.google.com/drive/u/0/folders/1k8MlHOkqo3co8nEVJhVUmCdW4xTOsLnW — origem dos lotes de ingestão do acervo.

## Armadilhas e atalhos medidos — ingestão do Drive (2026-09-21)

- **Espelhar com `--drive`, não `--origem`, quando o staging anterior puder estar sujo.** `acervo ingerir obra --drive <url>` cria staging limpo em `~/AI/entrada/drive-<data>-<slug>`. `--origem` reusa `/srv/.../var/entrada/...`; rclone é aditivo, então arquivo apagado do Drive PERMANECE no staging e reaparece na corrida.
- **Timeout da ferramenta ≠ morte do processo.** A tool corta a resposta em 180s, mas o lote segue no servidor e conclui. Dispare UMA vez e monitore por `acervo.lote` / `acervo.impressao` (servindo). Passar `timeout` < 180 na tool MATA o grupo de processo — não faça.
- **Não fatiar por `--ate` re-invocando `acervo ingerir`.** Cada invocação abre um lote e uma impressão nova (veredito `edicao`) → multiplicidade de impressão `em_construcao`. Rode UMA invocação `--ate vetor` e deixe concluir. Se sobrar duplicata, aposente as `em_construcao` das obras do lote (a `servindo` vence). Multiplicidade é normal, não é perda.
- **0 bytes na origem** (sha `e3b0c442…855`, o store dá 400): desde `aeb1845` (conhecimento) o portão `origem` reprova como `ArquivoVazio` sem abortar o lote, e `bin/ingerir` (`d12e6f1`) tem guarda `len>0`. Antes, um 0-byte derrubava o lote inteiro.
- **`UndefinedColumn` ao catalogar** = migração `051_lote_semantico.sql` (coluna `acervo.lote.semantico`, card #3073) não aplicada na instância. Cura: `migrar aplicar rag` com o ALTER. Conferir migração pendente antes de ingerir em ambiente novo.

## A teia: como ler sem concluir errado (2026-09-22)

- **A tabela `conceito_relacao` não é a árvore, e lê-la como tal inverte o diagnóstico.** A hierarquia de navegação mora na coluna `conceito.mais_amplo_id` — um pai por conceito. A tabela guarda só o que a coluna não comporta: segundo pai, lateral dirigida e lateral simétrica (`ont:0085` §2). Medir famílias só na tabela faz a casa parecer quase sem hierarquia quando é o contrário.
- **Lavrar lateral não faz o motor achar mais.** Só `generica`, `partitiva` e `instancia` expandem consulta (`ont:0080` §3). Aresta associativa dá vizinhança, não gênero — subir por ela é o modo de falha caro, `vizinho-plausivel`. Quem pede aresta lateral esperando recall melhor está pedindo a coisa errada.
- **O que decide aresta direta ou laço indireto é o motivo, não a distância no grafo.** `motivo` é obrigatório e tem de caber na frase-molde da família (`ont:0085` §5). Motivo que fecha sem citar o intermediário → aresta direta. Motivo que só fecha citando → são duas arestas, não uma.

## Varredura de branch: o que prova o quê (2026-09-22)

- **`git log origin/main..<branch>` não prova que o trabalho falta em main.** Prova só divergência. O que decide é `git diff <branch> origin/main -- <caminhos>`: vindo deleção, é a branch que está velha e mesclar regride. Trabalho chega em main por outro caminho, com outro card e outro nome de arquivo — três das quatro branches seguradas em 22/09 eram isso.
