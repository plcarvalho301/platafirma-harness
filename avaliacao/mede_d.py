#!/home/claudinho/AI/.venv-harness/bin/python
"""
mede_d.py -- card #2908. Mede D (a metrica de DISPARO da fase D do epico #283):
    D = fracao de ordens (sessao_aberta) que tiveram >=1 consulta ao motor.

CHAVE do join: campo 'sessao', comum aos dois eventos em var/log/ops.
    - lado ordem:   evento 'sessao_aberta' (emitido por monta_sessao, server.py:863)
    - lado disparo: evento 'consulta'      (emitido por motor buscar, bin/motor:265)

RESSALVAS (Elias, handoff 20260827T235935 / server.py:138-142) -- NAO opcionais:
  R1. 'sessao' == mcp-session-id == a CONEXAO do cliente, nao a fita. 13/32 conexoes
      atendem mais de uma cadeira. O join prova 'mesma conexao no intervalo', nao
      'mesma fita'. D medido assim e um LIMITE SUPERIOR de disparo por conexao.
  R2. sessao '-' e o fallback (sem header/sem env). Casar '-' com '-' e ruido:
      DESCARTA-SE sessao '-' dos dois lados antes de medir.
  R3. ordem_id do lado 'consulta' e '-' (nao existe no request de run_command).
      Ancorar SO em 'sessao'.

ESTADO CONHECIDO (28/08): sessao_aberta grava '-' no caminho da fita (nao ha header
mcp-session-id em monta_sessao chamado pela fita -- server.py:696 cai no default).
Enquanto esse elo (materia TI/IA) nao povoar 'sessao' no lado da ordem, o join casa
em zero por construcao. Este script mede o que houver; o denominador valido so cresce
quando os dois lados gravarem sessao real. Ver #2908 / handoff a IA.
"""
import json, glob, collections

def carrega(padrao="/home/claudinho/AI/var/log/ops/ops-2026-08-*.jsonl"):
    abertas = collections.defaultdict(list)
    consultas = collections.defaultdict(list)
    for fn in sorted(glob.glob(padrao)):
        for l in open(fn):
            if not l.strip():
                continue
            try:
                e = json.loads(l)
            except Exception:
                continue
            ev = e.get("evento")
            s = e.get("sessao")
            if ev == "sessao_aberta":
                abertas[s].append(e)
            elif ev == "consulta":
                consultas[s].append(e)
    return abertas, consultas

def mede_d(abertas, consultas):
    ab = {s: v for s, v in abertas.items() if s and s != "-"}
    co = {s: v for s, v in consultas.items() if s and s != "-"}
    sessoes_ordem = set(ab)
    sessoes_com_consulta = set(co)
    denom = len(sessoes_ordem)
    num = len(sessoes_ordem & sessoes_com_consulta)
    return {
        "sessao_aberta_total": sum(len(v) for v in abertas.values()),
        "sessao_aberta_fallback_descartado": len(abertas.get("-", [])),
        "sessao_aberta_valida": denom,
        "consulta_total": sum(len(v) for v in consultas.values()),
        "consulta_valida_sessoes": len(sessoes_com_consulta),
        "sessoes_com_disparo": num,
        "D": (num / denom) if denom else None,
        "nota": "D=None => lado ordem sem sessao real; join immensuravel ate propagar (ver cabecalho)",
    }

if __name__ == "__main__":
    ab, co = carrega()
    print(json.dumps(mede_d(ab, co), ensure_ascii=False, indent=1))
