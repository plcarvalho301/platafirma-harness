
# tool_manifest — claudinho-seguranca
 
Fonte canônica: `PlataFirma:Sec/ferramental` na wiki. Este arquivo é cópia de trabalho para o Project.
Executável: `platafirma-core:deploy/seguranca/` (commit `d2f5345`).
 
Ambiente: Linux Mint 22.3 (base Ubuntu 24.04), usuário `claudinho`, **sem sudo**.
35 ferramentas, todas FOSS, todas testadas contra alvo real — não apenas `--version`.
 
---
 
## Instalar
 
```
bash ~/AI/platafirma-core/deploy/seguranca/instala-ferramental-seguranca.sh
```
 
Idempotente, sem privilégio. Binário estático em `~/AI/bin`, ferramenta Python isolada
por `uv tool` em `~/.local/bin`, venv de biblioteca em `~/AI/.venv-seg`.
 
Bloco que exige root (pedido ao `megafone`, sempre em duas linhas):
 
```
sudo apt update
sudo apt install -y oathtool ninja-build ldap-utils nmap openscap-utils libimage-exiftool-perl
```
 
## Head — identidade, autenticação, federação, autorização
 
| ferramenta | serve para |
|---|---|
| `jwt` | decodificar/validar token do Keycloak; claims `dominio:papel:escopo` e `aud` |
| `oauth2c` | disparar fluxo OIDC ponta a ponta — authorization code, PKCE, client credentials, device code |
| `step` | discovery OIDC, JWKS, certificado, mTLS, JWT/JWK cru |
| `hurl` | fluxo HTTP como arquivo versionado — teste que vai pro repo |
| `opa` | prototipar Rego. **Não é escolha de motor de PDP** — decisão aberta |
| `oathtool` | TOTP; é o que exercita AAL2 |
| `ldapsearch` / `ldapwhoami` | federação LDAP (por antecedência; nada em uso hoje) |
| `keepassxc-cli` | cofre `.kdbx` |
| `kcadm` | wrapper do `kcadm.sh`, que vive dentro do contêiner |
 
`~/AI/.venv-seg`: `pyjwt[crypto]`, `authlib`, `cryptography`, `jwcrypto`, `python-jose`, `requests`.
 
## Dados e privacidade
 
| ferramenta | serve para |
|---|---|
| `gitleaks` | segredo no histórico git |
| `trufflehog` | segredo com verificação ativa da credencial |
| `detect-secrets` | baseline e hook de pré-commit |
| `exiftool` | metadado em arquivo publicado |
 
## Plataforma e aplicações
 
| ferramenta | serve para |
|---|---|
| `trivy` | CVE em imagem/fs/repo + misconfig de Dockerfile e compose |
| `grype` | CVE via SBOM — segunda opinião ao trivy |
| `syft` | SBOM (SPDX/CycloneDX) |
| `dockle` | CIS Docker Benchmark por imagem |
| `hadolint` | lint de Dockerfile |
| `semgrep` / `bandit` | SAST multi-linguagem e Python |
| `pip-audit` / `osv-scanner` | CVE em dependência |
| `yamllint` | sanidade de compose e manifesto |
| `pre-commit` | **o gatilho** dos scanners acima |
| `lynis` | hardening do host, independente de distro |
| `docker-bench-security` | CIS Docker Benchmark do daemon |
| `nmap` | superfície exposta |
 
## Criptografia e chaves
 
| ferramenta | serve para |
|---|---|
| `age` / `age-keygen` | cifra de segredo em repouso |
| `sops` | cifrar campo de arquivo estruturado com backend age |
| `openssl-pqc` | OpenSSL com oqs-provider — ML-KEM, ML-DSA, SLH-DSA |
| `cosign` / `minisign` | assinar e verificar artefato |
| `testssl.sh` / `sslyze` | TLS de endpoint público |
| `ssh-audit` | algoritmos do sshd |
| `restic` | backup cifrado (instalado, não configurado) |
 
### PQC
 
```
bash ~/AI/platafirma-core/deploy/seguranca/build-oqs.sh
openssl-pqc list -providers
```
 
Disponíveis: `mlkem512/768/1024`, `mldsa44/65/87`, `slh-dsa-sha2-128s` e híbridos
(`x25519_mlkem768`, `p256_mldsa44`, `rsa3072_mldsa44`). Verificado ponta a ponta:
chave ML-DSA-65, assinatura e verificação.
 
Limitação: chave ML-KEM não serializa em PEM via `genpkey` nesta versão. KEM se
exercita no handshake, não como chave em arquivo.
 
## Governança e catálogo de controles
 
```
oscap-casco [cis_level1_server|cis_level1_workstation|cis_level2_server|cis_level2_workstation|stig]
oscap-casco-falhas ~/AI/var/oscap/eval-<perfil>-<stamp>.log
ssg-deriva
```
 
Primeira avaliação (02/08/2026, CIS Level 1 workstation, sem root):
**234 pass · 103 fail · 50 notapplicable · 11 error**.
 
---
 
## Comandos criados nesta passada
 
| comando | o que é |
|---|---|
| `openssl-pqc` | OpenSSL do sistema com o provider PQC carregado via `OPENSSL_CONF` próprio |
| `kcadm` | `kcadm.sh` do Keycloak, que só existe dentro do contêiner |
| `oscap-casco` | avaliação CIS contra o datastream derivado, com placar e relatório |
| `oscap-casco-falhas` | extrai as regras em falha de um log do oscap |
| `ssg-deriva` | regenera o datastream derivado (ver armadilha do CPE) |
 
## Armadilhas
 
**Datastream de Ubuntu descarta toda regra no Mint.** O conteúdo SCAP checa a plataforma
por CPE (`ID=ubuntu`); o Mint responde `ID=linuxmint` e as 399 regras saem `notapplicable`
— sem erro, código de saída zero. Um placar de 399 `notapplicable` lê-se como "nada a
corrigir" e significa "nada foi avaliado". `ssg-deriva` remove só o `platform idref` do
CPE de sistema operacional, preservando os 259 de applicability por regra.
 
**O resultado do `oscap-casco` é conteúdo derivado.** Não é SCAP oficial validado. Serve
como checklist técnico e mapa de controle, não como evidência de conformidade formal.
 
**API anônima do GitHub limita a 60 req/h.** Estourado o teto, devolve JSON de erro em vez
de assets, e o instalador reporta "asset não encontrado" para ferramenta que existe. O
instalador usa `gh auth token` quando disponível.
 
**PyPI não tem assinatura de pacote.** As ferramentas via `uv tool` chegam por HTTPS e
nome. Risco aceito e registrado; mitigação proporcional é fixar versão.
 
**`age` vem do arquivo do Ubuntu, não do upstream.** O release do GitHub não publica hash
nem assinatura, e é a ferramenta que custodia segredo. Custo: 1.1.1 em vez da mais recente.
 
**`step-cli` instala o binário com outro nome** (`step-cli`, não `step`), e só publica
`.deb`/`.rpm`.
 
**`openssl-pqc` não é o `openssl`.** Mesmo binário, `OPENSSL_CONF` e `LD_LIBRARY_PATH`
diferentes. `openssl` puro não achar `mldsa65` é o esperado.
 
## Procedência
 
```
bash ~/AI/platafirma-core/deploy/seguranca/verifica-procedencia.sh
bash ~/AI/platafirma-core/deploy/seguranca/verifica-procedencia-hash-por-asset.sh
```
 
**15 de 15 binários com cadeia de verificação.** Treze por checksum publicado no release,
`minisign` por assinatura Ed25519 contra a chave pública do autor, `age` pela cadeia do
arquivo Ubuntu. `jd` foi removido — não publica hash nem assinatura, e uso marginal não
justifica binário não verificado.
 
Critério para o que vier depois: ferramenta sem procedência só entra se for insubstituível,
e entra com o risco escrito.
 
## Ausente por decisão
 
| não instalado | por quê |
|---|---|
| `presidio` (PII) | spacy + modelo, qualidade mediana em português, sem volume que justifique |
| `regal` (linter Rego) | só serve se OPA virar o PDP; instalar antes enviesa a decisão |
| `checkov` / `kics` | `trivy config` já cobre compose e Dockerfile |
| `hashcat` / `john` | não há corpo de hash a auditar |
| `auditd` | é política de log de auditoria (CIS Control 8), não ferramental |
| `step-ca` | não é ferramental, é infraestrutura nova |
