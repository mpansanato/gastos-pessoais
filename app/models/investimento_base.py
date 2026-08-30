from app.extensions import db


class InvestimentoBase(db.Model):
    """Template permanente de um ativo na carteira. Gera Investimento mensal via rolling."""
    __tablename__ = 'investimentos_base'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    instituicao_id = db.Column(db.Integer, db.ForeignKey('instituicoes.id'), nullable=False)
    risco = db.Column(db.String(10), nullable=False, default='baixo')
    emissor = db.Column(db.String(200), nullable=True)
    fundo = db.Column(db.String(200), nullable=True)
    vencimento = db.Column(db.Date, nullable=True)
    observacao = db.Column(db.String(300), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    # Baixa por vencimento: quando preenchido, o ativo foi resgatado/encerrado.
    encerrado_em = db.Column(db.Date, nullable=True)
    receita_baixa_id = db.Column(db.Integer, db.ForeignKey('receitas_extras.id'), nullable=True)

    saldos = db.relationship('Investimento', back_populates='base', lazy='dynamic',
                             foreign_keys='Investimento.investimento_base_id')
    instituicao = db.relationship('Instituicao', backref='investimentos_base')
    receita_baixa = db.relationship('ReceitaExtra', foreign_keys=[receita_baixa_id])

    def __repr__(self):
        return f'<InvestimentoBase {self.nome}>'
