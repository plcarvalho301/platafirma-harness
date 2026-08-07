## Limite de WIP (work in progress)

**Definição.** Limite de WIP é a restrição imposta à quantidade de itens de trabalho que podem estar simultaneamente em andamento em um processo, com o objetivo de controlar o tempo de ciclo (cycle time) e o fluxo. Tecnicamente, corresponde a transformar um sistema de fila sem limite (M/M/1/∞) em um sistema com limite superior k (M/M/1/k): quando o WIP atinge esse teto, novas entradas de demanda são bloqueadas.

— *Transcrito/derivado* de **The Principles of Product Development Flow** (Reinertsen), seção *Applying WIP Constraints › The Economic Logic of WIP Control › W1: The Principle of WIP Constraints: Constrain WIP to control cycle time and flow* [6]. O texto afirma explicitamente: "When we set a limit on WIP, we create one positive effect and two negative ones. The positive effect is to reduce average cycle time." E localiza o mecanismo formal no modelo M/M/1/k, em oposição ao M/M/1/∞ sem limite.

**Mecanismo de enforcement.** A forma mais simples de operar um limite de WIP é bloquear toda demanda nova quando o teto é atingido — é exatamente o método usado no sistema kanban, e análogo a um sinal de "ocupado" em um sistema telefônico. O bloqueio pode ser feito ejetando o item que chega ou retendo-o numa fila anterior (esta segunda forma é a usada no Toyota Production System, que também aplica limites de WIP às filas upstream).

— *Transcrito* de **The Principles of Product Development Flow**, seção *Applying WIP Constraints › Reacting to Emergent Queues › W6: The Principle of Demand Blocking* [7].

**Limites diferenciados por categoria.** Como o fluxo de trabalho normalmente não é homogêneo, uma prática mais sofisticada consiste em subdividir o WIP em categorias por custo de atraso (alto, médio, baixo) e usar a Fórmula de Little para determinar um limite de WIP específico por categoria, alcançando tempos de fluxo diferenciados mesmo compartilhando o mesmo recurso.

— *Transcrito/derivado* de **The Principles of Product Development Flow**, seção *Applying WIP Constraints › WIP Constraints in Practice › W18: The Principle of Differential Service* [3].

**Como prática de gestão lean (Accelerate).** Limitar o WIP é listado como um dos três componentes das práticas de Lean Management aplicadas à entrega de software, ao lado de displays visuais e uso de dados de monitoramento. O achado empírico do livro é que o limite de WIP isolado não prediz fortemente a performance de entrega — o efeito forte aparece quando combinado com displays visuais e loop de feedback de produção.

— *Transcrito/derivado* de **Accelerate — The Science of Lean Software and DevOps**, seção *Software › Lean Management Practices* [5].

**Sobre o kanban de Olsen [2] e o resumo de kanban [1]:** o trecho de *The Lean Product Playbook* descreve o quadro kanban e suas colunas, e o *Essential Kanban Condensed* traz um foreword geral sobre o método — nenhum dos dois, no recorte que chegou, define ou explica o limite de WIP em si (o segundo é prefácio, sem matéria técnica sobre o conceito), então não os uso para sustentar a definição.
