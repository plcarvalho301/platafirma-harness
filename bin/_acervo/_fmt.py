#!/usr/bin/env python3
"""Formatador humano do acervo status. Lê o JSON do monitor em stdin."""
import sys, json

d = json.load(sys.stdin)
g, f, x, k = d["degraus"], d["fuga_por_degrau"], d["fora_da_escada"], d["chunks"]

print(f'ACERVO — medido em {d["medido_em"][:19]}  (postgres rag_extractor + minio, leitura direta)')
ci = d.get("contrato_do_indice") or {}
if ci:
    print("contrato do índice: " + " · ".join(f"{a}={b}" for a, b in ci.items()))
print()
print(f'  a  catalogadas ................ {g["a_catalogadas"]:>5}')
print(f'  b  armazenadas ................ {g["b_armazenadas"]:>5}   objeto conferido no store')
print(f'  c  ingeridas (chunkadas) ...... {g["c_ingeridas"]:>5}')
print(f'  d  embedded (texto) ........... {g["d_embedded"]:>5}   todo chunk textual com vetor')
print(f'  e  vetorizadas (metadado) ..... {g["e_vetor_meta"]:>5}   todo chunk textual com vetor de metadado')
print()
print(f'  fora da escada: {x["paginas_wiki"]} obras wiki:// — a obra É a página, nunca tem objeto')
print()
print("FUGA POR DEGRAU (0 em tudo = escada sem vazamento)")
for rot, ch in [
    ("catálogo aponta pro vazio", "catalogo_aponta_pro_vazio"),
    ("objeto sem documento", "objeto_sem_documento"),
    ("documento sem chunk", "documento_sem_chunk"),
    ("embedding parcial", "embedding_parcial"),
    ("embedding_meta parcial", "embedding_meta_parcial"),
    ("objeto no store sem obra", "objeto_no_store_sem_obra"),
    # arq:0027 — hoje 0 por construção (FK NOT NULL + CASCADE). Vigia, não descoberta.
    ("documento sem obra (órfão)", "documento_sem_obra"),
    ("chunk sem documento (órfão)", "chunk_sem_documento"),
]:
    # `.get`, não indexação dura: chave nova no formatador sem contraparte no SQL levantava
    # KeyError e derrubava a saída inteira por causa de uma linha.
    v = f.get(ch)
    if v is None:
        print(f'  ? {rot:.<34} {"ausente":>5}')
        continue
    print(f'  {"!" if v else " "} {rot:.<34} {v:>5}')
print()
print(f'  chunks: {k["total"]}  =  {k["textuais"]} textuais + {k["nao_textuais"]} não-textuais')
print(f'  dos textuais: {k["com_vetor"]} com vetor · {k["com_vetor_meta"]} com vetor de metadado')
print(f'  o não-textual (tabela, figura, artefato de layout) NUNCA recebe vetor: `embedding IS')
print(f'  NULL` cru conta esses e não mede pendência. A pendência real é "embedding parcial".')
