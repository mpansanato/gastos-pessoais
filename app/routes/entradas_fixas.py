from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, FieldList, FormField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from wtforms.form import Form as BaseForm
from app.fields import BRDecimalField as DecimalField
from app.models.parcela_entrada_fixa import ParcelaEntradaFixa

from app.extensions import db
from app.models.entrada_fixa import EntradaFixa
from app.models.receita_fixa import ReceitaFixa

entradas_fixas_bp = Blueprint('entradas_fixas', __name__, url_prefix='/entradas/fixas')

MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


# ── Formulário ─────────────────────────────────────────────────────────────────

class ParcelaForm(BaseForm):
    valor           = DecimalField('Valor', validators=[DataRequired(), NumberRange(min=0)], places=2)
    dia_recebimento = IntegerField('Dia', validators=[Optional(), NumberRange(min=1, max=31)])


class EntradaFixaForm(FlaskForm):
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    valor = DecimalField('Valor Mensal (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    dia_recebimento = IntegerField(
        'Dia de Recebimento',
        validators=[Optional(), NumberRange(min=1, max=31)],
    )
    parcelas = FieldList(FormField(ParcelaForm), min_entries=0)
    submit = SubmitField('Salvar')


# ── Helpers de geração ─────────────────────────────────────────────────────────

def _prox(mes: int, ano: int):
    return (mes % 12 + 1, ano + 1 if mes == 12 else ano)


def _ensure_12_meses(entrada: EntradaFixa, hoje_mes: int, hoje_ano: int) -> int:
    """Garante que existam receitas geradas para os 12 meses seguintes ao atual."""
    if entrada.tem_parcelas:
        criados = 0
        for mes_offset in range(1, 13):
            m = hoje_mes + mes_offset
            a = hoje_ano + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            for parcela in entrada.parcelas:
                existe = db.session.scalar(
                    db.select(db.func.count()).select_from(ReceitaFixa).where(
                        ReceitaFixa.entrada_fixa_id == entrada.id,
                        ReceitaFixa.mes == m,
                        ReceitaFixa.ano == a,
                        ReceitaFixa.parcela_ordem == parcela.ordem,
                    )
                )
                if not existe:
                    db.session.add(ReceitaFixa(
                        descricao=entrada.descricao,
                        valor=parcela.valor,
                        mes=m,
                        ano=a,
                        entrada_fixa_id=entrada.id,
                        observacao=entrada.observacao,
                        dia_recebimento=parcela.dia_recebimento,
                        parcela_ordem=parcela.ordem,
                    ))
                    criados += 1
        if criados:
            db.session.commit()
        return criados

    mes, ano = hoje_mes, hoje_ano
    criados = 0
    for _ in range(12):
        mes, ano = _prox(mes, ano)
        existe = db.session.scalar(
            db.select(db.func.count()).select_from(ReceitaFixa).where(
                ReceitaFixa.entrada_fixa_id == entrada.id,
                ReceitaFixa.mes == mes,
                ReceitaFixa.ano == ano,
            )
        ) > 0
        if not existe:
            db.session.add(ReceitaFixa(
                descricao=entrada.descricao,
                valor=entrada.valor,
                mes=mes, ano=ano,
                entrada_fixa_id=entrada.id,
                observacao=entrada.observacao,
                dia_recebimento=entrada.dia_recebimento,
                parcela_ordem=None,
            ))
            criados += 1
    if criados:
        db.session.commit()
    return criados


def _atualizar_futuros(entrada: EntradaFixa, hoje_mes: int, hoje_ano: int):
    """Atualiza desc/valor nas receitas futuras geradas. Nunca toca no mês atual nem no passado."""
    if entrada.tem_parcelas:
        futuros = db.session.scalars(
            db.select(ReceitaFixa).where(
                ReceitaFixa.entrada_fixa_id == entrada.id,
                db.or_(
                    ReceitaFixa.ano > hoje_ano,
                    db.and_(ReceitaFixa.ano == hoje_ano, ReceitaFixa.mes > hoje_mes),
                ),
            )
        ).all()
        for r in futuros:
            parcela = next((p for p in entrada.parcelas if p.ordem == r.parcela_ordem), None)
            if parcela:
                r.descricao       = entrada.descricao
                r.valor           = parcela.valor
                r.dia_recebimento = parcela.dia_recebimento
                r.observacao      = entrada.observacao
        if futuros:
            db.session.commit()
        return len(futuros)

    prox_mes, prox_ano = _prox(hoje_mes, hoje_ano)
    futuros = db.session.scalars(
        db.select(ReceitaFixa).where(
            ReceitaFixa.entrada_fixa_id == entrada.id,
            db.or_(
                ReceitaFixa.ano > prox_ano,
                db.and_(ReceitaFixa.ano == prox_ano, ReceitaFixa.mes >= prox_mes),
            ),
        )
    ).all()
    for r in futuros:
        r.descricao = entrada.descricao
        r.valor = entrada.valor
        r.observacao = entrada.observacao
    if futuros:
        db.session.commit()
    return len(futuros)


def rolling_forward():
    """Para cada entrada fixa ativa, garante 12 meses à frente."""
    hoje = datetime.today()
    entradas = db.session.scalars(
        db.select(EntradaFixa).where(EntradaFixa.ativo == True)
    ).all()
    for entrada in entradas:
        _ensure_12_meses(entrada, hoje.month, hoje.year)


# ── Rotas ──────────────────────────────────────────────────────────────────────

@entradas_fixas_bp.route('/')
@login_required
def index():
    hoje = datetime.today()
    rolling_forward()

    entradas = db.session.scalars(
        db.select(EntradaFixa).order_by(EntradaFixa.ativo.desc(), EntradaFixa.descricao)
    ).all()

    form = EntradaFixaForm()

    preview_meses = []
    m, a = hoje.month, hoje.year
    for _ in range(12):
        m, a = _prox(m, a)
        preview_meses.append((m, a))

    entradas_data = []
    for entrada in entradas:
        meses_gerados = {
            (r.mes, r.ano)
            for r in db.session.scalars(
                db.select(ReceitaFixa).where(
                    ReceitaFixa.entrada_fixa_id == entrada.id,
                    db.or_(
                        ReceitaFixa.ano > hoje.year,
                        db.and_(ReceitaFixa.ano == hoje.year, ReceitaFixa.mes > hoje.month),
                    ),
                )
            ).all()
        }
        entradas_data.append({'entrada': entrada, 'meses_gerados': meses_gerados})

    return render_template(
        'entradas/fixas.html',
        entradas_data=entradas_data,
        form=form,
        preview_meses=preview_meses,
        meses_abrev=MESES_ABREV,
        hoje_mes=hoje.month,
        hoje_ano=hoje.year,
    )


@entradas_fixas_bp.route('/nova', methods=['POST'])
@login_required
def nova():
    hoje = datetime.today()
    form = EntradaFixaForm()
    if form.validate_on_submit():
        entrada = EntradaFixa(
            descricao=form.descricao.data,
            valor=form.valor.data,
            observacao=form.observacao.data or None,
            dia_recebimento=form.dia_recebimento.data or None,
            ativo=True,
        )
        db.session.add(entrada)
        db.session.flush()
        parcelas_data = form.parcelas.data or []
        parcelas_validas = [p for p in parcelas_data if p.get('valor') is not None]
        for i, p_data in enumerate(parcelas_validas):
            db.session.add(ParcelaEntradaFixa(
                entrada_fixa_id=entrada.id,
                valor=p_data['valor'],
                dia_recebimento=p_data.get('dia_recebimento') or None,
                ordem=i + 1,
            ))
        db.session.commit()
        n = _ensure_12_meses(entrada, hoje.month, hoje.year)
        flash(f'"{entrada.descricao}" criada e projetada para os próximos {n} meses.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('entradas_fixas.index'))


@entradas_fixas_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    hoje = datetime.today()
    entrada = db.get_or_404(EntradaFixa, id)
    form = EntradaFixaForm(obj=entrada)

    if form.validate_on_submit():
        entrada.descricao = form.descricao.data
        entrada.valor = form.valor.data
        entrada.observacao = form.observacao.data or None
        entrada.dia_recebimento = form.dia_recebimento.data or None
        # Recriar parcelas
        for p in list(entrada.parcelas):
            db.session.delete(p)
        db.session.flush()
        parcelas_data = form.parcelas.data or []
        parcelas_validas = [p for p in parcelas_data if p.get('valor') is not None]
        for i, p_data in enumerate(parcelas_validas):
            db.session.add(ParcelaEntradaFixa(
                entrada_fixa_id=entrada.id,
                valor=p_data['valor'],
                dia_recebimento=p_data.get('dia_recebimento') or None,
                ordem=i + 1,
            ))
        db.session.commit()
        n_atualizados = _atualizar_futuros(entrada, hoje.month, hoje.year)
        _ensure_12_meses(entrada, hoje.month, hoje.year)
        flash(
            f'"{entrada.descricao}" atualizada — '
            f'{n_atualizados} meses futuros atualizados. '
            f'O mês atual não foi alterado.',
            'success',
        )
        return redirect(url_for('entradas_fixas.index'))

    return render_template('entradas/fixas_form.html', form=form, entrada=entrada)


@entradas_fixas_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id: int):
    hoje = datetime.today()
    entrada = db.get_or_404(EntradaFixa, id)
    entrada.ativo = not entrada.ativo
    db.session.commit()

    prox_mes, prox_ano = _prox(hoje.month, hoje.year)

    if entrada.ativo:
        n = _ensure_12_meses(entrada, hoje.month, hoje.year)
        flash(f'"{entrada.descricao}" reativada — {n} meses projetados.', 'success')
    else:
        futuros = db.session.scalars(
            db.select(ReceitaFixa).where(
                ReceitaFixa.entrada_fixa_id == entrada.id,
                db.or_(
                    ReceitaFixa.ano > prox_ano,
                    db.and_(ReceitaFixa.ano == prox_ano, ReceitaFixa.mes >= prox_mes),
                ),
            )
        ).all()
        for r in futuros:
            db.session.delete(r)
        db.session.commit()
        flash(
            f'"{entrada.descricao}" pausada — {len(futuros)} lançamentos futuros removidos.',
            'warning',
        )
    return redirect(url_for('entradas_fixas.index'))


@entradas_fixas_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id: int):
    entrada = db.get_or_404(EntradaFixa, id)
    hoje = datetime.today()
    prox_mes, prox_ano = _prox(hoje.month, hoje.year)

    futuros = db.session.scalars(
        db.select(ReceitaFixa).where(
            ReceitaFixa.entrada_fixa_id == entrada.id,
            db.or_(
                ReceitaFixa.ano > prox_ano,
                db.and_(ReceitaFixa.ano == prox_ano, ReceitaFixa.mes >= prox_mes),
            ),
        )
    ).all()
    for r in futuros:
        db.session.delete(r)

    # Desvincula registros passados (preserva histórico)
    db.session.execute(
        db.update(ReceitaFixa).where(ReceitaFixa.entrada_fixa_id == entrada.id).values(entrada_fixa_id=None)
    )

    nome = entrada.descricao
    db.session.delete(entrada)
    db.session.commit()
    flash(f'"{nome}" excluída. {len(futuros)} lançamentos futuros removidos.', 'success')
    return redirect(url_for('entradas_fixas.index'))
