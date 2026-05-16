from app.extensions import db


class ReceitaFixa(db.Model):
    """Lançamento mensal gerado por uma EntradaFixa."""
    __tablename__ = 'receitas_fixas'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    entrada_fixa_id = db.Column(db.Integer, db.ForeignKey('entradas_fixas.id'), nullable=True)
    observacao = db.Column(db.String(300), nullable=True)

    entrada_fixa = db.relationship('EntradaFixa', back_populates='receitas')

    def __repr__(self):
        return f'<ReceitaFixa {self.descricao} {self.mes}/{self.ano}>'
