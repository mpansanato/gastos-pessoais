from app.extensions import db


class Instituicao(db.Model):
    __tablename__ = 'instituicoes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    cor = db.Column(db.String(7), nullable=False, default='#6c757d')

    investimentos = db.relationship('Investimento', backref='instituicao', lazy='select')

    def __repr__(self) -> str:
        return f'<Instituicao {self.nome}>'
