import hashlib
import base64
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from PIL import Image
import face_recognition
import mediapipe as mp
from sqlalchemy.exc import IntegrityError
import locale
from flask import Response
from io import StringIO
import numpy as np

locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DATABASE = SQLAlchemy(app)
app.secret_key = 'your_secret_key_here'

socketio = SocketIO(app)
CORS(app)

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.1)

class Usuario(DATABASE.Model):
    id = DATABASE.Column(DATABASE.Integer, primary_key=True)
    nome = DATABASE.Column(DATABASE.String(100), nullable=False)
    data_nascimento = DATABASE.Column(DATABASE.String(10), nullable=False)
    cpf = DATABASE.Column(DATABASE.String(14), unique=True, nullable=False)
    email = DATABASE.Column(DATABASE.String(120), unique=True, nullable=False)
    foto = DATABASE.Column(DATABASE.LargeBinary, nullable=True)
    embedding = DATABASE.Column(DATABASE.LargeBinary, nullable=True)
    status = DATABASE.Column(DATABASE.String(10), nullable=False, default='liberado')
    password = DATABASE.Column(DATABASE.String(255), nullable=False)
    is_admin = DATABASE.Column(DATABASE.Boolean, nullable=False, default=False)

    def set_password(self, password):
        """Método para hash da senha usando MD5."""
        self.password = hashlib.md5(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """Método para verificar se a senha informada é a mesma armazenada."""
        return self.password == hashlib.md5(password.encode('utf-8')).hexdigest()
class LogAcesso(DATABASE.Model):
    id = DATABASE.Column(DATABASE.Integer, primary_key=True)
    usuario_id = DATABASE.Column(DATABASE.Integer, DATABASE.ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    status = DATABASE.Column(DATABASE.String(10), nullable=False)
    timestamp = DATABASE.Column(DATABASE.DateTime, default=datetime.utcnow, nullable=False)

    usuario = DATABASE.relationship('Usuario', backref=DATABASE.backref('logs', lazy=True, cascade="all, delete-orphan"))

def create_default_admin():

    usuario_admin = Usuario.query.filter_by(email='admin@admin.com').first()

    if not usuario_admin:

        usuario_admin = Usuario(
            nome='Admin',
            data_nascimento='01/01/1990',
            cpf='000.000.000-00',
            email='admin@admin.com',
            foto=None,
            embedding=None,
            status='liberado',
            is_admin=True
        )

        usuario_admin.set_password('admin')

        DATABASE.session.add(usuario_admin)
        DATABASE.session.commit()

        print("Usuário admin padrão criado!")
    else:
        print("Usuário admin já existe!")

with app.app_context():
    DATABASE.create_all()
    create_default_admin()


@app.route('/exportar_logs', methods=['GET'])
def exportar_logs():

    logs = LogAcesso.query.join(Usuario).add_columns(
        Usuario.nome, Usuario.cpf, Usuario.email,
        LogAcesso.timestamp, LogAcesso.status
    ).all()

    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)

    csv_writer.writerow(['Nome', 'CPF', 'Email', 'Data', 'Status'])

    for log in logs:
        csv_writer.writerow([
            log.nome,
            log.cpf,
            log.email,
            log.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            log.status
        ])

    response = make_response(csv_output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=logs_acesso.csv'
    response.headers['Content-Type'] = 'text/csv'

    return response

@app.route('/usuario/<int:id>/exportar_logs', methods=['GET'])
def exportar_logs2(id):
    if 'username' not in session:
        return redirect('/')

    logs = LogAcesso.query.filter_by(usuario_id=id).order_by(LogAcesso.timestamp.desc()).all()

    if not logs:
        return jsonify({'error': 'Nenhum log encontrado para este usuário.'}), 404

    output = StringIO()
    csv_writer = csv.writer(output)

    csv_writer.writerow(['Nome', 'CPF', 'Email', 'Data Nasc', 'Data e Hora do Acesso', 'Status'])

    for log in logs:
        csv_writer.writerow([
            log.usuario.nome,
            log.usuario.cpf,
            log.usuario.email,
            log.usuario.data_nascimento,
            log.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            '🟢 Liberado' if log.status == 'liberado' else '🔴 Bloqueado'
        ])

    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=logs_usuario_{id}.csv"}
    )

@app.route('/painel')
def painel():
    if 'username' not in session:
        return redirect('/')

    logs = LogAcesso.query.all()
    return render_template('painel.html', painel=logs)

@app.route('/logout')
def logout():

    session.pop('username', None)
    return redirect('/')

@app.route('/usuario/<int:id>/editar', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'username' not in session:
        return redirect('/')
    usuario = Usuario.query.get_or_404(id)

    if usuario.foto:
        foto_base64 = base64.b64encode(usuario.foto).decode('utf-8')
    else:
        foto_base64 = None

    if request.method == 'POST':

        usuario.nome = request.form['nome']
        usuario.data_nascimento = request.form['data']
        usuario.cpf = request.form['cpf']
        usuario.email = request.form['email']

        foto = request.files.get('foto')
        if foto:
            try:

                foto_bin = foto.read()

                image = Image.open(io.BytesIO(foto_bin)).convert('RGB')
                image_np = np.array(image)

                results = face_detection.process(image_np)

                if results.detections:

                    detection = results.detections[0]
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = image_np.shape
                    bbox = [
                        int(bboxC.xmin * iw),
                        int(bboxC.ymin * ih),
                        int(bboxC.width * iw),
                        int(bboxC.height * ih)
                    ]

                    face_img = image_np[bbox[1]:bbox[1] + bbox[3], bbox[0]:bbox[0] + bbox[2]]
                    face_pil_img = Image.fromarray(face_img)

                    buffered = io.BytesIO()
                    face_pil_img.save(buffered, format="PNG")
                    face_bin = buffered.getvalue()

                    usuario.foto = face_bin
                else:
                    flash('Nenhum rosto detectado na foto.', 'error')
                    return redirect(url_for('editar_usuario', id=usuario.id))

            except Exception as e:
                flash(f'Erro ao processar a foto: {str(e)}', 'error')
                return redirect(url_for('editar_usuario', id=usuario.id))

        DATABASE.session.commit()

        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('usuario_perfil', id=usuario.id))

    return render_template('editar_usuario.html', usuario=usuario, foto_base64=foto_base64)

def get_face_embedding(image_data):
    image = face_recognition.load_image_file(image_data)
    face_encodings = face_recognition.face_encodings(image)
    if face_encodings:
        return face_encodings[0]
    return None

def compare_face(image_embedding):
    global percentage
    rows = Usuario.query.all()

    for row in rows:
        db_base64_image = row.foto
        db_embedding = (
            np.frombuffer(row.embedding, dtype=np.float64) if row.embedding else None
        )

        if db_embedding is None or db_embedding.shape != image_embedding.shape:
            continue

        distance = np.linalg.norm(image_embedding - db_embedding)
        percentage = (1 - distance) * 100
        if distance < 0.5:

            print(5)
            return db_base64_image, row.id, row.status
    return None

@socketio.on('frame')
def handle_frame(data):
    if 'session_id' not in data or 'image' not in data:
        emit('error', {'error': 'session_id or image data is missing'})
        return

    image_data = data.get('image')
    session_id = data.get('session_id')

    try:
        image_data = base64.b64decode(image_data.split(',')[1])
        image_embedding = get_face_embedding(io.BytesIO(image_data))
        if image_embedding is None:
            emit('error', {'error': 'No face detected in the image'})
        else:
            match, id, status = compare_face(image_embedding)
            if match:

                log = LogAcesso(usuario_id=id, status=status)
                DATABASE.session.add(log)
                DATABASE.session.commit()

                user = DATABASE.session.query(Usuario).filter_by(id=id).first()
                user_name = user.nome if user else "Usuário desconhecido"
                print(6)
                if status == 'liberado':
                    print(1)
                    emit('result', {'message': 'Match found', 'matched_face': match, 'percentage': f'{percentage:.2f}%', 'name': user_name})
                elif status == 'bloqueado':
                    print(2)
                    emit('result', {'message': 'Match bloqueado', 'matched_face': match, 'percentage': f'{percentage:.2f}%', 'name': user_name})
            else:
                emit('result', {'message': 'No match found'})
    except Exception as e:
        emit('error', {'error': f'Invalid Base64 image data: {str(e)}'})

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if 'username' not in session:
        return redirect('/')
    if request.method == 'POST':

        nome = request.form['nome']
        data_nascimento = request.form['data']
        cpf = request.form['cpf']
        email = request.form['email']
        foto = request.files['foto']
        senha = request.form['senha']
        is_admin = request.form['is_admin'] == 'true'
        md5_hash = hashlib.md5(senha.encode()).hexdigest()

        foto_bin = foto.read() if foto else None

        if foto_bin:
            try:

                image = Image.open(io.BytesIO(foto_bin)).convert('RGB')
                image_np = np.array(image)

                results = face_detection.process(image_np)

                if results.detections:

                    detection = results.detections[0]
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = image_np.shape
                    bbox = [
                        int(bboxC.xmin * iw),
                        int(bboxC.ymin * ih),
                        int(bboxC.width * iw),
                        int(bboxC.height * ih)
                    ]

                    face_img = image_np[bbox[1]:bbox[1] + bbox[3], bbox[0]:bbox[0] + bbox[2]]
                    face_pil_img = Image.fromarray(face_img)

                    buffered = io.BytesIO()
                    face_pil_img.save(buffered, format="PNG")
                    face_bin = buffered.getvalue()
                    face_embedding = get_face_embedding(io.BytesIO(buffered.getvalue()))

                    novo_usuario = Usuario(nome=nome, data_nascimento=data_nascimento, cpf=cpf, email=email,
                                           foto=face_bin, embedding=face_embedding.tobytes(), is_admin=is_admin, password=md5_hash)
                    DATABASE.session.add(novo_usuario)
                    DATABASE.session.commit()

                    return redirect(url_for('cadastrar'))

                else:
                    return jsonify({'error': 'Nenhum rosto detectado na imagem.'}), 400

            except Exception as e:
                return jsonify({'error': f'Erro ao processar a imagem: {str(e)}'}), 500

    return render_template('cadastrar.html')

@app.route('/usuarios')
def usuarios():
    if 'username' not in session:
        return redirect('/')
    usuarios = Usuario.query.all()

    for usuario in usuarios:
        if usuario.foto:

            foto_binaria = usuario.foto if isinstance(usuario.foto, bytes) else bytes(usuario.foto, 'utf-8')
            usuario.foto_base64 = base64.b64encode(foto_binaria).decode('utf-8')
        else:

            with open('static/uploads/user-placeholder.jpg', 'rb') as f:
                usuario.foto_base64 = base64.b64encode(f.read()).decode('utf-8')

    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuario/<int:id>')
def usuario_perfil(id):
    if 'username' not in session:
        return redirect('/')

    usuario = Usuario.query.get_or_404(id)

    if usuario.foto:
        foto_binaria = usuario.foto if isinstance(usuario.foto, bytes) else bytes(usuario.foto, 'utf-8')
        usuario.foto_base64 = base64.b64encode(foto_binaria).decode('utf-8')
    else:

        with open('static/uploads/user-placeholder.jpg', 'rb') as f:
            usuario.foto_base64 = base64.b64encode(f.read()).decode('utf-8')

    logs = LogAcesso.query.filter_by(usuario_id=id).order_by(LogAcesso.timestamp.desc()).all()

    return render_template('usuario_perfil.html', usuario=usuario, logs=logs)

@app.route('/usuario/<int:id>/deletar', methods=['POST'])
def deletar_usuario(id):
    usuario = DATABASE.session.get(Usuario, id)

    if not usuario:
        flash("Usuário não encontrado", "error")
        return redirect(url_for('usuarios'))

    try:

        DATABASE.session.delete(usuario)
        DATABASE.session.commit()
        flash("Usuário deletado com sucesso!", "success")
        return redirect(url_for('usuarios'))
    except IntegrityError:
        DATABASE.session.rollback()
        flash("Erro ao deletar usuário, há dados relacionados", "error")
        return redirect(url_for('usuarios'))

@app.route('/usuario/<int:id>/atualizar_status', methods=['POST'])
def atualizar_status(id):
    if 'username' not in session:
        return redirect('/')

    novo_status = request.form.get('status')
    if novo_status not in ['liberado', 'bloqueado']:
        return jsonify({'error': 'Status inválido'}), 400

    usuario = Usuario.query.get_or_404(id)

    usuario.status = novo_status
    DATABASE.session.commit()

    return jsonify({'message': 'Status atualizado com sucesso', 'novo_status': usuario.status}), 200

@app.route('/bio')
def bio():
    return render_template('index.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':

        if 'username' in session:
            return redirect('/cadastrar')
        return render_template('login.html')

    elif request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return "Email and password are required", 400

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None:
            return "Usuário não encontrado", 404

        if usuario.check_password(password):
            if usuario.is_admin:
                session['username'] = usuario.nome
                return redirect('/cadastrar')
            else:
                return "Acesso negado: Somente administradores podem acessar.", 403
        else:
            return "Usuário ou senha inválidos", 401

if __name__ == '__main__':
    app.run(debug=True, port=8890, ssl_context=('cert.pem', 'key.pem'))