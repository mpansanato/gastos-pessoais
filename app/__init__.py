import os
from datetime import datetime
from decimal import Decimal

from flask import Flask
from sqlalchemy import text
from config import Config
from app.extensions import db, login_manager, csrf


def _format_brl(value) -> str:
    if value is None:
        return '—'
    try:
        v = float(value)
        sign = '-' if v < 0 else ''
        fmt = '{:,.2f}'.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'{sign}R$ {fmt}'
    except (TypeError, ValueError):
        return '—'


def _migrate_gastos():
    """Adiciona colunas novas à tabela gastos sem perder dados existentes."""
    with db.engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text('PRAGMA table_info(gastos)'))]
        if 'gasto_fixo_id' not in cols:
            conn.execute(text(
                'ALTER TABLE gastos ADD COLUMN gasto_fixo_id INTEGER REFERENCES gastos_fixos(id)'
            ))
        if 'parcela_total' not in cols:
            conn.execute(text('ALTER TABLE gastos ADD COLUMN parcela_total INTEGER'))
        if 'parcela_num' not in cols:
            conn.execute(text('ALTER TABLE gastos ADD COLUMN parcela_num INTEGER'))
        if 'parcela_grupo_id' not in cols:
            conn.execute(text('ALTER TABLE gastos ADD COLUMN parcela_grupo_id INTEGER'))
        conn.commit()


def _migrate_investimentos():
    """Adiciona colunas novas à tabela investimentos sem perder dados existentes."""
    with db.engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text('PRAGMA table_info(investimentos)'))]
        if 'risco' not in cols:
            conn.execute(text("ALTER TABLE investimentos ADD COLUMN risco VARCHAR(10) NOT NULL DEFAULT 'baixo'"))
        if 'emissor' not in cols:
            conn.execute(text('ALTER TABLE investimentos ADD COLUMN emissor VARCHAR(200)'))
        if 'fundo' not in cols:
            conn.execute(text('ALTER TABLE investimentos ADD COLUMN fundo VARCHAR(200)'))
        conn.commit()


def _seed_instituicoes():
    from app.models.instituicao import Instituicao
    if db.session.scalar(db.select(db.func.count()).select_from(Instituicao)) == 0:
        defaults = [
            ('XP Investimentos', '#1e40af'),
            ('Itaú',             '#f97316'),
            ('Ágora (BTG)',      '#0ea5e9'),
            ('Bradesco',         '#dc2626'),
            ('Previdência',      '#198754'),
        ]
        for nome, cor in defaults:
            db.session.add(__import__('app.models.instituicao', fromlist=['Instituicao']).Instituicao(
                nome=nome, cor=cor
            ))
        db.session.commit()


def _seed_categorias():
    from app.models.categoria import Categoria
    if db.session.scalar(db.select(db.func.count()).select_from(Categoria)) == 0:
        defaults = [
            ('Cartão de Crédito', 'fixo',    '#dc3545', 1),
            ('Serviços',          'fixo',    '#0dcaf0', 2),
            ('Escola',            'fixo',    '#6f42c1', 3),
            ('Investimentos',     'fixo',    '#198754', 4),
            ('Seguros',           'fixo',    '#fd7e14', 5),
            ('Energia',           'fixo',    '#ffc107', 6),
            ('Alimentação',       'variavel', '#0d6efd', 7),
            ('Transporte',        'variavel', '#6c757d', 8),
            ('Lazer',             'variavel', '#20c997', 9),
        ]
        for nome, tipo, cor, ordem in defaults:
            db.session.add(__import__('app.models.categoria', fromlist=['Categoria']).Categoria(
                nome=nome, tipo=tipo, cor=cor, ordem=ordem
            ))
        db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    app.jinja_env.filters['brl'] = _format_brl
    app.jinja_env.filters['float'] = float
    app.jinja_env.globals['now'] = datetime.now
    app.jinja_env.globals['enumerate'] = enumerate

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.usuario import Usuario
        return db.session.get(Usuario, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.gastos import gastos_bp
    from app.routes.gastos_fixos import gastos_fixos_bp
    from app.routes.investimentos import investimentos_bp
    from app.routes.projecoes import projecoes_bp
    from app.routes.dados import dados_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(gastos_fixos_bp)
    app.register_blueprint(investimentos_bp)
    app.register_blueprint(projecoes_bp)
    app.register_blueprint(dados_bp)

    with app.app_context():
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        db.create_all()   # cria receitas_extras automaticamente (nova tabela)
        _migrate_gastos()
        _migrate_investimentos()
        _seed_categorias()
        _seed_instituicoes()

    return app
