**Definição**

Arquitetura de dados é o conjunto de blueprints/modelos mestres que identificam as necessidades de dados de uma organização e orientam como esses dados são integrados, controlados e alinhados à estratégia de negócio. Ela representa o estado atual e futuro dos sistemas de dados que sustentam as necessidades de longo prazo de uma organização.

Há mais de uma formulação nas fontes que chegaram, e vale mostrar as três porque se complementam:

1. **Definição da DAMA (DMBOK)** — transcrita da fonte [3]:
> "Identifying the data needs of the enterprise (regardless of structure) and designing and maintaining the master blueprints to meet those needs. Using master blueprints to guide data integration, control data assets, and align data investments with business strategy."

Fonte: *Fundamentals of Data Engineering* (Reis & Housley), Capítulo 3 — Designing Good Data Architecture › DAMA's definition.

2. **Versão simplificada, de outro acervo** — transcrita da fonte [2], que primeiro resume a definição do DMBOK (mestre de modelos de dados e abordagens de design, a coluna "data" do Zachman Framework, ou a infraestrutura tecnológica física) e depois oferece a que o autor prefere usar em contexto de negócio:
> "Data architecture is a representation of the DM environment, its components, and their interactions. This picture, or abstraction, interrelates the framework, people, processes, projects, policies, technologies, and procedures to manage and use valuable enterprise information assets."

Fonte: *Data Governance* — Data literacy and concepts › Data architecture.

3. **Formulação de Reis & Housley** — transcrita da fonte [5]:
> "A data architecture reflects the current and future state of data systems that support an organization's long-term data needs and strategy."

Fonte: *Fundamentals of Data Engineering*, Capítulo 2 — The Data Engineering Lifecycle › Data Architecture. O mesmo trecho situa arquitetura de dados como "undercurrent" (corrente subjacente) do ciclo de vida de engenharia de dados, e distingue o papel de engenheiro de dados do de arquiteto de dados (são papéis tipicamente separados).

**Observação derivada** (não transcrita, mas ligando as três): as três definições convergem num ponto — arquitetura de dados não é a implementação em si, é a representação/blueprint que orienta decisões sobre dados (modelagem, integração, governança, trade-offs) em nível organizacional, distinta da execução tática do dia a dia.

**Fora do escopo da pergunta, deixado de lado**: as fontes [1], [4] e [7] tocam em arquitetura de dados mas não a definem no trecho que chegou — [1] é a introdução do capítulo que *antecede* as definições (o trecho corta antes de mostrar as definições em si), [4] fala de tipos/exemplos, e [7] fala de critérios de escolha de tecnologia. As fontes [6] e [8], de *Continuous Architecture in Practice*, tratam "dados" como preocupação arquitetural dentro da arquitetura de software geral, não definem "arquitetura de dados" como disciplina — não usei o conteúdo delas como definição por esse motivo.
