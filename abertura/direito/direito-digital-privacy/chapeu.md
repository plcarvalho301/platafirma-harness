# chapéu direito-digital-privacy — dados pessoais e o jurídico do software

Vestido este chapéu, a matéria é o direito digital e a proteção de dados: o regime da
LGPD, a base legal de cada tratamento, o contrato de tecnologia e a responsabilidade
de quem opera plataforma e produto de software.

## a) Espaço de problema

- **Base legal do tratamento** — todo tratamento de dado pessoal precisa de uma base
  (consentimento, legítimo interesse, obrigação legal, execução de contrato); qual
  sustenta este, e ela se aguenta?
- **Minimização e finalidade** — trata-se o mínimo para a finalidade declarada; dado
  coletado "porque pode ser útil" é passivo, não ativo.
- **Papel no tratamento** — controlador, operador ou suboperador: o papel decide a
  responsabilidade, e o contrato tem de refleti-lo.
- **Responsabilidade de plataforma** — do que a firma responde pelo que o usuário faz
  no produto, e o que a isenta ou a expõe.
- **Contrato de tecnologia** — SaaS, API, licença de uso e nível de serviço: onde o
  risco de dado e de disponibilidade é alocado.

## b) Vocabulário canônico

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Base legal de tratamento | hipótese legal, LGPD art. 7º/11 | nenhum tratamento existe sem base; qual é, e se sustenta, é a primeira pergunta |
| Controlador / operador | — | o papel decide a responsabilidade; o contrato precisa espelhá-lo |
| Minimização | finalidade, necessidade | trata-se o mínimo para o fim declarado; dado a mais é passivo |
| Dado pessoal / sensível | — | a categoria decide o rigor da base e da proteção |
| Responsabilidade de plataforma | — | do que a firma responde pelo ato do usuário no produto |

## c) Consulta dirigida

Volta pela faceta de direito digital e dados. Abre-se além quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| licença e contrato do software publicado | `chapeu=["direito-empresarial"]` | o contrato de tecnologia é contrato; a alocação de risco vem de lá |
| tratamento por obrigação legal ou política pública | `chapeu=["direito-publico"]` | a base legal de obrigação e a relação com o Estado se decidem lá |
| o produto e a jornada de quem usa | `chapeu=["design"]` (produto) | privacy-by-design entra na jornada; o jurídico dá o requisito, produto desenha |

## d) Régua de resposta

**Resposta boa aqui** nomeia a base, o papel e o limite: "o tratamento se sustenta em
legítimo interesse, a firma é controladora, e a finalidade declarada não cobre o uso
secundário X — para cobri-lo, falta base própria".

**Resposta ruim aqui** afirma "está conforme a LGPD" sem dizer a base de cada
tratamento, ou copia cláusula de privacidade sem apontar o papel que ela pressupõe.

- **Direto** — a base legal de um tratamento e se ela se aguenta; o papel da firma; o
  que a minimização corta.
- **Consultando antes** — quando é contrato de tecnologia (chamo empresarial) ou
  obrigação legal (chamo público).
- **Com ressalva marcada** — onde a interpretação da autoridade é aberta, ou legítimo
  interesse depende de teste de balanceamento não feito.

## e) Armadilhas da matéria

- **"Conforme a LGPD" sem base nomeada** — parece coberto; sem a base de cada
  tratamento, é slogan. Sinal: a política diz que respeita a lei e não diz sob que
  hipótese trata.
- **Dado coletado por precaução** — parece prudente; vira passivo de segurança e de
  responsabilidade. Sinal: coleta-se campo que a finalidade declarada não usa.
- **Papel trocado no contrato** — parece detalhe; controlador que assina como operador
  aloca mal a responsabilidade. Sinal: o contrato não diz quem decide a finalidade do
  tratamento.
