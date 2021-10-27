import os

env = os.environ['ENV']
user = os.environ['POSTGRES_USER']
password = os.environ['POSTGRES_PASSWORD']
host = os.environ['POSTGRES_HOST']
database = os.environ['POSTGRES_DB']
port = os.environ['POSTGRES_PORT']

class Config(object):
    DEBUG = False
    TESTING = False

class ProductionConfig(Config):
    DATABASE_URI = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}'

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URI = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}'

class TestingConfig(Config):
    TESTING = True

if env == 'DEV':
    config = DevelopmentConfig()

if env == 'PROD':
    config = ProductionConfig()

