from app.extensions import db


class GastoFixo(db.Model):
    """Template de gasto recorrente. Gera Gasto entries para os próximos 12 meses."""
    __tablename__ = 'gastos_fixos'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacao = db.Column(db.String(300), nullable=True)

    categoria = db.relationship('Categoria', backref='gastos_fixos')
    gastos = db.relationship('Gasto', back_populates='gasto_fixo', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<GastoFixo {self.descricao}>'
