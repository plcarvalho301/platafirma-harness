# Procedência do harness

Todo caminho de execução alcançável por `~/AI/bin` resolve para dentro de
`platafirma-harness` — salvo as exceções declaradas abaixo, cada uma com dono e
motivo. Quem mede é `conferir procedencia`, e o que ele lê é **este arquivo**:
acrescentar linha aqui é o único jeito de calar o predicado, e é por isso que
cada linha carrega de quem é a decisão.

Ausência deste arquivo reprova a conferência. Excepcionar em silêncio, no
código, seria transformar decisão de dono em detalhe de implementação.

## O que o predicado julga

Uma entrada de `~/AI/bin` está **conforme** quando o que ela executa mora no
harness — symlink cujo `readlink -f` cai dentro de
`~/AI/platafirma-harness`. Nome do link diferente do nome do arquivo de destino
não é divergência: alias (`encerrar` → `descansar`, `fila` → `fila_streams.py`)
continua sendo um caminho de execução com origem única.

Está **fora** quando resolve para qualquer outro lugar — outro repo, `~/AI/opt`,
pacote de sistema — ou quando é arquivo comum em vez de symlink, porque cópia
não é forma válida de instalação (`arq:0037`). Fora sem linha aqui reprova.

Link quebrado também reprova: caminho de execução que não chega a lugar nenhum
é ausência, e ausência se declara.

Isto **não** é a régua de `arq:0037` — cabeçalho de três linhas e a conta de um
verbo por capacidade são de `conferir verbo`. Aqui só se pergunta onde o
arquivo executado mora.

## Exceções declaradas

Forma, a mesma de `.conferir-repo` — um nome por linha, dono e motivo no
comentário: `permite: nome` (ou `permite-classe: classe`) seguido de
`# dono: cadeira · motivo: por que não é do harness`. Nome entre `<>` é
ilustração e o predicado o ignora — exemplo de forma não vale como exceção.

Classe conhecida: `binario-de-terceiro` — arquivo comum sem shebang, isto é,
binário compilado que veio do fornecedor. Um verbo da plataforma copiado para
`~/AI/bin` é script, não binário, e portanto **não** é coberto por ela: continua
reprovando, que é o defeito que se quer pegar.

```
permite: nvcc   # dono: claudinho-TI · motivo: CUDA do pacote de sistema (/usr/local/cuda), instalado com privilégio de root — não é construção da plataforma
permite: lynis   # dono: claudinho-seguranca · motivo: terceiro em ~/AI/opt, instalação de fornecedor e não fonte do harness
permite: testssl.sh   # dono: claudinho-seguranca · motivo: terceiro em ~/AI/opt, instalação de fornecedor e não fonte do harness
permite-classe: binario-de-terceiro   # dono: claudinho-TI · motivo: binário baixado do fornecedor, sem fonte neste repo para apontar; o PATH é de TI, o uso de cada ferramenta se manifesta na cadeira que a chama
```

Dono aqui é de quem é a **decisão de manter a exceção**, não quem usa a
ferramenta. Atribuição feita pela fábrica ao lavrar o #396 a partir do que o
card nomeou; corrigir é ato de claudinho-TI, e uma linha basta.

## Verificar

```
conferir procedencia            # 0 = todo caminho declarado; 1 = há divergência
conferir procedencia <nome>     # uma entrada só
conferir procedencia --json     # para quem consome, não para quem lê
```
