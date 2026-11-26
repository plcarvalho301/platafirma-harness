---
name: ritual-conserto
description: Use quando serviço, porta, bancada ou verbo cair ou quebrar, houver incidente declarado ou o dono disser conserta, caiu ou «está dando erro». NÃO dispare para débito técnico sem parada, refatoração planejada ou análise com tudo no ar.
---

# Ritual de conserto

Enquanto a fita estiver em conserto, estas linhas dizem para que lado você puxa quando há escolha. Não são passos: os passos vêm do processo em curso, quando houver um. O ritual sai quando a atividade muda.

- Diante de um serviço fora do ar e da vontade de achar logo a causa raiz, puxo para pôr o serviço de pé primeiro, por volta de versão ou reinício controlado, como no procedimento religar a porta pelo host (https://github.com/plcarvalho301/platafirma-casa/blob/main/instancias/procedimento/religar-a-porta.md), em vez de investigar com o sistema parado, porque o impacto cresce a cada minuto fora do ar e a causa raiz cabe depois, com o serviço respondendo.
- Diante de várias suspeitas sobre o que quebrou, puxo para descartar primeiro as causas mais baratas olhando o estado vivo da máquina e dos logs, em vez de perseguir a hipótese mais engenhosa, porque um teste negativo barato corta metade do espaço de busca e evita mexer no que não falhou.
- Diante de uma falha em produção que admite mais de um reparo, puxo para a mudança menor e com volta conhecida, em vez de aproveitar o incidente para refatorar ou corrigir desvios vizinhos, porque cada mudança extra amplia o raio de alcance e confunde o que de fato resolveu a falha.
- Diante de um travamento de ambiente ou de acesso que pede ação rápida, puxo para o caminho já previsto na casa, como recuperar a bancada (https://github.com/plcarvalho301/platafirma-casa/blob/main/instancias/procedimento/recuperar-a-bancada.md) ou agir no host com a porta caída (https://github.com/plcarvalho301/platafirma-casa/blob/main/instancias/procedimento/agir-no-host-com-a-porta-caida.md), em vez de improvisar conserto manual fora da trilha, porque o improviso resolve a hora e planta deriva difícil de desfazer.
- Diante de um comando de reparo que voltou sem erro, puxo para conferir o efeito real pelo lado de quem chama o serviço, em vez de dar a falha por encerrada no retorno do comando, porque o processo pode subir de pé com a versão velha ou atrás de uma entrada ainda quebrada.
- Diante de um serviço já restabelecido, puxo para registrar a causa provável e a prevenção enquanto os fatos estão frescos, em vez de virar a página assim que o alerta apaga, porque consertar o mesmo defeito duas vezes vira labuta operacional e esconde o defeito estrutural.

Este texto é cópia do ritual gravado na casa nova; se os dois divergirem, vale o gravado:
https://github.com/plcarvalho301/platafirma-casa/blob/main/instancias/ritual/conserto.md
