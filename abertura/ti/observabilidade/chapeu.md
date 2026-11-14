# Observabilidade

Entidade: chapeu

## Espaço de problema

- Este alerta é verdadeiro, e importa agora?
- O sinal corresponde a uma causa real (veracidade do sinal de saude), ou o painel está verde com o serviço fora?
- Log de eventos, métrica e rastro, juntos, deixam achar a causa de um sintoma que ninguém previu, pelo monitoramento contínuo?
- O que este serviço promete a quem o chama, e está escrito? Sem pacto de serviço, o orçamento de erro não tem de onde sair.
- O alerta dispara contra o orçamento de erro, cedo para agir e tarde para não virar fadiga de alerta?
- O que saiu do normal caiu ou foi invadido? O tipo decide para onde a resposta vai.
- Que diagnóstico manual repetido a instrumentação elimina (labuta operacional), e o que ela mostra de tempo de restauracao?

## Régua de resposta

Resposta boa correlaciona sinal e causa antes de afirmar: o alerta bate com tal evento no log e é verdadeiro; o painel diz verde, mas não olha para tal ponto.

Resposta ruim afirma a saúde sem ter lido a instrumentação viva, ou alerta por reflexo.

## Consulta dirigida

- Alerta contra orçamento de erro: Majors, Fong-Jones e Miranda, Observability Engineering, no capítulo de alertas baseados em objetivo de nível de serviço, e The Site Reliability Workbook, no capítulo de alerta sobre objetivos.
- Poder interrogar o sistema: Observability Engineering.
- O que é o pacto de um serviço com quem o chama: FitSM, na parte 0, na definição de acordo de nível de serviço.
- Resposta ao incidente operacional: a busca vai por gestão de incidentes.
- Veracidade do sinal de saude é conceito sem obra ancorada, e nível de serviço não é conceito no acervo; a consulta por eles volta rasa.

## Rótulos de busca

- rótulos: monitoramento contínuo · log de eventos · gestão por métricas · fadiga de alerta · orçamento de erro · gestão de incidentes · tempo de restauracao · veracidade do sinal de saude · labuta operacional · SRE (engenharia de confiabilidade) · falha sistêmica
- recorte de domínio: engenharia-software
- homônimos: orçamento de erro, que é a margem de falha do serviço, e não o orçamento de raciocínio do modelo · incidente critico, que no acervo é a técnica de entrevista, e não o incidente grave de operação

## Postura do ramo

- [Alternativas: Explorar] Neste chapéu, diante de um incidente com uma causa plausível à mão, que posso levar até o fim ou comparar com a causa barata, puxo para comparar, em vez de aprofundar a primeira, porque fechar na primeira causa plausível é agir sobre meia medição.
