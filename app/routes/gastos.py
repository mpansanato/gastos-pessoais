from datetime import datetime
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from app.fields import BRDecimalField as DecimalField

from app.extensions import db
from app.models.categoria import Categoria
from app.models.gasto import Gasto
from app.models.instituicao import Instituicao
from app.models.parametro_mensal import ParametroMensal
from app.models.receita_extra import ReceitaExtra

gastos_bp = Blueprint('gastos', __name__, url_prefix='/gastos')

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

CORES = [
    ('#dc3545', 'Vermelho'), ('#0d6efd', 'Azul'), ('#198754', 'Verde'),
    ('#ffc107', 'Amarelo'), ('#0dcaf0', 'Ciano'), ('#6f42c1', 'Roxo'),
    ('#fd7e14', 'Laranja'), ('#20c997', 'Teal'), ('#6c757d', 'Cinza'),
]


# ── Formulários ────────────────────────────────────────────────────────────────

_PARCELAS_CHOICES = [(1, 'À vista (1×)')] + [(n, f'{n}×') for n in range(2, 25)]


class GastoForm(FlaskForm):
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    categoria_id = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    valor_previsto = DecimalField('Valor Previsto (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    valor_pago = DecimalField('Valor Pago (R$)', validators=[Optional(), NumberRange(min=0)], places=2)
    parcelas = SelectField('Parcelas', choices=_PARCELAS_CHOICES, coerce=int, default=1)
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Salvar')


class CategoriaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    tipo = SelectField('Tipo', choices=[('fixo', 'Fixo'), ('variavel', 'Variável')])
    cor = SelectField('Cor', choices=CORES)
    submit = SubmitField('Criar Categoria')


class SalarioForm(FlaskForm):
    salario = DecimalField('Salário (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    submit = SubmitField('Salvar')


class ReceitaExtraForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[(t, t) for t in ReceitaExtra.TIPOS])
    descricao = StringField('Descrição (opcional — usa o Tipo se vazio)', validators=[Optional(), Length(max=200)])
    valor = DecimalField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    instituicao_id = SelectField('Instituição (se Saque)', coerce=int, validators=[Optional()])
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Adicionar')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_or_create_parametro(mes: int, ano: int) -> ParametroMensal:
    param = db.session.scalar(
        db.select(ParametroMensal).where(
            ParametroMensal.mes == mes, ParametroMensal.ano == ano
        )
    )
    if not param:
        param = ParametroMensal(mes=mes, ano=ano, salario=Decimal('0'))
        db.session.add(param)
        db.session.commit()
    return param


def _calcular_totais(gastos: list, salario: Decimal, receitas_extras: list = None) -> dict:
    receitas_extras = receitas_extras or []
    total_previsto = sum(float(g.valor_previsto) for g in gastos)
    total_pago = sum(float(g.valor_pago) for g in gastos if g.valor_pago is not None)
    sal = float(salario)
    total_extras = sum(float(r.valor) for r in receitas_extras)
    total_entradas = sal + total_extras
    return {
        'total_previsto': total_previsto,
        'total_pago': total_pago,
        'total_extras': total_extras,
        'total_entradas': total_entradas,
        'parcial': total_entradas - total_previsto,
        'sobra': total_entradas - total_pago,
    }


def _nav_mes(mes: int, ano: int):
    mes_ant = (mes - 2) % 12 + 1
    ano_ant = ano - 1 if mes == 1 else ano
    mes_prox = mes % 12 + 1
    ano_prox = ano + 1 if mes == 12 else ano
    return mes_ant, ano_ant, mes_prox, ano_prox


def _avancar_mes(mes: int, ano: int, n: int = 1):
    for _ in range(n):
        if mes == 12:
            mes, ano = 1, ano + 1
        else:
            mes += 1
    return mes, ano


# ── Rotas: Gastos ──────────────────────────────────────────────────────────────

@gastos_bp.route('/')
@login_required
def index():
    # Rolling automático: garante 12 meses à frente para cada gasto fixo ativo
    from app.routes.gastos_fixos import rolling_forward
    rolling_forward()
    hoje = datetime.today()
    return redirect(url_for('gastos.por_mes', ano=hoje.year, mes=hoje.month))


@gastos_bp.route('/<int:ano>/<int:mes>')
@login_required
def por_mes(ano: int, mes: int):
    if not (1 <= mes <= 12):
        return redirect(url_for('gastos.index'))

    categorias = db.session.scalars(
        db.select(Categoria).order_by(Categoria.ordem, Categoria.nome)
    ).all()

    todos_gastos = db.session.scalars(
        db.select(Gasto)
        .where(Gasto.mes == mes, Gasto.ano == ano)
        .order_by(Gasto.categoria_id, Gasto.descricao)
    ).all()

    param = _get_or_create_parametro(mes, ano)

    receitas_extras = db.session.scalars(
        db.select(ReceitaExtra)
        .where(ReceitaExtra.mes == mes, ReceitaExtra.ano == ano)
        .order_by(ReceitaExtra.tipo, ReceitaExtra.descricao)
    ).all()

    totais = _calcular_totais(todos_gastos, param.salario, receitas_extras)

    gastos_por_cat = {}
    for cat in categorias:
        lancamentos = [g for g in todos_gastos if g.categoria_id == cat.id]
        if lancamentos:
            gastos_por_cat[cat] = {
                'lancamentos': lancamentos,
                'subtotal_previsto': sum(float(g.valor_previsto) for g in lancamentos),
                'subtotal_pago': sum(float(g.valor_pago) for g in lancamentos if g.valor_pago is not None),
            }

    mes_ant, ano_ant, mes_prox, ano_prox = _nav_mes(mes, ano)

    salario_form = SalarioForm(salario=param.salario)
    gasto_form = GastoForm()
    gasto_form.categoria_id.choices = [(c.id, c.nome) for c in categorias]

    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    receita_form = ReceitaExtraForm()
    receita_form.instituicao_id.choices = [(0, '— selecione —')] + [(i.id, i.nome) for i in instituicoes]

    saques = [r for r in receitas_extras if r.eh_saque]

    return render_template(
        'gastos/index.html',
        mes=mes, ano=ano, nome_mes=MESES[mes - 1],
        categorias=categorias,
        gastos_por_cat=gastos_por_cat,
        totais=totais,
        param=param,
        receitas_extras=receitas_extras,
        saques=saques,
        salario_form=salario_form,
        gasto_form=gasto_form,
        receita_form=receita_form,
        mes_ant=mes_ant, ano_ant=ano_ant,
        mes_prox=mes_prox, ano_prox=ano_prox,
    )


@gastos_bp.route('/<int:ano>/<int:mes>/salario', methods=['POST'])
@login_required
def atualizar_salario(ano: int, mes: int):
    param = _get_or_create_parametro(mes, ano)
    form = SalarioForm()
    if form.validate_on_submit():
        param.salario = form.salario.data
        db.session.commit()
        flash('Salário atualizado.', 'success')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


@gastos_bp.route('/<int:ano>/<int:mes>/novo', methods=['POST'])
@login_required
def novo(ano: int, mes: int):
    categorias = db.session.scalars(db.select(Categoria).order_by(Categoria.nome)).all()
    form = GastoForm()
    form.categoria_id.choices = [(c.id, c.nome) for c in categorias]
    if form.validate_on_submit():
        n = form.parcelas.data or 1
        grupo_id = None
        for i in range(n):
            m, a = _avancar_mes(mes, ano, i)
            pago = form.valor_pago.data if (i == 0 and form.valor_pago.data is not None) else None
            gasto = Gasto(
                descricao=form.descricao.data,
                categoria_id=form.categoria_id.data,
                valor_previsto=form.valor_previsto.data,
                valor_pago=pago,
                mes=m, ano=a,
                observacao=form.observacao.data or None,
                parcela_total=n if n > 1 else None,
                parcela_num=i + 1 if n > 1 else None,
                parcela_grupo_id=None,
            )
            db.session.add(gasto)
            db.session.flush()
            if i == 0:
                grupo_id = gasto.id
            if n > 1:
                gasto.parcela_grupo_id = grupo_id
        db.session.commit()
        if n > 1:
            flash(f'Gasto parcelado em {n}× adicionado nos próximos {n} meses.', 'success')
        else:
            flash('Gasto adicionado.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


@gastos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    gasto = db.get_or_404(Gasto, id)
    categorias = db.session.scalars(db.select(Categoria).order_by(Categoria.nome)).all()
    form = GastoForm(obj=gasto)
    form.categoria_id.choices = [(c.id, c.nome) for c in categorias]
    if form.validate_on_submit():
        n = form.parcelas.data or 1
        # Parcelar a partir deste gasto (só quando não é já parte de um grupo)
        if n > 1 and not gasto.parcela_grupo_id:
            gasto.descricao = form.descricao.data
            gasto.categoria_id = form.categoria_id.data
            gasto.valor_previsto = form.valor_previsto.data
            gasto.valor_pago = form.valor_pago.data if form.valor_pago.data is not None else None
            gasto.observacao = form.observacao.data or None
            gasto.parcela_total = n
            gasto.parcela_num = 1
            gasto.parcela_grupo_id = gasto.id
            for i in range(1, n):
                m, a = _avancar_mes(gasto.mes, gasto.ano, i)
                novo = Gasto(
                    descricao=form.descricao.data,
                    categoria_id=form.categoria_id.data,
                    valor_previsto=form.valor_previsto.data,
                    valor_pago=None,
                    mes=m, ano=a,
                    observacao=form.observacao.data or None,
                    parcela_total=n,
                    parcela_num=i + 1,
                    parcela_grupo_id=gasto.id,
                )
                db.session.add(novo)
            db.session.commit()
            flash(f'Gasto convertido em {n}× — parcelas criadas nos próximos meses.', 'success')
        else:
            gasto.descricao = form.descricao.data
            gasto.categoria_id = form.categoria_id.data
            gasto.valor_previsto = form.valor_previsto.data
            gasto.valor_pago = form.valor_pago.data if form.valor_pago.data is not None else None
            gasto.observacao = form.observacao.data or None
            db.session.commit()
            flash('Gasto atualizado.', 'success')
        return redirect(url_for('gastos.por_mes', ano=gasto.ano, mes=gasto.mes))
    return render_template('gastos/form.html', form=form, gasto=gasto)


@gastos_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id: int):
    gasto = db.get_or_404(Gasto, id)
    ano, mes = gasto.ano, gasto.mes
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto removido.', 'success')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


@gastos_bp.route('/excluir-grupo/<int:grupo_id>', methods=['POST'])
@login_required
def excluir_grupo(grupo_id: int):
    gastos = db.session.scalars(
        db.select(Gasto).where(Gasto.parcela_grupo_id == grupo_id)
    ).all()
    if not gastos:
        flash('Grupo de parcelas não encontrado.', 'danger')
        return redirect(url_for('gastos.index'))
    primeiro = gastos[0]
    ano, mes = primeiro.ano, primeiro.mes
    n = len(gastos)
    for g in gastos:
        db.session.delete(g)
    db.session.commit()
    flash(f'{n} parcelas removidas.', 'success')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


# ── Rotas: Receitas Extras ─────────────────────────────────────────────────────

@gastos_bp.route('/<int:ano>/<int:mes>/receita/nova', methods=['POST'])
@login_required
def nova_receita(ano: int, mes: int):
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = ReceitaExtraForm()
    form.instituicao_id.choices = [(0, '— selecione —')] + [(i.id, i.nome) for i in instituicoes]
    if form.validate_on_submit():
        inst_id = form.instituicao_id.data or None
        if inst_id == 0:
            inst_id = None
        descricao = (form.descricao.data or '').strip() or form.tipo.data
        receita = ReceitaExtra(
            descricao=descricao,
            tipo=form.tipo.data,
            valor=form.valor.data,
            mes=mes, ano=ano,
            instituicao_id=inst_id,
            observacao=form.observacao.data or None,
        )
        db.session.add(receita)
        db.session.commit()
        flash(f'{receita.tipo} — {receita.descricao} adicionado às entradas do mês.', 'success')
    else:
        for nome_campo, erros in form.errors.items():
            campo = getattr(form, nome_campo, None)
            label = campo.label.text if campo and hasattr(campo, 'label') else nome_campo
            for e in erros:
                flash(f'{label}: {e}', 'danger')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


@gastos_bp.route('/receita/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_receita(id: int):
    receita = db.get_or_404(ReceitaExtra, id)
    ano, mes = receita.ano, receita.mes
    db.session.delete(receita)
    db.session.commit()
    flash('Receita removida.', 'success')
    return redirect(url_for('gastos.por_mes', ano=ano, mes=mes))


# ── Rotas: Categorias ──────────────────────────────────────────────────────────

@gastos_bp.route('/categorias')
@login_required
def categorias():
    cats = db.session.scalars(
        db.select(Categoria).order_by(Categoria.ordem, Categoria.nome)
    ).all()
    form = CategoriaForm()
    return render_template('gastos/categorias.html', categorias=cats, form=form)


@gastos_bp.route('/categorias/nova', methods=['POST'])
@login_required
def nova_categoria():
    form = CategoriaForm()
    if form.validate_on_submit():
        if db.session.scalar(db.select(Categoria).where(Categoria.nome == form.nome.data)):
            flash('Já existe uma categoria com esse nome.', 'danger')
        else:
            cat = Categoria(nome=form.nome.data, tipo=form.tipo.data, cor=form.cor.data)
            db.session.add(cat)
            db.session.commit()
            flash(f'Categoria "{cat.nome}" criada.', 'success')
    return redirect(url_for('gastos.categorias'))


@gastos_bp.route('/categorias/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_categoria(id: int):
    cat = db.get_or_404(Categoria, id)
    if cat.gastos.count() > 0:
        flash('Não é possível excluir: categoria possui gastos vinculados.', 'danger')
    else:
        nome = cat.nome
        db.session.delete(cat)
        db.session.commit()
        flash(f'Categoria "{nome}" removida.', 'success')
    return redirect(url_for('gastos.categorias'))
