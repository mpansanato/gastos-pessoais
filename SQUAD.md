# SQUAD Configuration — gastos-pessoais

---

## 1. Identidade do Projeto

- **Nome:** gastos-pessoais
- **Descrição:** Aplicação web para controle de finanças pessoais. Permite registrar gastos variáveis e fixos por categoria, gerenciar entradas (receitas fixas e extras), acompanhar investimentos em carteira, visualizar projeções financeiras e analisar o dashboard com gráficos.
- **Domínio:** Finanças pessoais
- **Usuários:** Usuário único autenticado (uso pessoal)

## 2. Tech Stack

- **Linguagem / Runtime:** Python 3.11
- **Framework Backend:** Flask 3.x
- **Banco de Dados:** SQLite com SQLAlchemy ORM + Flask-Migrate
- **Frontend:** Jinja2 + Bootstrap 5 + Chart.js
- **Framework de Testes:** pytest (testes manuais via navegador)
- **Gerenciador de Pacotes:** pip
- **Outras libs relevantes:** Flask-Login, Flask-Migrate, Flask-WTF, campo customizado DecimalField em `app/fields.py`

## 3. Estrutura do Projeto

```
app/
├── __init__.py              # App factory — cria a app Flask
├── extensions.py            # Instâncias de extensões (db, login_manager, etc.)
├── fields.py                # Campo customizado DecimalField para formulários
├── models/                  # SQLAlchemy models
│   ├── categoria.py         # Categoria de gastos
│   ├── entrada_fixa.py      # Receitas fixas mensais
│   ├── gasto.py             # Gastos variáveis
│   ├── gasto_fixo.py        # Gastos fixos mensais
│   ├── instituicao.py       # Instituições financeiras
│   ├── investimento.py      # Aportes de investimento
│   ├── investimento_base.py # Investimentos base (ativos na carteira)
│   ├── parametro_mensal.py  # Parâmetros mensais (salário, teto de gastos)
│   ├── parametro_projecao.py# Parâmetros de projeção financeira
│   ├── receita_extra.py     # Receitas extras pontuais
│   ├── receita_fixa.py      # Receitas fixas
│   ├── retirada_investimento.py # Retiradas de investimentos
│   └── usuario.py           # Usuário (autenticação)
├── routes/                  # Blueprints (um por feature)
│   ├── auth.py              # Login, logout, alterar senha
│   ├── dados.py             # Importação/exportação de dados
│   ├── entradas_fixas.py    # CRUD de entradas fixas
│   ├── gastos.py            # CRUD de gastos variáveis
│   ├── gastos_fixos.py      # CRUD de gastos fixos
│   ├── investimentos.py     # Módulo de investimentos (carteira, aportes, retiradas, risco)
│   ├── main.py              # Dashboard principal
│   └── projecoes.py         # Projeções financeiras
├── templates/
│   ├── base.html            # Layout base com navbar e flash messages
│   ├── auth/                # login.html, alterar_senha.html
│   ├── dados/               # importar.html, importar_resultado.html, index.html
│   ├── entradas/            # fixas.html, fixas_form.html
│   ├── gastos/              # index.html, form.html, fixos.html, fixos_form.html, categorias.html
│   ├── investimentos/       # index.html, form.html, carteira.html, carteira_form.html, risco.html, instituicoes.html
│   ├── main/                # dashboard.html
│   └── projecoes/           # index.html
└── static/
    ├── css/
    └── js/
run.py                       # Entry point — inicia o servidor Flask
requirements.txt
```

## 4. Como Executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor de desenvolvimento (Windows com venv)
venv/Scripts/python run.py

# Testar manualmente em http://localhost:5000

# Migrações de banco
flask db migrate -m "descrição da migração"
flask db upgrade
```

## 5. Convenções do Projeto

- **Nomenclatura:** snake_case para funções/variáveis/arquivos, PascalCase para classes
- **Rotas:** um Blueprint por feature, registrado em `app/__init__.py`
- **Templates:** todos herdam de `base.html` com `{% extends 'base.html' %}`
- **Models:** uma classe por entidade, herda de `db.Model`, primary key `id` autoincrement
- **Campos de valor monetário:** usar o campo customizado `DecimalField` de `app/fields.py`
- **Flash messages:** `flash('mensagem', 'success/danger/warning/info')` para feedback ao usuário
- **Redirecionamento pós-POST:** sempre redirecionar após POST bem-sucedido (padrão PRG)
- **Queries:** sempre usar SQLAlchemy ORM — nunca SQL raw concatenado com variáveis
- **Formatação de dinheiro:** padrão brasileiro (R$ 1.234,56 — ponto como separador de milhar, vírgula como decimal)

## 6. Funcionalidades Existentes

- **Autenticação:** login, logout, alterar senha
- **Gastos variáveis:** CRUD completo com data, valor, descrição e categoria
- **Gastos fixos:** gastos recorrentes mensais com valor e categoria
- **Categorias:** CRUD de categorias de gastos
- **Entradas fixas:** receitas fixas mensais
- **Investimentos:** carteira de ativos, aportes, retiradas, análise de risco por classe de ativo, gestão de instituições
- **Projeções:** projeções financeiras com parâmetros configuráveis
- **Dashboard:** visão geral com gráficos Chart.js (gastos por categoria, evolução temporal)
- **Dados:** importação e exportação de dados

## 7. Padrões de Segurança

- Validar todos os inputs de formulário no backend (valor, data, strings)
- Usar SQLAlchemy ORM para todas as queries (nunca concatenar SQL)
- Sanitizar outputs exibidos em HTML (Jinja2 faz auto-escape — não desativar)
- Rotas que manipulam dados devem verificar autenticação (`@login_required`)
- Verificar se registros pertencem ao usuário autenticado antes de operar

## 8. Configurações da SQUAD

- **Max DEV Agents paralelos:** 2
- **Max iterações de correção de bugs (QA loop):** 3
- **Diretório de workspace:** `.squad-workspace/`
- **Idioma dos artefatos:** Português
