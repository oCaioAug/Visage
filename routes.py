from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import *
import os
import base64

def register_routes(app, db):

  @app.route('/teste')
  def teste():
    tipo_usuario_id = TipoUsuario.query.all()
    user = Usuario.query.join(TipoUsuario).all()

    return str(tipo_usuario_id)
  
  @app.route('/set_data')
  def set_data():
      session['name'] = 'Mike'
      session['other'] = 'Xique-Xique BA'

      return render_template('aaa.html', message='Session stored succesfully')

  @app.route('/', methods=['GET', 'POST'])
  def index():
      if request.method == 'GET':
          return render_template('login.html')
      elif request.method == 'POST':
          username = request.form['username']
          password = request.form['password']

          if username == 'caio' and password == '123':
              return redirect('/cadastrar')
          else:
              return "HAHAHAHAHAH"

  @app.route('/cadastrar', methods=['GET', 'POST'])
  def cadastrar():
      if request.method == 'POST':
          nome = request.form['nome']
          data_nascimento = request.form['data']
          cpf = request.form['cpf']
          email = request.form['email']
          foto = request.files['foto']
          foto_bin = foto.read() if foto else None
          tipo_usuario = request.form['tipo_usuario']

          novo_usuario = Usuario(tipo_usuario_id=tipo_usuario, nome=nome, data_nascimento=data_nascimento, cpf=cpf, email=email, base64_image=foto_bin)

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
          if usuario.base64_image:
              foto_binaria = usuario.base64_image if isinstance(usuario.base64_image, bytes) else bytes(usuario.base64_image, 'utf-8')
              usuario.base64_image = base64.b64encode(foto_binaria).decode('utf-8')
          else:
              with open('static/uploads/RJ.png', 'rb') as f:
                  usuario.base64_image = base64.b64encode(f.read()).decode('utf-8')
      return render_template('usuarios.html', usuarios=usuarios)

  @app.route('/usuario/<int:id>')
  def usuario_perfil(id):
      usuario = Usuario.query.get_or_404(id)
      if usuario.base64_image:
          foto_binaria = usuario.base64_image if isinstance(usuario.base64_image, bytes) else bytes(usuario.base64_image, 'utf-8')
          usuario.foto_base64 = base64.b64encode(foto_binaria).decode('utf-8')
      else:
          with open('static/default.jpg', 'rb') as f:
              usuario.foto_base64 = base64.b64encode(f.read()).decode('utf-8')
      return render_template('usuario_perfil.html', usuario=usuario)

  @app.route('/painel')
  def painel():
      acessos = Acesso.query.order_by(Acesso.data, Acesso.hora).all()
      return render_template('painel.html', acessos=acessos)

  @app.route('/funcionarios')
  def funcionarios():
#     funcionarios = [
#         Funcionario("João Silva", "1990-01-01", "123.456.789-00", "joao.silva@example.com", None, None, "liberado"),
#         Funcionario("Maria Oliveira", "1985-05-15", "987.654.321-00", "maria.oliveira@example.com", None, None, "liberado"),
#         Funcionario("Carlos Santos", "1992-03-20", "456.789.123-00", "carlos.santos@example.com", None, None, "liberado")
#     ]
#     return render_template('funcionarios.html', funcionarios=funcionarios)
    return 'asdf'

  @app.route('/administradores')
  def admins():
#     admins = [
#         Admin("João Silva", "1990-01-01", "123.456.789-00", "joao.silva@example.com", None, None, "liberado"),
#         Admin("Maria Oliveira", "1985-05-15", "987.654.321-00", "maria.oliveira@example.com", None, None, "liberado"),
#         Admin("Carlos Santos", "1992-03-20", "456.789.123-00", "carlos.santos@example.com", None, None, "liberado"),
#     ]
#     return render_template('administradores.html', admins=admins)
    return 'asd'

  @app.route('/login')
  def login():
      return render_template('login.html')

  @app.route('/bio')
  def bio():
      return render_template('index.html')
  