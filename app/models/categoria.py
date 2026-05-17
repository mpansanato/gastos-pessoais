from app.extensions import db


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False, default='variavel')  # fixo | variavel
    cor = db.Column(db.String(7), nullable=False, default='#6c757d')
    ordem = db.Column(db.Integer, default=0)
    limite_mensal = db.Column(db.Numeric(12, 2), nullable=True)

    gastos = db.relationship('Gasto', backref='categoria', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<Categoria {self.nome}>'
