from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'sua_chave_secreta_para_flash_messages'

db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.String(10), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    foto = db.Column(db.LargeBinary, nullable=True)
    embedding = db.Column(db.LargeBinary, nullable=True)
    status = db.Column(db.String(10), nullable=False, default='liberado')

with app.app_context():
    db.create_all()

class Acesso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    data = db.Column(db.String(10), nullable=False)
    hora = db.Column(db.String(5), nullable=False)
    dia_semana = db.Column(db.String(10), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('acessos', lazy=True))

with app.app_context():
    db.create_all()

# def validar_cpf(cpf):
#     cpf = re.sub(r'[^0-9]', '', cpf)
#     if len(cpf) != 11 or cpf == cpf[0] * 11:
#         return False
#     soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
#     resto = (soma * 10 % 11) % 10
#     if resto != int(cpf[9]):
#         return False
#     soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
#         resto = (soma * 10 % 11) % 10
#         if resto != int(cpf[10]):
#             return False
#     return True

@app.route('/')
def home():
    return "<h1>Bem-vindo ao meu site Flask!</h1>"

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        data_nascimento = request.form['data']
        cpf = request.form['cpf']
        email = request.form['email']
        foto = request.files['foto']
        foto_bin = foto.read() if foto else None
        novo_usuario = Usuario(nome=nome, data_nascimento=data_nascimento, cpf=cpf, email=email, foto=foto_bin)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('cadastrar'))
    return render_template('cadastrar.html')

@app.route('/foto_base64/<int:usuario_id>')
def foto_base64(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if usuario and usuario.foto:
        foto_base64 = base64.b64encode(usuario.foto).decode('utf-8')
        return f"data:image/jpeg;base64,{foto_base64}"
    with open('static/default.jpg', 'rb') as f:
        default_foto = f.read()
    default_foto_base64 = base64.b64encode(default_foto).decode('utf-8')
    return f"data:image/jpeg;base64,{default_foto_base64}"

@app.route('/usuario/<int:id>/atualizar_status', methods=['POST'])
def atualizar_status(id):
    usuario = Usuario.query.get_or_404(id)
    novo_status = request.form['status']
    usuario.status = novo_status
    db.session.commit()
    return '', 200

@app.route('/usuarios')
def usuarios():
    usuarios = Usuario.query.all()
    for usuario in usuarios:
        if usuario.foto:
            foto_binaria = usuario.foto if isinstance(usuario.foto, bytes) else bytes(usuario.foto, 'utf-8')
            usuario.foto_base64 = base64.b64encode(foto_binaria).decode('utf-8')
        else:
            with open('static/default.jpg', 'rb') as f:
                usuario.foto_base64 = base64.b64encode(f.read()).decode('utf-8')
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuario/<int:id>')
def usuario_perfil(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.foto:
        foto_binaria = usuario.foto if isinstance(usuario.foto, bytes) else bytes(usuario.foto, 'utf-8')
        usuario.foto_base64 = base64.b64encode(foto_binaria).decode('utf-8')
    else:
        with open('static/default.jpg', 'rb') as f:
            usuario.foto_base64 = base64.b64encode(f.read()).decode('utf-8')
    return render_template('usuario_perfil.html', usuario=usuario)

@app.route('/painel')
def painel():
    acessos = Acesso.query.order_by(Acesso.data, Acesso.hora).all()
    return render_template('painel.html', acessos=acessos)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    app.run(debug=True, port=80)
