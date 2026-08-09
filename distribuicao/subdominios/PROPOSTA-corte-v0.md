# Subdomínios — proposta de corte v0

Recorte de prateleira para os dez domínios da coleção `firma`. Propõe a grade,
não a designação: nenhuma obra é pré-classificada aqui. Quem designa é a cadeira
dona do domínio, depois que o corte for despachado como decisão.

Autoria: claudinha-produto. Rótulo dos slugs passa por claudinho-conhecimento.
Perfil de acesso não é matéria desta proposta.

## Régua

Teto de **6 subdomínios por domínio**. Duas funções, nesta ordem: encontrar a
prateleira sem busca textual, e servir de recorte grosso de leitura humana. A
navegação fina entre assuntos é da teia de conceitos, não daqui.

Três regras de corte:

1. **Corta por assunto**, não por natureza do texto — "norma" e "livro-texto"
   não são prateleiras, são espécie de obra e já existem como campo próprio.
2. **Prateleira que não se enche não existe.** Subdomínio previsto e vazio some
   da grade; volta no dia em que houver obra.
3. **Mesma gramática entre domínios.** O leitor que troca de domínio troca de
   assunto, não de lógica de organização.

## A grade

### seguranca-privacidade (179 obras · hoje 9 subdomínios)

| subdomínio | escopo |
|---|---|
| `governanca-e-risco` | política, framework de controle, gestão de risco, certificação, papel de conselho |
| `identidade-e-acesso` | identidade, autenticação, federação, autorização, zero trust |
| `criptografia` | algoritmo, chave, módulo criptográfico, PQC, homologação |
| `privacidade-e-dados-pessoais` | LGPD e GDPR, encarregado, anonimização, ciclo de vida do dado pessoal |
| `defesa-de-plataforma` | aplicação, container, rede, host, hardening, cadeia de suprimento |
| `deteccao-e-resposta` | incidente, forense, continuidade, inteligência de ameaça, teste ofensivo |

Absorve os nove atuais sem redesignar obra: `seg-governanca-controles` →
`governanca-e-risco`; `seg-acessos` → `identidade-e-acesso`; `seg-cripto` →
`criptografia`; `seg-dados-privacidade` → `privacidade-e-dados-pessoais`;
`seg-plataforma-aplicacoes` + `seg-redes` + `seg-operacional` →
`defesa-de-plataforma`; `seg-deteccao-resposta` + `seg-ofensiva` →
`deteccao-e-resposta`.

### capacidade-estatal (130 · hoje 4)

Grade atual (`ce-fundamentacao`, `ce-implementacao`, `ce-normativo`,
`ce-prescritivo`) corta por natureza do texto, não por assunto — viola a regra 1
e a regra 3. Recorte por assunto exige redesignar as 130 obras já classificadas.
Decisão do dono, em aberto.

### ia (65 · hoje 7, um vazio)

| subdomínio | escopo |
|---|---|
| `fundamentos-de-modelo` | arquitetura de modelo, treino, quantização, contexto longo |
| `recuperacao-e-busca` | RAG, embedding, ranqueamento, avaliação de recuperação |
| `agentes-e-harness` | agente, skill, engenharia de contexto, ferramenta, multiagente |
| `infra-e-serving` | execução local, formato de peso, integração, protocolo de ferramenta |
| `avaliacao-e-governanca-de-ia` | eval, benchmark, norma de gestão de IA, risco de modelo |

`ia-produto` sai: previsto e vazio.

### inteligencia (49 · hoje nenhum)

| subdomínio | escopo |
|---|---|
| `doutrina-e-analise` | técnica analítica estruturada, psicologia da análise, doutrina |
| `marco-legal-e-controle` | lei, decreto orgânico, controle externo, composição de sistema |
| `politica-e-estrategia` | política e estratégia nacional, plano, portaria de diretriz |
| `protecao-do-conhecimento` | infraestrutura crítica, área sensível, credenciamento, salvaguarda |

### estudos-ontologias (52 · hoje 3)

| subdomínio | escopo |
|---|---|
| `fundamentos-ontologicos` | ontologia de fundamentação, lógica descritiva, categoria formal |
| `engenharia-de-ontologia` | construção, alinhamento, avaliação, linguagem de representação |
| `organizacao-do-conhecimento` | vocabulário controlado, taxonomia, tesauro, arquitetura de informação |
| `arquivistica-e-registro` | descrição arquivística, requisito de sistema de registro, política de arquivo |
| `cognicao-e-aprendizagem` | aprendizagem, memória organizacional, prática reflexiva, resolução de problema |

### engenharia-software (51 · hoje 5, um vazio)

| subdomínio | escopo |
|---|---|
| `artesania-e-design-de-codigo` | padrão, refatoração, teste, legado |
| `entrega-e-operacao` | pipeline, DORA, confiabilidade, observabilidade, patch |
| `gestao-de-servico-de-ti` | ITIL, FitSM, COBIT, CMMI, catálogo de serviço |
| `dados-e-persistencia` | engenharia de dados, streaming, banco, formato de arquivo |
| `interfaces-e-integracao` | REST, contrato de API, protocolo de interoperação |

`engenharia-front-end` sai: previsto e vazio.

### produtos-digitais (41 · hoje 2)

| subdomínio | escopo |
|---|---|
| `descoberta-e-estrategia` | discovery, posicionamento, trabalho a ser feito, armadilha de build |
| `design-de-interacao` | usabilidade, heurística, affordance, interação humano-sistema |
| `especificacao-e-entrega` | história de usuário, mapeamento de impacto, recorte de escopo, caso de uso |
| `produto-publico-digital` | usuário de serviço público, lacuna projeto-realidade, direito do usuário |

### arquiteturas (37 · hoje 4)

| subdomínio | escopo |
|---|---|
| `decisao-arquitetural` | registro de decisão, conhecimento arquitetural, atributo de qualidade |
| `estilos-e-decomposicao` | microsserviço, modularidade, evento, sistema distribuído |
| `modelagem-de-dominio` | DDD, contexto delimitado, modernização por fronteira |
| `arquitetura-de-dados-e-negocio` | governança de dados, malha de dados, arquitetura corporativa, processo |

### gestao-organizacional (34 · hoje 3, dois vazios)

| subdomínio | escopo |
|---|---|
| `estrategia-e-resultado` | estratégia, objetivo e resultado-chave, medição, portfólio |
| `estrutura-e-topologia` | desenho de time, lei de Conway, estrutura organizacional, isomorfismo |
| `governanca-institucional` | governança pública e corporativa, conselho, norma de governança |
| `trabalho-e-fluxo` | fluxo de trabalho, produtividade, regime de trabalho, execução pessoal |

### platafirma (2)

Sem corte. Dois itens não sustentam prateleira.

## O que fica em aberto

- Recorte de `capacidade-estatal`: manter a grade por natureza do texto ou
  redesignar 130 obras por assunto.
- Rótulo final dos slugs: passe de claudinho-conhecimento.
