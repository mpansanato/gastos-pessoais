# Plano Técnico — Entradas com Valor Previsto e Valor Realizado

**Feature:** Valor previsto + realizado em ReceitaFixa; parcelas em EntradaFixa; Saldo Realizado vs Previsto  
**Gerado por:** Agente LT  
**Data:** 2026-05-31

---

## 1. Análise de Impacto

### Arquivos a MODIFICAR

| Arquivo | O que muda |
|---------|-----------|
| `app/models/receita_fixa.py` | + campos `valor_realizado` (Numeric 12,2 nullable) e `dia_recebimento` (Integer nullable) |
| `app/models/entrada_fixa.py` | + relationship `parcelas` com `ParcelaEntradaFixa`; campo `dia_recebimento` (Integer nullable) para entrada simples |
| `app/__init__.py` | + `_migrate_receitas_fixas()`, `_migrate_entradas_fixas()`, `_migrate_salario_para_entrada_fixa()` chamados no `create_app` |
| `app/routes/gastos.py` | `_calcular_totais()` separado em `total_fixas_previsto` / `total_fixas_realizado`; Saldo Realizado e Saldo Previsto; nova rota `registrar_realizado` |
| `app/routes/entradas_fixas.py` | `_ensure_12_meses()` adaptado para parcelas; `EntradaFixaForm` com `FieldList` de parcelas; rotas `nova` e `editar` adaptadas |
| `app/routes/main.py` | Dashboard: `sobra_mes` baseada em `total_fixas_realizado + total_extras - total_pago`; novo contexto `saldo_previsto_mes` |
| `app/routes/relatorio.py` | `meses_data` inclui `fixas_previsto` e `fixas_realizado`; tabela Seção D com colunas adicionais |
| `app/templates/gastos/index.html` | Nova seção "Entradas do Mês" com tabela; cards de saldo substituídos por "Saldo Previsto" + "Saldo Realizado" |
| `app/templates/entradas/fixas.html` | Form de criação com suporte a N parcelas (JS dinâmico) |
| `app/templates/entradas/fixas_form.html` | Form de edição com suporte a N parcelas (JS dinâmico + pré-população) |
| `app/templates/main/dashboard.html` | Card "Sobra" mostra Saldo Realizado como principal, subtexto mostra Saldo Previsto |
| `app/templates/relatorio/index.html` | Seção D: colunas `Ent. Fixas Previstas` e `Ent. Fixas Realizadas`; "—" para `valor_realizado` nulo |

### Arquivos a CRIAR

| Arquivo | Propósito |
|---------|-----------|
| `app/models/parcela_entrada_fixa.py` | Modelo `ParcelaEntradaFixa` — tabela `parcelas_entrada_fixa` |

### Dependências externas

Nenhuma — stack existente (Flask-WTF, SQLAlchemy, Bootstrap 5) é suficiente.

---

## 2. Decisões de Arquitetura

**Decisão:** Usar PRAGMA `ALTER TABLE` idempotente (padrão do projeto) para as novas colunas em vez de Flask-Migrate.  
**Justificativa:** O projeto já usa o padrão `_migrate_*` em `app/__init__.py` com verificação por `PRAGMA table_info`. Introduzir Flask-Migrate quebraria a consistência e exigiria setup adicional.  
**Alternativa descartada:** `flask db migrate` — descartado por incompatibilidade com o padrão do projeto.

---

**Decisão:** `ParcelaEntradaFixa` como tabela separada (não array JSON em `EntradaFixa`).  
**Justificativa:** Permite queries diretas, integridade referencial, e segue o padrão ORM do projeto. SQLite suporta bem relacionamentos simples.  
**Alternativa descartada:** Campo JSON serializado em `EntradaFixa.parcelas_json` — descartado por impossibilidade de queries eficientes e violação dos padrões do projeto.

---

**Decisão:** `_calcular_totais()` retorna dicionário estendido com `total_fixas_previsto`, `total_fixas_realizado`, `saldo_realizado`, `saldo_previsto` — mantendo `total_fixas`, `parcial` e `sobra` para compatibilidade retroativa.  
**Justificativa:** O template `gastos/index.html` já usa `totais.sobra`, `totais.total_fixas`. Manter chaves existentes evita quebras em partes do código não modificadas neste ciclo.  
**Alternativa descartada:** Renomear chaves existentes — descartado pelo risco de regressão.

---

**Decisão:** Rota separada `POST /<ano>/<mes>/receita-fixa/<id>/registrar` para registrar `valor_realizado`.  
**Justificativa:** Mantém separação de responsabilidades. Formulário mínimo (valor + CSRF). Lógica de bloqueio de mês futuro encapsulada.  
**Alternativa descartada:** Reaproveitar a rota de edição — descartado pois ReceitaFixa não tem rota de edição exposta ao usuário.

---

**Decisão:** `rolling_forward` gera uma `ReceitaFixa` por `ParcelaEntradaFixa` quando a entrada tem parcelas. Adicionar campo `parcela_ordem` em `receitas_fixas` para identificar qual parcela originou o lançamento.  
**Justificativa:** Permite a query de existência (`COUNT > 0`) ser precisa por parcela sem mudar a semântica do rolling. `ReceitaFixa` continua sendo o lançamento mensal concreto consumido por toda a aplicação.  
**Alternativa descartada:** Usar apenas `entrada_fixa_id + mes + ano` como chave — ambíguo quando há N parcelas no mesmo mês.

---

**Decisão:** Migração `ParametroMensal.salario → EntradaFixa` executada em `create_app` via `_migrate_salario_para_entrada_fixa()`, idempotente por flag (`observacao='migrado_de_parametro_mensal'`).  
**Justificativa:** Segue o padrão `_seed_*` / `_migrate_*` do projeto. Simples e sem estado externo.  
**Alternativa descartada:** Script avulso (CLI) — descartado para não exigir execução manual pelo usuário.

---

## 3. Schema de Banco de Dados

### 3.1 Alterações em tabelas existentes

#### Tabela `receitas_fixas` — novas colunas

```sql
ALTER TABLE receitas_fixas ADD COLUMN valor_realizado NUMERIC(12,2);
ALTER TABLE receitas_fixas ADD COLUMN dia_recebimento INTEGER;
ALTER TABLE receitas_fixas ADD COLUMN parcela_ordem INTEGER;
```

- `valor_realizado`: nullable — ausência = não realizado, presença = valor efetivamente recebido
- `dia_recebimento`: dia do mês esperado (1–31), informativo, nullable
- `parcela_ordem`: ordem da parcela de origem (1, 2, ...), nullable (NULL = entrada simples sem parcelas)

#### Tabela `entradas_fixas` — nova coluna

```sql
ALTER TABLE entradas_fixas ADD COLUMN dia_recebimento INTEGER;
```

- `dia_recebimento`: dia padrão de recebimento para entrada simples; nullable

### 3.2 Nova tabela

```sql
CREATE TABLE IF NOT EXISTS parcelas_entrada_fixa (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    entrada_fixa_id   INTEGER NOT NULL REFERENCES entradas_fixas(id),
    valor             NUMERIC(12,2) NOT NULL,
    dia_recebimento   INTEGER,
    ordem             INTEGER NOT NULL DEFAULT 1
);
```

### 3.3 Migração de `ParametroMensal.salario`

Lógica executada em `_migrate_salario_para_entrada_fixa()`:

```python
# Pseudocódigo
# 1. Verificar se já existe EntradaFixa com observacao='migrado_de_parametro_mensal' → se sim, return
# 2. Buscar todos ParametroMensal com salario > 0, ordenados por (ano, mes)
# 3. Se não há nenhum: return
# 4. Criar EntradaFixa(descricao='Salário', valor=ultimo_salario, ativo=True,
#                       observacao='migrado_de_parametro_mensal')
# 5. flush() para obter o id
# 6. Para cada ParametroMensal (salario > 0):
#    criar ReceitaFixa(descricao='Salário', valor=pm.salario, mes=pm.mes, ano=pm.ano,
#                      entrada_fixa_id=entrada.id, valor_realizado=None)
# 7. commit()
```

### 3.4 Modelo Python — ParcelaEntradaFixa

```python
# app/models/parcela_entrada_fixa.py
class ParcelaEntradaFixa(db.Model):
    __tablename__ = 'parcelas_entrada_fixa'
    id               = db.Column(db.Integer, primary_key=True)
    entrada_fixa_id  = db.Column(db.Integer, db.ForeignKey('entradas_fixas.id'), nullable=False)
    valor            = db.Column(db.Numeric(12, 2), nullable=False)
    dia_recebimento  = db.Column(db.Integer, nullable=True)
    ordem            = db.Column(db.Integer, nullable=False, default=1)
    entrada_fixa     = db.relationship('EntradaFixa', back_populates='parcelas')
```

---

## 4. Tarefas Técnicas

```
TASK-1a: Modelo ParcelaEntradaFixa
- Arquivo(s): app/models/parcela_entrada_fixa.py (CRIAR)
- Complexidade: P
- Depende de: nenhuma
- Descrição:
  Criar o arquivo com a classe ParcelaEntradaFixa conforme schema 3.4.
  5 colunas: id (PK), entrada_fixa_id (FK→entradas_fixas), valor (Numeric 12,2 NOT NULL),
  dia_recebimento (Integer nullable), ordem (Integer NOT NULL default=1).
  Relationship: entrada_fixa = db.relationship('EntradaFixa', back_populates='parcelas')
- Aceite Técnico:
  Arquivo existe. Classe herda db.Model. __tablename__ = 'parcelas_entrada_fixa'.
  5 colunas conforme schema. Relationship definido com back_populates='parcelas'.
```

```
TASK-1b: Migrations PRAGMA e migração de salário
- Arquivo(s): app/__init__.py
- Complexidade: M
- Depende de: TASK-1a
- Descrição:
  1. Adicionar import no topo do arquivo (junto aos imports de modelos existentes):
     from app.models.parcela_entrada_fixa import ParcelaEntradaFixa
     (necessário para db.create_all() criar a tabela)
  2. Criar função _migrate_receitas_fixas():
     - PRAGMA table_info(receitas_fixas)
     - Se 'valor_realizado' não existe: ALTER TABLE ADD COLUMN valor_realizado NUMERIC(12,2)
     - Se 'dia_recebimento' não existe: ALTER TABLE ADD COLUMN dia_recebimento INTEGER
     - Se 'parcela_ordem' não existe: ALTER TABLE ADD COLUMN parcela_ordem INTEGER
     - conn.commit()
  3. Criar função _migrate_entradas_fixas():
     - PRAGMA table_info(entradas_fixas)
     - Se 'dia_recebimento' não existe: ALTER TABLE ADD COLUMN dia_recebimento INTEGER
     - conn.commit()
  4. Criar função _migrate_salario_para_entrada_fixa():
     - Importa localmente: EntradaFixa, ReceitaFixa, ParametroMensal
     - Se existe EntradaFixa com observacao='migrado_de_parametro_mensal': return (idempotente)
     - Busca ParametroMensal.salario > 0, ordena por (ano, mes)
     - Se lista vazia: return
     - Cria EntradaFixa(descricao='Salário', valor=ultimo_salario, ativo=True,
                         observacao='migrado_de_parametro_mensal')
     - db.session.add(entrada); db.session.flush()
     - Para cada pm na lista: cria ReceitaFixa(descricao='Salário', valor=pm.salario,
       mes=pm.mes, ano=pm.ano, entrada_fixa_id=entrada.id, valor_realizado=None)
     - db.session.commit()
  5. No create_app(), dentro do with app.app_context(), APÓS db.create_all():
     _migrate_receitas_fixas()
     _migrate_entradas_fixas()
     _migrate_salario_para_entrada_fixa()
- Aceite Técnico:
  App inicializa sem erros. PRAGMA table_info(receitas_fixas) mostra valor_realizado, dia_recebimento,
  parcela_ordem. PRAGMA table_info(entradas_fixas) mostra dia_recebimento. Tabela parcelas_entrada_fixa
  existe. Se havia ParametroMensal com salario > 0: EntradaFixa 'Salário' criada e ReceitaFixas
  correspondentes existem. Segunda execução do app: sem duplicação (idempotente).
```

```
TASK-2: Atualizar modelos ReceitaFixa e EntradaFixa
- Arquivo(s): app/models/receita_fixa.py, app/models/entrada_fixa.py
- Complexidade: P
- Depende de: TASK-1a
- Descrição:
  receita_fixa.py:
    - Adicionar coluna: valor_realizado = db.Column(db.Numeric(12, 2), nullable=True)
    - Adicionar coluna: dia_recebimento = db.Column(db.Integer, nullable=True)
    - Adicionar coluna: parcela_ordem = db.Column(db.Integer, nullable=True)
    - NÃO adicionar property status no modelo — status será calculado no template com Jinja2
      (simplifica e evita dependência de datetime no modelo)
  entrada_fixa.py:
    - Adicionar import: from app.models.parcela_entrada_fixa import ParcelaEntradaFixa
      (ATENÇÃO: import circular possível — se ocorrer, usar string 'ParcelaEntradaFixa' no relationship
       e mover o import para dentro de um TYPE_CHECKING block ou omitir o import direto)
    - Adicionar coluna: dia_recebimento = db.Column(db.Integer, nullable=True)
    - Adicionar relationship:
      parcelas = db.relationship('ParcelaEntradaFixa', back_populates='entrada_fixa',
                                  order_by='ParcelaEntradaFixa.ordem', cascade='all, delete-orphan',
                                  lazy='select')
    - Adicionar property:
      @property
      def tem_parcelas(self):
          return len(self.parcelas) > 0
- Aceite Técnico:
  Instâncias de ReceitaFixa têm .valor_realizado, .dia_recebimento, .parcela_ordem acessíveis.
  Instâncias de EntradaFixa têm .parcelas (list), .tem_parcelas (bool), .dia_recebimento acessíveis.
  App inicia sem ImportError.
```

```
TASK-3: Lógica _calcular_totais e rota registrar_realizado (gastos.py)
- Arquivo(s): app/routes/gastos.py
- Complexidade: M
- Depende de: TASK-2
- Descrição:
  1. Adicionar RegistrarRealizadoForm antes dos helpers:
     class RegistrarRealizadoForm(FlaskForm):
         valor_realizado = DecimalField('Valor Realizado (R$)',
                                        validators=[DataRequired(), NumberRange(min=0)], places=2)
         submit = SubmitField('Registrar')

  2. Atualizar _calcular_totais(gastos, salario, receitas_extras=None, receitas_fixas=None):
     - Manter todos os cálculos originais (total_previsto, total_pago, sal, total_extras, total_fixas,
       total_entradas, parcial, sobra) SEM ALTERAR para compatibilidade retroativa
     - Adicionar:
       total_fixas_previsto = total_fixas  # alias semântico
       total_fixas_realizado = sum(float(r.valor_realizado) for r in receitas_fixas
                                   if r.valor_realizado is not None)
       saldo_realizado = total_fixas_realizado + total_extras - total_pago
       saldo_previsto  = total_fixas_previsto + total_extras + sal - total_previsto
     - Retornar dicionário com TODAS as chaves (antigas + novas):
       total_fixas_previsto, total_fixas_realizado, saldo_realizado, saldo_previsto
       + total_previsto, total_pago, total_extras, total_fixas, total_entradas, parcial, sobra

  3. Em por_mes(): adicionar ao render_template:
     registrar_form=RegistrarRealizadoForm()

  4. Adicionar rota:
     @gastos_bp.route('/<int:ano>/<int:mes>/receita-fixa/<int:id>/registrar', methods=['POST'])
     @login_required
     def registrar_realizado(ano, mes, id):
         hoje = datetime.today()
         if (ano * 100 + mes) > (hoje.year * 100 + hoje.month):
             flash('Não é possível registrar realizado em mês futuro.', 'danger')
             return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))
         receita = db.session.scalar(
             db.select(ReceitaFixa).where(ReceitaFixa.id == id,
                                          ReceitaFixa.mes == mes,
                                          ReceitaFixa.ano == ano)
         )
         if not receita:
             flash('Lançamento não encontrado.', 'danger')
             return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))
         form = RegistrarRealizadoForm()
         if form.validate_on_submit():
             receita.valor_realizado = form.valor_realizado.data
             db.session.commit()
             flash(f'Realizado de "{receita.descricao}" registrado.', 'success')
         else:
             for erros in form.errors.values():
                 for e in erros:
                     flash(e, 'danger')
         return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))
- Aceite Técnico:
  totais retornado por _calcular_totais contém as keys: total_fixas_previsto, total_fixas_realizado,
  saldo_realizado, saldo_previsto. Chaves originais presentes e com valores iguais ao comportamento
  anterior. POST válido registra valor_realizado. POST em mês futuro: flash de erro, sem alteração.
```

```
TASK-4: Rolling forward com suporte a parcelas (entradas_fixas.py)
- Arquivo(s): app/routes/entradas_fixas.py
- Complexidade: M
- Depende de: TASK-2
- Descrição:
  1. Adicionar imports no topo:
     from wtforms import IntegerField, FieldList, FormField
     from wtforms.validators import NumberRange
     from wtforms.form import Form as BaseForm  # para FormField interno
     from app.models.parcela_entrada_fixa import ParcelaEntradaFixa

  2. Adicionar ParcelaForm (ANTES de EntradaFixaForm):
     class ParcelaForm(BaseForm):
         valor = DecimalField('Valor', validators=[DataRequired(), NumberRange(min=0)], places=2)
         dia_recebimento = IntegerField('Dia', validators=[Optional(), NumberRange(min=1, max=31)])

  3. Atualizar EntradaFixaForm:
     - Manter campos: descricao, valor, observacao
     - Adicionar: dia_recebimento = IntegerField('Dia de Recebimento (padrão)',
                                                  validators=[Optional(), NumberRange(min=1, max=31)])
     - Adicionar: parcelas = FieldList(FormField(ParcelaForm), min_entries=0)

  4. Atualizar _ensure_12_meses(entrada, hoje_mes, hoje_ano):
     - Se len(entrada.parcelas) > 0:
       Para cada mes/ano nos próximos 12:
         Para cada parcela em entrada.parcelas (já ordenadas por .ordem):
           existe = COUNT > 0 WHERE entrada_fixa_id=entrada.id AND mes=mes AND ano=ano
                    AND parcela_ordem=parcela.ordem
           Se não existe:
             db.session.add(ReceitaFixa(
                 descricao=entrada.descricao,
                 valor=parcela.valor,
                 mes=mes, ano=ano,
                 entrada_fixa_id=entrada.id,
                 observacao=entrada.observacao,
                 dia_recebimento=parcela.dia_recebimento,
                 parcela_ordem=parcela.ordem,
             ))
             criados += 1
     - Senão (entrada simples): comportamento atual, mas adicionar dia_recebimento=entrada.dia_recebimento
       e parcela_ordem=None na criação da ReceitaFixa

  5. Atualizar _atualizar_futuros(entrada, hoje_mes, hoje_ano):
     - Se len(entrada.parcelas) > 0:
       futuros = ReceitaFixa WHERE entrada_fixa_id=entrada.id AND futuro
       Para cada r in futuros:
         parcela = next((p for p in entrada.parcelas if p.ordem == r.parcela_ordem), None)
         Se parcela:
           r.descricao = entrada.descricao
           r.valor = parcela.valor
           r.dia_recebimento = parcela.dia_recebimento
           r.observacao = entrada.observacao
     - Senão: comportamento atual

  6. Rota nova(): APÓS criar a EntradaFixa e antes de commit:
     parcelas_data = [p for p in form.parcelas.data if p.get('valor') is not None]
     Se parcelas_data:
       Para cada i, p_data em enumerate(parcelas_data):
         db.session.add(ParcelaEntradaFixa(
             entrada_fixa_id=entrada.id,
             valor=p_data['valor'],
             dia_recebimento=p_data.get('dia_recebimento'),
             ordem=i + 1,
         ))
     db.session.commit()  # commita entrada + parcelas juntos
     Depois: _ensure_12_meses(entrada, ...)

  7. Rota editar(): similar, mas:
     - Apagar parcelas existentes da entrada (db.session.delete para cada uma)
     - Recriar parcelas com novos dados do form
     - Chamar _atualizar_futuros ANTES de recriar parcelas (usa parcelas antigas ainda na memória)
     - ATENÇÃO: após apagar e recriar parcelas, as ReceitaFixas futuras precisam ser atualizadas —
       chamar _atualizar_futuros APÓS recriar parcelas OR incluir lógica direta de update

- Aceite Técnico:
  EntradaFixa com 2 parcelas gera 2 ReceitaFixas por mês (parcela_ordem=1 e parcela_ordem=2) nos 12 meses.
  EntradaFixa sem parcelas: comportamento idêntico ao anterior (1 ReceitaFixa/mês, parcela_ordem=NULL).
  Edição de parcelas: ReceitaFixas futuras atualizadas por parcela_ordem. ReceitaFixas passadas intactas.
```

```
TASK-5: Template gastos/index.html — seção Entradas do Mês + cards de saldo
- Arquivo(s): app/templates/gastos/index.html
- Complexidade: M
- Depende de: TASK-3
- Descrição:
  1. Substituir o card "Sobra" (4º card) por DOIS cards lado a lado.
     O bloco de 4 cards passa a ter 5 cards (col-6 col-md); ajustar para col-12 col-sm-6 col-md-4
     OU manter 4 colunas e colocar os 2 novos cards em substituição ao único "Sobra" usando col-3 cada.
     Layout final dos cards (da esquerda para direita):
       [Entradas] [Previsto] [Pago] [Saldo Previsto] [Saldo Realizado]
     Em tela md+: 5 colunas (col-md-2 ou flexível). Em mobile: empilhados (col-6 para os dois novos).

     Card "Saldo Previsto":
       - ícone: bi-calendar-check, cor: text-secondary
       - valor: {{ totais.saldo_previsto | brl }}
       - subtexto: "entradas previstas − gastos previstos"
       - sem cor condicional (sempre secondary)

     Card "Saldo Realizado":
       - ícone: bi-piggy-bank, cor: text-success se >= 0, text-danger se < 0
       - valor: {{ totais.saldo_realizado | brl }}
       - cor do valor: text-success/text-danger conforme sinal
       - subtexto: "após pagamentos realizados"

  2. Adicionar seção "Entradas do Mês" ENTRE o bloco de cards e a barra de ações:
     <div class="d-flex justify-content-between align-items-center mb-2 mt-4">
       <h6 class="text-uppercase text-muted fw-semibold mb-0" style="font-size:.72rem;letter-spacing:.08em;">
         Entradas do Mês
       </h6>
     </div>
     {% if receitas_fixas %}
     <div class="card mb-4">
       <div class="table-responsive">
         <table class="table table-hover align-middle mb-0" style="font-size:.875rem;">
           <thead class="table-light">
             <tr>
               <th>Descrição</th>
               <th class="text-center" style="width:60px">Dia</th>
               <th class="text-end">Previsto</th>
               <th class="text-end">Realizado</th>
               <th class="text-center">Status</th>
               <th style="width:90px"></th>
             </tr>
           </thead>
           <tbody>
             {% for r in receitas_fixas %}
             {% set is_futuro = (ano * 100 + mes) > (hoje_ano * 100 + hoje_mes) %}
             <tr>
               <td>{{ r.descricao }}</td>
               <td class="text-center text-muted small">{{ r.dia_recebimento or '—' }}</td>
               <td class="text-end">{{ r.valor | brl }}</td>
               <td class="text-end {% if r.valor_realizado is not none %}text-success{% else %}text-muted{% endif %}">
                 {% if r.valor_realizado is not none %}{{ r.valor_realizado | brl }}{% else %}—{% endif %}
               </td>
               <td class="text-center">
                 {% if r.valor_realizado is not none %}
                   <span class="badge bg-success">Recebido</span>
                 {% elif is_futuro %}
                   <span class="badge bg-secondary">Futuro</span>
                 {% else %}
                   <span class="badge bg-warning text-dark">Pendente</span>
                 {% endif %}
               </td>
               <td class="text-end">
                 {% if r.valor_realizado is none and not is_futuro %}
                 <button class="btn btn-sm btn-outline-success py-0 px-2"
                         data-bs-toggle="modal"
                         data-bs-target="#modalRegistrar{{ r.id }}">
                   <i class="bi bi-check2-circle me-1" style="font-size:.75rem;"></i>Registrar
                 </button>
                 {% endif %}
               </td>
             </tr>
             {% endfor %}
           </tbody>
           <tfoot class="table-light">
             <tr>
               <td colspan="2" class="fw-semibold small">Total Entradas Fixas</td>
               <td class="text-end fw-semibold">{{ totais.total_fixas_previsto | brl }}</td>
               <td class="text-end fw-semibold {% if totais.total_fixas_realizado > 0 %}text-success{% endif %}">
                 {% if totais.total_fixas_realizado > 0 %}{{ totais.total_fixas_realizado | brl }}{% else %}—{% endif %}
               </td>
               <td colspan="2"></td>
             </tr>
           </tfoot>
         </table>
       </div>
     </div>
     {% endif %}

  3. Para cada receita_fixa sem valor_realizado e em mês não-futuro, adicionar modal ANTES de {% endblock %}:
     {% for r in receitas_fixas %}
     {% if r.valor_realizado is none and not ((ano * 100 + mes) > (hoje_ano * 100 + hoje_mes)) %}
     <div class="modal fade" id="modalRegistrar{{ r.id }}" tabindex="-1">
       <div class="modal-dialog modal-dialog-centered modal-sm">
         <div class="modal-content">
           <div class="modal-header border-0 pb-0">
             <h6 class="modal-title fw-bold">Registrar Recebimento</h6>
             <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
           </div>
           <form method="POST"
                 action="{{ url_for('gastos.registrar_realizado', ano=ano, mes=mes, id=r.id) }}"
                 novalidate>
             {{ registrar_form.hidden_tag() }}
             <div class="modal-body">
               <p class="small text-muted mb-2">{{ r.descricao }} — {{ nome_mes }} {{ ano }}</p>
               <label class="form-label fw-medium small">Valor Realizado (R$) *</label>
               {{ registrar_form.valor_realizado(class="form-control",
                                                  placeholder="0,00",
                                                  value=(r.valor | float)) }}
             </div>
             <div class="modal-footer border-0 pt-0">
               <button type="button" class="btn btn-outline-secondary btn-sm"
                       data-bs-dismiss="modal">Cancelar</button>
               {{ registrar_form.submit(class="btn btn-success btn-sm px-4") }}
             </div>
           </form>
         </div>
       </div>
     </div>
     {% endif %}
     {% endfor %}

  IMPORTANTE: Adicionar ao contexto passado pelo por_mes():
     hoje_mes=hoje.month, hoje_ano=hoje.year  (já disponíveis como variáveis locais — passar ao template)

- Aceite Técnico:
  Página renderiza sem erros. Seção "Entradas do Mês" visível com tabela correta.
  Botão "Registrar" presente apenas em entradas sem realizado e em mês não-futuro.
  Dois cards de saldo (Previsto e Realizado) exibidos. Modal abre ao clicar em "Registrar".
```

```
TASK-6: Template entradas/fixas.html e fixas_form.html — suporte a N parcelas
- Arquivo(s): app/templates/entradas/fixas.html, app/templates/entradas/fixas_form.html
- Complexidade: M
- Depende de: TASK-4
- Descrição:
  fixas.html (formulário lateral "Nova Entrada Fixa"):
    No card-body do formulário, APÓS o campo "Observação" e ANTES do alert:
    1. Adicionar campo "Dia de Recebimento (padrão)":
       <div class="mb-3">
         <label class="form-label fw-medium small">Dia de Recebimento <span class="text-muted fw-normal">(opcional, 1-31)</span></label>
         {{ form.dia_recebimento(class="form-control", placeholder="Ex: 5") }}
       </div>
    2. Adicionar seção de parcelas:
       <div class="mb-3">
         <div class="form-check mb-2">
           <input class="form-check-input" type="checkbox" id="toggleParcelasNova">
           <label class="form-check-label small fw-medium" for="toggleParcelasNova">
             Esta entrada possui múltiplas parcelas por mês
           </label>
         </div>
         <div id="containerParcelasNova" style="display:none;">
           <div class="small text-muted mb-2">
             <i class="bi bi-info-circle me-1"></i>
             Se parcelas preenchidas, o "Valor Mensal" acima é ignorado.
           </div>
           <div id="listaParcelasNova"></div>
           <button type="button" class="btn btn-outline-secondary btn-sm mt-2"
                   onclick="adicionarParcelaNova()">
             <i class="bi bi-plus me-1"></i>Adicionar Parcela
           </button>
         </div>
       </div>
    3. Adicionar bloco de scripts no {% block extra_scripts %} (ou no final do template):
       function adicionarParcelaNova() {
           const lista = document.getElementById('listaParcelasNova');
           const idx = lista.children.length;
           const div = document.createElement('div');
           div.className = 'd-flex gap-2 mb-2 align-items-center';
           div.innerHTML = `
             <input type="number" step="0.01" min="0" name="parcelas-${idx}-valor"
                    class="form-control form-control-sm" placeholder="Valor" required>
             <input type="number" min="1" max="31" name="parcelas-${idx}-dia_recebimento"
                    class="form-control form-control-sm" style="width:80px" placeholder="Dia">
             <button type="button" class="btn btn-outline-danger btn-sm py-0 px-1"
                     onclick="this.parentElement.remove(); renumerarParcelasNova()">
               <i class="bi bi-x"></i>
             </button>`;
           lista.appendChild(div);
       }
       function renumerarParcelasNova() {
           const lista = document.getElementById('listaParcelasNova');
           Array.from(lista.children).forEach((div, idx) => {
               div.querySelector('input[placeholder="Valor"]').name = `parcelas-${idx}-valor`;
               div.querySelector('input[placeholder="Dia"]').name = `parcelas-${idx}-dia_recebimento`;
           });
       }
       document.getElementById('toggleParcelasNova').addEventListener('change', function() {
           document.getElementById('containerParcelasNova').style.display =
               this.checked ? '' : 'none';
       });

  fixas_form.html (edição):
    - Mesma estrutura do formulário de criação
    - Campo dia_recebimento: {{ form.dia_recebimento(class="form-control", placeholder="Ex: 5") }}
    - Seção de parcelas: mesma lógica JS, mas com id="toggleParcelasEdit", "containerParcelasEdit", etc.
    - Pré-população via Jinja2: se entrada.parcelas, renderizar as linhas existentes como inputs
      preenchidos e marcar o checkbox como checked (atributo checked)
    - Implementação JS: função adicionarParcelaEdit() equivalente

- Aceite Técnico:
  Formulário de criação sem parcelas: POST sem campos parcelas-*. Funcionamento idêntico ao atual.
  Formulário com 2 parcelas: POST contém parcelas-0-valor, parcelas-0-dia_recebimento,
  parcelas-1-valor, parcelas-1-dia_recebimento. Rota nova() persiste 2 ParcelaEntradaFixa.
  Formulário de edição: pré-popula parcelas existentes. Remover e adicionar novas: POST atualizado.
```

```
TASK-7: Dashboard — saldo usa realizado (main.py + dashboard.html)
- Arquivo(s): app/routes/main.py, app/templates/main/dashboard.html
- Complexidade: P
- Depende de: TASK-2
- Descrição:
  main.py:
    1. Adicionar import: from app.models.receita_fixa import ReceitaFixa
    2. Após calcular total_extras_mes, adicionar:
       receitas_fixas_mes = db.session.scalars(
           db.select(ReceitaFixa).where(ReceitaFixa.mes == mes, ReceitaFixa.ano == ano)
       ).all()
       total_fixas_previsto_mes = sum(float(r.valor) for r in receitas_fixas_mes)
       total_fixas_realizado_mes = sum(float(r.valor_realizado) for r in receitas_fixas_mes
                                       if r.valor_realizado is not None)
    3. Recalcular saldos:
       saldo_realizado_mes = total_fixas_realizado_mes + total_extras_mes - total_pago_mes
       saldo_previsto_mes  = total_fixas_previsto_mes + total_extras_mes + salario - total_prev_mes
       sobra_mes = salario + total_extras_mes - total_pago_mes  # MANTER para não quebrar nada
    4. Passar ao template: saldo_realizado_mes=saldo_realizado_mes, saldo_previsto_mes=saldo_previsto_mes
       (manter sobra_mes também para compatibilidade)

  dashboard.html:
    - No card "Sobra {{ nome_mes }}":
      - Condição de exibição: if salario > 0 or total_fixas_realizado_mes > 0 or total_extras_mes > 0
        (usar variável passada — simplificar verificando se saldo_realizado_mes != 0 ou alguma entrada existe)
      - Valor principal: {{ saldo_realizado_mes | brl }}
      - Cor: text-success se >= 0, text-danger se < 0
      - Subtexto: "Previsto: {{ saldo_previsto_mes | brl }}"
    - Manter lógica de exibição do subtexto de salário se quiser, mas simplificar para mostrar previsto

- Aceite Técnico:
  Dashboard exibe saldo_realizado_mes no card "Sobra". Subtexto mostra saldo_previsto_mes.
  Com ReceitaFixas sem valor_realizado: saldo_realizado_mes = total_extras - total_pago (correto).
  Com ReceitaFixas com valor_realizado: valor refletido.
```

```
TASK-8: Relatório anual — entradas previstas vs realizadas
- Arquivo(s): app/routes/relatorio.py, app/templates/relatorio/index.html
- Complexidade: M
- Depende de: TASK-2
- Descrição:
  relatorio.py:
    1. Adicionar import: from app.models.receita_fixa import ReceitaFixa
    2. No loop de meses_data (for m in range(1, 13)), adicionar:
       fixas_previsto = float(
           db.session.scalar(
               db.select(db.func.sum(ReceitaFixa.valor))
               .where(ReceitaFixa.mes == m, ReceitaFixa.ano == ano)
           ) or 0
       )
       fixas_realizado_val = db.session.scalar(
           db.select(db.func.sum(ReceitaFixa.valor_realizado))
           .where(ReceitaFixa.mes == m, ReceitaFixa.ano == ano,
                  ReceitaFixa.valor_realizado.isnot(None))
       )
       fixas_realizado = float(fixas_realizado_val) if fixas_realizado_val is not None else None
       receita_total = salario + extras + fixas_previsto
       receita_realizada = (salario + extras + fixas_realizado) if fixas_realizado is not None else None
       saldo: se eh_futuro → None
              elif receita_realizada is not None → receita_realizada - pago
              else → None  (sem valor_realizado = não exibir saldo)
       Incluir no dict: 'fixas_previsto': fixas_previsto, 'fixas_realizado': fixas_realizado,
                         'receita_total': receita_total, 'receita_realizada': receita_realizada
    3. Recalcular totais anuais:
       total_recebido = sum(m['receita_realizada'] for m in meses_data
                            if not m['eh_futuro'] and m['receita_realizada'] is not None)
       Se total_recebido == 0: fallback para sum(m['receita_total'] para não-futuros) — para anos sem realizado
       Atualizar saldo_anual e taxa_poupanca com total_recebido atualizado

  relatorio/index.html — Seção D:
    - Adicionar colunas após "Extras":
      <th class="text-end">Ent. Fixas Prev.</th>
      <th class="text-end">Ent. Fixas Real.</th>
    - Células correspondentes:
      <td class="text-end">{% if m.fixas_previsto %}{{ m.fixas_previsto | brl }}{% else %}<span class="text-muted">—</span>{% endif %}</td>
      <td class="text-end {% if m.fixas_realizado is not none %}text-success{% endif %}">
        {% if m.fixas_realizado is not none %}{{ m.fixas_realizado | brl }}{% else %}<span class="text-muted">—</span>{% endif %}
      </td>
    - Coluna "Receita Total": manter baseada em receita_total (previsto) para não quebrar visualização
    - tfoot: somar fixas_previsto e fixas_realizado dos meses não-futuros
    - Coluna "Saldo": usar m.saldo (já recalculado na rota) — exibe "—" se None

- Aceite Técnico:
  Relatório renderiza sem erros. Colunas "Ent. Fixas Prev." e "Ent. Fixas Real." visíveis.
  Meses sem valor_realizado: coluna "Real." exibe "—".
  Saldo mensal correto apenas para meses com realizado preenchido.
  Anos anteriores sem valor_realizado: saldo anual usa fallback de receita_total.
```

---

## 5. Distribuição por DEV Agent

```
DEV Agent 1: [TASK-1a, TASK-1b, TASK-2]
  → Backend Foundation — Criação do modelo ParcelaEntradaFixa, migrations PRAGMA idempotentes
    (receitas_fixas + entradas_fixas + criação de tabela), migração de salário, atualização
    dos modelos ReceitaFixa e EntradaFixa.
    PODE RODAR TOTALMENTE EM PARALELO COM DEV Agent 2 (antes das tasks de TASK-3 e TASK-4).

DEV Agent 2: [TASK-3]
  → Backend Gastos — _calcular_totais estendido, RegistrarRealizadoForm, rota registrar_realizado.
    DEPENDE de TASK-2 (ReceitaFixa.valor_realizado deve existir no modelo).
    Inicia após DEV Agent 1 terminar TASK-2.

DEV Agent 3: [TASK-4]
  → Backend Rolling + Form Parcelas — _ensure_12_meses com parcelas, _atualizar_futuros com parcelas,
    EntradaFixaForm com FieldList, rotas nova() e editar() adaptadas.
    DEPENDE de TASK-2. Pode rodar em paralelo com DEV Agent 2.
    Inicia após DEV Agent 1 terminar TASK-2.

Sequencial (após DEV 2 e DEV 3): [TASK-5, TASK-6, TASK-7, TASK-8]
  → Frontend + Dashboard + Relatório.
  TASK-5 depende de TASK-3 (rota registrar_realizado + totais.saldo_realizado).
  TASK-6 depende de TASK-4 (form com FieldList).
  TASK-7 depende de TASK-2 (ReceitaFixa importável em main.py).
  TASK-8 depende de TASK-2 (ReceitaFixa.valor_realizado).
  TASK-5, TASK-6, TASK-7 e TASK-8 são independentes entre si — podem ser paralelizadas.
```

**Diagrama de dependências simplificado:**
```
TASK-1a ──→ TASK-1b
TASK-1a ──→ TASK-2 ──→ TASK-3 ──→ TASK-5
                   ──→ TASK-4 ──→ TASK-6
                   ──→ TASK-7
                   ──→ TASK-8
```

**Caminho crítico:** TASK-1a → TASK-2 → TASK-3 → TASK-5

---

## 6. Estratégia de Teste

### Como executar a aplicação

```powershell
cd c:\Users\mpans\OneDrive\Documentos\GitHub\gastos-pessoais
python run.py
# Acessar: http://localhost:5000
```

### O que o QA Agent deve verificar por tarefa

**TASK-1b (migrations):**
- App inicializa sem erro 500. Acessar `/gastos` e `/entradas/fixas` sem erro.
- Tabela `parcelas_entrada_fixa` existe no banco (verificar via logs ou SQLite browser).
- `receitas_fixas` tem colunas: `valor_realizado`, `dia_recebimento`, `parcela_ordem`.
- `entradas_fixas` tem coluna: `dia_recebimento`.
- Se havia ParametroMensal com salario > 0: EntradaFixa "Salário" criada, ReceitaFixas correspondentes.
- Reiniciar app: sem duplicação (idempotência confirmada).

**TASK-3 (gastos.py — totais e rota):**
- GET `/gastos/<ano>/<mes>`: página renderiza, dois cards de saldo presentes.
- Com receitas fixas sem valor_realizado: saldo_realizado = 0 + extras - pago.
- POST `/gastos/<ano>/<mes>/receita-fixa/<id>/registrar` com valor válido: flash de sucesso, banco atualizado.
- POST com mês futuro: flash de erro, banco não atualizado.
- POST com valor negativo ou vazio: flash de erro, banco não atualizado.

**TASK-4 (rolling com parcelas):**
- Criar EntradaFixa com 2 parcelas (valores distintos, ex: R$ 1.000 e R$ 500):
  Confirmar 2 ReceitaFixas por mês nos próximos 12 meses (24 registros total).
  `parcela_ordem` = 1 e 2 nos registros criados.
- Editar valores das parcelas: ReceitaFixas futuras atualizadas com novos valores.
- Criar EntradaFixa sem parcelas: comportamento anterior preservado (1 ReceitaFixa/mês, `parcela_ordem` = NULL).

**TASK-5 (gastos/index.html):**
- Seção "Entradas do Mês" visível na página de gastos mensal.
- ReceitaFixa com `valor_realizado=None` em mês atual/passado: badge "Pendente", botão "Registrar" visível.
- ReceitaFixa com `valor_realizado` preenchido: badge "Recebido" (verde), sem botão "Registrar".
- ReceitaFixa de mês futuro: badge "Futuro", sem botão "Registrar".
- Modal de registro: valor pré-preenchido com valor previsto. Envio atualiza página corretamente.
- Cards "Saldo Previsto" e "Saldo Realizado" exibidos com valores corretos.

**TASK-6 (entradas/fixas.html):**
- Formulário sem parcelas: POST sem campos `parcelas-*`. Comportamento idêntico ao anterior.
- Adicionar 2 parcelas via JS: campos `parcelas-0-valor`, `parcelas-1-valor` presentes no POST.
- Submeter com 2 parcelas: 2 `ParcelaEntradaFixa` criadas, 24 `ReceitaFixa` geradas (2 por mês × 12 meses).
- Editar entrada com parcelas: form de edição pré-popula parcelas existentes, checkbox marcado.
- Remover parcela no form de edição e salvar: parcelas antigas removidas, novas persistidas.

**TASK-7 (dashboard):**
- Card "Sobra" exibe `saldo_realizado_mes` como valor principal.
- Subtexto: "Previsto: R$ X.XXX,XX".
- Com `valor_realizado` preenchido em ReceitaFixas do mês: card reflete o valor.
- Sem nenhum `valor_realizado`: saldo_realizado = total_extras - total_pago.

**TASK-8 (relatório):**
- Seção D do relatório anual: colunas "Ent. Fixas Prev." e "Ent. Fixas Real." visíveis.
- Meses sem `valor_realizado` em nenhuma ReceitaFixa: coluna "Real." exibe "—".
- Meses com valor_realizado: exibe valor, coluna "Saldo" calculada corretamente.
- Anos anteriores (sem valor_realizado): sem erro, saldo anual usa fallback de receita_total.
- Totais do rodapé corretos.

### Testes automatizados

O projeto não possui suíte de testes automatizados configurada. Toda validação é manual via browser conforme checklist acima.

### Regressão crítica (verificar ao final de todas as tasks)

- Gastos mensais existentes (`Gasto`, `ReceitaExtra`): sem alteração de comportamento.
- `ParametroMensal.salario` e `SalarioForm`: campo "Salário" no card de Entradas ainda editável.
- EntradaFixa sem parcelas: rolling continua gerando 1 ReceitaFixa por mês.
- Relatório de anos anteriores: Seção D sem erro, colunas novas exibem "—" para histórico sem realizado.
- Todas as rotas existentes (gastos fixos, investimentos, projeções, dados): sem erro 500.
