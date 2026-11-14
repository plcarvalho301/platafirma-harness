# Busca

Entidade: chapeu

## Espaço de problema

- O trecho certo estava no índice, e em que posição da lista ele ficou?
- No corte, o teto do trecho sai da janela do modelo de embedding, e o corte foi revisto quando o modelo trocou?
- Na similaridade, os embeddings aproximam o que a pergunta quer dizer, ou só o que ela repete? A recuperação densa perde o termo raro, e a recuperação semântica pede o braço de palavra exata ao lado.
- Na lista, a fusão recíproca de rankings junta os braços com que peso, e o ranqueamento multiestágio, com o revisor (o rerank) no fim, paga a latência que custa? A interação tardia fica entre os dois.
- No grafo, a pergunta se responde melhor por linguagem de consulta de grafo sobre o RDF da casa do que por vetor? O Graph RAG vale quando a resposta está na ligação entre trechos, e não num trecho só.
- No vocabulário, a recuperação guiada por ontologia expande a pergunta pelo vocabulário controlado, e a expansão traz o conceito vizinho ou traz ruído?
- Na cobertura, o que o motor declara bate com o que o índice tem, e a estimativa de cobertura por não vistos diz quanto ficou de fora?
- Na máquina, o orcamento de VRAM cabe o modelo de embedding e o revisor juntos, e a quantização paga a degradacao por quantizacao que traz? Placa de vídeo parada com o modelo rodando no processador é o primeiro lugar a olhar.
- No código, o gargalo é de algoritmo ou de estrutura de dados, achado por análise de desempenho antes de qualquer ajuste fino em python?
- No gabarito (as perguntas de resposta conhecida), a relevância graduada foi marcada por gente, o juiz das rodadas foi conferido contra ela, e alguma pergunta vazou para o ajuste?

## Régua de resposta

Resposta boa sai em diferença contra o que está servido, sobre a mesma versão do gabarito, com o ajuste a mudar e o que ele custa em latência e em VRAM. Resposta ruim é número absoluto sem comparação, medida que não termina em ajuste, ou culpa posta no corpus com o trecho certo no índice e fora do topo.

Troca de corte, de modelo de embedding ou de revisor invalida a medida anterior: a rodada nova se compara sobre o mesmo gabarito.

## Consulta dirigida

- O trecho certo não veio ao topo: Pretrained Transformers for Text Ranking, de Lin, Nogueira e Yates, traz o ranqueamento multiestágio e o revisor.
- Que modelo de embedding serve a português e a trecho longo: o artigo do M3-Embedding traz a recuperação densa, a esparsa e a interação tardia no mesmo modelo.
- Montar ou consertar o pipeline RAG de ponta a ponta: A Simple Guide to Retrieval Augmented Generation, de Kimothi, e o LLM Engineer's Handbook, de Iusztin e Labonne.
- Expandir a pergunta e medir a lista à moda clássica: Introduction to Information Retrieval.
- Quando o grafo responde melhor que o vetor: RAG vs. GraphRAG: A Systematic Evaluation and Key Insights; para a recuperação guiada por ontologia, o OG-RAG.
- Escrever a consulta ao grafo: Semantic Web for the Working Ontologist, capítulo 6, para SPARQL, e a documentação do Owlready2 para rodá-la em python.
- O vocabulário controlado dentro da busca: a ANSI/NISO Z39.19, seção 5.3.6.
- Rodar o modelo na placa de vídeo: AI Engineering, de Huyen, capítulo 9, para os aceleradores, e o LLM Engineer's Handbook para a quantização. CUDA ainda não é conceito no tesauro, e a busca por ele volta só essas duas.
- O que a quantização tira do modelo: Quantize with Confidence?, medido em geração de código.
- Marcar o gabarito e decidir a rodada: o protocolo-medicao-rag, da casa, fixa estrato, tamanho e regra de decisão antes de medir.

## Rótulos de busca

- rótulos: pipeline RAG · embeddings · modelo de embedding · recuperação densa · recuperação semântica · interação tardia · ranqueamento multiestágio · fusão recíproca de rankings · relevância graduada · recuperacao contextual · Graph RAG · grafo de conhecimento · PageRank personalizado · detecção de comunidades · recuperação guiada por ontologia · vocabulário controlado · problema do vocabulário · linguagem de consulta de grafo · RDF · banco de dados de grafo · raciocinador · estimativa de cobertura por não vistos · degradacao declarada · RAG antes de fine-tuning · pesos do modelo · rede neural · LoRA e QLoRA · quantização · degradacao por quantizacao · orcamento de VRAM · OCR · extração de dados · estruturação de dados · python · algoritmo · estrutura de dados · complexidade assintotica · análise de desempenho · juiz-modelo · validade de construto · calibragem de confianca · vazamento de dados em avaliação · reserva cega
- recorte de domínio: ia · estudos-ontologias · engenharia-software
- homônimos: busca, que na capacidade de mesmo nome é o ato de procurar e de parar, matéria do chapéu orquestracao · avaliação, que no design é a avaliação heurística
