import json
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from app.extensions import db
from app.models.categoria import Categoria
from app.models.gasto import Gasto
from app.models.gasto_fixo import GastoFixo
from app.models.investimento import Investimento
from app.models.parametro_projecao import ParametroProjecao
from app.models.receita_extra import ReceitaExtra
from app.models.receita_fixa import ReceitaFixa

main_bp = Blueprint('main', __name__)

MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _mes_anterior(mes: int, ano: int):
    return (12, ano - 1) if mes == 1 else (mes - 1, ano)


def _proximo_mes(mes: int, ano: int):
    return (1, ano + 1) if mes == 12 else (mes + 1, ano)


def _label(mes: int, ano: int) -> str:
    return f'{MESES_ABREV[mes - 1]}/{ano % 100}'


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    hoje = datetime.today()
    mes, ano = hoje.month, hoje.year

    # ── Mês atual: gastos ───────────────────────────────────────────────────
    gastos_mes = db.session.scalars(
        db.select(Gasto).where(Gasto.mes == mes, Gasto.ano == ano)
    ).all()

    total_pago_mes = sum(float(g.valor_pago) for g in gastos_mes if g.valor_pago is not None)
    total_prev_mes = sum(float(g.valor_previsto) for g in gastos_mes)

    receitas_extras_mes = db.session.scalars(
        db.select(ReceitaExtra).where(ReceitaExtra.mes == mes, ReceitaExtra.ano == ano)
    ).all()
    total_extras_mes = sum(float(r.valor) for r in receitas_extras_mes)

    # ── Entradas fixas do mês: previsto e realizado ─────────────────────
    receitas_fixas_mes = db.session.scalars(
        db.select(ReceitaFixa).where(ReceitaFixa.mes == mes, ReceitaFixa.ano == ano)
    ).all()
    total_fixas_previsto_mes = sum(float(r.valor) for r in receitas_fixas_mes)
    total_fixas_realizado_mes = sum(
        float(r.valor_realizado)
        for r in receitas_fixas_mes
        if r.valor_realizado is not None
    )
    total_entradas_mes = total_extras_mes + total_fixas_previsto_mes
    saldo_realizado_mes = total_fixas_realizado_mes + total_extras_mes - total_pago_mes
    saldo_previsto_mes  = total_fixas_previsto_mes + total_extras_mes - total_prev_mes

    # ── Patrimônio investido (mês atual / mais recente não-futuro) ──────────
    # Restringe a meses <= atual para não exibir projeções futuras como
    # "Total Investido" — mantém o card idêntico à tela de Investimentos.
    inv_base = db.session.execute(
        db.select(Investimento.ano, Investimento.mes)
        .where(db.or_(
            Investimento.ano < ano,
            db.and_(Investimento.ano == ano, Investimento.mes <= mes),
        ))
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
        .limit(1)
    ).first()

    total_investido = 0.0
    total_investido_previdencia = 0.0
    total_investido_outros = 0.0
    inv_base_mes, inv_base_ano = mes, ano
    if inv_base:
        inv_base_mes, inv_base_ano = inv_base.mes, inv_base.ano
        total_investido = float(
            db.session.scalar(
                db.select(db.func.sum(Investimento.valor)).where(
                    Investimento.mes == inv_base_mes,
                    Investimento.ano == inv_base_ano,
                )
            ) or 0
        )
        total_investido_previdencia = float(
            db.session.scalar(
                db.select(db.func.sum(Investimento.valor)).where(
                    Investimento.mes == inv_base_mes,
                    Investimento.ano == inv_base_ano,
                    Investimento.tipo == 'Previdência Privada',
                )
            ) or 0
        )
        total_investido_outros = total_investido - total_investido_previdencia

    # ── Projeção 12 meses ───────────────────────────────────────────────────
    param_proj = db.session.scalar(db.select(ParametroProjecao))
    projecao_12m = 0.0
    if param_proj and total_investido > 0:
        saldo = total_investido
        r = float(param_proj.rendimento_mensal_pct) / 100
        a = float(param_proj.aporte_mensal)
        for _ in range(12):
            saldo = saldo * (1 + r) + a
        projecao_12m = saldo

    # ── Gastos fixos ativos ─────────────────────────────────────────────────
    fixos_ativos = db.session.scalar(
        db.select(db.func.count()).select_from(GastoFixo).where(GastoFixo.ativo == True)
    ) or 0
    total_fixos = float(
        db.session.scalar(
            db.select(db.func.sum(GastoFixo.valor)).where(GastoFixo.ativo == True)
        ) or 0
    )

    # ── Vencimentos próximos (30 dias) ──────────────────────────────────────
    hoje_date = date.today()
    limite_30 = hoje_date + timedelta(days=30)

    vencimentos_proximos = db.session.scalars(
        db.select(Investimento)
        .where(
            Investimento.vencimento.isnot(None),
            Investimento.vencimento >= hoje_date,
            Investimento.vencimento <= limite_30,
            Investimento.mes == inv_base_mes,
            Investimento.ano == inv_base_ano,
        )
        .order_by(Investimento.vencimento.asc())
        .limit(5)
    ).all()

    # ── Chart 1: Gastos por categoria (mês atual) ───────────────────────────
    cat_totais: dict[str, float] = {}
    cat_cores: dict[str, str] = {}
    for g in gastos_mes:
        cat_totais[g.categoria.nome] = cat_totais.get(g.categoria.nome, 0) + float(g.valor_previsto)
        cat_cores[g.categoria.nome] = g.categoria.cor
    cat_sorted = sorted(cat_totais.items(), key=lambda x: -x[1])
    chart_categorias = json.dumps({
        'labels': [c[0] for c in cat_sorted],
        'data':   [c[1] for c in cat_sorted],
        'cores':  [cat_cores[c[0]] for c in cat_sorted],
    })

    # ── Limites por Categoria ────────────────────────────────────────────────
    cat_pagos: dict[str, float] = {}
    cat_limites: dict[str, float] = {}
    cat_cores_lim: dict[str, str] = {}

    for g in gastos_mes:
        if g.categoria.limite_mensal is not None:
            nome_cat = g.categoria.nome
            cat_limites[nome_cat] = float(g.categoria.limite_mensal)
            cat_cores_lim[nome_cat] = g.categoria.cor
            if g.valor_pago is not None:
                cat_pagos[nome_cat] = cat_pagos.get(nome_cat, 0) + float(g.valor_pago)

    limites_categorias = []
    for nome_cat, limite in sorted(cat_limites.items()):
        pago = cat_pagos.get(nome_cat, 0.0)
        pct = (pago / limite * 100) if limite > 0 else 0.0
        if pct < 80:
            cor_barra = 'success'
        elif pct < 100:
            cor_barra = 'warning'
        else:
            cor_barra = 'danger'
        limites_categorias.append({
            'nome':      nome_cat,
            'cor':       cat_cores_lim[nome_cat],
            'pago':      pago,
            'limite':    limite,
            'pct':       int(pct) if pct == int(pct) else round(pct, 1),
            'pct_barra': min(pct, 100.0),
            'cor_barra': cor_barra,
        })

    # ── Chart 2: Evolução gastos últimos 6 meses ────────────────────────────
    gastos_6m_labels, gastos_6m_pago, gastos_6m_prev = [], [], []
    m, a = mes, ano
    meses_6 = []
    for _ in range(6):
        meses_6.insert(0, (m, a))
        m, a = _mes_anterior(m, a)
    for m, a in meses_6:
        gastos_6m_labels.append(_label(m, a))
        gastos_6m_pago.append(float(
            db.session.scalar(
                db.select(db.func.sum(Gasto.valor_pago))
                .where(Gasto.mes == m, Gasto.ano == a, Gasto.valor_pago.isnot(None))
            ) or 0
        ))
        gastos_6m_prev.append(float(
            db.session.scalar(
                db.select(db.func.sum(Gasto.valor_previsto))
                .where(Gasto.mes == m, Gasto.ano == a)
            ) or 0
        ))
    chart_gastos = json.dumps({
        'labels':   gastos_6m_labels,
        'pago':     gastos_6m_pago,
        'previsto': gastos_6m_prev,
    })

    # ── Chart 3: Patrimônio real + projeção ─────────────────────────────────
    hist_rows = db.session.execute(
        db.select(Investimento.ano, Investimento.mes, db.func.sum(Investimento.valor).label('total'))
        .group_by(Investimento.ano, Investimento.mes)
        .order_by(Investimento.ano.asc(), Investimento.mes.asc())
    ).all()

    hist_labels = [_label(r.mes, r.ano) for r in hist_rows]
    hist_data   = [float(r.total) for r in hist_rows]

    # Projeção a partir do último ponto real
    proj_labels, proj_data = [], []
    if hist_data and param_proj:
        saldo = hist_data[-1]
        r = float(param_proj.rendimento_mensal_pct) / 100
        a = float(param_proj.aporte_mensal)
        pm, pa = (hist_rows[-1].mes, hist_rows[-1].ano) if hist_rows else (mes, ano)
        for _ in range(12):
            pm, pa = _proximo_mes(pm, pa)
            saldo = saldo * (1 + r) + a
            proj_labels.append(_label(pm, pa))
            proj_data.append(round(saldo, 2))

    chart_patrimonio = json.dumps({
        'hist_labels': hist_labels,
        'hist_data':   hist_data,
        'proj_labels': proj_labels,
        'proj_data':   proj_data,
    })

    return render_template(
        'main/dashboard.html',
        # Cards
        mes=mes, ano=ano,
        nome_mes=MESES_ABREV[mes - 1],
        total_pago_mes=total_pago_mes,
        total_prev_mes=total_prev_mes,
        saldo_realizado_mes=saldo_realizado_mes,
        saldo_previsto_mes=saldo_previsto_mes,
        total_investido=total_investido,
        total_investido_previdencia=total_investido_previdencia,
        total_investido_outros=total_investido_outros,
        inv_base_mes=MESES_ABREV[inv_base_mes - 1],
        inv_base_ano=inv_base_ano,
        projecao_12m=projecao_12m,
        # Quick stats
        fixos_ativos=fixos_ativos,
        total_fixos=total_fixos,
        vencimentos_proximos=vencimentos_proximos,
        # Charts JSON
        chart_categorias=chart_categorias,
        chart_gastos=chart_gastos,
        chart_patrimonio=chart_patrimonio,
        tem_gastos=len(gastos_mes) > 0,
        tem_investimentos=len(hist_data) > 0,
        limites_categorias=limites_categorias,
    )
