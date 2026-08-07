**Definição — nível de garantia de autenticação (Authentication Assurance Level, AAL)**

O nível de garantia de autenticação é o grau de confiança de que quem está se autenticando é de fato o legítimo titular do identificador (subscriber) usado. A fonte [1] transcreve essa noção ao afirmar, no prefácio da NIST SP 800-63B: *"This document, SP 800-63B, provides requirements to credential service providers (CSPs) for remote user authentication at each of three authentication assurance levels (AALs)."* — ou seja, a norma define três AALs, e o restante do documento (fora do trecho recuperado aqui) estabelece os requisitos técnicos associados a cada um.

**De onde sai:** NIST Special Publication 800-63B-4 (2025) — seção de Prefácio, dentro do trecho recuperado sob o breadcrumb "List of Figures".

O trecho que chegou não traz a definição individual de AAL1, AAL2 e AAL3 nem os critérios técnicos de cada patamar — só a afirmação de que existem três níveis e que o documento os regula. Se precisar do detalhamento de cada AAL, essa parte específica não está no que recebi.

**Complemento ilustrativo (fonte diferente, caráter explicitamente não-normativo)**

A fonte [3] (*Solving Identity Management in Modern Applications*, cap. 12 — Step-Up Authentication) descreve a mesma ideia em linguagem de aplicação prática, mas com uma ressalva explícita do próprio texto: os autores usam "nível um" e "nível dois" como exemplo arbitrário, não como taxonomia formal — *"Our choice of levels and names is an arbitrary example for purposes of illustration."* Essa fonte é útil para entender o conceito de forma intuitiva (autenticação mais forte eleva a garantia da sessão — o chamado *step-up authentication*), mas não deve ser tomada como equivalente à definição normativa de AAL do NIST.

**O que não usei e por quê**

A fonte [8] (MCT ITI vol. 2, ICP-Brasil) trata de "Níveis de Segurança de Homologação" (NSH) — um conceito de homologação de software de AC/AR, não de garantia de autenticação de usuário. É vizinho semântico (ambos falam de "nível" em contexto de segurança/identidade), mas não é o mesmo conceito, por isso não usei para sustentar a definição pedida.

As fontes [2], [4], [5], [6] e [7] tratam de tópicos correlatos (modelo de identidade digital, usabilidade de autenticadores, prova de identidade, serviços de autenticação no Windows) mas não definem nível de garantia de autenticação nos trechos recebidos.