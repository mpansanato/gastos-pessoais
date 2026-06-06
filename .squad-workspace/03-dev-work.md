# Relatório de Desenvolvimento

## DEV Agent 1 (TASK-1 + TASK-2)
- `app/models/categoria.py`: adicionado `limite_mensal = db.Column(db.Numeric(12, 2), nullable=True)` após `ordem`
- `app/__init__.py`: adicionada função `_migrate_categorias()` e chamada no app_context, seguindo padrão PRAGMA existente

## DEV Agent 2 (TASK-3 + TASK-4)
- `app/routes/gastos.py`:
  - CategoriaForm: campo `limite_mensal` como BRDecimalField com Optional() e NumberRange(min=0)
  - nova_categoria(): passa `limite_mensal=form.limite_mensal.data or None` ao criar Categoria
  - Nova rota `editar_categoria(id)` (POST) com verificação de duplicata por nome
- `app/templates/gastos/categorias.html`:
  - Coluna `<th>Limite/mês</th>` no thead
  - Célula com `{{ cat.limite_mensal | brl }}` ou "—" em cada linha
  - Botão "Editar" com data-* attributes
  - Campo `limite_mensal` no formulário Nova Categoria
  - Modal `#modalEditarCategoria` + script JS para popular campos

## DEV Agent 3 (TASK-5 + TASK-6)
- `app/routes/main.py`:
  - Bloco `limites_categorias` inserido após `chart_categorias`
  - Itera `gastos_mes`, filtra categorias com limite, calcula pct, cor_barra, pct_barra
  - Passado `limites_categorias=limites_categorias` ao render_template
- `app/templates/main/dashboard.html`:
  - Seção "Limites por Categoria" inserida entre linha 2 e linha 3 do grid
  - Protegida por `{% if limites_categorias %}`
  - Grid col-md-6, filtro `| brl`, barras `bg-success/warning/danger`

## Nota
Filtro `| brl` confirmado como registrado em `app/__init__.py` linha 151.
