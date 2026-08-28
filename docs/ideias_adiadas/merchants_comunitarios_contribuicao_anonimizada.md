**Data de criação:** 27 de agosto de 2026  
**Status:** adiada e **removida do produto**  
**Decisão:** 27 de agosto de 2026 — retirar o opt-in “Contribuir com dados anonimizados” e o pipeline associado, até existir um desenho que resista a uma análise de LGPD.

---

## 1. Por que este documento existe

A ideia era boa de produto: melhorar o *cold start* da categorização com padrões que vários usuários já confirmaram (iFood → Alimentação, padaria local → Alimentação, etc.).

A implementação que existia **não era anonimização no sentido da Lei 13.709/2018**. Manter o interruptor no app, com o rótulo “dados anonimizados”, criava risco de transparência enganosa, dado de terceiro (PIX pessoa física) e contribuição sem efeito de esquecimento.

**Documentar a ideia neste arquivo não fere a lei.** Isto não é tratamento de dado pessoal: não há coleta, não há base de usuários, não há perfil. É memória de engenharia. O que a LGPD regula é **tratar dados de pessoas no sistema**, não anotar um desenho interno.

---

## 2. O que a feature tentava resolver

Problema: usuário novo (ou merchant que o catálogo fixo não cobre) recebe pouca sugestão até ter histórico próprio.

Hipótese: se N pessoas independentes categorizam o mesmo estabelecimento da mesma forma, o sistema pode promover uma **regra global** (`RegraCategorizacao` com `usuario=NULL`) e acelerar a primeira importação de todo mundo.

Isso era **complementar**, não substituto, de:

- catálogo estático `MerchantGlobal` (`categorizacao/data/merchants_br.json` + `seed_merchants_globais`);
- memória e regras **pessoais** (`MemoriaMerchantUsuario`, `RegraCategorizacao` do usuário);
- camadas fuzzy / `pg_trgm` / ML / LLM.

A categorização automática do titular **não dependia** deste opt-in. Remover a feature não reduz precisão nas contas atuais.

---

## 3. Como estava implementado (estado ao remover)

### 3.1 Superfície

- Checkbox em **Configurações → Preferências financeiras**
- Rótulo: *Contribuir com dados anonimizados*
- Ajuda: *Permite usar padrões agregados (sem descrições) para melhorar sugestões globais.*
- Campo: `Perfil.categorizacao_contribuir_globais` (`BooleanField`, default `False`)

### 3.2 Escrita (opt-in)

Em `categorizacao/services/learning.py`, após `processar_feedback_transacao` aceitar ou corrigir uma categoria (e **não** quando a fonte era LLM):

1. Resolver `merchant_key` (normalização da descrição; em PIX PF podia ser `pix_person:<nome>`).
2. Se o perfil tinha o opt-in ligado, chamar `_contribuir_agregacao_global`.
3. Upsert em `AgregacaoMerchantGlobal`:
   - `merchant_key`
   - `categoria_padrao_nome` = `categoria.nome` (inclusive categoria **customizada**)
   - `tipo` (receita/despesa)
   - `ocorrencias` incrementado
   - `usuarios_distintos` preenchido só na **criação** (`1`); **nunca incrementado de novo**

Não se gravava nessa tabela: descrição bruta, e-mail, valor, `usuario_id`.

### 3.3 Promoção a regra global (batch)

- Função: `agregar_contribuicoes_globais(min_usuarios=10)` (`K_ANONIMITY = 10`)
- Comando: `python manage.py agregar_contribuicoes_globais`
- Task Celery: `agregar_globais_task` (sem beat schedule no código)

Critério: `usuarios_distintos >= 10` **e** `ocorrencias >= 10`. Aí criava `RegraCategorizacao` global (`usuario=None`, `origem="seed"`, `tipo_regra="merchant_exact"`, `confianca_base=0.82`), desde que existisse categoria **padrão** com o mesmo nome.

### 3.4 Leitura no pipeline

O classificador **não lia** `contribuir_globais`. Só usava regras globais já existentes (`classificar_regras_globais`). O opt-in só alimentava o agregador.

---

## 4. Por que foi adiada (LGPD e qualidade)

Estes pontos precisam estar resolvidos **antes** de reviver a feature.

### 4.1 O rótulo “anonimizado” não se sustentava

LGPD arts. 5º, III e XI, e 12: dado anonimizado deixa de ser pessoal só se, com meios razoáveis, **não der para identificar**. Aqui:

- a mesma `merchant_key` continuava em `EventoCategorizacao` e na memória pessoal, **com usuário**;
- chave PIX PF era nome de pessoa (`pix_person:joao da silva`);
- o nome da categoria podia ser texto do usuário (“Aluguel do João”).

Isso é, no máximo, agregação/pseudonimização. Continua dado pessoal quando a chave identifica alguém.

### 4.2 Dados de terceiro

Opt-in do titular **não cobre** o nome de quem recebeu um PIX. Consentimento do usuário A não autoriza tratar o nome de B.

### 4.3 K-anonimato quebrado

`usuarios_distintos` não era atualizado nas contribuições seguintes. A promoção a regra global praticamente **nunca ocorria**, mas a linha identificável **já tinha sido gravada**.

### 4.4 Esquecimento

`AgregacaoMerchantGlobal` não tinha FK para o usuário. Excluir a conta **não revertia** a contribuição. Desligar o checkbox só parava gravações futuras.

### 4.5 Transparência

A Política de Privacidade **não descrevia** esse tratamento. O consentimento na UI era um checkbox curto, sem registro de aceite específico, sem revogação com efeito sobre o já agregado.

### 4.6 Dado sensível

Categoria de saúde (ou equivalente) + merchant único pode chegar a dado sensível (art. 11), que exigiria consentimento específico e destacado — inexistente.

### 4.7 Produto

Mesmo no melhor caso, o ganho era *cold start coletivo* de longo prazo (item P3 no roadmap de categorização). O catálogo `merchants_br.json` e o aprendizado **pessoal** já cobrem o caminho feliz.

---

## 5. O que foi removido do código (27/08/2026)

| Peça | Destino |
|------|---------|
| `Perfil.categorizacao_contribuir_globais` | campo removido (migration em `usuarios`) |
| Checkbox no form de preferências | removido |
| `_contribuir_agregacao_global` e `agregar_contribuicoes_globais` | removidos de `learning.py` |
| Model `AgregacaoMerchantGlobal` | removido (migration em `categorizacao`; **apaga a tabela e qualquer linha já gravada**) |
| Admin da agregação | removido |
| `agregar_globais_task` | removida |
| Comando `agregar_contribuicoes_globais` | removido |
| `PreferenciasCategorizacao.contribuir_globais` | removido |

**Não foi removido** (não é esta feature):

- `MerchantGlobal` e `seed_merchants_globais`
- camada `regra_global` (regras do sistema, se existirem por outro meio)
- `categorizacao_auto_aplicar` e `categorizacao_limiar_auto`
- memória/regras por usuário, fuzzy, ML, LLM

---

## 6. Como reviver com segurança (checklist)

Só retomar se **todos** os itens abaixo estiverem verdadeiros. Caso contrário, manter adiada.

1. **Não chamar de anonimizado** até um jurista e um teste de reidentificação sustentarem o termo. Linguagem honesta: “contribuir com padrões de estabelecimentos comerciais”.
2. **Política de Privacidade** descreve finalidade, o que entra, o que não entra, retenção, oposição e o que acontece na exclusão de conta.
3. **Bloquear PIX pessoa física** e qualquer `merchant_key` com cara de nome próprio (`pix_person:…`, nomes extraídos).
4. **Só categorias padrão do sistema**, nunca `categoria.nome` customizado.
5. **Allowlist ou heurística de merchant comercial** (catálogo + sinais corporativos), não padaria do bairro com nome de pessoa.
6. **K-anonimato real:** contar usuários distintos **sem persistir quem foi**; **não gravar** a linha identificável até `k ≥ N` (ex.: 10). Hash salgado descartável é uma via; incremento quebrado como o antigo **não** serve.
7. **Minimização:** merchant canônico + slug de categoria padrão + tipo. Sem descrição, sem valor, sem user id na tabela publicada.
8. **Revogação:** desligar para o futuro; se ainda houver dado ligável, apagar ou isolar. Se o agregado já for estatística irreversível *e* realmente anônimo, documentar isso na política **antes**.
9. **Base legal explícita:** consentimento informado (art. 8º) **ou** legítimo interesse com RIPD/LIA, só para merchants comerciais. Nomes de pessoa física não entram por LI.
10. **Dado sensível:** não promover (nem agregar) pares merchant×categoria de saúde/religião/vida sexual sem base específica.
11. **Testes:** contribuição bloqueada para PIX PF; k só sobe com usuários distintos; exclusão de conta e opt-out cobertos; pipeline de sugestão **não** depende do opt-in.
12. **Revisão jurídica** antes de GA. Este arquivo não substitui parecer.

Caminho de produto mais seguro, se o *cold start* for o objetivo: **crescer o catálogo `merchants_br.json`** (curadoria interna, sem dado de usuário) em vez de um pool comunitário.

---

## 7. Referências no repositório (histórico)

Código removido; git guarda o estado anterior. Pontos úteis para quem for reler o commit de remoção:

- `usuarios/models.py` — campo do perfil (removido)
- `categorizacao/services/learning.py` — escrita e promoção (removidas)
- `categorizacao/models.py` — `AgregacaoMerchantGlobal` (removido)
- `categorizacao/types.py` — `PreferenciasCategorizacao`
- Camada que **permanece** e não deve ser confundida: `categorizacao/services/layers/regras.py` (`classificar_regras_globais`) e `categorizacao/services/layers/fuzzy.py` (`MerchantGlobal`)

Documentos relacionados (não substituem este):

- `docs/seguranca/RELATORIO_SEGURANCA_LGPD.md`
- `docs/seguranca/01_SEGURANCA_PRIVACIDADE_COMPLIANCE.md`
- Plano interno de categorização: merchants comunitários listados como custo de privacidade/LGPD (P3)
