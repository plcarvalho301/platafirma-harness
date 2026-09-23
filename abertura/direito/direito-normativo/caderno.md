## conhecimento curado

- Colegiado que «reconhece a própria competência» — parece legitimação e é
  autoatribuição; a competência nasce do ato de quem pode dá-la (autoridade máxima,
  regimento, decreto). Sinal: a ata do comitê é citada como fonte do poder do comitê.
- Norma amarrada a órgão em reestruturação — parece concreta e caduca com o
  organograma. Cura: norma por função, com artigo de transição dizendo quem exerce a
  função até o órgão definitivo existir. Sinal: política que nomeia colegiado ainda
  por criar.
- «Ou colegiado equivalente» lido como ordem de criar órgão novo — a cláusula abre
  acumulação; o equivalente cumpre a composição mais exigente entre as normas que ele
  atende. Sinal: «o decreto obriga criar o comitê X».
- Negociação colegiada sem prazo — parece participação e é veto pelo cansaço. Cura:
  consulta obrigatória com prazo fixo e subida automática da matéria vencido o prazo.
  Sinal: colegiado com todas as unidades decidindo a fronteira entre elas.
- Guia do órgão central lido como norma — é orientação e se declara adaptável; vincula
  o decreto ou a portaria que ele comenta. Sinal: «o guia exige».
- Densidade da norma é escolha de capacidade — regra exige capacidade de executar;
  padrão só se justifica se quem aplica está em melhor posição que o redator e tem
  capacidade de julgar. Dispositivo que não é nem regra clara nem padrão confiado a
  quem sabe julgar isenta o gestor: não há contra o que cobrar. Conduta frequente pede
  regra, rara pede padrão. Sinal: dispositivo vago que não diz quem julga.
- Norma interna de órgão cai fora do regime de qualidade regulatória (AIR só para
  interesse geral de agentes econômicos ou usuários; linguagem simples só para texto
  ao cidadão; consulta da LINDB ressalva organização interna). O que a rege é o
  D12002, que alcança ato inferior a decreto. Sinal: «precisa de AIR» ou «a lei de
  linguagem simples obriga» dito de portaria interna.
- Regra interna sigilosa impede o afetado de checar o desvio dela. Em política de
  órgão de inteligência, a norma nomeia quem confere o cumprimento no lugar de quem
  não pode ler a regra. Sinal: norma classificada sem instância de verificação.
- Conflito de linha resolvido por lotação prova demais — quando toda unidade é
  Proprietária de algum domínio, toda unidade é primeira linha, e «o gestor não pode
  ficar em área X» barra todos. Cura: regra de impedimento (o gestor não avalia o domínio
  da própria unidade) e contagem de assento, onde quer que ele esteja lotado. Sinal:
  recomendação de lotação justificada por segregação de linhas.
- Minuta de política não redesenha o organograma — estrutura, colegiado, composição e
  lotação são dado de entrada; o que a política pode fazer com colegiado fora do
  escopo autorizado é deixar de mencioná-lo. Sinal: proposta de extinguir, recompor ou
  redistribuir função de colegiado que o dono não pôs na mesa.

## diario de bordo

- 2026-09-22 — tentei repo ler platafirma-arquitetura docs/proposta-cobertura-direito-2026-09-22.md, voltou vazio (worktree direito inexistente, fallback em clone de ramo de outra cadeira); tentei release ler, vazio (release de 20/09, anterior ao doc) — contorno encontrado NA DATA 2026-09-22 foi repo git fetch origin main + show origin/main:<caminho>.
- 2026-09-22 — tentei pesquisar ler em planalto.gov.br (L14129, D12198), voltou conteúdo vazio com status 0, também com --render — contorno encontrado NA DATA 2026-09-22 foi fonte secundária (legjur, lex) pela busca web do chat; verbo não resolveu.
- 2026-09-22 — tentei acervo psql em acervo.trecho com join por obra_id, coluna inexistente — contorno encontrado NA DATA 2026-09-22 foi motor rag buscar obra.
- 2026-09-22 — tentei mesa anota com prosa no lugar do slot, recusou (slot: minúsculas, dígitos e hífen, até 24 chars); criei slots livres e descansar os marcou órfãos (slug não declarado na persona) — contorno encontrado NA DATA 2026-09-22 foi consolidar no slot do chapéu e limpar os órfãos.
- 2026-09-22 — tentei ler os PDFs do Project do claude.ai com pdfinfo/pdftotext, falharam: são zip de jpeg+txt por página — contorno encontrado NA DATA 2026-09-22 foi unzip e ler os .txt.
- 2026-09-22 — tentei escrever caderno por mesa caderno, é só leitura; o clone de fallback estava em ramo fabrica/180 — contorno encontrado NA DATA 2026-09-22 foi repo abrir (worktree destacado em origin/main) + write_file + commitar/empurrar.
- 2026-09-23 — tentei conferir existe persona guara, erro de uso (tipos aceitos: cadeira|verbo|card|arquivo|mesa); tentei motor rag buscar casa "Guará persona cadeira", não trouxe o alias — contorno encontrado NA DATA 2026-09-23 foi persona foto (alias → slug).
- 2026-09-23 — tentei run_command com lote de 6 motor buscar, 2 itens voltaram omitido_por_teto — contorno encontrado NA DATA 2026-09-23 foi reenviar os itens restantes em lote novo.
- 2026-09-23 — tentei acrescentar à mesa com mesa anota, ele reescreve o slot inteiro (sem append) e avisa que ato pendente vai em mesa item — contorno encontrado NA DATA 2026-09-23 foi reenviar o slot completo e plantar a pendência com mesa item.
- 2026-09-23 — tentei acervo ler obra fcb134a4 (IN GSI 1/2020, achada por motor rag buscar obra) para ler o texto integral, recusou «combinação nao servida»; motor devolve só o início da obra — contorno encontrado NA DATA 2026-09-23 foi web_fetch da IN consolidada no gov.br (redação da IN 9/2026 já incorporada).
- 2026-09-23 — tentei motor rag buscar casa pela hierarquia/organograma do órgão, cobertura fraca (0,43, piso 0,5), sem retorno útil — contorno encontrado NA DATA 2026-09-23 foi perguntar ao dono (dado do órgão não mora no acervo).
