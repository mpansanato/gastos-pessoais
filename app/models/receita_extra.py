from app.extensions import db


class ReceitaExtra(db.Model):
    __tablename__ = 'receitas_extras'

    TIPOS = [
        'Bônus', 'Restituição IRPF', 'Outorga', 'PLR',
        'Saque de Investimento', 'Dividendos', 'Outro',
    ]

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    # Preenchido apenas quando tipo == 'Saque de Investimento'
    instituicao_id = db.Column(db.Integer, db.ForeignKey('instituicoes.id'), nullable=True)
    observacao = db.Column(db.String(300), nullable=True)

    instituicao = db.relationship('Instituicao', backref='receitas_extras')

    @property
    def eh_saque(self) -> bool:
        return self.tipo == 'Saque de Investimento'

    def __repr__(self) -> str:
        return f'<ReceitaExtra {self.tipo}: {self.descricao}>'
