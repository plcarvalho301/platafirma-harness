Trunk-based development é a prática de mesclar código continuamente no trunk (branch principal), evitando feature branches de vida longa [2][6]. É considerada complementar à integração contínua e demonstra, ao longo de anos de pesquisa, acelerar a velocidade de entrega de software [2].

**Definição e mecânica**

A prática consiste em todos os desenvolvedores fazerem check-in na mesma "trunk" do código-fonte; para evitar que mudanças incompletas afetem outros, usam-se técnicas como feature flags para "esconder" trabalho não finalizado [6]. Isso se opõe ao feature branching, em que o trabalho isolado em branches atrasa a integração e gera merges mais complexos quando finalmente ocorrem [6].

**Evidências de impacto no desempenho**

A pesquisa da Accelerate mostrou que desenvolver a partir do trunk/master, em vez de branches de longa duração, correlaciona-se com maior desempenho de entrega de software [7]. Times de melhor desempenho apresentavam: menos de três branches ativos a qualquer momento, branches com vida muito curta (menos de um dia) antes de serem mescladas ao trunk, e nunca tinham períodos de "code freeze" ou estabilização [7]. Esses resultados são independentes de tamanho de time, tamanho de organização ou indústria [7].

O relatório de 2017 confirma achados similares: mesclar código no trunk diariamente, branches ou forks com vida muito curta (menos de um dia), e menos de três branches ativos contribuem para maior desempenho de entrega [5]. Times sem períodos de "code lock" também apresentaram desempenho superior [5].

**Contraponto ao GitHub Flow**

Apesar das evidências, alguns desenvolvedores acostumados ao workflow recomendado pelo GitHub — que depende fortemente de desenvolvimento em branches com merges periódicos ao trunk — permanecem céticos [5][7]. A pesquisa argumenta que trabalhar em branches curtas, mescladas ao trunk pelo menos diariamente, é consistente com práticas de integração contínua amplamente aceitas [5][7].

**Papel da experiência (achado de 2022)**

O relatório de 2022 aponta que a experiência do profissional importa na implementação: indivíduos com 16+ anos de experiência que usam trunk-based development percebem os benefícios da prática — maior desempenho geral de entrega, menos trabalho não planejado, menos propensão a erros e menor taxa de falha em mudanças [2]. Já profissionais com menos experiência tendem a ver resultados menos positivos, incluindo desempenho geral de entrega reduzido [2]. Isso é atribuído às práticas adicionais necessárias para implementar a técnica com sucesso — como regras rigorosas contra deixar o trunk quebrado sem correção e uso de gated code branches com rollback automático quando o trunk quebra [2].

**Posição no conjunto de capacidades técnicas DevOps**

O relatório DORA de 2021 lista trunk-based development como uma das capacidades técnicas medidas, ao lado de arquitetura fracamente acoplada, testes contínuos e integração contínua [8].
