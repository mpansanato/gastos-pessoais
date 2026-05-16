from app.extensions import db


class EntradaFixa(db.Model):
    """Template de entrada recorrente. Gera ReceitaFixa entries para os próximos 12 meses."""
    __tablename__ = 'entradas_fixas'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacao = db.Column(db.String(300), nullable=True)

    receitas = db.relationship('ReceitaFixa', back_populates='entrada_fixa', lazy='dynamic')

    def __repr__(self):
        return f'<EntradaFixa {self.descricao}>'
