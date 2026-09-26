# Guia: Acrescentar classe de lint

Este guia descreve a ordem de passos para adicionar uma nova classe de verificação ao verbo `lint`, conforme `spec_lint` e `arq:0110`.

## Ordem de execução

A adição de uma classe de lint segue o fluxo estrito:
**lista → cabeçalho → golden record → teste de contrato → servir**

---

### 1. Lista de verificação (acervo)
Se a classe for baseada em lista, a lista de verificação deve ser registrada no acervo da casa antes de qualquer código:
```bash
acervo escrever casa lista-de-verificacao <chave>
```
O molde da lista define os campos:
- `id`: identificador estável da regra.
- `o que fere`: descrição do desvio.
- `fonte`: decisão ou norma de origem (`arq:NNNN`, `spec_*`, etc.).
- `detector`: método ou expressão de detecção.
- `severidade`: `bloqueante` (reprova no pre-commit) ou `aviso` (reportado pelo `lint`).
- `cura`: comando ou instrução exata de correção.
- `rev`: versão inteira da lista.

Se a classe for puramente estrutural de repositório (sem checklist externa, como `codigo` ou `fossil`), declara-se o tipo `repositorio`.

---

### 2. Implementação do predicado em `bin/_lint/`
Crie um módulo dedicado em `bin/_lint/<classe>.py` expondo a função de verificação:
```python
from .resultado import Apontamento

def verificar_<classe>(raiz, alvo=None, staged=False) -> list[Apontamento]:
    ...
    return apontamentos
```
Se a verificação trouxer regras que impeçam commit (como artefatos gerados ou vazamento de segredos), marque `severidade="bloqueante"` para integração com `pre-commit`.

---

### 3. Cabeçalho de `bin/lint` (Q1 / `arq:0110`)
Adicione a diretiva `# regua:` no cabeçalho de `bin/lint` declarando a chave da lista (sem versão, que é resolvida no servido):
```bash
# regua: <classe> lista-de-verificacao <chave>
```
Ou, se for sem lista:
```bash
# regua: <classe> repositorio
```
Atualize o registro interno `CLASSES_LINT` em `bin/lint` com o detector e descrição.

---

### 4. Golden Record
Registe a nova capacidade e o descritor da ferramenta no acervo da casa:
```bash
acervo escrever casa ferramental lint
```

---

### 5. Teste de contrato
Adicione os casos de teste da nova classe em `controle/tests/test_contrato_lint.py`:
- Execução limpa (exit `0`)
- Detecção de desvios com âncora e cura (exit `1`)
- Falha graciosa na ausência de dependência ou lista (exit `3` ou `5`)

Garanta que `controle/tests/VERDES` contenha a suíte de teste de contrato.

---

### 6. Servir e promover
Promova o harness pela esteira de release:
```bash
release promover platafirma-harness <sha>
release conferir verbo lint
```
