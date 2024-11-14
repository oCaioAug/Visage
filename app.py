from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def create_app():
  app = Flask(__name__, template_folder='templates')
  app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:example@localhost:3306/visage'

  db.init_app(app)

  #import later on 
  from routes import register_routes
  register_routes(app, db)

  migrate = Migrate(app, db)

  return app