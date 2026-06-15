import os

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-keep-it-secret-129384729')
    
    # Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
    
    # Database Configuration (SQLite by default, switches to PostgreSQL if DATABASE_URL is set)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Render/Heroku support for postgressql:// vs postgres://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'downloader.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
