from app.extensions import db


class SaldoConta(db.Model):
    __tablename__ = 'saldo_conta'

    id             = db.Column(db.Integer, primary_key=True)
    mes            = db.Column(db.Integer, nullable=False)
    ano            = db.Column(db.Integer, nullable=False)
    saldo_inicial  = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (db.UniqueConstraint('mes', 'ano', name='uq_saldo_conta_mes_ano'),)
