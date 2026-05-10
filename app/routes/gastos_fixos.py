from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from app.fields import BRDecimalField as DecimalField

from app.extensions import db
from app.models.categoria import Categoria
from app.models.gasto import Gasto
from app.models.gasto_fixo import GastoFixo

gastos_fixos_bp = Blueprint('gastos_fixos', __name__, url_prefix='/gastos/fixos')

MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


# ── Formulário ─────────────────────────────────────────────────────────────────

class GastoFixoForm(FlaskForm):
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    categoria_id = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    valor = DecimalField('Valor Previsto (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Salvar')


# ── Helpers de geração ─────────────────────────────────────────────────────────

def _prox(mes: int, ano: int):
    return (mes % 12 + 1, ano + 1 if mes == 12 else ano)


def _ensure_12_meses(fixo: GastoFixo, hoje_mes: int, hoje_ano: int) -> int:
    """Garante que existam gastos gerados para os 12 meses seguintes ao atual.
    Retorna quantos meses foram criados."""
    mes, ano = hoje_mes, hoje_ano
    criados = 0
    for _ in range(12):
        mes, ano = _prox(mes, ano)
        existe = db.session.scalar(
            db.select(db.func.count()).select_from(Gasto).where(
                Gasto.gasto_fixo_id == fixo.id,
                Gasto.mes == mes,
                Gasto.ano == ano,
            )
        ) > 0
        if not existe:
            db.session.add(Gasto(
                descricao=fixo.descricao,
                categoria_id=fixo.categoria_id,
                valor_previsto=fixo.valor,
                valor_pago=None,
                mes=mes, ano=ano,
                gasto_fixo_id=fixo.id,
                observacao=fixo.observacao,
            ))
            criados += 1
    if criados:
        db.session.commit()
    return criados


def _atualizar_futuros(fixo: GastoFixo, hoje_mes: int, hoje_ano: int):
    """Atualiza desc/categoria/valor nos gastos futuros gerados.
    NUNCA toca no mês atual nem no passado."""
    prox_mes, prox_ano = _prox(hoje_mes, hoje_ano)
    futuros = db.session.scalars(
        db.select(Gasto).where(
            Gasto.gasto_fixo_id == fixo.id,
            db.or_(
                Gasto.ano > prox_ano,
                db.and_(Gasto.ano == prox_ano, Gasto.mes >= prox_mes),
            ),
        )
    ).all()
    for g in futuros:
        g.descricao = fixo.descricao
        g.categoria_id = fixo.categoria_id
        g.valor_previsto = fixo.valor
        g.observacao = fixo.observacao
    if futuros:
        db.session.commit()
    return len(futuros)


def rolling_forward():
    """Ponto de entrada para o rolling mensal.
    Chamado automaticamente ao acessar qualquer página de gastos.
    Para cada gasto fixo ativo, garante 12 meses à frente."""
    hoje = datetime.today()
    fixos = db.session.scalars(
        db.select(GastoFixo).where(GastoFixo.ativo == True)
    ).all()
    for fixo in fixos:
        _ensure_12_meses(fixo, hoje.month, hoje.year)


# ── Rotas ──────────────────────────────────────────────────────────────────────

@gastos_fixos_bp.route('/')
@login_required
def index():
    hoje = datetime.today()
    rolling_forward()  # rolling automático ao acessar o painel

    fixos = db.session.scalars(
        db.select(GastoFixo).order_by(GastoFixo.ativo.desc(), GastoFixo.descricao)
    ).all()
    categorias = db.session.scalars(
        db.select(Categoria).order_by(Categoria.ordem, Categoria.nome)
    ).all()

    form = GastoFixoForm()
    form.categoria_id.choices = [(c.id, c.nome) for c in categorias]

    # Preview: quais dos próximos 12 meses já foram gerados por cada fixo
    preview_meses = []
    m, a = hoje.month, hoje.year
    for _ in range(12):
        m, a = _prox(m, a)
        preview_meses.append((m, a))

    fixos_data = []
    for fixo in fixos:
        meses_gerados = {
            (g.mes, g.ano)
            for g in db.session.scalars(
                db.select(Gasto).where(
                    Gasto.gasto_fixo_id == fixo.id,
                    db.or_(
                        Gasto.ano > hoje.year,
                        db.and_(Gasto.ano == hoje.year, Gasto.mes > hoje.month),
                    ),
                )
            ).all()
        }
        fixos_data.append({'fixo': fixo, 'meses_gerados': meses_gerados})

    return render_template(
        'gastos/fixos.html',
        fixos_data=fixos_data,
        form=form,
        preview_meses=preview_meses,
        meses_abrev=MESES_ABREV,
        hoje_mes=hoje.month,
        hoje_ano=hoje.year,
    )


@gastos_fixos_bp.route('/novo', methods=['POST'])
@login_required
def novo():
    hoje = datetime.today()
    categorias = db.session.scalars(db.select(Categoria).order_by(Categoria.nome)).all()
    form = GastoFixoForm()
    form.categoria_id.choices = [(c.id, c.nome) for c in categorias]
    if form.validate_on_submit():
        fixo = GastoFixo(
            descricao=form.descricao.data,
            categoria_id=form.categoria_id.data,
            valor=form.valor.data,
            observacao=form.observacao.data or None,
            ativo=True,
        )
        db.session.add(fixo)
        db.session.commit()
        n = _ensure_12_meses(fixo, hoje.month, hoje.year)
        flash(f'"{fixo.descricao}" criado e projetado para os próximos {n} meses.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('gastos_fixos.index'))


@gastos_fixos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    hoje = datetime.today()
    fixo = db.get_or_404(GastoFixo, id)
    categorias = db.session.scalars(db.select(Categoria).order_by(Categoria.nome)).all()
    form = GastoFixoForm(obj=fixo)
    form.categoria_id.choices = [(c.id, c.nome) for c in categorias]

    if form.validate_on_submit():
        fixo.descricao = form.descricao.data
        fixo.categoria_id = form.categoria_id.data
        fixo.valor = form.valor.data
        fixo.observacao = form.observacao.data or None
        db.session.commit()
        n_atualizados = _atualizar_futuros(fixo, hoje.month, hoje.year)
        _ensure_12_meses(fixo, hoje.month, hoje.year)
        flash(
            f'"{fixo.descricao}" atualizado — '
            f'{n_atualizados} meses futuros atualizados. '
            f'O mês atual não foi alterado.',
            'success',
        )
        return redirect(url_for('gastos_fixos.index'))

    return render_template('gastos/fixos_form.html', form=form, fixo=fixo)


@gastos_fixos_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id: int):
    hoje = datetime.today()
    fixo = db.get_or_404(GastoFixo, id)
    fixo.ativo = not fixo.ativo
    db.session.commit()

    prox_mes, prox_ano = _prox(hoje.month, hoje.year)

    if fixo.ativo:
        n = _ensure_12_meses(fixo, hoje.month, hoje.year)
        flash(f'"{fixo.descricao}" reativado — {n} meses projetados.', 'success')
    else:
        # Remove apenas futuros não-pagos
        futuros = db.session.scalars(
            db.select(Gasto).where(
                Gasto.gasto_fixo_id == fixo.id,
                Gasto.valor_pago.is_(None),
                db.or_(
                    Gasto.ano > prox_ano,
                    db.and_(Gasto.ano == prox_ano, Gasto.mes >= prox_mes),
                ),
            )
        ).all()
        for g in futuros:
            db.session.delete(g)
        db.session.commit()
        flash(
            f'"{fixo.descricao}" pausado — {len(futuros)} lançamentos futuros removidos.',
            'warning',
        )
    return redirect(url_for('gastos_fixos.index'))


@gastos_fixos_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id: int):
    hoje = datetime.today()
    fixo = db.get_or_404(GastoFixo, id)
    prox_mes, prox_ano = _prox(hoje.month, hoje.year)

    # Deleta futuros não-pagos
    futuros = db.session.scalars(
        db.select(Gasto).where(
            Gasto.gasto_fixo_id == fixo.id,
            Gasto.valor_pago.is_(None),
            db.or_(
                Gasto.ano > prox_ano,
                db.and_(Gasto.ano == prox_ano, Gasto.mes >= prox_mes),
            ),
        )
    ).all()
    for g in futuros:
        db.session.delete(g)

    # Desvincula gastos passados/pagos (preserva histórico)
    db.session.execute(
        db.update(Gasto).where(Gasto.gasto_fixo_id == fixo.id).values(gasto_fixo_id=None)
    )

    nome = fixo.descricao
    db.session.delete(fixo)
    db.session.commit()
    flash(f'"{nome}" excluído. {len(futuros)} lançamentos futuros removidos.', 'success')
    return redirect(url_for('gastos_fixos.index'))
