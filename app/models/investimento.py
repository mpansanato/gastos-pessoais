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
    emissor = db.Column(db.String(200), nullable=True)  # quem emitiu: Banco Master, Banco Pan…
    fundo = db.Column(db.String(200), nullable=True)    # nome do fundo (FII, multimercado…)
    observacao = db.Column(db.String(300), nullable=True)

    def __repr__(self) -> str:
        return f'<Investimento {self.nome}>'
