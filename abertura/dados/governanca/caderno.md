# caderno dados/governança

## Régua

- **Catálogo é a fonte; derivado e migração aplicada não são lugar de corrigir.** Valor de catálogo errado se conserta por UPDATE na fonte, mais migração nova para banco novo nascer certo. Migração já rodada é história e não se edita; export se regenera, não se digita. O teste: se eu editar aqui e alguém rodar o gerador, minha edição some? Então não era aqui.
- **Proteger conteúdo publicado exige saber onde o controle de acesso acaba.** Esvaziar a página corrente só protege se histórico, diff, API e export também tiverem grão. Enquanto a dívida do hook estiver aberta, o que protege é a instância inteira, e todo resíduo segue legível por quem alcança a superfície. A pergunta antes de qualquer expurgo de superfície: por quantas portas esse conteúdo ainda sai?
- **Antes de apagar rastro, medir quem depende dele.** Rastro removido é auditoria perdida de quem citava aquela versão. A dependência se mede — quem indexou, quem aponta —, não se presume em nenhum dos dois sentidos: nem "ninguém usa", nem "alguém pode vir a usar".
- **Branch com commit próprio não prova trabalho que falta em main.** Prova só que divergiu. O que decide mesclar ou descartar é o diff no sentido inverso: branch contra main vindo com deleção significa que a branch é a velha, e mesclar regride. Trabalho chega em main por outro caminho, com outro card e outro nome de arquivo.

## Diário de bordo

2026-09-22 — `mesa item 4` para LER o item 4, exit 2 "--ato e --alvo sao obrigatorios" — `mesa item` CRIA item, não lê; a leitura é `mesa ver`, que já vem no pacote de abertura. Contorno na data: usar o que a abertura já serviu.

2026-09-22 — `acervo ler arq:0110` → "particao desconhecida"; com `casa` → "faltam argumentos"; `acervo ler casa spec spec_acervo` → exit 1, e o título com parênteses também falhou. A forma é `acervo ler casa <especie> <seletor>` e o seletor de spec é o título, não o nome do arquivo. Contorno na data: `repo ler platafirma-arquitetura docs/spec_acervo.md`, que a própria linha `vizinho:` do exit 1 sugeria.

2026-09-22 — `acervo psql` com `\i /caminho.sql` no stdin: exit 0, mas stderr "No such file or directory" — o psql roda noutro contêiner e não enxerga a bancada. Contorno na data: mandar o corpo do SQL inteiro por stdin. Exit 0 com erro em stderr é leitura muda (Q6 de arq:0110).

2026-09-22 — `exportar-acervo` pela porta: recusado, "sem verbo", `sugestao: null`. Nenhum verbo servido cobre a regeneração do export do acervo; por arq:0110 §8 isso é card de verbo novo por construção. O `bin/curar` standalone o chamava por subprocess, o que Q8 reprova. Contorno na data: nenhum — export fica desatualizado, declarado como pendência no PR #22.

2026-09-22 — `write_file` em `.jsonl`: recusado, tipo fora da lista. Resolveu a dúvida que eu estava ponderando (antecipar o derivado à mão): não dá, e não devia. Contorno na data: nenhum necessário, a recusa era a resposta certa.

2026-09-22 — `repo commitar` em conhecimento: exit 1, "a sessão não tocou platafirma-conhecimento", com o arquivo escrito e legível por `read_file`. Causa: escrevi em `AI/platafirma-conhecimento` (clone principal, parado noutro ramo) e o `repo` opera em `AI/wt/<repo>/<cadeira>`. O aviso de fallback só aparece quando o worktree NÃO existe — existindo, o `repo` vai para lá calado. Contorno na data: `repo git <repo> rev-parse --show-toplevel` antes de escrever, e escrever no caminho que ele devolve.

2026-09-22 — 502 da Cloudflare no meio de um `acervo psql`. Reenviei a MESMA consulta e a poda respondeu "igual ao giro 60 — 154 bytes não reenviados": o ledger de dedup considerou servido um retorno que nunca chegou a mim. Contorno na data: variar a consulta (acrescentei uma coluna-marca) para forçar sha novo. Vale para qualquer retorno perdido em falha de transporte.
