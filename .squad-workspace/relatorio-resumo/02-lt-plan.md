# Plano Técnico — Relatório Financeiro Consolidado

## Arquivos a Criar
- `app/routes/relatorio.py` — Blueprint com toda a lógica de dados
- `app/templates/relatorio/index.html` — Template único da página

## Arquivos a Modificar
- `app/__init__.py` — Import + register_blueprint
- `app/templates/base.html` — Link de navegação

## Zero mudanças de schema. Nenhuma migration necessária.

## Dependências entre Tasks
```
TASK-1 → TASK-2
TASK-1 → TASK-3
TASK-1 → TASK-5
TASK-2 → TASK-4
TASK-3 → TASK-4
```

## Distribuição
- Fase 1: TASK-1 (bootstrap blueprint)
- Fase 2 (paralela): TASK-2 (seções A/B/D) + TASK-3 (seções C/E/F/G/H) + TASK-5 (nav)
- Fase 3: TASK-4 (template completo)

## Detalhes das Tasks

### TASK-1 — Bootstrap do Blueprint (app/routes/relatorio.py)
Criar arquivo com:
- `relatorio_bp = Blueprint('relatorio', __name__, url_prefix='/relatorio')`
- Imports: json, datetime, date, Blueprint, render_template, request, login_required, db
- Models: Gasto, Categoria, ParametroMensal, ReceitaExtra, Investimento, Instituicao
- MESES_ABREV = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
- MESES_NOMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
- Stub da rota: `@relatorio_bp.route('/') @login_required def index(): return render_template('relatorio/index.html')`

### TASK-2 — Lógica seções A, B, D (app/routes/relatorio.py)
Dentro da função `index()`:

**Anos disponíveis:**
```python
anos_raw = set()
for col in [Gasto.ano, ReceitaExtra.ano, Investimento.ano, ParametroMensal.ano]:
    rows = db.session.execute(db.select(col).distinct()).scalars().all()
    anos_raw.update(rows)
anos_raw.add(datetime.today().year)
anos_disponiveis = sorted(anos_raw, reverse=True)
ano = int(request.args.get('ano', datetime.today().year))
if ano not in anos_raw:
    ano = datetime.today().year
```

**Por mês 1..12:**
```python
hoje = date.today()
hoje_ref = hoje.year * 100 + hoje.month
meses_data = []
for m in range(1, 13):
    pm = db.session.scalar(db.select(ParametroMensal).where(ParametroMensal.mes==m, ParametroMensal.ano==ano))
    salario = float(pm.salario) if pm else 0.0
    extras = float(db.session.scalar(db.select(db.func.sum(ReceitaExtra.valor)).where(ReceitaExtra.mes==m, ReceitaExtra.ano==ano)) or 0)
    previsto = float(db.session.scalar(db.select(db.func.sum(Gasto.valor_previsto)).where(Gasto.mes==m, Gasto.ano==ano)) or 0)
    pago = float(db.session.scalar(db.select(db.func.sum(Gasto.valor_pago)).where(Gasto.mes==m, Gasto.ano==ano, Gasto.valor_pago.isnot(None))) or 0)
    eh_futuro = (ano * 100 + m) > hoje_ref
    receita_total = salario + extras
    saldo = receita_total - pago if not eh_futuro else None
    meses_data.append({'mes': m, 'nome': MESES_NOMES[m-1], 'abrev': MESES_ABREV[m-1],
                       'salario': salario, 'extras': extras, 'receita_total': receita_total,
                       'previsto': previsto, 'pago': pago, 'saldo': saldo, 'eh_futuro': eh_futuro})
```

**Totais anuais (só meses não futuros):**
```python
total_recebido = sum(m['receita_total'] for m in meses_data if not m['eh_futuro'])
total_gasto = sum(m['pago'] for m in meses_data if not m['eh_futuro'])
saldo_anual = total_recebido - total_gasto
taxa_poupanca = round(saldo_anual / total_recebido * 100, 1) if total_recebido > 0 else None
```

**JSON gráfico B:**
```python
chart_fluxo = json.dumps({
    'labels': MESES_ABREV,
    'receita': [m['receita_total'] for m in meses_data],
    'gasto_pago': [m['pago'] if not m['eh_futuro'] else None for m in meses_data],
    'saldo': [m['saldo'] for m in meses_data],
})
```

### TASK-3 — Lógica seções C, E, F, G, H (app/routes/relatorio.py)

**Seção C — Categorias:**
```python
rows_cat = db.session.execute(
    db.select(Categoria.nome, Categoria.cor, db.func.sum(Gasto.valor_pago).label('total'))
    .join(Categoria, Gasto.categoria_id == Categoria.id)
    .where(Gasto.ano == ano, Gasto.valor_pago.isnot(None))
    .group_by(Categoria.id)
    .order_by(db.desc('total'))
).all()
top7 = rows_cat[:7]
outros_total = sum(float(r.total) for r in rows_cat[7:])
cat_labels = [r.nome for r in top7] + (['Outros'] if outros_total > 0 else [])
cat_data = [float(r.total) for r in top7] + ([outros_total] if outros_total > 0 else [])
cat_cores = [r.cor for r in top7] + (['#adb5bd'] if outros_total > 0 else [])
chart_cat_donut = json.dumps({'labels': cat_labels, 'data': cat_data, 'cores': cat_cores})
chart_cat_bar = json.dumps({'labels': cat_labels, 'data': cat_data, 'cores': cat_cores})
```

**Seção E — Receitas extras:**
```python
receitas_extras_ano = db.session.scalars(
    db.select(ReceitaExtra).where(ReceitaExtra.ano == ano)
    .order_by(ReceitaExtra.mes, ReceitaExtra.id)
).all()
total_extras_ano = sum(float(r.valor) for r in receitas_extras_ano)
```

**Seção F — Parcelamentos ativos:**
```python
subq = (db.select(Gasto.parcela_grupo_id,
                  db.func.max(Gasto.ano * 100 + Gasto.mes).label('fim_ref'),
                  db.func.min(Gasto.ano * 100 + Gasto.mes).label('ini_ref'))
        .where(Gasto.parcela_grupo_id.isnot(None))
        .group_by(Gasto.parcela_grupo_id)
        .subquery())
grupos_ativos_rows = db.session.execute(
    db.select(subq).where(subq.c.fim_ref >= hoje_ref)
).all()
parcelamentos = []
for row in grupos_ativos_rows:
    parcelas = db.session.scalars(
        db.select(Gasto).where(Gasto.parcela_grupo_id == row.parcela_grupo_id)
        .order_by(Gasto.ano, Gasto.mes)
    ).all()
    if not parcelas:
        continue
    # Parcela atual = primeira com (ano*100+mes) >= hoje_ref
    parcela_atual = next((p for p in parcelas if p.ano * 100 + p.mes >= hoje_ref), parcelas[-1])
    ultima = parcelas[-1]
    parcelamentos.append({
        'descricao': parcelas[0].descricao,
        'parcela_num': parcela_atual.parcela_num,
        'parcela_total': parcelas[0].parcela_total,
        'valor_mes': float(parcelas[0].valor_previsto),
        'data_quitacao': f'{MESES_ABREV[ultima.mes - 1]}/{ultima.ano}',
        'categoria': parcela_atual.categoria.nome,
    })
parcelamentos.sort(key=lambda p: p['data_quitacao'])
```

**Seção G — Investimentos:**
```python
inv_ultimo = db.session.execute(
    db.select(Investimento.ano, Investimento.mes)
    .order_by(Investimento.ano.desc(), Investimento.mes.desc()).limit(1)
).first()
if inv_ultimo:
    inv_rows = db.session.scalars(
        db.select(Investimento).where(Investimento.mes == inv_ultimo.mes, Investimento.ano == inv_ultimo.ano)
    ).all()
    patrimonio_atual = sum(float(r.valor) for r in inv_rows)
    rend_real_ano = float(db.session.scalar(
        db.select(db.func.sum(Investimento.rendimento_real))
        .where(Investimento.ano == ano, Investimento.rendimento_real.isnot(None))
    ) or 0)
    # Donuts
    from collections import defaultdict
    risco_totais = defaultdict(float)
    tipo_totais = defaultdict(float)
    for r in inv_rows:
        risco_totais[r.risco] += float(r.valor)
        tipo_totais[r.tipo] += float(r.valor)
    CORES_RISCO = {'baixo': '#198754', 'medio': '#ffc107', 'alto': '#dc3545'}
    CORES_TIPO = ['#0d6efd','#6f42c1','#0dcaf0','#fd7e14','#20c997','#6c757d']
    chart_inv_risco = json.dumps({
        'labels': list(risco_totais.keys()), 'data': list(risco_totais.values()),
        'cores': [CORES_RISCO.get(k, '#adb5bd') for k in risco_totais.keys()]})
    tipos = list(tipo_totais.keys())
    chart_inv_tipo = json.dumps({
        'labels': tipos, 'data': list(tipo_totais.values()),
        'cores': CORES_TIPO[:len(tipos)]})
else:
    inv_rows, patrimonio_atual, rend_real_ano = [], 0, 0
    chart_inv_risco = chart_inv_tipo = json.dumps({'labels':[], 'data':[], 'cores':[]})
```

**Seção H — Limites:**
```python
cats_limite = db.session.scalars(db.select(Categoria).where(Categoria.limite_mensal.isnot(None))).all()
limites_relatorio = []
for cat in cats_limite:
    pag_rows = db.session.execute(
        db.select(Gasto.mes, db.func.sum(Gasto.valor_pago).label('pago'))
        .where(Gasto.categoria_id == cat.id, Gasto.ano == ano, Gasto.valor_pago.isnot(None))
        .group_by(Gasto.mes)
    ).all()
    if not pag_rows:
        continue
    total_cat = sum(float(r.pago) for r in pag_rows)
    media = total_cat / len(pag_rows)
    excedidos = sum(1 for r in pag_rows if float(r.pago) > float(cat.limite_mensal))
    pct = media / float(cat.limite_mensal) * 100
    limites_relatorio.append({'nome': cat.nome, 'cor': cat.cor, 'limite': float(cat.limite_mensal),
                               'media_paga': media, 'meses_excedidos': excedidos,
                               'pct_media': round(pct, 1), 'pct_barra': min(pct, 100.0),
                               'cor_barra': 'danger' if pct >= 100 else 'warning' if pct >= 80 else 'success'})
limites_relatorio.sort(key=lambda x: -x['pct_media'])
```

### TASK-4 — Template app/templates/relatorio/index.html
Template completo com as 8 seções + seletor de ano.
Criar diretório `app/templates/relatorio/`.
Seção B: gráfico misto Chart.js (barras + linha) via canvas `chartFluxo`.
Seção C: canvas `chartCatDonut` (col-md-5) + canvas `chartCatBar` indexAxis:'y' (col-md-7).
Seção D: tabela 12 linhas + totais, células futuras com "—" e text-muted.
Seção G: canvas `chartInvRisco` + `chartInvTipo` lado a lado.

### TASK-5 — Registro e navegação
Em `app/__init__.py`: import + register_blueprint do relatorio_bp.
Em `app/templates/base.html`: link "Relatório Anual" com ícone `bi-file-earmark-bar-graph`.
