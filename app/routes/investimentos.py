from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from app.fields import BRDecimalField as DecimalField

from app.extensions import db
from app.models.instituicao import Instituicao
from app.models.investimento import Investimento

investimentos_bp = Blueprint('investimentos', __name__, url_prefix='/investimentos')

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

TIPOS = [
    'CDB', 'LCI', 'LCA', 'Debênture',
    'Ação', 'BDR', 'ETF',
    'Tesouro Selic', 'Tesouro IPCA+', 'Tesouro Prefixado',
    'Previdência Privada', 'FII',
    'Fundo de Investimento', 'Poupança', 'Outros',
]

CORES = [
    ('#1e40af', 'Azul escuro'), ('#0d6efd', 'Azul'), ('#0ea5e9', 'Azul claro'),
    ('#dc2626', 'Vermelho'), ('#f97316', 'Laranja'), ('#198754', 'Verde'),
    ('#6f42c1', 'Roxo'), ('#6c757d', 'Cinza'), ('#ffc107', 'Amarelo'),
]


# ── Formulários ────────────────────────────────────────────────────────────────

RISCO_CHOICES = [('baixo', 'Baixo'), ('medio', 'Médio'), ('alto', 'Alto')]
RISCO_ORDEM   = {'alto': 0, 'medio': 1, 'baixo': 2}
RISCO_LABEL   = {'alto': 'Alto', 'medio': 'Médio', 'baixo': 'Baixo'}
RISCO_COR     = {'alto': 'danger', 'medio': 'warning', 'baixo': 'success'}

# Produtos cobertos pelo FGC (limite de R$ 250k por CPF por emissor)
TIPOS_FGC   = frozenset({'CDB', 'LCI', 'LCA', 'LC', 'LH', 'Poupança'})
FGC_LIMITE  = 250_000.0


class InvestimentoForm(FlaskForm):
    nome          = StringField('Nome / Descrição', validators=[DataRequired(), Length(max=200)])
    tipo          = SelectField('Tipo', choices=[(t, t) for t in TIPOS])
    instituicao_id = SelectField('Corretora / Custodiante', coerce=int, validators=[DataRequired()])
    valor         = DecimalField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    risco         = SelectField('Risco do Emissor', choices=RISCO_CHOICES, default='baixo')
    emissor       = StringField('Emissor (banco/empresa que emitiu)',
                                validators=[Optional(), Length(max=200)])
    fundo         = StringField('Fundo / Produto (FII, multimercado…)',
                                validators=[Optional(), Length(max=200)])
    vencimento    = DateField('Vencimento', validators=[Optional()])
    observacao    = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    submit        = SubmitField('Salvar')


class InstituicaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    cor = SelectField('Cor', choices=CORES)
    submit = SubmitField('Criar Instituição')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _nav_mes(mes: int, ano: int):
    mes_ant = (mes - 2) % 12 + 1
    ano_ant = ano - 1 if mes == 1 else ano
    mes_prox = mes % 12 + 1
    ano_prox = ano + 1 if mes == 12 else ano
    return mes_ant, ano_ant, mes_prox, ano_prox


# ── Rotas: Investimentos ───────────────────────────────────────────────────────

@investimentos_bp.route('/')
@login_required
def index():
    hoje = datetime.today()
    return redirect(url_for('investimentos.por_mes', ano=hoje.year, mes=hoje.month))


@investimentos_bp.route('/<int:ano>/<int:mes>')
@login_required
def por_mes(ano: int, mes: int):
    if not (1 <= mes <= 12):
        return redirect(url_for('investimentos.index'))

    instituicoes = db.session.scalars(
        db.select(Instituicao).order_by(Instituicao.nome)
    ).all()

    todos = db.session.scalars(
        db.select(Investimento)
        .where(Investimento.mes == mes, Investimento.ano == ano)
        .order_by(Investimento.instituicao_id, Investimento.nome)
    ).all()

    total_geral = sum(float(i.valor) for i in todos)

    # Agrupar por instituição
    por_inst = {}
    for inst in instituicoes:
        items = [i for i in todos if i.instituicao_id == inst.id]
        if items:
            por_inst[inst] = {
                'lancamentos': items,
                'subtotal': sum(float(i.valor) for i in items),
            }

    # Calcular percentual por instituição
    for dados in por_inst.values():
        dados['percentual'] = (dados['subtotal'] / total_geral * 100) if total_geral else 0

    mes_ant, ano_ant, mes_prox, ano_prox = _nav_mes(mes, ano)

    form = InvestimentoForm()
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]

    return render_template(
        'investimentos/index.html',
        mes=mes, ano=ano, nome_mes=MESES[mes - 1],
        instituicoes=instituicoes,
        por_inst=por_inst,
        total_geral=total_geral,
        qtd=len(todos),
        form=form,
        mes_ant=mes_ant, ano_ant=ano_ant,
        mes_prox=mes_prox, ano_prox=ano_prox,
    )


@investimentos_bp.route('/<int:ano>/<int:mes>/novo', methods=['POST'])
@login_required
def novo(ano: int, mes: int):
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = InvestimentoForm()
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]
    if form.validate_on_submit():
        inv = Investimento(
            nome=form.nome.data,
            tipo=form.tipo.data,
            instituicao_id=form.instituicao_id.data,
            valor=form.valor.data,
            mes=mes, ano=ano,
            risco=form.risco.data,
            emissor=form.emissor.data.strip() or None,
            fundo=form.fundo.data.strip() or None,
            vencimento=form.vencimento.data,
            observacao=form.observacao.data or None,
        )
        db.session.add(inv)
        db.session.commit()
        flash('Investimento adicionado.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('investimentos.por_mes', ano=ano, mes=mes))


@investimentos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    inv = db.get_or_404(Investimento, id)
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = InvestimentoForm(obj=inv)
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]
    if form.validate_on_submit():
        inv.nome = form.nome.data
        inv.tipo = form.tipo.data
        inv.instituicao_id = form.instituicao_id.data
        inv.valor = form.valor.data
        inv.risco    = form.risco.data
        inv.emissor  = form.emissor.data.strip() or None
        inv.fundo    = form.fundo.data.strip() or None
        inv.vencimento = form.vencimento.data
        inv.observacao = form.observacao.data or None
        db.session.commit()
        flash('Investimento atualizado.', 'success')
        return redirect(url_for('investimentos.por_mes', ano=inv.ano, mes=inv.mes))
    return render_template('investimentos/form.html', form=form, inv=inv)


@investimentos_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id: int):
    inv = db.get_or_404(Investimento, id)
    ano, mes = inv.ano, inv.mes
    db.session.delete(inv)
    db.session.commit()
    flash('Investimento removido.', 'success')
    return redirect(url_for('investimentos.por_mes', ano=ano, mes=mes))


# ── Rotas: Instituições ────────────────────────────────────────────────────────

@investimentos_bp.route('/instituicoes')
@login_required
def instituicoes():
    insts = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = InstituicaoForm()
    return render_template('investimentos/instituicoes.html', instituicoes=insts, form=form)


@investimentos_bp.route('/instituicoes/nova', methods=['POST'])
@login_required
def nova_instituicao():
    form = InstituicaoForm()
    if form.validate_on_submit():
        if db.session.scalar(db.select(Instituicao).where(Instituicao.nome == form.nome.data)):
            flash('Já existe uma instituição com esse nome.', 'danger')
        else:
            inst = Instituicao(nome=form.nome.data, cor=form.cor.data)
            db.session.add(inst)
            db.session.commit()
            flash(f'Instituição "{inst.nome}" criada.', 'success')
    return redirect(url_for('investimentos.instituicoes'))


@investimentos_bp.route('/instituicoes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_instituicao(id: int):
    inst = db.get_or_404(Instituicao, id)
    if inst.investimentos.count() > 0:
        flash('Não é possível excluir: instituição possui investimentos vinculados.', 'danger')
    else:
        nome = inst.nome
        db.session.delete(inst)
        db.session.commit()
        flash(f'Instituição "{nome}" removida.', 'success')
    return redirect(url_for('investimentos.instituicoes'))


# ── Rota: Painel de Risco ──────────────────────────────────────────────────────

@investimentos_bp.route('/risco')
@login_required
def painel_risco():
    result = db.session.execute(
        db.select(Investimento.ano, Investimento.mes)
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
        .limit(1)
    ).first()

    if not result:
        return render_template('investimentos/risco.html', sem_dados=True)

    base_ano, base_mes = result.ano, result.mes
    todos = db.session.scalars(
        db.select(Investimento)
        .where(Investimento.mes == base_mes, Investimento.ano == base_ano)
    ).all()

    total = sum(float(i.valor) for i in todos)

    # ── Breakdown por nível de risco
    por_risco = {
        'alto':  {'label': 'Alto',  'cor': 'danger',  'total': 0.0, 'pct': 0.0, 'lancamentos': []},
        'medio': {'label': 'Médio', 'cor': 'warning', 'total': 0.0, 'pct': 0.0, 'lancamentos': []},
        'baixo': {'label': 'Baixo', 'cor': 'success', 'total': 0.0, 'pct': 0.0, 'lancamentos': []},
    }
    for inv in sorted(todos, key=lambda i: RISCO_ORDEM.get(i.risco, 3)):
        r = por_risco.get(inv.risco, por_risco['baixo'])
        r['total'] += float(inv.valor)
        r['lancamentos'].append(inv)
    for r in por_risco.values():
        r['pct'] = r['total'] / total * 100 if total else 0

    # ── Concentração por EMISSOR (risco principal: crédito do emissor)
    emissores: dict = {}
    sem_emissor: list = []
    for inv in todos:
        chave = (inv.emissor or '').strip()
        if not chave:
            sem_emissor.append(inv)
            continue
        if chave not in emissores:
            emissores[chave] = {
                'total': 0.0, 'fgc_elegivel': 0.0, 'pct': 0.0,
                'lancamentos': [], 'risco_max': 'baixo',
            }
        e = emissores[chave]
        v = float(inv.valor)
        e['total'] += v
        e['lancamentos'].append(inv)
        if inv.tipo in TIPOS_FGC:
            e['fgc_elegivel'] += v
        if RISCO_ORDEM.get(inv.risco, 3) < RISCO_ORDEM.get(e['risco_max'], 3):
            e['risco_max'] = inv.risco

    total_coberto = 0.0
    total_exposto = 0.0
    for e in emissores.values():
        e['pct']     = e['total'] / total * 100 if total else 0
        e['coberto'] = min(e['fgc_elegivel'], FGC_LIMITE)
        e['exposto'] = max(0.0, e['fgc_elegivel'] - FGC_LIMITE)
        total_coberto += e['coberto']
        total_exposto += e['exposto']
    emissores = dict(sorted(emissores.items(), key=lambda x: x[1]['total'], reverse=True))

    # ── Alertas por emissor
    alertas = []
    for nome_emissor, e in emissores.items():
        if e['exposto'] > 0 and e['risco_max'] == 'alto':
            alertas.append({'nivel': 'danger', 'icone': 'bi-exclamation-octagon-fill',
                'msg': (f'<strong>{nome_emissor}</strong>: '
                        f'<strong>{_brl(e["exposto"])}</strong> acima do limite do FGC '
                        f'e o emissor está com risco <strong>ALTO</strong>. '
                        f'Valor não coberto em caso de liquidação.')})
        elif e['exposto'] > 0:
            alertas.append({'nivel': 'warning', 'icone': 'bi-exclamation-triangle-fill',
                'msg': (f'<strong>{nome_emissor}</strong>: '
                        f'<strong>{_brl(e["exposto"])}</strong> acima do limite de '
                        f'R$ 250 mil do FGC — valor não coberto pelo garantidor.')})
        elif e['risco_max'] == 'alto':
            alertas.append({'nivel': 'warning', 'icone': 'bi-exclamation-triangle-fill',
                'msg': (f'<strong>{nome_emissor}</strong>: emissor com risco '
                        f'<strong>ALTO</strong> — monitore de perto.')})

    if sem_emissor:
        alertas.append({'nivel': 'info', 'icone': 'bi-info-circle-fill',
            'msg': (f'<strong>{len(sem_emissor)} investimento(s)</strong> sem emissor preenchido '
                    f'— não entram na análise FGC. Edite-os para incluir.')})

    return render_template(
        'investimentos/risco.html',
        sem_dados=False,
        alertas=alertas,
        por_risco=por_risco,
        emissores=emissores,
        sem_emissor=sem_emissor,
        total=total,
        total_coberto=total_coberto,
        total_exposto=total_exposto,
        fgc_limite=FGC_LIMITE,
        base_mes=base_mes,
        base_ano=base_ano,
        nome_mes=MESES[base_mes - 1],
    )


def _brl(v: float) -> str:
    fmt = '{:,.2f}'.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {fmt}'
