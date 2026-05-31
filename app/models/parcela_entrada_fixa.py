from app.extensions import db


class ParcelaEntradaFixa(db.Model):
    __tablename__ = 'parcelas_entrada_fixa'

    id              = db.Column(db.Integer, primary_key=True)
    entrada_fixa_id = db.Column(db.Integer, db.ForeignKey('entradas_fixas.id'), nullable=False)
    valor           = db.Column(db.Numeric(12, 2), nullable=False)
    dia_recebimento = db.Column(db.Integer, nullable=True)
    ordem           = db.Column(db.Integer, nullable=False, default=1)

    entrada_fixa = db.relationship('EntradaFixa', back_populates='parcelas')

    def __repr__(self):
        return f'<ParcelaEntradaFixa ordem={self.ordem} valor={self.valor}>'
