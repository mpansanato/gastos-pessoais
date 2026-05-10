from decimal import Decimal
from app.extensions import db


class ParametroProjecao(db.Model):
    __tablename__ = 'parametros_projecao'

    id = db.Column(db.Integer, primary_key=True)
    rendimento_mensal_pct = db.Column(db.Numeric(6, 4), nullable=False, default=Decimal('1.0000'))
    aporte_mensal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    meses_projecao = db.Column(db.Integer, nullable=False, default=12)
