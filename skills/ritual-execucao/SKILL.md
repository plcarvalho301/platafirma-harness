---
name: ritual-execucao
description: Use quando a story de código entrar em execução ou o dono disser executa, implementa, codifica, «sobe essa mudança». Dá para que lado puxar: lotes pequenos e verificados, raio do card, confirmar na fonte, provar com teste, corrigir a causa em vez de contornar o portão. NÃO dispare para escrever documento ou card, para revisar código pronto (auditoria) nem para serviço fora do ar (conserto).
---

# Ritual de execução

Enquanto a fita estiver em execução, estas linhas dizem para que lado você puxa quando há escolha. Não são passos: os passos vêm do processo em curso, quando houver um. O ritual sai quando a atividade muda.

- Diante de uma tarefa de código que admite atalhos ou ordem livre, puxo para fechá-la em lotes pequenos e verificados sob a missão executar a story de código (https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/instancias/missao/executar-a-story-de-codigo.md), em vez de acumular mudanças até o fim, porque o lote pequeno mostra onde o erro nasceu e entra no tronco sem briga.
- Diante de um trecho feio ou de uma melhoria vizinha achada no caminho, puxo para anotá-la à parte como dívida e manter o raio do card, em vez de consertá-la no mesmo lote, porque mudança misturada esconde o que quebrou o aceite.
- Diante de uma dúvida entre inferir o comportamento no código ou checar o que a casa e o código já têm, puxo para confirmar na fonte antes de escrever, em vez de preencher o vão por analogia, porque código escrito sobre suposição cobra o erro na integração.
- Diante de uma escolha que altera o aceite ou o contrato de quem chama, puxo para parar e devolver a pergunta a quem formulou, em vez de resolvê-la na linha de código, porque decidir requisito no meio da implementação muda o combinado sem aviso.
- Diante de um ajuste pronto que parece óbvio, puxo para prová-lo com teste automatizado na fronteira que mudou, em vez de dá-lo por feito só pela leitura do diff, porque sem prova executável a mudança vira aposta.
- Diante de uma ferramenta ou verificação que recusa a mudança, puxo para corrigir a causa na bancada, em vez de contornar o bloqueio ou afrouxar o teste, porque o portão desligado deixa passar o erro que ele existia para barrar.

Este texto é cópia do ritual gravado na casa nova; se os dois divergirem, vale o gravado:
https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/instancias/ritual/execucao.md
