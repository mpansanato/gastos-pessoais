from app.extensions import db


class Gasto(db.Model):
    __tablename__ = 'gastos'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    valor_previsto = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_pago = db.Column(db.Numeric(12, 2), nullable=True)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    observacao = db.Column(db.String(300), nullable=True)

    # NULL = lançamento manual; preenchido = gerado por um GastoFixo
    gasto_fixo_id = db.Column(db.Integer, db.ForeignKey('gastos_fixos.id'), nullable=True)
    gasto_fixo = db.relationship('GastoFixo', back_populates='gastos')

    # Parcelamento: NULL = à vista; preenchido = parte de um grupo de N parcelas
    parcela_total = db.Column(db.Integer, nullable=True)    # total de parcelas (ex: 4)
    parcela_num   = db.Column(db.Integer, nullable=True)    # número desta parcela (1..N)
    parcela_grupo_id = db.Column(db.Integer, nullable=True) # id da 1ª parcela do grupo

    @property
    def diferenca(self):
        if self.valor_pago is None:
            return None
        return float(self.valor_pago) - float(self.valor_previsto)

    def __repr__(self) -> str:
        return f'<Gasto {self.descricao}>'
