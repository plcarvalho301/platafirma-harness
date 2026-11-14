# Cripto

Entidade: chapeu

## Espaço de problema

- A primitiva é padrão ou inventada, a chave tem custódia e ciclo definidos, e o sigilo precisa durar mais do que o algoritmo aguenta?
- A primitiva criptográfica é padrão, revisada e com implementação validada?
- A chave tem ciclo do nascimento à morte (geração, distribuição, uso, rotação, expiração, destruição), com criptoperíodo definido?
- Onde a chave mora: num módulo criptográfico, de onde não sai em claro, e que serviço distribui, rotaciona e revoga?
- Por quanto tempo o dado precisa ficar secreto (vida útil do sigilo), e o algoritmo cai antes? Dado interceptado hoje e guardado é decifrado depois.
- A transição PQC é urgente para este dado?
- O sistema troca de primitiva sem ser refeito (agilidade criptográfica)?
- O segredo está fora do repositório e entra no que roda sem vazar (gestão de segredo)?
- Quando o segredo aparece numa saída, numa fita ou num chat, ele é declarado exposto e trocado, e a sessão que ele abria cai?
- A informação pede algoritmo de estado?

## Régua de resposta

Resposta boa exige primitiva padrão e recusa a caseira, define ciclo e custódia antes de aceitar o desenho, pesa a vida útil do sigilo contra a do algoritmo, e projeta a troca.

Resposta ruim valida a primitiva pela aparência de força, aceita chave sem ciclo, como «está num arquivo protegido», protege só para hoje, ou amarra o sistema a uma primitiva.

## Consulta dirigida

- Ciclo de vida e estados da chave: NIST SP 800-57, na parte 1.
- Algoritmos e tamanhos de chave em transição: NIST SP 800-131A.
- Gestão de chaves na prática: Anderson, Security Engineering.
- Transição pós-quântica no Brasil: o Relatório Executivo sobre a estratégia de transição PQC e soberania digital, e a Consolidação de Matrizes PQC.
- Serviço de gestão de chaves não tem conceito próprio no acervo; a busca vai por gestão de chaves e módulo criptográfico.

## Rótulos de busca

- rótulos: primitiva criptográfica · criptografia · módulo criptográfico · algoritmo de estado · gestão de chaves · criptoperíodo · rotação de credencial · raiz de confiança · cadeia de confiança · vida útil do sigilo · transição PQC · agilidade criptográfica · gestão de segredo · segredo em repositório · injeção de segredo em implantação · cifra fim a fim
- recorte de domínio: seguranca-privacidade · engenharia-software
- homônimos: chave, que neste ramo é a chave criptográfica, e não a chave de um documento da casa · segredo, que é o material sensível custodiado, e não o grau de sigilo da informação
