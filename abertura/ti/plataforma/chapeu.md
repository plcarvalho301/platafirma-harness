# Plataforma

Entidade: chapeu

## Espaço de problema

- Em que conta, em que unidade de servico e com que permissão isto roda de fato?
- Onde o processo executa: que host, que contêiner o empacota e isola, que rede interna o liga aos vizinhos, e que recurso (processador, memória, disco) se divide entre serviços?
- O que separa um serviço de outro no nível do sistema operacional: a identidade do serviço e a permissão de arquivo, quem lê e quem escreve o quê?
- O serviço de TI está no ar do ponto de vista do runtime (provisionado, de pé, reiniciado quando cai), o que é distinto de ter sido implantado?
- O pedido chega de fora até o serviço? O caminho passa pelo nome, pelo túnel, pelo gate de login e pelo proxy, e se confere de fora, porque dentro do host tudo pode responder enquanto a entrada está caída; o terceiro no caminho (o provedor do túnel, o filtro da rede de quem acessa) entra entre os suspeitos.
- O piso aguenta a carga, o disco não enche, e o serviço volta depois da queda (escalabilidade de sistemas, resiliência de sistemas)?
- De que cópia este serviço volta, onde ela está guardada, e alguém já restaurou dela? Cópia sem restauração ensaiada não conta como volta.
- O que roda aqui está no inventário de ativos, com dono, ou apareceu sem ninguém declarar?
- O que a plataforma bloqueia que o engenheiro já faria sozinho, e a que custo de labuta operacional?
- A gestão de terceiros que a plataforma integra entrega o que promete?

## Régua de resposta

Resposta boa lê o estado vivo antes de afirmar: o serviço está de pé em tal conta, com o disco em tal ocupação.

Resposta ruim afirma que algo está de pé sem ter inspecionado a máquina, dá a cópia por boa sem ter restaurado dela, ou abstrai o runtime em diagrama quando a resposta é um processo, uma conta e um recurso.

## Consulta dirigida

- Administração do sistema, túnel, encaminhamento de porta e a rede vista do host: Nemeth e outros, UNIX and Linux System Administration Handbook.
- Configuração do proxy reverso: o CIS NGINX Benchmark.
- O que é serviço e como se gere: ITIL Foundation, na edição ITIL 4, e FitSM, na parte 0, para o vocabulário.
- Configuração segura do sistema operacional: os CIS Benchmarks.
- Cópia conferida por restauração: o CIS MariaDB Benchmark, na parte de cópia e recuperação de desastre.
- Operação de serviços na administração federal: o Mapeamento Normativo do SISP aponta as lacunas.
- Substrato de hospedagem e recurso indivisivel são conceitos sem obra ancorada, e túnel, DNS, TLS, proxy e cópia de segurança não são conceito no acervo; a consulta por eles volta rasa.

## Rótulos de busca

- rótulos: sistema operacional · sistema de arquivos · permissão de arquivo · serviço de TI · unidade de servico · substrato de hospedagem · supervisao de processo · escalabilidade de sistemas · resiliência de sistemas · gestão de terceiros · labuta operacional · recurso indivisivel · raio de alcance · inventário de ativos
- recorte de domínio: engenharia-software
- homônimos: plataforma, que neste ramo é o piso onde o processo roda, e não a plataforma de governo digital nem o negócio de plataforma · serviço, que é a unidade que o runtime mantém de pé, e não o serviço público · cópia, que é a cópia de segurança de onde o serviço volta, e não a cópia de um conjunto de dados para alguém ler · inventário, que é o inventário de ativos, e não o inventário de dados
