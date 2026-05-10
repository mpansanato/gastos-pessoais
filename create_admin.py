"""Cria o usuário administrador inicial do sistema."""
import getpass
import sys

from app import create_app
from app.extensions import db
from app.models.usuario import Usuario


def create_admin() -> None:
    app = create_app()
    with app.app_context():
        username = input('Nome de usuário: ').strip()
        if not username:
            print('ERRO: Nome de usuário não pode ser vazio.')
            sys.exit(1)

        existing = db.session.scalar(db.select(Usuario).where(Usuario.username == username))
        if existing:
            print(f"ERRO: Usuário '{username}' já existe.")
            sys.exit(1)

        senha = getpass.getpass('Senha (mínimo 8 caracteres): ')
        if len(senha) < 8:
            print('ERRO: Senha muito curta (mínimo 8 caracteres).')
            sys.exit(1)

        confirmacao = getpass.getpass('Confirme a senha: ')
        if senha != confirmacao:
            print('ERRO: Senhas não conferem.')
            sys.exit(1)

        usuario = Usuario(username=username)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        print(f"\n  Usuário '{username}' criado com sucesso!")


if __name__ == '__main__':
    create_admin()
