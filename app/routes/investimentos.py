from datetime import datetime, date
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from app.fields import BRDecimalField as DecimalField

from app.extensions import db
from app.models.instituicao import Instituicao
from app.models.investimento import Investimento
from app.models.investimento_base import InvestimentoBase
from app.models.retirada_investimento import RetiradaInvestimento
from app.models.receita_extra import ReceitaExtra
from app.models.parametro_projecao import ParametroProjecao

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

RISCO_CHOICES = [('baixo', 'Baixo'), ('medio', 'Médio'), ('alto', 'Alto')]
RISCO_ORDEM   = {'alto': 0, 'medio': 1, 'baixo': 2}
RISCO_LABEL   = {'alto': 'Alto', 'medio': 'Médio', 'baixo': 'Baixo'}
RISCO_COR     = {'alto': 'danger', 'medio': 'warning', 'baixo': 'success'}

TIPOS_FGC  = frozenset({'CDB', 'LCI', 'LCA', 'LC', 'LH', 'Poupança'})
FGC_LIMITE = 250_000.0


# ── Formulários ────────────────────────────────────────────────────────────────

class CarteiraForm(FlaskForm):
    """Formulário para criar/editar um InvestimentoBase."""
    nome           = StringField('Nome / Descrição', validators=[DataRequired(), Length(max=200)])
    tipo           = SelectField('Tipo', choices=[(t, t) for t in TIPOS])
    instituicao_id = SelectField('Corretora / Custodiante', coerce=int, validators=[DataRequired()])
    risco          = SelectField('Risco do Emissor', choices=RISCO_CHOICES, default='baixo')
    emissor        = StringField('Emissor', validators=[Optional(), Length(max=200)])
    fundo          = StringField('Fundo / Produto', validators=[Optional(), Length(max=200)])
    vencimento     = DateField('Vencimento', validators=[Optional()])
    observacao     = TextAreaField('Observação', validators=[Optional(), Length(max=300)])
    valor_inicial  = DecimalField('Saldo Atual (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    valor_atual    = DecimalField('Corrigir Saldo (R$)', validators=[Optional(), NumberRange(min=0)], places=2)
    submit         = SubmitField('Salvar')


class TaxaForm(FlaskForm):
    rendimento_mensal_pct = DecimalField(
        'Rendimento mensal estimado (%)',
        validators=[DataRequired(), NumberRange(min=0, max=100)],
        places=4,
    )
    submit = SubmitField('Salvar e Recalcular')


class ConfirmarForm(FlaskForm):
    saldo_final = DecimalField('Saldo Final (R$)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    submit      = SubmitField('Confirmar')


class RetiradaForm(FlaskForm):
    valor     = DecimalField('Valor da Retirada (R$)', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    descricao = StringField('Descrição', validators=[Optional(), Length(max=200)])
    submit    = SubmitField('Registrar Retirada')


class InstituicaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    cor  = SelectField('Cor', choices=CORES)
    submit = SubmitField('Criar Instituição')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _prox(mes: int, ano: int):
    return (mes % 12 + 1, ano + 1 if mes == 12 else ano)


def _anterior(mes: int, ano: int):
    return (12, ano - 1) if mes == 1 else (mes - 1, ano)


def _get_taxa() -> float:
    param = db.session.scalar(db.select(ParametroProjecao))
    return float(param.rendimento_mensal_pct) / 100 if param else 0.01


def _nav_mes(mes: int, ano: int):
    mes_ant = (mes - 2) % 12 + 1
    ano_ant = ano - 1 if mes == 1 else ano
    mes_prox = mes % 12 + 1
    ano_prox = ano + 1 if mes == 12 else ano
    return mes_ant, ano_ant, mes_prox, ano_prox


def _ultimo_saldo(base_id: int) -> Investimento | None:
    """Retorna a entrada mais recente (confirmada ou projetada) de um base."""
    return db.session.scalar(
        db.select(Investimento)
        .where(Investimento.investimento_base_id == base_id)
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
    )


def _ensure_12_meses(base: InvestimentoBase, taxa: float, hoje_mes: int, hoje_ano: int) -> int:
    """Garante 12 meses projetados à frente do mês atual para este ativo."""
    ultimo = _ultimo_saldo(base.id)
    if not ultimo:
        return 0

    # Limite: 12 meses à frente de hoje
    fim_mes, fim_ano = hoje_mes, hoje_ano
    for _ in range(12):
        fim_mes, fim_ano = _prox(fim_mes, fim_ano)

    ref_mes, ref_ano = ultimo.mes, ultimo.ano
    ref_valor = float(ultimo.valor)
    criados = 0

    while (ref_ano, ref_mes) < (fim_ano, fim_mes):
        prox_mes, prox_ano = _prox(ref_mes, ref_ano)
        valor_proj = round(ref_valor * (1 + taxa), 2)
        rend_proj  = round(ref_valor * taxa, 2)

        existente = db.session.scalar(
            db.select(Investimento).where(
                Investimento.investimento_base_id == base.id,
                Investimento.mes == prox_mes,
                Investimento.ano == prox_ano,
            )
        )

        if not existente:
            db.session.add(Investimento(
                nome=base.nome,
                tipo=base.tipo,
                instituicao_id=base.instituicao_id,
                valor=Decimal(str(valor_proj)),
                mes=prox_mes, ano=prox_ano,
                risco=base.risco,
                emissor=base.emissor,
                fundo=base.fundo,
                vencimento=base.vencimento,
                observacao=base.observacao,
                investimento_base_id=base.id,
                confirmado=False,
                rendimento_real=None,
                rendimento_projetado=Decimal(str(rend_proj)),
            ))
            ref_valor = valor_proj
            criados += 1
        else:
            ref_valor = float(existente.valor)

        ref_mes, ref_ano = prox_mes, prox_ano

    if criados:
        db.session.commit()
    return criados


def rolling_forward():
    """Garante 12 meses projetados para todos os ativos ativos."""
    hoje = datetime.today()
    taxa = _get_taxa()
    bases = db.session.scalars(db.select(InvestimentoBase).where(InvestimentoBase.ativo == True)).all()
    for base in bases:
        _ensure_12_meses(base, taxa, hoje.month, hoje.year)


def _reprojetar_futuros(base: InvestimentoBase, a_partir_mes: int, a_partir_ano: int,
                        taxa: float, hoje_mes: int, hoje_ano: int):
    """Após confirmar um mês, deleta projeções futuras e re-projeta."""
    futuros = db.session.scalars(
        db.select(Investimento).where(
            Investimento.investimento_base_id == base.id,
            Investimento.confirmado == False,
            db.or_(
                Investimento.ano > a_partir_ano,
                db.and_(Investimento.ano == a_partir_ano, Investimento.mes > a_partir_mes),
            ),
        )
    ).all()
    for f in futuros:
        db.session.delete(f)
    db.session.commit()
    _ensure_12_meses(base, taxa, hoje_mes, hoje_ano)


# ── Rota: Taxa de rendimento ───────────────────────────────────────────────────

@investimentos_bp.route('/taxa', methods=['POST'])
@login_required
def atualizar_taxa():
    hoje = datetime.today()
    form = TaxaForm()
    if form.validate_on_submit():
        param = db.session.scalar(db.select(ParametroProjecao))
        if not param:
            param = ParametroProjecao()
            db.session.add(param)
        param.rendimento_mensal_pct = form.rendimento_mensal_pct.data
        db.session.commit()

        # Recalcula todos os futuros projetados com a nova taxa
        nova_taxa = float(form.rendimento_mensal_pct.data) / 100
        bases = db.session.scalars(
            db.select(InvestimentoBase).where(InvestimentoBase.ativo == True)
        ).all()
        for base in bases:
            # Remove projeções futuras não confirmadas a partir do próximo mês
            prox_mes, prox_ano = _prox(hoje.month, hoje.year)
            db.session.execute(
                db.delete(Investimento).where(
                    Investimento.investimento_base_id == base.id,
                    Investimento.confirmado == False,
                    db.or_(
                        Investimento.ano > prox_ano,
                        db.and_(Investimento.ano == prox_ano, Investimento.mes >= prox_mes),
                    ),
                )
            )
        db.session.commit()
        # Re-projeta com nova taxa
        for base in bases:
            _ensure_12_meses(base, nova_taxa, hoje.month, hoje.year)

        flash(
            f'Taxa atualizada para {form.rendimento_mensal_pct.data}%/mês — '
            f'projeções de {len(bases)} ativo(s) recalculadas.',
            'success',
        )
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('investimentos.index'))


# ── Rotas: Carteira (InvestimentoBase) ────────────────────────────────────────

@investimentos_bp.route('/carteira')
@login_required
def carteira():
    hoje = datetime.today()
    rolling_forward()

    bases = db.session.scalars(
        db.select(InvestimentoBase).order_by(InvestimentoBase.ativo.desc(), InvestimentoBase.nome)
    ).all()
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()

    form = CarteiraForm()
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]

    param = db.session.scalar(db.select(ParametroProjecao))
    taxa_form = TaxaForm(
        rendimento_mensal_pct=param.rendimento_mensal_pct if param else None
    )

    # Último saldo confirmado de cada ativo
    dados = []
    for base in bases:
        ultimo = db.session.scalar(
            db.select(Investimento)
            .where(Investimento.investimento_base_id == base.id,
                   Investimento.confirmado == True)
            .order_by(Investimento.ano.desc(), Investimento.mes.desc())
        )
        dados.append({'base': base, 'ultimo': ultimo})

    # Agrupa por instituição, ordenando ativos por valor desc dentro de cada grupo
    grupos: dict = {}
    for d in dados:
        inst = d['base'].instituicao
        if inst.id not in grupos:
            grupos[inst.id] = {'instituicao': inst, 'ativos': []}
        grupos[inst.id]['ativos'].append(d)
    for g in grupos.values():
        g['ativos'].sort(key=lambda d: float(d['ultimo'].valor) if d['ultimo'] else 0, reverse=True)
        g['total'] = sum(float(d['ultimo'].valor) if d['ultimo'] else 0 for d in g['ativos'])
    grupos_lista = sorted(grupos.values(), key=lambda g: g['total'], reverse=True)

    return render_template(
        'investimentos/carteira.html',
        grupos=grupos_lista, form=form, taxa_form=taxa_form,
        param=param, instituicoes=instituicoes,
        hoje_mes=hoje.month, hoje_ano=hoje.year,
        meses=MESES,
    )


@investimentos_bp.route('/carteira/nova', methods=['POST'])
@login_required
def nova_carteira():
    hoje = datetime.today()
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = CarteiraForm()
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]

    if form.validate_on_submit():
        base = InvestimentoBase(
            nome=form.nome.data,
            tipo=form.tipo.data,
            instituicao_id=form.instituicao_id.data,
            risco=form.risco.data,
            emissor=(form.emissor.data or '').strip() or None,
            fundo=(form.fundo.data or '').strip() or None,
            vencimento=form.vencimento.data,
            observacao=form.observacao.data or None,
            ativo=True,
        )
        db.session.add(base)
        db.session.flush()

        # Cria o saldo inicial como confirmado no mês atual
        db.session.add(Investimento(
            nome=base.nome, tipo=base.tipo,
            instituicao_id=base.instituicao_id,
            valor=form.valor_inicial.data,
            mes=hoje.month, ano=hoje.year,
            risco=base.risco, emissor=base.emissor,
            fundo=base.fundo, vencimento=base.vencimento,
            observacao=base.observacao,
            investimento_base_id=base.id,
            confirmado=True,
            rendimento_real=None,
            rendimento_projetado=None,
        ))
        db.session.commit()

        taxa = _get_taxa()
        n = _ensure_12_meses(base, taxa, hoje.month, hoje.year)
        flash(f'"{base.nome}" adicionado à carteira — {n} meses projetados.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('investimentos.carteira'))


@investimentos_bp.route('/carteira/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_carteira(id: int):
    hoje = datetime.today()
    base = db.get_or_404(InvestimentoBase, id)
    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()
    form = CarteiraForm(obj=base)
    form.instituicao_id.choices = [(i.id, i.nome) for i in instituicoes]
    del form.valor_inicial  # gerenciado pela correção abaixo

    # Saldo confirmado mais recente para exibir no template
    ultimo = db.session.scalar(
        db.select(Investimento)
        .where(Investimento.investimento_base_id == base.id,
               Investimento.confirmado == True)
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
    )

    if form.validate_on_submit():
        base.nome           = form.nome.data
        base.tipo           = form.tipo.data
        base.instituicao_id = form.instituicao_id.data
        base.risco          = form.risco.data
        base.emissor        = (form.emissor.data or '').strip() or None
        base.fundo          = (form.fundo.data or '').strip() or None
        base.vencimento     = form.vencimento.data
        base.observacao     = form.observacao.data or None

        # Propaga metadados para todos os lançamentos mensais vinculados
        db.session.execute(
            db.update(Investimento)
            .where(Investimento.investimento_base_id == base.id)
            .values(
                nome=base.nome,
                tipo=base.tipo,
                instituicao_id=base.instituicao_id,
                risco=base.risco,
                emissor=base.emissor,
                fundo=base.fundo,
                vencimento=base.vencimento,
                observacao=base.observacao,
            )
        )

        # Corrige saldo se preenchido
        novo_saldo = form.valor_atual.data
        if novo_saldo is not None and ultimo:
            ultimo.valor = novo_saldo
            ultimo.rendimento_real = None
            db.session.commit()
            taxa = _get_taxa()
            _reprojetar_futuros(base, ultimo.mes, ultimo.ano, taxa, hoje.month, hoje.year)
            flash(
                f'"{base.nome}" atualizado — saldo corrigido para {_brl(float(novo_saldo))} '
                f'e projeções recalculadas.',
                'success',
            )
        else:
            db.session.commit()
            flash(f'"{base.nome}" atualizado — metadados propagados para todos os meses.', 'success')

        return redirect(url_for('investimentos.carteira'))

    return render_template('investimentos/carteira_form.html', form=form, base=base, ultimo=ultimo)


@investimentos_bp.route('/carteira/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_carteira(id: int):
    hoje = datetime.today()
    base = db.get_or_404(InvestimentoBase, id)
    base.ativo = not base.ativo
    db.session.commit()

    if base.ativo:
        taxa = _get_taxa()
        n = _ensure_12_meses(base, taxa, hoje.month, hoje.year)
        flash(f'"{base.nome}" reativado — {n} meses projetados.', 'success')
    else:
        prox_mes, prox_ano = _prox(hoje.month, hoje.year)
        futuros = db.session.scalars(
            db.select(Investimento).where(
                Investimento.investimento_base_id == base.id,
                Investimento.confirmado == False,
                db.or_(
                    Investimento.ano > prox_ano,
                    db.and_(Investimento.ano == prox_ano, Investimento.mes >= prox_mes),
                ),
            )
        ).all()
        for f in futuros:
            db.session.delete(f)
        db.session.commit()
        flash(f'"{base.nome}" pausado — {len(futuros)} projeções removidas.', 'warning')
    return redirect(url_for('investimentos.carteira'))


@investimentos_bp.route('/carteira/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_carteira(id: int):
    base = db.get_or_404(InvestimentoBase, id)
    nome = base.nome
    # Remove projeções futuras não confirmadas
    db.session.execute(
        db.delete(Investimento).where(
            Investimento.investimento_base_id == base.id,
            Investimento.confirmado == False,
        )
    )
    # Desvincula histórico confirmado (preserva)
    db.session.execute(
        db.update(Investimento)
        .where(Investimento.investimento_base_id == base.id)
        .values(investimento_base_id=None)
    )
    db.session.delete(base)
    db.session.commit()
    flash(f'"{nome}" removido da carteira.', 'success')
    return redirect(url_for('investimentos.carteira'))


# ── Rotas: Retiradas ──────────────────────────────────────────────────────────

@investimentos_bp.route('/retirada/nova/<int:base_id>/<int:ano>/<int:mes>', methods=['POST'])
@login_required
def nova_retirada(base_id: int, ano: int, mes: int):
    hoje = datetime.today()
    base = db.get_or_404(InvestimentoBase, base_id)
    form = RetiradaForm()
    if form.validate_on_submit():
        valor_retirada = form.valor.data

        # Cria o Saque de Investimento em Gastos Mensais
        receita = ReceitaExtra(
            descricao=form.descricao.data or f'Retirada: {base.nome}',
            tipo='Saque de Investimento',
            valor=valor_retirada,
            mes=mes, ano=ano,
            instituicao_id=base.instituicao_id,
            observacao=None,
        )
        db.session.add(receita)
        db.session.flush()  # garante receita.id antes de vincular

        # Registra a retirada vinculada à receita criada
        db.session.add(RetiradaInvestimento(
            investimento_base_id=base_id,
            valor=valor_retirada,
            mes=mes, ano=ano,
            data=datetime.today().date(),
            descricao=form.descricao.data or f'Retirada de {base.nome}',
            receita_extra_id=receita.id,
        ))

        # Debita do saldo do mês atual
        inv_mes = db.session.scalar(
            db.select(Investimento).where(
                Investimento.investimento_base_id == base_id,
                Investimento.mes == mes,
                Investimento.ano == ano,
            )
        )
        if inv_mes:
            inv_mes.valor = inv_mes.valor - valor_retirada

        db.session.commit()

        # Reprojeta meses futuros a partir do novo saldo
        taxa = _get_taxa()
        _reprojetar_futuros(base, mes, ano, taxa, hoje.month, hoje.year)

        flash(
            f'Retirada de {_brl(float(valor_retirada))} registrada — '
            f'saldo atualizado e projeções recalculadas. '
            f'Lançamento criado automaticamente em Gastos Mensais.',
            'success',
        )
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')
    return redirect(url_for('investimentos.por_mes', ano=ano, mes=mes))


@investimentos_bp.route('/retirada/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_retirada(id: int):
    hoje = datetime.today()
    retirada = db.get_or_404(RetiradaInvestimento, id)
    ano, mes, base_id = retirada.ano, retirada.mes, retirada.investimento_base_id
    valor = retirada.valor

    # Estorna o valor no saldo do mês
    inv_mes = db.session.scalar(
        db.select(Investimento).where(
            Investimento.investimento_base_id == base_id,
            Investimento.mes == mes,
            Investimento.ano == ano,
        )
    )
    if inv_mes:
        inv_mes.valor = inv_mes.valor + valor

    # Remove a receita vinculada em Gastos Mensais
    if retirada.receita_extra_id:
        receita = db.session.get(ReceitaExtra, retirada.receita_extra_id)
        if receita:
            db.session.delete(receita)

    db.session.delete(retirada)
    db.session.commit()

    # Reprojeta futuros com saldo restaurado
    base = db.session.get(InvestimentoBase, base_id)
    taxa = _get_taxa()
    if base:
        _reprojetar_futuros(base, mes, ano, taxa, hoje.month, hoje.year)

    flash('Retirada removida — saldo estornado, lançamento em Gastos Mensais excluído e projeções recalculadas.', 'warning')
    return redirect(url_for('investimentos.por_mes', ano=ano, mes=mes))


# ── Rota: Confirmação de rendimento ───────────────────────────────────────────

@investimentos_bp.route('/confirmar/<int:inv_id>', methods=['POST'])
@login_required
def confirmar(inv_id: int):
    hoje = datetime.today()
    inv = db.get_or_404(Investimento, inv_id)
    form = ConfirmarForm()

    if form.validate_on_submit() and inv.investimento_base_id:
        saldo_final = form.saldo_final.data

        # Saldo anterior: valor atual se já confirmado, senão mês anterior confirmado
        if inv.confirmado:
            saldo_ant = inv.valor
        else:
            prev_mes, prev_ano = _anterior(inv.mes, inv.ano)
            anterior = db.session.scalar(
                db.select(Investimento).where(
                    Investimento.investimento_base_id == inv.investimento_base_id,
                    Investimento.mes == prev_mes,
                    Investimento.ano == prev_ano,
                    Investimento.confirmado == True,
                )
            )
            saldo_ant = anterior.valor if anterior else Decimal('0')

        # Total de retiradas já registradas neste mês para este ativo
        total_retiradas = db.session.scalar(
            db.select(db.func.sum(RetiradaInvestimento.valor)).where(
                RetiradaInvestimento.investimento_base_id == inv.investimento_base_id,
                RetiradaInvestimento.mes == inv.mes,
                RetiradaInvestimento.ano == inv.ano,
            )
        ) or Decimal('0')

        # rendimento = saldo_final − saldo_anterior + retiradas
        rendimento_real = saldo_final - saldo_ant + total_retiradas

        inv.valor          = saldo_final
        inv.rendimento_real = rendimento_real
        inv.retirada        = None
        inv.confirmado      = True
        db.session.commit()

        # Re-projeta futuros a partir deste mês
        base = db.session.get(InvestimentoBase, inv.investimento_base_id)
        taxa = _get_taxa()
        _reprojetar_futuros(base, inv.mes, inv.ano, taxa, hoje.month, hoje.year)

        flash(f'"{inv.nome}" confirmado para {MESES[inv.mes-1]}/{inv.ano}.', 'success')
    else:
        for erros in form.errors.values():
            for e in erros:
                flash(e, 'danger')

    return redirect(url_for('investimentos.por_mes', ano=inv.ano, mes=inv.mes))


# ── Rotas: Visão mensal ────────────────────────────────────────────────────────

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

    rolling_forward()

    hoje = date.today()
    mes_ant, ano_ant, mes_prox, ano_prox = _nav_mes(mes, ano)

    instituicoes = db.session.scalars(db.select(Instituicao).order_by(Instituicao.nome)).all()

    todos = db.session.scalars(
        db.select(Investimento)
        .where(Investimento.mes == mes, Investimento.ano == ano)
        .order_by(Investimento.instituicao_id, Investimento.valor.desc())
    ).all()

    total_geral = sum(float(i.valor) for i in todos)

    # Separa Previdência Privada dos demais investimentos
    prev_items   = [i for i in todos if i.tipo == 'Previdência Privada']
    outros_items = [i for i in todos if i.tipo != 'Previdência Privada']

    def _agrupar_por_inst(itens: list, total_bloco: float) -> dict:
        """Agrupa lançamentos por instituição, com subtotal e % dentro do bloco."""
        grupos = {}
        for inst in instituicoes:
            do_inst = [i for i in itens if i.instituicao_id == inst.id]
            if do_inst:
                subtotal = sum(float(i.valor) for i in do_inst)
                grupos[inst] = {
                    'lancamentos': do_inst,
                    'subtotal': subtotal,
                    'percentual': (subtotal / total_bloco * 100) if total_bloco else 0,
                }
        return grupos

    # Totais projetado vs confirmado
    confirmados = [i for i in todos if i.confirmado]
    projetados  = [i for i in todos if not i.confirmado and i.investimento_base_id]

    total_confirmado = sum(float(i.valor) for i in confirmados)
    total_projetado  = sum(float(i.valor) for i in projetados)

    total_geral_previdencia = sum(float(i.valor) for i in prev_items)
    total_geral_outros      = sum(float(i.valor) for i in outros_items)
    total_confirmado_previdencia = sum(float(i.valor) for i in confirmados if i.tipo == 'Previdência Privada')
    total_confirmado_outros      = total_confirmado - total_confirmado_previdencia

    por_inst_prev   = _agrupar_por_inst(prev_items, total_geral_previdencia)
    por_inst_outros = _agrupar_por_inst(outros_items, total_geral_outros)

    # Nº de instituições distintas com posições (card de resumo)
    qtd_inst = len({i.instituicao_id for i in todos})

    rend_real_total = sum(float(i.rendimento_real) for i in confirmados if i.rendimento_real)
    rend_proj_total = sum(float(i.rendimento_projetado) for i in todos if i.rendimento_projetado)

    # Rendimentos por bloco (rodapés)
    rend_real_prev   = sum(float(i.rendimento_real) for i in prev_items if i.confirmado and i.rendimento_real)
    rend_proj_prev   = sum(float(i.rendimento_projetado) for i in prev_items if i.rendimento_projetado)
    rend_real_outros = rend_real_total - rend_real_prev
    rend_proj_outros = rend_proj_total - rend_proj_prev

    # Lançamentos vinculados a uma base (para gerar os modais)
    todos_base = [i for i in todos if i.investimento_base_id]

    # Retiradas do mês agrupadas por base_id
    retiradas_mes = db.session.scalars(
        db.select(RetiradaInvestimento).where(
            RetiradaInvestimento.mes == mes, RetiradaInvestimento.ano == ano
        ).order_by(RetiradaInvestimento.data, RetiradaInvestimento.id)
    ).all()
    retiradas_por_base: dict[int, list] = {}
    for r in retiradas_mes:
        retiradas_por_base.setdefault(r.investimento_base_id, []).append(r)

    # Saldo anterior por ativo (para mostrar no modal de confirmação)
    saldo_anterior_por_inv: dict[int, Decimal] = {}
    for inv in todos:
        if inv.investimento_base_id:
            if inv.confirmado:
                saldo_anterior_por_inv[inv.id] = inv.valor
            else:
                pm, pa = _anterior(inv.mes, inv.ano)
                ant = db.session.scalar(
                    db.select(Investimento).where(
                        Investimento.investimento_base_id == inv.investimento_base_id,
                        Investimento.mes == pm, Investimento.ano == pa,
                        Investimento.confirmado == True,
                    )
                )
                saldo_anterior_por_inv[inv.id] = ant.valor if ant else Decimal('0')

    confirm_form  = ConfirmarForm()
    retirada_form = RetiradaForm()
    eh_passado    = (ano, mes) <= (hoje.year, hoje.month)
    eh_atual      = (ano == hoje.year and mes == hoje.month)

    param = db.session.scalar(db.select(ParametroProjecao))
    taxa_form = TaxaForm(
        rendimento_mensal_pct=param.rendimento_mensal_pct if param else None
    )

    return render_template(
        'investimentos/index.html',
        mes=mes, ano=ano, nome_mes=MESES[mes - 1],
        instituicoes=instituicoes,
        por_inst_prev=por_inst_prev,
        por_inst_outros=por_inst_outros,
        total_geral=total_geral,
        total_confirmado=total_confirmado,
        total_projetado=total_projetado,
        total_geral_previdencia=total_geral_previdencia,
        total_geral_outros=total_geral_outros,
        total_confirmado_previdencia=total_confirmado_previdencia,
        total_confirmado_outros=total_confirmado_outros,
        rend_real_total=rend_real_total,
        rend_proj_total=rend_proj_total,
        rend_real_prev=rend_real_prev,
        rend_proj_prev=rend_proj_prev,
        rend_real_outros=rend_real_outros,
        rend_proj_outros=rend_proj_outros,
        qtd=len(todos),
        qtd_inst=qtd_inst,
        todos_base=todos_base,
        retiradas_por_base=retiradas_por_base,
        saldo_anterior_por_inv=saldo_anterior_por_inv,
        confirm_form=confirm_form,
        retirada_form=retirada_form,
        taxa_form=taxa_form,
        param=param,
        eh_passado=eh_passado,
        eh_atual=eh_atual,
        mes_ant=mes_ant, ano_ant=ano_ant,
        mes_prox=mes_prox, ano_prox=ano_prox,
    )


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
    qtd = db.session.scalar(
        db.select(db.func.count()).select_from(Investimento).where(Investimento.instituicao_id == inst.id)
    )
    if qtd > 0:
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
        .where(Investimento.confirmado == True)
        .order_by(Investimento.ano.desc(), Investimento.mes.desc())
        .limit(1)
    ).first()

    if not result:
        # fallback: qualquer mês
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

    total_coberto = total_exposto = 0.0
    for e in emissores.values():
        e['pct']     = e['total'] / total * 100 if total else 0
        e['coberto'] = min(e['fgc_elegivel'], FGC_LIMITE)
        e['exposto'] = max(0.0, e['fgc_elegivel'] - FGC_LIMITE)
        total_coberto += e['coberto']
        total_exposto += e['exposto']
        e['lancamentos'].sort(key=lambda i: float(i.valor), reverse=True)
    emissores = dict(sorted(emissores.items(), key=lambda x: x[1]['total'], reverse=True))

    alertas = []
    for nome_emissor, e in emissores.items():
        if e['exposto'] > 0 and e['risco_max'] == 'alto':
            alertas.append({'nivel': 'danger', 'icone': 'bi-exclamation-octagon-fill',
                'msg': (f'<strong>{nome_emissor}</strong>: '
                        f'<strong>{_brl(e["exposto"])}</strong> acima do limite do FGC '
                        f'e emissor com risco <strong>ALTO</strong>.')})
        elif e['exposto'] > 0:
            alertas.append({'nivel': 'warning', 'icone': 'bi-exclamation-triangle-fill',
                'msg': (f'<strong>{nome_emissor}</strong>: '
                        f'<strong>{_brl(e["exposto"])}</strong> acima do limite de R$ 250k do FGC.')})
        elif e['risco_max'] == 'alto':
            alertas.append({'nivel': 'warning', 'icone': 'bi-exclamation-triangle-fill',
                'msg': f'<strong>{nome_emissor}</strong>: emissor com risco <strong>ALTO</strong>.'})

    if sem_emissor:
        alertas.append({'nivel': 'info', 'icone': 'bi-info-circle-fill',
            'msg': (f'<strong>{len(sem_emissor)} investimento(s)</strong> sem emissor preenchido '
                    f'— não entram na análise FGC.')})

    return render_template(
        'investimentos/risco.html',
        sem_dados=False, alertas=alertas,
        por_risco=por_risco, emissores=emissores,
        sem_emissor=sem_emissor, total=total,
        total_coberto=total_coberto, total_exposto=total_exposto,
        fgc_limite=FGC_LIMITE,
        base_mes=base_mes, base_ano=base_ano,
        nome_mes=MESES[base_mes - 1],
    )


def _brl(v: float) -> str:
    sign = '-' if v < 0 else ''
    fmt = '{:,.2f}'.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'{sign}R$ {fmt}'
