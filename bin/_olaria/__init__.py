"""O verbo `ontologia` (e a variante `olaria`) da porta (cards #4214 e #4254; referencias/instancias/verbo/ontologia.md).

É a porta da cadeira para o serviço de escrita da Olaria: recebe o ato e o YAML, chama o serviço por HTTP e devolve o resultado
como saída de verbo. Só usa a biblioteca padrão, não abre o banco e não importa o pacote `olaria`.

- `cliente.py`: o ambiente, o prazo, o id da fornada e as cinco chamadas ao serviço;
- `saida.py`: a tradução da resposta em texto e em código de saída;
- `ajuda.py`: a usage, os códigos de saída e a ajuda dos campos, que vem do serviço;
- `__main__.py`: a leitura dos argumentos e o despacho dos cinco atos.
"""
