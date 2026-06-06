import json
from collections import defaultdict
from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.extensions import db
from app.models.categoria import Categoria
from app.models.gasto import Gasto
from app.models.investimento import Investimento
from app.models.receita_extra import ReceitaExtra
from app.models.receita_fixa import ReceitaFixa

relatorio_bp = Blueprint('relatorio', __name__, url_prefix='/relatorio')

MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

MESES_NOMES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
               'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def _secao_categorias(ano: int) -> dict:
    rows = db.session.execute(
        db.select(Categoria.nome, Categoria.cor,
                  db.func.sum(Gasto.valor_pago).label('total'))
        .join(Categoria, Gasto.categoria_id == Categoria.id)
        .where(Gasto.ano == ano, Gasto.valor_pago.isnot(None))
        .group_by(Categoria.id)
        .order_by(db.desc('total'))
    ).all()
    if not rows:
        return {'chart_donut': json.dumps({'labels': [], 'data': [], 'cores': []}),
                'chart_bar': json.dumps({'labels': [], 'data': [], 'cores': []})}
    top8 = rows[:8]
    outros_total = sum(float(r.total) for r in rows[8:])
    labels = [r.nome for r in top8] + (['Outros'] if outros_total > 0 else [])
    data = [float(r.total) for r in top8] + ([outros_total] if outros_total > 0 else [])
    cores = [r.cor for r in top8] + (['#adb5bd'] if outros_total > 0 else [])
    return {
        'chart_donut': json.dumps({'labels': labels, 'data': data, 'cores': cores}),
        'chart_bar': json.dumps({'labels': labels, 'data': data, 'cores': cores}),
    }


def _secao_extras(ano: int) -> dict:
    receitas = db.session.scalars(
        db.select(ReceitaExtra)
        .where(ReceitaExtra.ano == ano)
        .order_by(ReceitaExtra.mes, ReceitaExtra.id)
    ).all()
    total = sum(float(r.valor) for r in receitas)
    return {'receitas': receitas, 'total': total}


def _secao_parcelamentos(hoje_ref: int) -> list:
    subq = (
        db.select(
            Gasto.parcela_grupo_id,
            db.func.max(Gasto.ano * 100 + Gasto.mes).label('fim_ref'),
        )
        .where(Gasto.parcela_grupo_id.isnot(None))
        .group_by(Gasto.parcela_grupo_id)
        .subquery()
    )
    grupos = db.session.execute(
        db.select(subq.c.parcela_grupo_id).where(subq.c.fim_ref >= hoje_ref)
    ).scalars().all()

    resultado = []
    for grupo_id in grupos:
        parcelas = db.session.scalars(
            db.select(Gasto)
            .where(Gasto.parcela_grupo_id == grupo_id)
            .order_by(Gasto.ano, Gasto.mes)
        ).all()
        if not parcelas:
            continue
        parcela_atual = next(
            (p for p in parcelas if p.ano * 100 + p.mes >= hoje_ref), parcelas[-1]
        )
        ultima = parcelas[-1]
        resultado.append({
            'descricao': parcelas[0].descricao,
            'parcela_num': parcela_atual.parcela_num,
            'parcela_total': parcelas[0].parcela_total,
            'valor_mes': float(parcelas[0].valor_previsto),
            'data_quitacao': f'{MESES_ABREV[ultima.mes - 1]}/{ultima.ano}',
            'categoria': parcela_atual.categoria.nome,
            'ano_quit': ultima.ano,
            'mes_quit': ultima.mes,
        })
    resultado.sort(key=lambda p: (p['ano_quit'], p['mes_quit']))
    return resultado


def _secao_investimentos(ano: int) -> dict:
    inv_ultimo = db.session.execute(
        db.select(Investimento.ano, Investimento.mes)
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
        .limit(1)
    ).first()
    if not inv_ultimo:
        vazio = json.dumps({'labels': [], 'data': [], 'cores': []})
        return {'inv_rows': [], 'patrimonio_atual': 0, 'rend_real_ano': 0,
                'chart_risco': vazio, 'chart_tipo': vazio}

    inv_rows = db.session.scalars(
        db.select(Investimento)
        .where(Investimento.mes == inv_ultimo.mes, Investimento.ano == inv_ultimo.ano)
        .order_by(Investimento.valor.desc())
    ).all()
    patrimonio = sum(float(r.valor) for r in inv_rows)

    rend_real = float(
        db.session.scalar(
            db.select(db.func.sum(Investimento.rendimento_real))
            .where(Investimento.ano == ano, Investimento.rendimento_real.isnot(None))
        ) or 0
    )

    risco_totais: dict[str, float] = defaultdict(float)
    tipo_totais: dict[str, float] = defaultdict(float)
    for r in inv_rows:
        if r.risco:
            risco_totais[r.risco] += float(r.valor)
        if r.tipo:
            tipo_totais[r.tipo] += float(r.valor)

    CORES_RISCO = {'baixo': '#198754', 'medio': '#ffc107', 'médio': '#ffc107', 'alto': '#dc3545'}
    CORES_TIPO = ['#0d6efd', '#6f42c1', '#0dcaf0', '#fd7e14', '#20c997', '#6c757d', '#ffc107']

    chart_risco = json.dumps({
        'labels': list(risco_totais.keys()),
        'data': list(risco_totais.values()),
        'cores': [CORES_RISCO.get(k.lower(), '#adb5bd') for k in risco_totais.keys()],
    })
    tipos = list(tipo_totais.keys())
    chart_tipo = json.dumps({
        'labels': tipos,
        'data': list(tipo_totais.values()),
        'cores': CORES_TIPO[:len(tipos)],
    })
    return {'inv_rows': inv_rows, 'patrimonio_atual': patrimonio, 'rend_real_ano': rend_real,
            'chart_risco': chart_risco, 'chart_tipo': chart_tipo}


def _secao_limites(ano: int) -> list:
    cats = db.session.scalars(
        db.select(Categoria).where(Categoria.limite_mensal.isnot(None))
    ).all()
    resultado = []
    for cat in cats:
        pag_rows = db.session.execute(
            db.select(Gasto.mes, db.func.sum(Gasto.valor_pago).label('pago'))
            .where(Gasto.categoria_id == cat.id, Gasto.ano == ano,
                   Gasto.valor_pago.isnot(None))
            .group_by(Gasto.mes)
        ).all()
        if not pag_rows:
            continue
        total_cat = sum(float(r.pago) for r in pag_rows)
        media = total_cat / len(pag_rows)
        excedidos = sum(1 for r in pag_rows if float(r.pago) > float(cat.limite_mensal))
        pct = media / float(cat.limite_mensal) * 100
        resultado.append({
            'nome': cat.nome, 'cor': cat.cor,
            'limite': float(cat.limite_mensal),
            'media_paga': media,
            'meses_excedidos': excedidos,
            'pct_media': round(pct, 1),
            'pct_barra': min(pct, 100.0),
            'cor_barra': 'danger' if pct >= 100 else 'warning' if pct >= 80 else 'success',
        })
    resultado.sort(key=lambda x: -x['pct_media'])
    return resultado


@relatorio_bp.route('/')
@login_required
def index():
    hoje = date.today()
    hoje_ref = hoje.year * 100 + hoje.month

    # ── Anos disponíveis ────────────────────────────────────────────────
    anos_raw = set()
    for col in [Gasto.ano, ReceitaExtra.ano, Investimento.ano, ReceitaFixa.ano]:
        rows = db.session.execute(db.select(col).distinct()).scalars().all()
        anos_raw.update(rows)
    anos_raw.add(hoje.year)
    anos_disponiveis = sorted(anos_raw, reverse=True)

    try:
        ano = int(request.args.get('ano', hoje.year))
    except (ValueError, TypeError):
        ano = hoje.year
    if ano not in anos_raw:
        ano = hoje.year

    # ── Dados por mês (Seções B e D) ────────────────────────────────────
    meses_data = []
    for m in range(1, 13):
        extras = float(
            db.session.scalar(
                db.select(db.func.sum(ReceitaExtra.valor))
                .where(ReceitaExtra.mes == m, ReceitaExtra.ano == ano)
            ) or 0
        )
        previsto = float(
            db.session.scalar(
                db.select(db.func.sum(Gasto.valor_previsto))
                .where(Gasto.mes == m, Gasto.ano == ano)
            ) or 0
        )
        pago = float(
            db.session.scalar(
                db.select(db.func.sum(Gasto.valor_pago))
                .where(Gasto.mes == m, Gasto.ano == ano, Gasto.valor_pago.isnot(None))
            ) or 0
        )
        eh_futuro = (ano * 100 + m) > hoje_ref

        # Entradas fixas do mês
        fixas_previsto_val = db.session.scalar(
            db.select(db.func.sum(ReceitaFixa.valor))
            .where(ReceitaFixa.mes == m, ReceitaFixa.ano == ano)
        ) or 0
        fixas_previsto = float(fixas_previsto_val)

        fixas_realizado_val = db.session.scalar(
            db.select(db.func.sum(ReceitaFixa.valor_realizado))
            .where(ReceitaFixa.mes == m, ReceitaFixa.ano == ano,
                   ReceitaFixa.valor_realizado.isnot(None))
        )
        fixas_realizado = float(fixas_realizado_val) if fixas_realizado_val is not None else None

        receita_total     = extras + fixas_previsto
        receita_realizada = (extras + fixas_realizado) if fixas_realizado is not None else None

        if eh_futuro:
            saldo = None
        elif receita_realizada is not None:
            saldo = receita_realizada - pago
        else:
            saldo = None  # sem valor_realizado: não exibir saldo

        meses_data.append({
            'mes': m, 'nome': MESES_NOMES[m - 1], 'abrev': MESES_ABREV[m - 1],
            'extras': extras, 'receita_total': receita_total,
            'previsto': previsto, 'pago': pago, 'saldo': saldo, 'eh_futuro': eh_futuro,
            'fixas_previsto':    fixas_previsto,
            'fixas_realizado':   fixas_realizado,
            'receita_realizada': receita_realizada,
        })

    # ── Totais anuais (Seção A) ──────────────────────────────────────────
    # Total recebido: usa receita_realizada quando disponível, senão receita_total
    total_recebido = sum(
        m['receita_realizada'] if m['receita_realizada'] is not None else m['receita_total']
        for m in meses_data if not m['eh_futuro']
    )
    total_gasto = sum(m['pago'] for m in meses_data if not m['eh_futuro'])
    saldo_anual = total_recebido - total_gasto
    taxa_poupanca = round(saldo_anual / total_recebido * 100, 1) if total_recebido > 0 else None

    # ── Chart: Fluxo Mensal (Seção B) ───────────────────────────────────
    chart_fluxo = json.dumps({
        'labels': MESES_ABREV,
        'receita': [m['receita_total'] for m in meses_data],
        'gasto_pago': [m['pago'] if not m['eh_futuro'] else None for m in meses_data],
        'saldo': [m['saldo'] for m in meses_data],
    })

    # ── Seções C/E/F/G/H ───────────────────────────────────────────────
    dados_cat = _secao_categorias(ano)
    dados_extras = _secao_extras(ano)
    dados_parc = _secao_parcelamentos(hoje_ref)
    dados_inv = _secao_investimentos(ano)
    dados_lim = _secao_limites(ano)

    return render_template(
        'relatorio/index.html',
        ano=ano,
        anos_disponiveis=anos_disponiveis,
        meses_data=meses_data,
        total_recebido=total_recebido,
        total_gasto=total_gasto,
        saldo_anual=saldo_anual,
        taxa_poupanca=taxa_poupanca,
        chart_fluxo=chart_fluxo,
        chart_cat_donut=dados_cat['chart_donut'],
        chart_cat_bar=dados_cat['chart_bar'],
        receitas_extras_ano=dados_extras['receitas'],
        total_extras_ano=dados_extras['total'],
        parcelamentos=dados_parc,
        inv_rows=dados_inv['inv_rows'],
        patrimonio_atual=dados_inv['patrimonio_atual'],
        rend_real_ano=dados_inv['rend_real_ano'],
        chart_inv_risco=dados_inv['chart_risco'],
        chart_inv_tipo=dados_inv['chart_tipo'],
        limites_relatorio=dados_lim,
    )
