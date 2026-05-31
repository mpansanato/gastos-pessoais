from app.extensions import db


class EntradaFixa(db.Model):
    """Template de entrada recorrente. Gera ReceitaFixa entries para os próximos 12 meses."""
    __tablename__ = 'entradas_fixas'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacao = db.Column(db.String(300), nullable=True)
    dia_recebimento = db.Column(db.Integer, nullable=True)

    receitas = db.relationship('ReceitaFixa', back_populates='entrada_fixa', lazy='dynamic')
    parcelas = db.relationship(
        'ParcelaEntradaFixa',
        back_populates='entrada_fixa',
        order_by='ParcelaEntradaFixa.ordem',
        cascade='all, delete-orphan',
        lazy='select',
    )

    @property
    def tem_parcelas(self):
        return len(self.parcelas) > 0

    def __repr__(self):
        return f'<EntradaFixa {self.descricao}>'
