from app.extensions import db


class ParametroMensal(db.Model):
    __tablename__ = 'parametros_mensais'

    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    salario = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('mes', 'ano', name='uq_parametro_mes_ano'),
    )
