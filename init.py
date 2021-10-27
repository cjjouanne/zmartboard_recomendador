from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import config

application = Flask(__name__)
CORS(application)
application.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
application.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URI
db = SQLAlchemy(application)

from sqlalchemy import create_engine
engine = create_engine(application.config['SQLALCHEMY_DATABASE_URI'])
print (f"engine: {engine}")

