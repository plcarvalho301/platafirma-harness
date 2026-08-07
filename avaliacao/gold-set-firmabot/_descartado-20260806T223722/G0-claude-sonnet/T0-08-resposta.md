## Definição

**Criptografia Pós-Quântica (PQC)** é o conjunto de algoritmos criptográficos que se acredita permanecerem seguros mesmo diante do poder de processamento de computadores quânticos — ela é a defesa primária contra a ameaça que a computação quântica representa aos esquemas criptográficos atuais.

*Transcrito de:* Ameaça da Computação Quântica e a Transição para a Criptografia Pós-Quântica: Relatório Executivo de Segurança › Criptografia Pós-Quântica (PQC) e Mitigação [1].

## Por que ela existe (contexto/motivação)

A necessidade da PQC decorre de uma ameaça concreta e nomeada: o **Algoritmo de Shor**, executável em computador quântico, quebra a criptografia assimétrica hoje em uso (RSA, baseado em fatoração de números grandes, e ECC/curvas elípticas, baseado em logaritmo discreto). Já o **Algoritmo de Grover** ataca a criptografia simétrica, exigindo dobrar o tamanho de chave (ex.: AES-256) para manter o nível de segurança atual.

*Transcrito/derivado de:* OSIC 15/24 › 3.2 Desafios da Computação Quântica para a Segurança da Informação e a Cibersegurança › 3.2.1 Quebra da criptografia assimétrica [4]; e Relatório Executivo — A Transição para a Criptografia Pós-Quântica (PQC) e a Proteção das Infraestruturas Críticas no Brasil › 1. Ameaça e Contexto Estratégico [8].

## Como ela é construída tecnicamente

A PQC não é uma única técnica, mas uma família de abordagens matemáticas alternativas às que o Algoritmo de Shor quebra. As soluções mais citadas nas fontes são:

- **Criptografia baseada em reticulados** (*lattice-based cryptography*);
- **Assinaturas baseadas em hash** (*hash-based signatures*), nas variantes stateless e stateful.

O NIST já publicou padrões nesses moldes.

*Transcrito de:* OSIC 15/24 › 3.2.1 Quebra da criptografia assimétrica [4].

## Observação sobre estratégia de adoção

Vale registrar que as fontes falam também de uma estratégia de transição — não de definição do conceito em si — chamada **criptografia híbrida** (combinar PQC com criptografia clássica), citada como caminho recomendado para mitigar o risco de "Harvest Now, Decrypt Later" (dados interceptados hoje e guardados para descriptografia futura). Isso aparece em três fontes distintas [3][5][7], mas é estratégia de implantação, não a definição do que é PQC — trago aqui só como complemento, não como parte da definição.