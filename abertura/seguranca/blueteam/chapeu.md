# Blueteam

Entidade: chapeu

## Espaço de problema

- O que esta regra tem de pegar, em que sinal ela lê, e a firma já coleta o evento que a correlação de eventos consome?
- Que táticas e técnicas adversárias a detecção codifica, em que ponto da cadeia de ataque atua, e o que só a correlação denuncia que o evento isolado não?
- A regra acende contra a amostra de ataque e fica muda contra a linha de base do tráfego normal, com a fadiga de alerta medida, e não afirmada?
- Qual o raio da automação de resposta: contém o movimento lateral sem derrubar o serviço legítimo, e preserva a cadeia de custódia antes de agir?
- Contra que superfície de ataque a cobertura se mede, priorizada pela modelagem de ameaças, e qual o efeito nos objetivos de recuperação?
- A regra e a automação estão em código que se lê, se versiona e se testa, e não em heurística que ninguém audita depois?
- Este pico é ataque ou falha operacional, e a causa operacional do mesmo sinal foi descartada antes de classificar?

## Régua de resposta

Resposta boa é defesa que pega o ataque especificado sem afogar o operador em ruído, testada dos dois lados, contra o ataque e contra uma semana de log limpo, e resposta que contém sem dano colateral e sem apagar evidência.

Resposta ruim casa o log de teste e é cega à variação, grita no tráfego legítimo, ou contém apagando o rastro.

## Consulta dirigida

- Como o adversário age: a busca vai por táticas e técnicas adversárias, cadeia de ataque e inteligência de ameaças.
- Resposta a incidente: a busca vai por gestão de incidentes e objetivos de recuperação.
- Como escrever a regra e a automação: as obras de python e de shell valem aqui, porque detecção e resposta são código.
- Detecção como código, engenharia de detecção e regra de detecção são conceitos sem obra ancorada; o que faltar sai marcado como lacuna.

## Rótulos de busca

- rótulos: controle de segurança · táticas e técnicas adversárias · cadeia de ataque · inteligência de ameaças · correlação de eventos · modelagem de ameaças · superfície de ataque · fadiga de alerta · gestão de incidentes · movimento lateral · objetivos de recuperação · cadeia de custódia · tempo de restauracao · detecção como código · engenharia de detecção · regra de detecção · linha de base de comportamento
- recorte de domínio: seguranca-privacidade · engenharia-software
- homônimos: regra, que neste ramo é a regra de detecção, e não a regra da casa · incidente, que é o incidente de segurança, e não o incidente operacional
