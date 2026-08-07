**Definição** (transcrita da fonte [6], ABNT NBR ISO/IEC 27002:2005, seção 11.2.2 "Gerenciamento de privilégios"):

Gestão de acesso privilegiado é a disciplina que restringe e controla a concessão e o uso de privilégios — direitos de acesso que ultrapassam os de um usuário comum, como os de administrador de sistema, banco de dados ou aplicação. A norma prescreve, entre outros pontos:

- identificar o privilégio de acesso associado a cada produto de sistema (SO, SGBD, aplicação) e as categorias de usuário que dele precisam;
- conceder privilégios apenas conforme a necessidade de uso, com base em eventos e alinhados à política de controle de acesso — "requisitos mínimos para sua função somente quando necessário";
- manter um processo de autorização formal e um registro de todos os privilégios concedidos, sem liberá-los antes de esse processo estar concluído;
- incentivar rotinas e programas de sistema que dispensem a necessidade de conceder privilégios a usuários;
- atribuir os privilégios a um ID de usuário diferente do usado normalmente para atividades de negócio.

A fonte [6] também registra, em trecho cortado no fim do excerto, que "o uso inapropriado de privilégios de administrador de sistemas" é tratado como fator de risco relevante — mas o texto que chegou não continua além desse ponto, então não sei o que a norma diz na sequência.

**De onde sai**: ABNT NBR ISO/IEC 27002:2005, seção 11 "Controle de acessos" › 11.2 "Gerenciamento de acesso do usuário" › 11.2.2 "Gerenciamento de privilégios" (fonte [6]).

**Complementos do mesmo acervo**:

- A análise crítica periódica desses direitos é tratada à parte, na 11.2.4: "autorizações para direitos de acesso privilegiado especial (ver 11.2.2) sejam analisadas criticamente em intervalos mais frequentes, por exemplo, em um período de três meses" — mais curto que a revisão geral de acesso de usuários (seis meses) — transcrito da fonte [7], mesma norma, seção 11.2.4.
- A fonte [1] (seção 11.2, objetivo geral) situa isso dentro do ciclo de vida de acesso do usuário, com "atenção especial [...] para a necessidade de controlar a distribuição de direitos de acesso privilegiado que permitem os usuários mudar controles de sistemas" — transcrito.
- A fonte [2] (ABNT NBR ISO/IEC 27701:2019, 6.6.2.3, mesmo título "Gerenciamento de direitos de acesso privilegiado") apenas remete ao controle da ISO/IEC 27002:2013, 9.2.3, sem trazer conteúdo próprio no trecho recebido — não sustenta afirmação adicional.
- A fonte [3] (guia de gestão de identidades e acessos, não específico de privilégio) trata do tema mais amplo de IAM e do princípio do menor privilégio (PoLP) como resposta ao risco de "gestão inadequada de permissões" — é conceito vizinho (IAM geral), não o mesmo recorte de "gestão de acesso privilegiado" da 27002, mas ajuda a contextualizar o princípio que sustenta essa prática.

A fonte [5] (ISO/IEC 27002:2013 em inglês, seção 9.2) e a fonte [8] (resumo de capítulo de livro didático) não trazem, nos trechos recebidos, conteúdo específico sobre gestão de acesso privilegiado — [5] corta antes do item 9.2.3 (que seria o correspondente em inglês) e [8] é só um resumo sem definição.
