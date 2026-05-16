from datetime import date as date_type
from app.extensions import db


class RetiradaInvestimento(db.Model):
    """Evento de retirada parcial de um ativo durante um mês."""
    __tablename__ = 'retiradas_investimentos'

    id = db.Column(db.Integer, primary_key=True)
    investimento_base_id = db.Column(db.Integer, db.ForeignKey('investimentos_base.id'), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, nullable=True)
    descricao = db.Column(db.String(200), nullable=True)
    receita_extra_id = db.Column(db.Integer, db.ForeignKey('receitas_extras.id'), nullable=True)

    base = db.relationship('InvestimentoBase', backref='retiradas')
    receita_extra = db.relationship('ReceitaExtra', foreign_keys=[receita_extra_id])

    def __repr__(self):
        return f'<RetiradaInvestimento {self.base.nome} {self.mes}/{self.ano} {self.valor}>'
