from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from app.extensions import db
from app.models.usuario import Usuario

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = db.session.scalar(
            db.select(Usuario).where(Usuario.username == form.username.data)
        )
        if usuario and usuario.check_senha(form.password.data):
            login_user(usuario, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('main.dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('auth.login'))


class AlterarSenhaForm(FlaskForm):
    senha_atual = PasswordField('Senha atual', validators=[DataRequired()])
    nova_senha = PasswordField('Nova senha', validators=[
        DataRequired(),
        Length(min=8, message='A senha deve ter no mínimo 8 caracteres.'),
    ])
    confirmar_senha = PasswordField('Confirmar nova senha', validators=[
        DataRequired(),
        EqualTo('nova_senha', message='As senhas não conferem.'),
    ])
    submit = SubmitField('Alterar senha')


@auth_bp.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    form = AlterarSenhaForm()
    if form.validate_on_submit():
        if not current_user.check_senha(form.senha_atual.data):
            flash('Senha atual incorreta.', 'danger')
            return render_template('auth/alterar_senha.html', form=form)

        current_user.set_senha(form.nova_senha.data)
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/alterar_senha.html', form=form)
