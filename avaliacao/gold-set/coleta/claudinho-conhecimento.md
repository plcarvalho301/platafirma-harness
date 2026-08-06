# Itens 1-10: próprios. Tipo declarado pela cadeira em 03/08 16:30.

1. Qual o procedimento passo a passo do e-ARQ Brasil para definir prazo de retenção e destinação de um documento arquivístico digital?
   tipo: simples
   esperada: e-ARQ Brasil

2. Quais são os requisitos formais que a ABNT/ISO impõe para que um vocabulário controlado seja considerado tesauro (relações BT/NT/RT, notas de escopo, forma de entrada)?
   tipo: simples
   esperada: z39-19-2005r2010

3. Como se declara em SKOS a diferença entre skos:broader e skos:broaderTransitive, e quando usar cada um num esquema de conceitos?
   tipo: simples
   esperada: SKOS

4. Qual a convenção da ISAD(G) para descrição multinível de um fundo — o que é obrigatório em cada nível e o que não pode se repetir entre níveis?
   tipo: simples
   esperada: nenhuma — seria ISAD(G) (Conselho Internacional de Arquivos) ou NOBRADE

5. Quais os critérios do BFO para decidir se uma entidade é continuant ou occurrent, e como isso se traduz em regra prática de modelagem de classe?
   tipo: simples
   esperada: Building_Ontologies_with_Basic_Formal_On

6. Se a teia de conceitos mostra dois conceitos com coocorrência muito acima do esperado no modelo nulo, quando isso justifica fusão dos conceitos, quando justifica criar um conceito-pai, e quando é só artefato da curadoria de 3 conceitos por obra?
   tipo: complexa
   esperada: nenhuma — seria obra de ciência de redes com modelos nulos (ex.: Newman, Networks: An Introduction)

7. Um domínio do acervo com poucas obras mas alta centralidade na projeção do grafo — isso indica domínio estruturante que merece investimento de curadoria, ou distorção estatística do corpus pequeno? Que evidência de fora da ontologia (aquisição, uso, RAG) precisaria entrar na decisão?
   tipo: complexa
   esperada: nenhuma

8. Onde termina a competência do vocabulário canônico e começa a do modelo de embeddings: quando um par de termos que a ontologia distingue mas o espaço vetorial não separa é problema de vocabulário, e quando é problema de modelo?
   tipo: complexa
   esperada: Fichamento: O contrato do espaço vetorial

9. Anti-padrões ontológicos tipo os de Sales & Guizzardi (ex.: relação entre tipos que deveria ser entre instâncias) — quais deles são detectáveis mecanicamente num esquema Cargo/SQL como o nosso, e quais exigem juízo humano por dependerem de intenção de modelagem?
   tipo: complexa
   esperada: Ontological anti-patterns: Empirically uncovered error-prone structures in ontology-driven conceptual models

10. Ao classificar obra normativa que foi revogada mas é citada por obras vigentes do acervo, o compromisso ontológico correto é registrá-la como espécie própria, como estado do ciclo de vida, ou como relação entre obras — e o que cada escolha custa para o RAG e para a recuperação arquivística?
   tipo: complexa
   esperada: The Intellectual Foundation of Information Organization -- Svenonius, Elaine -- Digital libraries and electronic publishing, 1st MIT Press -- The MIT -- isbn13 9780262194334 -- 0c56bc153bf168d2e0e0a9698fa463e1 -- Anna's Archive

# nenhuma (1-10): 3 (itens 4, 6, 7)

# Itens 11-20: OSINT, extensão da cadeira. Tipo já vinha no anexo enviado.

11. Qual sequência de ferramentas recupera a camada de texto de um PDF escaneado em alfabeto cirílico com xref corrompido, e em que ordem qpdf, gs e ocrmypdf entram sem destruir o metadado original?
   tipo: simples
   esperada: nenhuma — seria Developing with PDF (Rosenthol, O'Reilly)

12. Quais campos o padrão WARC 1.1 exige num registro de tipo `response` para que a captura valha como prova de que a página existia naquele conteúdo naquela hora?
   tipo: simples
   esperada: nenhuma — seria ISO 28500 (WARC 1.1)

13. Como o Tesseract decide segmentação de página (PSM) e qual modo usar para documento em coluna dupla com tabela embutida?
   tipo: simples
   esperada: nenhuma — seria documentação oficial do Tesseract

14. Que diretivas do robots.txt o Protego reconhece além de Allow/Disallow, e como ele resolve conflito entre regras de comprimento igual?
   tipo: simples
   esperada: nenhuma — seria documentação/fonte do Protego (Scrapy) e RFC 9309

15. Qual a diferença estrutural entre o content stream de um PDF "nato-digital" e um gerado por impressão virtual, e como isso afeta a extração de tabelas com pdfplumber?
   tipo: simples
   esperada: nenhuma — seria Developing with PDF (Rosenthol, O'Reilly)

16. Dado um corpus de normas técnicas em três idiomas com títulos transliterados de forma inconsistente, como desenhar um pipeline de deduplicação que combine normalização Unicode, transliteração reversa e casamento fuzzy sem colapsar normas distintas da mesma família?
   tipo: complexa
   esperada: Ontology Matching   [casamento parcial — dono flagou: cobre a caixa de ferramentas de string-matching, não o desenho do pipeline com transliteração]

17. Ao propor um esquema de classificação para um fundo documental misto (código, ata, norma, fichamento), onde termina o princípio arquivístico da proveniência e começa a ontologia formal — e quando os dois entram em contradição direta, qual cede?
   tipo: complexa
   esperada: nenhuma

18. Agregar registros públicos dispersos sobre uma organização cria um dado novo que nenhuma fonte individual continha: em que ponto essa síntese muda o regime jurídico do tratamento, e como documentar a procedência de uma inferência que não está escrita em lugar nenhum?
   tipo: complexa
   esperada: nenhuma — seria obra sobre efeito mosaico/agregação (ex.: Solove, Understanding Privacy)

19. Um site serve conteúdo diferente conforme fingerprint do cliente (cloaking): como desenhar uma captura que registre as variantes com valor probatório, sem cruzar a linha da não-atribuição declarada — e o que fazer quando as duas exigências se contradizem?
   tipo: complexa
   esperada: nenhuma

20. Para estimar a completude de uma coleta contra um universo desconhecido (quantos documentos existem que eu não achei), que métodos de captura-recaptura ou estimativa de cauda se transferem da ecologia e da bibliometria para OSINT documental, e quais premissas quebram na transferência?
   tipo: complexa
   esperada: nenhuma — seria literatura de captura-recaptura (ex.: estimadores de Chao)

# nenhuma (11-20): 9 (itens 11,12,13,14,15,17,18,19,20)
# nenhuma (total 1-20): 12

# achado lateral (fora do gabarito, decisão fora do meu recorte):
# corpus de ferramental da osint (Developing with PDF, Practical Web Scraping, Mastering Regular Expressions e
# afins) mora em /mnt/project/ da claudinha-osint, fora do índice do acervo. Se entra no acervo indexado ou
# fica onde está é decisão do Pedro com claudinha-osint — não decido, só nomeio.
