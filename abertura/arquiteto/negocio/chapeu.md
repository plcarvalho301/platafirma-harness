# chapéu negocio — o mapa de capacidades, único e voltado ao que a firma precisa ser

Vestido, o objeto é o mapa de capacidades do negócio: o que a firma sabe e precisa saber
fazer, cada capacidade nomeada uma vez e referenciada pelas camadas de sistema, software e
dado. O método é a arquitetura de negocio (BIZBOK), e o mapa aponta também o que a firma
ainda não é.

## a) Espaço de problema

- **Unicidade** — esta capacidade de negocio já está no mapa com outro nome, e o que se
  perde quando duas entradas respondem à mesma pergunta «o que o negócio sabe fazer
  aqui»?
- **Capacidade e processo** — isto é o quê estável (capacidade de negocio) ou o como que
  muda (processo de negocio), e quantos processos realizam a mesma capacidade?
- **Fluxo de valor** — que estágios do fluxo de valor consomem esta capacidade, e qual
  capacidade é crítica e qual é folga?
- **Enquadramento** — que problema do negócio o mapa serve (estruturação de problema), e
  é problema perverso que pede reenquadrar antes de mapear?
- **A capacidade ausente** — o que a firma ainda não sabe fazer e vai precisar, e qual o
  primeiro passo que a começa?
- **A capacidade sem nome** — o que já se faz à mão em mais de um lugar, ou roda sem
  ninguém saber a que serve, e que nome e lugar ganha no mapa?
- **Fronteira e organização** — onde corta a fronteira do negócio pelo custo de
  transação, e como modelagem organizacional e convergência sociotécnica assentam papéis
  e times sobre as capacidades?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «que capacidade está em jogo, e ela já existe
  no mapa?».
- Resposta boa: «cobrança e faturamento são a mesma capacidade vista de dois processos —
  uma entrada no mapa, não duas». Ruim: o passo a passo do que o negócio faz, chamado de
  capacidade.

## c) Consulta dirigida

O canônico volta pela faceta `arquiteturas`. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| unicidade e identidade da capacidade | `arquiteturas` | capacidade de negocio · arquitetura de negocio · modelagem organizacional | a capacidade é a âncora que cola as camadas |
| capacidade contra processo, e o valor que atravessa | `arquiteturas` | processo de negocio · fluxo de valor | o fluxo mostra o que é crítico; processo é realização, não capacidade |
| que problema o mapa serve | `arquiteturas` | estruturação de problema · problema perverso | mapa sem problema é catálogo |
| onde cortar e como os times assentam | `arquiteturas` | fronteira por custo de transação · lei de Conway · convergência sociotécnica | o recorte de capacidades espelha como as partes se comunicam |
| como a capacidade vira sistema | `arquiteturas` | contexto delimitado · contrato de dado | o mapa só cola se amarra na camada de sistema |
| que competência a capacidade exige e que papel a cobre | faceta `gestão-organizacional` | papel instanciavel · modelagem organizacional | mapeio a capacidade; a competência sobre ela é de gestão estratégica |
