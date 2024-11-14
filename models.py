from app import db

class TipoUsuario(db.Model):
  __tablename__ = 'tipo_usuario'

  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  tipo = db.Column(db.String(50))

  # Relacionamento com Usuario
  usuarios = db.relationship('Usuario', back_populates='tipo_usuario', cascade="all, delete-orphan")

  def __repr__(self) -> str:
    return f'tipo_usuario: {self.tipo}'

class Usuario(db.Model):
  __tablename__ = 'usuarios'
 
  id = db.Column(db.Integer, primary_key=True, autoincrement=True, default=None, nullable=False)
  tipo_usuario_id = db.Column(db.Integer, db.ForeignKey('tipo_usuario.id'), nullable=False, default=1)
  nome = db.Column(db.String(255))
  data_nascimento = db.Column(db.Date)
  cpf = db.Column(db.String(14))
  email = db.Column(db.String(255))
  base64_image = db.Column(db.LargeBinary)
  embedding = db.Column(db.LargeBinary)

  # Relacionamento com TipoUsuario e RegistroAutenticacao
  tipo_usuario = db.relationship('TipoUsuario', back_populates='usuarios')
  registros_autenticacao = db.relationship('RegistroAutenticacao', back_populates='usuario', cascade="all, delete-orphan")
  logs = db.relationship('Log', back_populates='usuario', cascade="all, delete-orphan")
  permissoes = db.relationship('Permissao', secondary='usuarios_permissoes', back_populates='usuarios')

  def __repr__(self):
    return f'User with name {self.nome}'
  
# Modelo RegistroAutenticacao
class RegistroAutenticacao(db.Model):
  __tablename__ = 'registro_autenticacao'
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  usuarios_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
  data_hora = db.Column(db.DateTime, nullable=False)
  status = db.Column(db.Boolean, nullable=False)
  tipo_acesso = db.Column(db.String(50), nullable=False)

  # Relacionamento com Usuario
  usuario = db.relationship('Usuario', back_populates='registros_autenticacao')

class Log(db.Model):
  __tablename__ = 'logs'
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
  data_hora = db.Column(db.DateTime, nullable=False)
  tipo_evento = db.Column(db.String(50), nullable=False)
  descricao = db.Column(db.String(255))
  nivel_gravidade = db.Column(db.String(50))

  # Relacionamento com Usuario
  usuario = db.relationship('Usuario', back_populates='logs')

# Modelo Permissao
class Permissao(db.Model):
  __tablename__ = 'permissoes'
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  nome_permissao = db.Column(db.String(50), nullable=False)

  # Relacionamento com Usuario
  usuarios = db.relationship('Usuario', secondary='usuarios_permissoes', back_populates='permissoes')

# Tabela de associação entre Usuario e Permissao
class UsuarioPermissao(db.Model):
  __tablename__ = 'usuarios_permissoes'
  usuarios_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
  permissoes_id = db.Column(db.Integer, db.ForeignKey('permissoes.id'), primary_key=True)