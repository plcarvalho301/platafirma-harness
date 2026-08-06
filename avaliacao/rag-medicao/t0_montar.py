#!/usr/bin/env python3
"""Monta os 10 arquivos T0-<NN>-<persona>.json: retorno inteiro da sonda +
estado de formalizacao (wiki e ADR) medido no mesmo instante."""
import json, sys, pathlib

PERSONA = sys.argv[1] if len(sys.argv) > 1 else "persona-nao-declarada"
BASE = pathlib.Path("/home/claudinho/AI/rag-medicao/T0")
brutas = json.load(open(BASE / "_sondas_brutas.json"))

W = lambda t, c, u: {"titulo": t, "criada_em": c, "ultima_edicao_em": u}
A = lambda r, p, c, u: {"repo": r, "caminho": p, "criada_em": c, "ultima_edicao_em": u}

CONH = "platafirma-conhecimento"
ARQ = "platafirma-arquitetura"

FORM = {
 "01": {
  "termo": "conceito / criterio de identidade",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Conceito"],
           "paginas_com_o_termo_no_titulo": [W("Estudos-ontologias/teia-de-conceitos", "2026-07-31T03:11:06Z", "2026-07-31T03:11:06Z")],
           "vizinhas_consultadas": [W("Ajuda:Glossário", "2026-08-02T21:17:32Z", "2026-08-04T12:33:42Z"),
                                     W("Estudos-ontologias", "2026-07-15T20:16:39Z", "2026-07-31T03:11:41Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [
             A(CONH, "ontologia/adr/0062-conceito-nao-estanteia.md", "2026-07-31T00:26:04-03:00", "2026-07-31T00:26:04-03:00"),
             A(CONH, "ontologia/adr/0063-teia-vizinhanca-por-conceito.md", "2026-07-31T00:26:04-03:00", "2026-07-31T00:26:04-03:00"),
             A(CONH, "ontologia/adr/0065-medida-de-qualidade-da-faceta-conceito.md", "2026-07-31T00:26:04-03:00", "2026-08-02T01:03:26-03:00")],
          "ausencia": False,
          "vizinhas_consultadas": [
             A(CONH, "ontologia/adr/0073-golden-record-de-obra.md", "2026-08-03T19:33:15-03:00", "2026-08-04T00:00:33-03:00"),
             A(CONH, "ontologia/adr/0074-nome-de-arquivo-nao-e-chave-nem-indice.md", "2026-08-04T01:38:03-03:00", "2026-08-04T01:38:03-03:00")]}},
 "02": {
  "termo": "tipo / papel",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Tipo", "Papel"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("Ajuda:Método/taxonomia", "2026-07-18T19:48:52Z", "2026-07-25T16:07:21Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [
             A(ARQ, "macro-global/capabilities/seguranca/decisions/0004-modelo-abac-com-papel-como-atributo.md", "2026-07-30T19:07:26-03:00", "2026-07-30T19:07:26-03:00")],
          "ausencia_para_tipo": True,
          "vizinhas_consultadas": []}},
 "03": {
  "termo": "arquitetura de software",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Arquitetura de software"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("Arquiteturas", "2026-07-15T20:16:36Z", "2026-07-28T03:05:47Z"),
                                     W("Engenharia-software", "2026-07-15T20:16:36Z", "2026-07-28T03:54:05Z"),
                                     W("Arquitetura:Índice", "2026-08-01T20:14:57Z", "2026-08-03T00:46:27Z"),
                                     W("Arquitetura:Topologia", "2026-07-29T12:14:18Z", "2026-08-03T00:45:22Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "arquivos_de_decisao_que_mencionam_o_termo_no_corpo": 0,
          "vizinhas_consultadas": [
             A(ARQ, "macro-global/decisions/0025-componente-e-substrato.md", "2026-08-03T18:50:58-03:00", "2026-08-03T18:57:44-03:00"),
             A(ARQ, "macro-global/decisions/0026-camada-de-fronteira.md", "2026-08-03T18:57:44-03:00", "2026-08-03T18:57:44-03:00")]}},
 "04": {
  "termo": "arquitetura de dados",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Arquitetura de dados"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("Engenharia-dados", "2026-07-28T03:54:05Z", "2026-07-28T03:54:05Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "arquivos_de_decisao_que_mencionam_o_termo_no_corpo": 0,
          "vizinhas_consultadas": []}},
 "05": {
  "termo": "governanca de dados",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Governança de dados", "Governanca de dados"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("Governo-digital", "2026-07-15T20:16:38Z", "2026-07-28T03:05:48Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "arquivos_de_decisao_que_mencionam_o_termo_no_corpo": 0,
          "vizinhas_consultadas": []}},
 "06": {
  "termo": "dominio",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Domínio", "Dominio"],
           "paginas_com_o_termo_no_titulo": [W("Ajuda:Criar um domínio", "2026-07-15T20:16:40Z", "2026-08-04T05:24:23Z")],
           "vizinhas_consultadas": [W("Ajuda:Explorar por faceta", "2026-07-16T02:50:34Z", "2026-07-28T03:46:53Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [
             A(CONH, "ontologia/adr/0057-dominio-platafirma-autorreferente.md", "2026-07-30T18:06:34-03:00", "2026-07-30T18:06:34-03:00"),
             A(CONH, "ontologia/adr/0059-gestao-organizacional-e-dominio.md", "2026-07-30T18:06:34-03:00", "2026-07-30T18:06:34-03:00"),
             A(CONH, "ontologia/adr/0069-dominio-declara-rotulo-e-recorte.md", "2026-08-02T17:30:51-03:00", "2026-08-02T17:30:51-03:00"),
             A(ARQ, "macro-global/decisions/0009-vocabulario-de-dominio-unico-por-instancia.md", "2026-07-29T17:41:50-03:00", "2026-07-30T02:28:35-03:00"),
             A(ARQ, "macro-global/decisions/0011-hierarquia-de-dominio-em-campo.md", "2026-07-29T17:41:50-03:00", "2026-07-30T02:28:35-03:00"),
             A(ARQ, "macro-global/decisions/0012-dominio-e-entidade-identificavel.md", "2026-07-29T17:41:50-03:00", "2026-07-30T02:28:35-03:00")],
          "ausencia": False, "vizinhas_consultadas": []}},
 "07": {
  "termo": "inteligencia",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Inteligência", "Inteligencia"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("IA", "2026-07-15T20:16:39Z", "2026-07-26T03:53:51Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "arquivos_de_decisao_que_mencionam_o_termo_no_corpo": [
             A(CONH, "ontologia/adr/0069-dominio-declara-rotulo-e-recorte.md", "2026-08-02T17:30:51-03:00", "2026-08-02T17:30:51-03:00")],
          "vizinhas_consultadas": []}},
 "08": {
  "termo": "criptografia pos-quantica",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Criptografia pós-quântica", "Criptografia pos-quantica", "PQC"],
           "paginas_com_o_termo_no_titulo": [],
           "vizinhas_consultadas": [W("Seguranca-privacidade", "2026-07-15T20:16:39Z", "2026-08-01T16:17:39Z"),
                                     W("Frente:modulo-firma/backlog-canalseguroPQC-draft", "2026-07-14T16:46:49Z", "2026-08-01T16:14:44Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "arquivos_de_decisao_que_mencionam_o_termo_no_corpo": 0,
          "vizinhas_consultadas": []}},
 "09": {
  "termo": "decisao arquitetural (ADR)",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Decisão arquitetural", "ADR"],
           "paginas_com_o_termo_no_titulo": [
              W("Arquitetura:ADRs", "2026-08-03T00:44:25Z", "2026-08-03T00:44:25Z"),
              W("Arquitetura:Registro-de-decisoes", "2026-08-03T00:44:25Z", "2026-08-03T00:44:25Z"),
              W("PlataFirma:Decisões/adrs", "2026-07-29T20:45:12Z", "2026-08-03T00:44:25Z"),
              W("Frente:mdm-rh/adr", "2026-07-28T13:01:05Z", "2026-08-01T03:22:11Z")],
           "vizinhas_consultadas": []},
  "adr": {"adr_com_o_termo_no_titulo": [
             A(ARQ, "macro-global/decisions/0005-politica-do-registro-de-decisoes.md", "2026-07-29T15:41:28-03:00", "2026-08-01T13:22:20-03:00"),
             A(ARQ, "macro-global/decisions/0006-adocoes-do-registro-institucional.md", "2026-07-29T15:41:28-03:00", "2026-07-30T02:28:35-03:00"),
             A(ARQ, "macro-global/decisions/0015-forma-da-adr.md", "2026-07-30T02:11:23-03:00", "2026-08-04T08:45:49-03:00")],
          "ausencia": False, "vizinhas_consultadas": []}},
 "10": {
  "termo": "curadoria de acervo",
  "wiki": {"pagina_com_titulo_igual_ao_termo": None,
           "titulos_testados_ausentes": ["Curadoria de acervo"],
           "paginas_com_o_termo_no_titulo": [
              W("Ajuda:Operar o acervo", "2026-08-03T00:43:51Z", "2026-08-03T00:43:51Z"),
              W("Ajuda:Sincronizar o acervo", "2026-08-03T12:35:12Z", "2026-08-03T12:35:12Z"),
              W("PlataFirma:Ops/operar-o-acervo", "2026-08-01T18:06:50Z", "2026-08-04T05:40:58Z")],
           "nota_de_medida": "nenhum titulo contem 'curadoria'; os acima contem 'acervo'",
           "vizinhas_consultadas": [W("Ajuda:Fichar um livro", "2026-07-16T05:20:39Z", "2026-07-28T11:54:24Z")]},
  "adr": {"adr_com_o_termo_no_titulo": [], "ausencia": True,
          "adr_com_acervo_no_titulo": [
             A(CONH, "ontologia/adr/0061-regimes-de-entrada-no-acervo.md", "2026-07-31T00:26:04-03:00", "2026-07-31T00:26:04-03:00")],
          "arquivos_de_decisao_que_mencionam_curadoria_no_corpo": [
             "ontologia/adr/0056-colecao-eixo-de-proveniencia.md",
             "ontologia/adr/0062-conceito-nao-estanteia.md",
             "ontologia/adr/0064-protocolo-de-leitura-da-teia.md",
             "ontologia/adr/0065-medida-de-qualidade-da-faceta-conceito.md",
             "ontologia/adr/0066-estado-de-obra-dois-eixos.md",
             "ontologia/adr/0072-endereco-e-a-moradia-da-obra.md",
             "ontologia/adr/0073-golden-record-de-obra.md"],
          "vizinhas_consultadas": []}},
}

MEDIDA = {
 "medido_em": "2026-08-04T16:45:00Z",
 "fonte_wiki": "MediaWiki API interna (127.0.0.1:8080), prop=revisions, primeira e ultima revisao",
 "fonte_adr": "git log --diff-filter=A (criacao) e git log -1 (ultima edicao) nos clones locais",
 "repos_sha": {"platafirma-arquitetura": "3158694036f799bca47ef8d6d56420ee37a3a416",
                "platafirma-conhecimento": "5b6c364c14005a2332ed7f6279a7a7bceccc6225"},
 "criterio": "'nomeia o termo' = o termo aparece no titulo da pagina ou no nome do arquivo da ADR. Ausencia registrada explicitamente.",
}

for nn, d in brutas.items():
    ret = d["retorno"]
    doc = {
      "sonda": "T0",
      "n": nn,
      "persona": PERSONA,
      "pergunta": d["pergunta"],
      "parametros_congelados": {"texto": "secao", "k": 8, "dominio": None,
                                 "subdominio": None, "frente": None, "colecao": None},
      "chamada_em": d["chamada_em"],
      "acervo_sha": (ret.get("indice") or {}).get("acervo_sha"),
      "retorno": ret,
      "formalizacao": dict(FORM[nn], **{"medida": MEDIDA}),
    }
    p = BASE / f"T0-{nn}-{PERSONA}.json"
    json.dump(doc, open(p, "w"), ensure_ascii=False, indent=1)
    print(p)
