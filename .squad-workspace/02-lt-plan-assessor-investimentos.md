# Plano Técnico — Assessor de Investimentos com IA

> Produzido pelo Agente LT (Tech Lead). Base: `.squad-workspace/01-po-spec-assessor-investimentos.md`.
> Stack: Flask 3 + SQLAlchemy + SQLite + Jinja2 + Bootstrap 5 (conforme SQUAD.md).

---

## Resumo da Abordagem

O assessor é implementado como um **novo blueprint `assessor`** que:
1. Coleta a carteira do mês de referência (mesma lógica "mês atual, não-futuro" já usada no dashboard) + o perfil do investidor.
2. Envia esse contexto para a **API da Claude** (SDK oficial `anthropic`, modelo `claude-opus-4-8`) **com a ferramenta server-side `web_search`** ligada — a própria Anthropic executa as buscas de Selic/CDI/IPCA, notícias e fundos/previdência (por nome/CNPJ). **Não é necessário integrar BCB/CVM em Python.**
3. Recebe um **relatório em Markdown** estruturado, persiste no histórico e renderiza em HTML.

Chamada **síncrona** (POST → gera → salva → redireciona para o relatório), com spinner no front — adequada a um app local de usuário único e muito mais simples que streaming/polling.

---

## 1. Análise de Impacto

**Arquivos a MODIFICAR:**
| Arquivo | O que muda |
|---------|-----------|
| `app/__init__.py` | Registrar `assessor_bp`; adicionar `_migrate_investimentos_base()` (coluna `cnpj`); `db.create_all()` já cria as tabelas novas; registrar filtro Jinja `markdown` |
| `app/templates/base.html` | Novo sub-item de nav "Assessor IA" sob Investimentos |
| `app/routes/investimentos.py` | `CarteiraForm`: novo campo `cnpj` (opcional); `nova_carteira`/`editar_carteira` persistem `cnpj` na `InvestimentoBase` |
| `app/templates/investimentos/carteira_form.html` | Campo de input para CNPJ |
| `app/models/investimento_base.py` | Nova coluna `cnpj` (opcional) |
| `requirements.txt` | Adicionar `anthropic` e `markdown` |
| `config.py` | Expor `ANTHROPIC_API_KEY` (lido do `.env` já carregado por `load_dotenv`) |
| `.env.example` (se existir) / instrução ao usuário | Documentar `ANTHROPIC_API_KEY` |

**Arquivos a CRIAR:**
| Arquivo | Propósito |
|---------|-----------|
| `app/models/perfil_investidor.py` | Model singleton do perfil de risco/objetivos |
| `app/models/analise_investimento.py` | Model do histórico de análises geradas |
| `app/assessor_ia.py` | Serviço de IA: montar contexto da carteira + chamar a API + tratar erros/pause_turn + system prompt |
| `app/routes/assessor.py` | Blueprint `assessor` (index, perfil, analisar, ver_analise) + forms |
| `app/templates/assessor/index.html` | Painel: perfil atual + botão "Analisar carteira" + histórico |
| `app/templates/assessor/perfil_form.html` | Cadastro/edição do perfil |
| `app/templates/assessor/analise.html` | Exibição do relatório + metadados + ressalva |

**Dependências externas:**
- `anthropic` (SDK oficial da Claude) — obrigatória.
- `markdown` (Python-Markdown) — renderizar o relatório MD → HTML.

---

## 2. Decisões de Arquitetura

**D1 — Superfície da API: uma chamada `messages.create` com `web_search` server-side (não Managed Agents).**
- *Justificativa:* o caso é "montar contexto → 1 análise → relatório". O tier mais simples que atende (start simple). `web_search_20260209` (suportado no Opus 4.8) traz macro/notícias/fundos sem cliente HTTP próprio. Sem loop de agente, sem sandbox, sem infra nova.
- *Alternativa descartada:* Managed Agents / agente no Console — mais plataforma do que o necessário; adiciona hospedagem, sessões e credenciais sem ganho para este fluxo.

**D2 — Relatório em Markdown (não JSON schema estrito).**
- *Justificativa:* o deliverable é um relatório para leitura. Markdown renderizado cobre bem; evita a incerteza de combinar `output_config.format` (structured outputs) com ferramentas server-side. Simples de persistir e exibir.
- *Alternativa descartada:* saída JSON estruturada por ativo — mais frágil junto de web_search e mais UI para montar; fica como evolução futura se quisermos tabela interativa de recomendações.

**D3 — Chamada síncrona com spinner (não streaming/async).**
- *Justificativa:* app local, usuário único, uma análise por vez. `max_tokens` moderado (~8000) fica bem abaixo dos limites de timeout do SDK. Muito menos complexidade.
- *Alternativa descartada:* streaming/SSE/polling — desnecessário para 1 requisição pontual.

**D4 — Dados externos via `web_search`, incluindo fundos/previdência por CNPJ.**
- *Justificativa:* honra o escopo (macro + notícias + cota de fundos/previdência) sem pipeline CVM/BCB dedicado nesta entrega. O CNPJ do produto (novo campo opcional na carteira) é passado ao modelo, que busca a cota/rentabilidade.
- *Alternativa descartada:* integração direta CVM (CSV diário) / BCB SGS — maior esforço; fica como evolução se a precisão da busca não bastar (registrado como risco).

**D5 — Perfil como model singleton (padrão `ParametroProjecao`).**
- *Justificativa:* consistente com o padrão de "parâmetros" do projeto (uma linha de configuração). Simples de ler/gravar.
- *Alternativa descartada:* perfil por usuário — o app é de usuário único; desnecessário.

**D6 — Novo blueprint `assessor` (não estender `investimentos.py`).**
- *Justificativa:* `investimentos.py` já tem ~900 linhas; separar mantém coesão. Continua no domínio de investimentos via nav.
- *Alternativa descartada:* rotas dentro de `investimentos.py` — aumentaria o acoplamento e o tamanho do arquivo.

**D7 — Reuso da lógica de risco/FGC existente.**
- *Justificativa:* `TIPOS_FGC`, `FGC_LIMITE` e o padrão de concentração por emissor de `painel_risco` são importados/reaproveitados para montar o contexto — evita duplicar regra.

---

## 3. Schema de Banco de Dados

**Nova coluna (migração inline, padrão `_migrate_*`):**
- `investimentos_base.cnpj` — `VARCHAR(20)`, nullable (CNPJ do fundo/previdência p/ busca de cota).

```python
def _migrate_investimentos_base():
    with db.engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text('PRAGMA table_info(investimentos_base)'))]
        if 'cnpj' not in cols:
            conn.execute(text('ALTER TABLE investimentos_base ADD COLUMN cnpj VARCHAR(20)'))
        conn.commit()
```

**Novas tabelas (criadas automaticamente por `db.create_all()` — basta os models existirem/importados):**

`perfis_investidor` (singleton — 1 linha):
| Campo | Tipo | Constraint |
|-------|------|-----------|
| id | Integer | PK |
| perfil | String(20) | not null, default 'Moderado' (Conservador/Moderado/Arrojado) |
| horizonte | String(20) | not null, default 'medio' (curto/medio/longo) |
| objetivos | String(500) | nullable (lista separada por vírgula ou texto) |
| necessidade_liquidez | String(20) | nullable (baixa/media/alta) |
| restricoes | String(500) | nullable (ex.: "não quero risco alto") |
| observacao | String(500) | nullable |
| atualizado_em | DateTime | default now |

`analises_investimento` (histórico):
| Campo | Tipo | Constraint |
|-------|------|-----------|
| id | Integer | PK |
| criado_em | DateTime | default now |
| mes_ref | Integer | not null |
| ano_ref | Integer | not null |
| perfil_snapshot | String(500) | nullable (perfil vigente no momento) |
| indicadores | String(300) | nullable (Selic/CDI/IPCA citados) |
| total_carteira | Numeric(15,2) | nullable (snapshot) |
| modelo | String(50) | nullable (ex.: 'claude-opus-4-8') |
| relatorio_md | Text | not null (relatório em Markdown) |

> Importante: importar os dois models novos em `app/__init__.py` (como já é feito com `SaldoConta`/`ParcelaEntradaFixa`) para garantir o `create_all`.

---

## 4. Tarefas Técnicas

```
TASK-1: Model PerfilInvestidor (singleton)
- Arquivo(s): app/models/perfil_investidor.py
- Complexidade: P
- Depende de: nenhuma
- Descrição: Criar model `PerfilInvestidor` (__tablename__='perfis_investidor') com os campos da seção 3.
  Seguir o padrão de ParametroProjecao. atualizado_em = db.Column(db.DateTime, default=datetime.utcnow).
- Aceite Técnico: `from app.models.perfil_investidor import PerfilInvestidor` importa sem erro; tabela criada por create_all.
```

```
TASK-2: Model AnaliseInvestimento (histórico)
- Arquivo(s): app/models/analise_investimento.py
- Complexidade: P
- Depende de: nenhuma
- Descrição: Criar model `AnaliseInvestimento` (__tablename__='analises_investimento') com os campos da seção 3.
  criado_em default now; relatorio_md como db.Text.
- Aceite Técnico: import OK; tabela criada por create_all.
```

```
TASK-3: Migração + wiring no create_app
- Arquivo(s): app/__init__.py, app/models/investimento_base.py
- Complexidade: P
- Depende de: TASK-1, TASK-2
- Descrição:
  (a) Em investimento_base.py, adicionar coluna `cnpj = db.Column(db.String(20), nullable=True)`.
  (b) Em __init__.py: importar os models novos (PerfilInvestidor, AnaliseInvestimento) no topo (como SaldoConta);
      criar `_migrate_investimentos_base()` (seção 3) e chamá-la no bloco `with app.app_context()` após os demais _migrate;
      registrar o blueprint assessor (ver TASK-5); registrar filtro Jinja `markdown` (ver TASK-6).
- Aceite Técnico: app sobe sem erro; `PRAGMA table_info(investimentos_base)` mostra `cnpj`; tabelas perfis_investidor e analises_investimento existem.
```

```
TASK-4: Serviço de IA (app/assessor_ia.py)
- Arquivo(s): app/assessor_ia.py
- Complexidade: G
- Depende de: TASK-1, TASK-2
- Descrição: Implementar:
  * `montar_contexto_carteira() -> dict/str`: seleciona o mês de referência (mais recente <= mês atual — MESMA
     lógica do dashboard corrigido em main.py), lista por ativo {nome, tipo, instituicao, emissor, cnpj (da base),
     risco, valor, vencimento, rendimento_real, rendimento_projetado, confirmado}, e agrega: total, total previdência
     vs demais, e exposição por emissor vs FGC (reutilizar TIPOS_FGC e FGC_LIMITE de app.routes.investimentos).
     Retornar também mes_ref/ano_ref e total_carteira.
  * `montar_texto_perfil(perfil) -> str`: descreve o perfil para o prompt (ou "sem perfil cadastrado").
  * `SYSTEM_PROMPT`: define papel (assessor), estrutura obrigatória do relatório em Markdown com seções
     [Resumo Executivo, Diagnóstico da Carteira, Análise de Risco (aderência ao perfil), Contexto de Mercado
     (Selic/CDI/IPCA + notícias), Recomendações (por ativo: Manter/Reforçar/Reduzir/Sair + justificativa; e aportes
     por classe), Ressalva], regras de negócio 4/5/6/8 da spec, Previdência em bloco separado, formato R$ brasileiro,
     e instrução para usar web_search para macro/notícias/cota de fundos por nome/CNPJ.
  * `gerar_analise(perfil, contexto) -> dict`: chama anthropic.Anthropic().messages.create(
       model='claude-opus-4-8', max_tokens=8000, thinking={'type':'adaptive'},
       output_config={'effort':'high'},
       tools=[{'type':'web_search_20260209','name':'web_search'}],
       system=SYSTEM_PROMPT, messages=[{'role':'user','content': <contexto+perfil serializados>}]).
     Tratar stop_reason == 'pause_turn' com re-envio (loop, máx ~5) — server tool pode pausar.
     Extrair o texto final (blocos type=='text'); retornar {relatorio_md, modelo, indicadores?}.
     Se ANTHROPIC_API_KEY ausente → levantar erro claro; capturar anthropic.APIError/APIConnectionError e propagar
     mensagem amigável (a rota faz o flash).
- Aceite Técnico: com ANTHROPIC_API_KEY válida e carteira populada, `gerar_analise` retorna um markdown não-vazio
  com as seções esperadas; sem a chave, erro claro; sem carteira, o chamador não invoca (ver TASK-5).
- Observação de segurança: nunca logar a chave; enviar apenas dados da carteira (sem segredos) no prompt.
```

```
TASK-5: Blueprint e rotas (app/routes/assessor.py) + forms + registro
- Arquivo(s): app/routes/assessor.py, app/__init__.py (registro)
- Complexidade: G
- Depende de: TASK-1, TASK-2, TASK-4, TASK-6
- Descrição: Criar `assessor_bp = Blueprint('assessor', __name__, url_prefix='/assessor')`.
  Forms (Flask-WTF): `PerfilForm` (SelectField perfil, SelectField horizonte, SelectField necessidade_liquidez,
  StringField/TextAreaField objetivos, restricoes, observacao, SubmitField). Botão analisar via form simples com csrf.
  Rotas (todas @login_required):
   * GET  '/'            -> index: carrega perfil (singleton), lista analises (desc por criado_em, limit ~20),
                           tem_carteira (bool: existe posição no mês de referência). Template assessor/index.html.
   * GET/POST '/perfil'  -> cria/edita o singleton PerfilInvestidor (PRG). Template assessor/perfil_form.html.
   * POST '/analisar'    -> valida carteira não-vazia (senão flash + redirect index); monta contexto (assessor_ia),
                           chama gerar_analise; em sucesso, persiste AnaliseInvestimento e redireciona para
                           ver_analise(id); em erro, flash 'danger' e redirect index. NÃO salvar análise parcial.
   * GET  '/analise/<int:id>' -> ver_analise: carrega AnaliseInvestimento; renderiza relatorio_md -> HTML
                           (filtro markdown) e passa como relatorio_html. Template assessor/analise.html.
  Registrar o blueprint em app/__init__.py.
- Aceite Técnico: /assessor/ responde 200 logado (302 deslogado); fluxo perfil salva; /analisar com carteira gera e
  redireciona ao relatório; carteira vazia mostra aviso; análise salva aparece no histórico e reabre.
```

```
TASK-6: Dependências, config e filtro markdown
- Arquivo(s): requirements.txt, config.py, app/__init__.py, .env.example (se existir)
- Complexidade: P
- Depende de: nenhuma
- Descrição:
  * requirements.txt: adicionar `anthropic>=0.69.0` e `markdown>=3.5`.
  * config.py: `ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')` (load_dotenv já roda). O SDK também lê do
    ambiente automaticamente; expor no Config facilita checagem de presença na rota.
  * app/__init__.py: registrar filtro `markdown` -> usar biblioteca markdown (extensões ['extra','sane_lists']),
    retornar `markupsafe.Markup(html)` para uso com |safe controlado (conteúdo vem da nossa própria chamada de IA).
  * .env.example: documentar `ANTHROPIC_API_KEY=`.
- Aceite Técnico: `pip install -r requirements.txt` instala; filtro `{{ '**oi**' | markdown }}` renderiza <strong>;
  Config.ANTHROPIC_API_KEY reflete o .env.
```

```
TASK-7: Templates do assessor
- Arquivo(s): app/templates/assessor/index.html, perfil_form.html, analise.html
- Complexidade: M
- Depende de: contrato de rotas/contexto da TASK-5 (pode ser feito em paralelo usando o contrato abaixo)
- Descrição: Todos herdam de base.html (padrão do projeto).
   * index.html: card do Perfil (mostra perfil/horizonte/objetivos ou CTA "Cadastrar perfil" se None);
     botão grande "Analisar carteira" (form POST para assessor.analisar com csrf_token); aviso se !tem_carteira;
     lista/tabela do histórico (data, mês ref, link "ver"). Spinner ao submeter (JS: desabilita botão + texto
     "Analisando…").
   * perfil_form.html: formulário do PerfilForm (selects + textareas), com dica de que o perfil personaliza a análise.
   * analise.html: cabeçalho com data/mês ref/indicadores; corpo = {{ analise.relatorio_md | markdown | safe }}
     (ou relatorio_html); box de RESSALVA destacado (alert) reforçando "informativo, gerado por IA, não é
     recomendação profissional"; botão voltar.
  Contrato de contexto:
     index      -> perfil (obj|None), analises (list), tem_carteira (bool)
     perfil_form-> form
     analise    -> analise (obj), relatorio_html (str)  [ou usar filtro markdown no template]
- Aceite Técnico: telas renderizam sem erro (validar com test client + login forçado); markdown vira HTML; ressalva visível.
```

```
TASK-8: Link de navegação
- Arquivo(s): app/templates/base.html
- Complexidade: P
- Depende de: TASK-5 (nome das rotas)
- Descrição: Adicionar sub-item "Assessor IA" sob Investimentos (mesmo padrão dos sub-itens Carteira/Painel de Risco,
  com style="padding-left:2.2rem;" e classe active quando request.blueprint == 'assessor'). Ícone bootstrap (ex.: bi-robot).
  Ajustar a condição `active` do item pai "Investimentos" para não conflitar (excluir endpoints do assessor, como já
  faz com painel_risco/carteira).
- Aceite Técnico: link aparece e marca ativo corretamente ao navegar.
```

```
TASK-9: Campo CNPJ na Carteira
- Arquivo(s): app/routes/investimentos.py, app/templates/investimentos/carteira_form.html
- Complexidade: P
- Depende de: TASK-3 (coluna cnpj na base)
- Descrição: Em CarteiraForm adicionar `cnpj = StringField('CNPJ (fundo/previdência)', validators=[Optional(), Length(max=20)])`.
  Em nova_carteira e editar_carteira, gravar `base.cnpj = (form.cnpj.data or '').strip() or None`. Exibir o campo no
  carteira_form.html (opcional, com dica: "usado pelo Assessor IA para buscar a cota do fundo/previdência").
- Aceite Técnico: cadastrar/editar ativo com CNPJ persiste; campo aparece preenchido ao editar.
```

```
TASK-10: Integração e verificação end-to-end
- Arquivo(s): (validação; ajustes finos onde necessário)
- Complexidade: M
- Depende de: TASK-1..TASK-9
- Descrição: Subir o app; validar migração (colunas/tabelas); validar fluxo completo: cadastrar perfil ->
  analisar carteira -> relatório salvo -> reabrir do histórico. Validar cenários de erro: carteira vazia (aviso);
  ANTHROPIC_API_KEY ausente (flash amigável, sem stacktrace). Conferir que a Previdência aparece em bloco separado no
  relatório e que a ressalva está presente.
- Aceite Técnico: todos os critérios BDD da spec verificáveis manualmente; sem erro 500; sem análise parcial salva em falha.
```

---

## 5. Distribuição por DEV Agent

```
DEV Agent 1 — Backend (models, migração, serviço de IA, rotas, deps)
  → TASK-1, TASK-2, TASK-3, TASK-6, TASK-4, TASK-5
  → Núcleo: cria os models, migra a base, adiciona deps/config, implementa o serviço `assessor_ia.py`
    e o blueprint `assessor` com as rotas. Publica o "contrato de contexto" (nomes de rotas e variáveis)
    para o DEV 2.

DEV Agent 2 — Frontend + Carteira (templates, nav, CNPJ)
  → TASK-7, TASK-8, TASK-9
  → Constrói as telas do assessor contra o contrato de contexto da TASK-5, o link de nav e o campo CNPJ na carteira.

Sequencial (após ambos): TASK-10
  → Integração e verificação end-to-end (feita na revisão/QA).
```

> Ordem interna do DEV 1: TASK-1/2 (models) → TASK-3 (migração/wiring) e TASK-6 (deps/config) → TASK-4 (serviço) → TASK-5 (rotas). DEV 2 pode iniciar em paralelo pelo contrato; TASK-9 depende só da coluna `cnpj` (TASK-3).

---

## 6. Estratégia de Teste

**Como executar (padrão do projeto):**
```
# matar processo na porta 5000 e subir:
venv/Scripts/python run.py     # HTTPS em https://127.0.0.1:5000
```

**Pré-requisito de ambiente:** definir `ANTHROPIC_API_KEY` no `.env` antes de testar a geração real.

**Verificação de páginas protegidas sem senha (padrão já usado no projeto):** test client Flask forçando a sessão
(`WTF_CSRF_ENABLED=False`; `s['_user_id']=uid; s['_fresh']=True`) e GET nas rotas — esperar 200 e marcadores no HTML.

**O que o QA deve verificar por tarefa:**
- TASK-1/2/3: app sobe; `PRAGMA table_info` mostra `cnpj`; tabelas novas criadas; nenhum dado existente perdido.
- TASK-4: `gerar_analise` retorna markdown com as seções; trata `pause_turn`; erro claro sem a chave.
- TASK-5: rotas 200 logado / 302 deslogado; PRG no perfil; /analisar com carteira gera e redireciona; carteira vazia avisa; erro de IA faz flash sem 500 e sem salvar análise parcial.
- TASK-7/8: telas renderizam; markdown → HTML; ressalva visível; nav "Assessor IA" ativa corretamente.
- TASK-9: CNPJ persiste e reaparece ao editar.
- TASK-10: fluxo completo + Previdência em bloco separado + cenários de erro.

**Testes automatizados disponíveis:** o projeto testa manualmente via navegador (SQUAD.md) — usar o test client de login forçado para smoke tests de render; a chamada real de IA deve ser validada manualmente (evitar mocar nesta fase, mas o QA pode simular ausência de chave e carteira vazia sem custo de API).

---

## 7. Riscos e Mitigações

1. **Precisão da busca de cota de fundos/previdência via web_search** — pode variar. Mitigação: passar CNPJ quando houver; se insatisfatório, evolução futura com CVM/BCB dedicado (fora do escopo desta entrega).
2. **Latência da chamada (web_search + relatório)** — mitigado por síncrono com spinner e `max_tokens` moderado; `pause_turn` tratado.
3. **Custo por análise (tokens + buscas)** — sob demanda (usuário aciona). Se necessário, limitar frequência numa próxima iteração (registrado na spec, item 4 das perguntas em aberto).
4. **Privacidade** — a carteira é enviada à API no momento da análise. Comunicar na UI (texto informativo na tela do assessor).
5. **Versão do SDK `anthropic`** — fixar após instalar a versão que suporta `web_search_20260209` (Opus 4.8). Se a conta/tier não tiver web_search, o serviço deve degradar (gerar sem contexto de mercado, avisando) — tratar `anthropic` errors no serviço.
```
