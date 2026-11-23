-- rastro — a chave humana de cada ficha do caminho das fichas entregues na página.
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «A caminhada pelas ligações».
-- $1 uuid[]  os identificadores das fichas do caminho
SELECT uuid, chave_humana FROM casa.ficha WHERE uuid = ANY ($1::uuid[]);
