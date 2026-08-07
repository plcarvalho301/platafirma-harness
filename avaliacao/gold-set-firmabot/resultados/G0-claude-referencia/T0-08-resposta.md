Criptografia pós-quântica (PQC) é o conjunto de algoritmos matemáticos desenvolvidos para permanecer seguros mesmo diante do poder de processamento de computadores quânticos, funcionando como defesa primária contra a ameaça quântica [1].

Sua necessidade surge porque algoritmos quânticos — como o Algoritmo de Shor — conseguem quebrar sistemas de criptografia assimétrica atuais (RSA e ECC), que dependem da dificuldade de fatoração de grandes números ou do logaritmo discreto [4][8]. Já o Algoritmo de Grover impacta a criptografia simétrica, exigindo o dobro do tamanho de chaves (ex.: AES-256) para manter o nível de segurança [8].

Entre as abordagens técnicas de PQC estão a criptografia baseada em reticulados (lattice-based) e as assinaturas baseadas em hash (hash-based), sendo que o NIST divulgou padrões nessas categorias [4]. Um exemplo prático dessa família é o CRYSTALS-Kyber, algoritmo lattice-based avaliado em integração híbrida com o protocolo Matrix para acordo de chaves [7].

A urgência da adoção é reforçada pela ameaça "Harvest Now, Decrypt Later" (HNDL/SNDL) — ou descriptografia retrospectiva —, em que adversários armazenam hoje dados cifrados classicamente para descriptografá-los assim que dispuserem de computação quântica capaz disso [8].

A estratégia recomendada não é a substituição pura, mas a criptografia híbrida, combinando segurança clássica com PQC, para mitigar esse risco de descriptografia futura [5]. No caso brasileiro, essa transição é tratada como imperativo de soberania digital e de financiamento contínuo de Defesa, sob uma abordagem "Quantum-Safe-by-Design" [3].

Por fim, distingue-se da criptografia quântica propriamente dita (como a distribuição quântica de chaves, QKD): a PQC é apontada como solução necessária de curto prazo, enquanto a QKD é vista como tecnologia de mais longo prazo [6].
