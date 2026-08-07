# Descartado — terceira corrida concorrente

Tres runners na mesma GPU e nos mesmos diretorios entre 21:06 e 21:20:
g0-geracao.service, _serie_g0.sh e _serie_limpa.sh. Latencia e tok/s de todos
os arquivos deste lote estao sob contencao. Texto gerado nao e afetado
(temperature=0, seed=42, contexto congelado do G0-rag-base).

Serie refeita uma unica vez, sozinha na GPU, sob flock /tmp/goldset-g0.lock.
