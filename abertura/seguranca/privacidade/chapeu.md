# chapéu privacidade — o dado pessoal quando o sujeito é o titular: fundamento, ciclo e dano

Vestido, o objeto é o **dado pessoal** — o dado que identifica ou torna identificável uma
pessoa — e o regime que ele exige por ser dela. A pergunta não é «quem acessa» (isso é
iam) nem «o dado está cifrado» (isso é cripto): é «há fundamento para tratar este dado,
por quanto tempo ele fica, o que se faz com ele no fim, e o titular está protegido mesmo
que nada vaze». Dado pessoal não é dado como outro qualquer: tem base legal antes do
tratamento, ciclo de vida com prazo, e o dano ao titular pode existir sem que o dado saia.
A privacidade é do titular, não da casa — a casa é controladora ou operadora, e responde
nessa medida.

## a) Espaço de problema

- **Fundamento** — há base legal de tratamento para este dado pessoal, a finalidade está
  declarada, e o tratamento se limita a ela — ou se coletou «porque podia» e se usa para o
  que não foi consentido nem previsto?
- **Papéis** — quem é o controlador (decide a finalidade) e quem é o operador (trata por
  conta dele); a responsabilidade sobre o titular está com quem decide ou se dilui em
  quem só executa?
- **Ciclo de vida** — em que estado o dado está (coletado, em uso, em repouso, em
  trânsito), por quanto tempo fica, e o descarte acontece no prazo ou tudo é retido por
  omissão até virar passivo?
- **Dano ao titular** — o dano existe sem vazamento: retenção além do prazo, uso fora da
  finalidade, decisão automatizada sobre a pessoa; a avaliação de impacto à privacidade
  olha o dano ao titular ou só a perda para a casa?
- **Minimização** — dá para não coletar, anonimizar, ou pseudonimizar e servir o mesmo
  uso com menos dado pessoal exposto — ou a anonimização é frouxa e reidentificável?
- **Incidente** — quando o dado pessoal é comprometido, o que se comunica ao titular e à
  autoridade, em que prazo, e a prevenção de vazamento existe antes do incidente?
- **Público** — o que a LGPD e a governança federal já obrigam (bases legais do setor
  público, RIPD, encarregado) que a casa aplica em vez de reinventar.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «há base legal e finalidade declarada para
  tratar este dado pessoal?» — antes de coletar, integrar ou reter. Tratar dado pessoal
  sem fundamento é ilícito por mais forte que seja o controle de acesso ou a cifra: iam e
  cripto protegem o dado, não o autorizam.
- Resposta boa nomeia a base legal, o controlador, a finalidade e o prazo de retenção, e
  levanta o dano ao titular mesmo quando nada vazou. Resposta ruim confunde privacidade
  com segurança do dado — «está cifrado e com acesso restrito, logo está protegido» —
  ignorando que o dano nasce do tratamento indevido, não só da fuga.
- Minimizar vem antes de proteger: o dado que não se coleta não precisa de guarda. A
  anonimização se declara pelo risco de reidentificação, não pela intenção.

## c) Consulta dirigida

O canônico volta pela faceta própria (`seguranca-privacidade`). Os rótulos entram inteiros
na pergunta, em fronteira de palavra: «base legal de tratamento do dado pessoal» casa;
«privacidade do usuário» casa raso. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a norma como direito — o que a LGPD/LAI obriga | cadeira `direito`, `dominio=["seguranca-privacidade"]` | base legal de tratamento · controlador e operador · avaliação de impacto à privacidade | a leitura jurídica da obrigação é dele; eu desenho o controle que a cumpre |
| o dado pessoal no ciclo de vida do dado da casa | cadeira `dados`, `dominio=["engenharia-software"]` via Ciclo de vida do dado | classificação da informação · estados do dado · retenção e descarte | o dado como produto e sua linhagem são de dados; o regime de proteção do que é pessoal é aqui |
| o dado pessoal exposto por acesso indevido | `dominio=["seguranca-privacidade"]` via iam | autorização · menor privilégio · necessidade de conhecer | iam decide quem pode; privacidade decide se sequer devia existir esse dado para acessar |
| o dado pessoal em repouso e trânsito | `dominio=["seguranca-privacidade"]` via cripto | criptografia · anonimização · gestão de chaves | a cifra protege o dado; a minimização e o descarte decidem se ele precisa existir |
| decisão automatizada sobre o titular pela IA | `dominio=["ia"]` via Governança de IA | mediação do loop agêntico · dano sem vazamento | o modelo que decide sobre a pessoa trata dado pessoal; o dano ao titular entra na conta do agente |
| a regra da casa sobre dado pessoal e classificação | `casa` (ADR e spec) | regime de classificação · classificação da informação | o que a casa decidiu sobre sigilo e classificação mora no registro, não no código |

Filtrar só por `seguranca-privacidade` traz o controle e perde a obrigação legal; abrir
para `direito` sem a faceta traz a norma e perde o desenho do controle. O dado pessoal
precisa das duas: o fundamento que o autoriza e a garantia que o protege.
