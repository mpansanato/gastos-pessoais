from app.extensions import db


class Investimento(db.Model):
    __tablename__ = 'investimentos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    instituicao_id = db.Column(db.Integer, db.ForeignKey('instituicoes.id'), nullable=False)
    valor = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    vencimento = db.Column(db.Date, nullable=True)
    risco = db.Column(db.String(10), nullable=False, default='baixo')  # baixo | medio | alto
    emissor = db.Column(db.String(200), nullable=True)
    fundo = db.Column(db.String(200), nullable=True)
    observacao = db.Column(db.String(300), nullable=True)

    # Campos de rolling/confirmação (nullable = legado sem base)
    investimento_base_id = db.Column(
        db.Integer, db.ForeignKey('investimentos_base.id'), nullable=True
    )
    confirmado = db.Column(db.Boolean, nullable=False, default=False)
    rendimento_real = db.Column(db.Numeric(12, 2), nullable=True)
    rendimento_projetado = db.Column(db.Numeric(12, 2), nullable=True)
    retirada = db.Column(db.Numeric(12, 2), nullable=True)

    base = db.relationship(
        'InvestimentoBase', back_populates='saldos',
        foreign_keys=[investimento_base_id],
    )

    def __repr__(self) -> str:
        return f'<Investimento {self.nome}>'
