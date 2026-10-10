from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from app.fields import BRDecimalField as DecimalField

from app.extensions import db
from app.models.gasto import Gasto
from app.models.gasto_fixo import GastoFixo
from app.models.investimento import Investimento
from app.models.parametro_mensal import ParametroMensal
from app.models.parametro_projecao import ParametroProjecao
from app.models.receita_extra import ReceitaExtra

projecoes_bp = Blueprint('projecoes', __name__, url_prefix='/projecoes')

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


# ── Formulário ─────────────────────────────────────────────────────────────────

class ProjecaoForm(FlaskForm):
    aporte_mensal = DecimalField(
        'Aporte mensal planejado (R$)',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2,
    )
    meses_projecao = SelectField(
        'Período de projeção',
        choices=[(6, '6 meses'), (12, '12 meses'), (18, '18 meses'), (24, '24 meses'), (36, '3 anos')],
        coerce=int,
    )
    submit = SubmitField('Atualizar Parâmetros')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_or_create_param() -> ParametroProjecao:
    param = db.session.scalar(db.select(ParametroProjecao))
    if not param:
        param = ParametroProjecao()
        db.session.add(param)
        db.session.commit()
    return param


def _proximo_mes(mes: int, ano: int):
    return (mes % 12 + 1, ano + 1 if mes == 12 else ano)


def _mes_anterior(mes: int, ano: int):
    return (12, ano - 1) if mes == 1 else (mes - 1, ano)


def extras_previstas_por_mes(hoje_mes: int, hoje_ano: int, n_meses: int) -> dict:
    """Soma, por (ano, mes), as receitas extras avulsas AINDA NÃO REALIZADAS
    (valor_realizado is None) nos próximos n_meses a partir de hoje (inclusive).

    Usado para sensibilizar a projeção de patrimônio com entradas pontuais já
    previstas (bônus, outorgas, restituições...) — sem mexer no aporte mensal
    "normal" configurado pelo usuário, só somando o extra no mês em que cai.
    """
    fim_mes, fim_ano = hoje_mes, hoje_ano
    for _ in range(n_meses):
        fim_mes, fim_ano = _proximo_mes(fim_mes, fim_ano)
    rows = db.session.execute(
        db.select(ReceitaExtra.ano, ReceitaExtra.mes, db.func.sum(ReceitaExtra.valor).label('total'))
        .where(
            ReceitaExtra.valor_realizado.is_(None),
            db.or_(
                ReceitaExtra.ano > hoje_ano,
                db.and_(ReceitaExtra.ano == hoje_ano, ReceitaExtra.mes >= hoje_mes),
            ),
            db.or_(
                ReceitaExtra.ano < fim_ano,
                db.and_(ReceitaExtra.ano == fim_ano, ReceitaExtra.mes <= fim_mes),
            ),
        )
        .group_by(ReceitaExtra.ano, ReceitaExtra.mes)
    ).all()
    return {(r.ano, r.mes): float(r.total) for r in rows}


def calcular_projecao(base_valor: float, rendimento_pct: float, aporte_mensal: float,
                      n_meses: int, base_mes: int, base_ano: int,
                      extras_por_mes: dict | None = None) -> list[dict]:
    extras_por_mes = extras_por_mes or {}
    resultados = []
    saldo = base_valor
    r = rendimento_pct / 100

    mes, ano = base_mes, base_ano
    for _ in range(n_meses):
        mes, ano = _proximo_mes(mes, ano)
        aporte_extra = extras_por_mes.get((ano, mes), 0.0)
        aporte_total = aporte_mensal + aporte_extra
        rendimento = saldo * r
        saldo_fim = saldo + rendimento + aporte_total
        resultados.append({
            'mes': mes, 'ano': ano,
            'nome_mes': MESES[mes - 1],
            'saldo_inicio': saldo,
            'rendimento': rendimento,
            'aporte': aporte_total,
            'aporte_base': aporte_mensal,
            'aporte_extra': aporte_extra,
            'saldo_fim': saldo_fim,
        })
        saldo = saldo_fim
    return resultados


def _contexto_financeiro(hoje: date) -> dict:
    """Calcula salário, gastos fixos, média de gastos e surplus para contextualizar o aporte."""

    # Salário: mês configurado mais recente com salário > 0
    ultimo_param = db.session.scalar(
        db.select(ParametroMensal)
        .where(ParametroMensal.salario > 0)
        .order_by(ParametroMensal.ano.desc(), ParametroMensal.mes.desc())
    )
    salario = float(ultimo_param.salario) if ultimo_param else 0.0
    salario_ref = f'{MESES[ultimo_param.mes - 1]} {ultimo_param.ano}' if ultimo_param else None

    # Gastos fixos ativos
    total_fixos = float(
        db.session.scalar(
            db.select(db.func.sum(GastoFixo.valor)).where(GastoFixo.ativo == True)
        ) or 0
    )
    qtd_fixos = db.session.scalar(
        db.select(db.func.count()).select_from(GastoFixo).where(GastoFixo.ativo == True)
    ) or 0

    # Média de gastos totais pagos nos últimos 6 meses
    totais_6m = []
    m, a = hoje.month, hoje.year
    for _ in range(6):
        total = float(
            db.session.scalar(
                db.select(db.func.sum(Gasto.valor_pago))
                .where(Gasto.mes == m, Gasto.ano == a, Gasto.valor_pago.isnot(None))
            ) or 0
        )
        if total > 0:
            totais_6m.append(total)
        m, a = _mes_anterior(m, a)
    media_gastos_6m = sum(totais_6m) / len(totais_6m) if totais_6m else 0.0

    surplus_fixos = salario - total_fixos
    surplus_media = salario - media_gastos_6m

    return {
        'salario': salario,
        'salario_ref': salario_ref,
        'total_fixos': total_fixos,
        'qtd_fixos': qtd_fixos,
        'media_gastos_6m': media_gastos_6m,
        'surplus_fixos': surplus_fixos,       # conservador: só descontando fixos
        'surplus_media': surplus_media,        # realista: descontando média histórica
        'tem_salario': salario > 0,
    }


# ── Rota principal ─────────────────────────────────────────────────────────────

@projecoes_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    hoje = date.today()
    param = _get_or_create_param()
    form = ProjecaoForm(obj=param)

    if form.validate_on_submit():
        param.aporte_mensal = form.aporte_mensal.data
        param.meses_projecao = form.meses_projecao.data
        db.session.commit()
        flash('Parâmetros atualizados.', 'success')
        return redirect(url_for('projecoes.index'))

    # Contexto financeiro (salário, fixos, surplus)
    contexto = _contexto_financeiro(hoje)

    # Histórico real de investimentos — restrito a meses <= hoje, para não usar como
    # "base" um mês que já é só projeção do rolling-forward do módulo de investimentos
    # (senão a projeção desta tela acabaria compondo 24 meses de crescimento em cima
    # de outros 12 já projetados, inflando o resultado).
    historico_rows = db.session.execute(
        db.select(
            Investimento.ano,
            Investimento.mes,
            db.func.sum(Investimento.valor).label('total'),
        )
        .where(db.or_(
            Investimento.ano < hoje.year,
            db.and_(Investimento.ano == hoje.year, Investimento.mes <= hoje.month),
        ))
        .group_by(Investimento.ano, Investimento.mes)
        .order_by(Investimento.ano.asc(), Investimento.mes.asc())
    ).all()

    if not historico_rows:
        return render_template(
            'projecoes/index.html',
            sem_dados=True, form=form, param=param,
            contexto=contexto, hoje=hoje,
        )

    historico = [
        {'mes': r.mes, 'ano': r.ano, 'nome_mes': MESES[r.mes - 1], 'total': float(r.total)}
        for r in historico_rows
    ]

    base = historico[-1]
    base_mes, base_ano, base_valor = base['mes'], base['ano'], base['total']

    extras_por_mes = extras_previstas_por_mes(base_mes, base_ano, param.meses_projecao)
    projecoes = calcular_projecao(
        base_valor=base_valor,
        rendimento_pct=float(param.rendimento_mensal_pct),
        aporte_mensal=float(param.aporte_mensal),
        n_meses=param.meses_projecao,
        base_mes=base_mes,
        base_ano=base_ano,
        extras_por_mes=extras_por_mes,
    )
    total_extras_previstos = sum(extras_por_mes.values())

    # Vencimentos nos próximos 12 meses
    try:
        limite = hoje.replace(year=hoje.year + 1)
    except ValueError:
        limite = hoje.replace(year=hoje.year + 1, day=28)

    vencimentos = db.session.scalars(
        db.select(Investimento)
        .where(
            Investimento.vencimento.isnot(None),
            Investimento.vencimento >= hoje,
            Investimento.vencimento <= limite,
        )
        .order_by(Investimento.vencimento.asc())
    ).all()

    return render_template(
        'projecoes/index.html',
        sem_dados=False,
        form=form,
        param=param,
        contexto=contexto,
        historico=historico,
        base_mes=base_mes,
        base_ano=base_ano,
        base_valor=base_valor,
        nome_mes_base=MESES[base_mes - 1],
        projecoes=projecoes,
        total_extras_previstos=total_extras_previstos,
        vencimentos=vencimentos,
        hoje=hoje,
    )
