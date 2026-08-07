## Gestão de acesso privilegiado

**Definição** (transcrita de [6], ABNT NBR ISO/IEC 27002:2005, 11.2.2 Gerenciamento de privilégios): é a disciplina que restringe e controla a concessão e o uso de privilégios em sistemas multiusuário. A norma prevê que isso se dê por processo de autorização formal, cobrindo:

- identificação do privilégio de acesso de cada produto de sistema (SO, SGBD, cada aplicação) e das categorias de usuários que precisam dele;
- concessão de privilégios por necessidade de uso, alinhada à política de controle de acesso — "requisitos mínimos para sua função, somente quando necessário";
- manutenção de registro e processo de autorização de todos os privilégios concedidos, sem liberar o privilégio antes do processo estar concluído;
- incentivo a rotinas e programas que dispensem a necessidade de privilégio;
- atribuição dos privilégios a um ID de usuário diferente do usado normalmente para os negócios.

O trecho de [6] segue mencionando o uso inapropriado de privilégios de administrador de sistemas como risco associado, mas o texto chega cortado nesse ponto — não dá para transcrever além disso.

**Controle complementar de revisão** (transcrito de [7], mesma obra, 11.2.4 Análise crítica dos direitos de acesso de usuário): direitos de acesso em geral são revisados a intervalos regulares (a norma cita seis meses como exemplo), mas autorizações de **acesso privilegiado especial** devem ser analisadas em intervalo mais frequente — a norma cita três meses como exemplo —, com verificação periódica das alocações de privilégio e registro das modificações em contas privilegiadas para análise posterior.

**Objetivo geral em que isso se encaixa** (transcrito de [1], 11.2 Gerenciamento de acesso do usuário, contexto-pai de 11.2.2): o objetivo da seção é assegurar acesso de usuário autorizado e prevenir acesso não autorizado, com atenção especial, "onde apropriado", à necessidade de controlar a distribuição de direitos de acesso privilegiado que permitem aos usuários mudar controles de sistemas — ou seja, na ABNT 27002:2005 o acesso privilegiado é tratado como caso de atenção reforçada dentro do gerenciamento de acesso do usuário, não como processo à parte.

**Nota sobre lacuna nas outras fontes**: [2] (ABNT NBR ISO/IEC 27701:2019, 6.6.2.3, com o breadcrumb exatamente "Gerenciamento de direitos de acesso privilegiado") só remete ao controle 9.2.3 da ISO/IEC 27002:2013 — o texto desse controle não veio no trecho recebido, então não posso transcrever nada de [2] além da remissão. [5] traz a ISO/IEC 27002:2013 em inglês, mas o trecho recuperado cobre 9.2.1 (user registration/de-registration) e 9.2.2 (user access provisioning), não o 9.2.3 (privileged access rights) — fica de fora por não tratar do conceito exato, ainda que a obra e a seção-pai (9.2 User access management) sejam pertinentes ao tema mais amplo. [8] (Security+, Ahmed Sheikh) traz só o resumo de um capítulo chamado "Access Control and Privilege Management" — é sumário de capítulo, não sustenta definição.

**Fonte de vizinho semântico, usada com ressalva** (derivado de [3], relatório OSIC 15-24, 2.2.5 Gerenciamento de identidades e acessos): essa fonte trata de IAM de modo mais amplo, mas contém elemento diretamente relevante — recomenda o princípio do menor privilégio (PoLP), combinado com need-to-know quando há informação classificada, e integração de sistemas de IAM com políticas de auditoria e revisão contínua de acessos. Não é a mesma seção que "gestão de acesso privilegiado" no sentido estrito das normas ISO acima, por isso trago separado.