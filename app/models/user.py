from app.database.db import db
from flask_login import UserMixin
from datetime import datetime, timezone

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    supabase_uid = db.Column(db.String(255), unique=True, nullable=True, index=True) # Nullable for local auth fallback
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True) # Nullable for Supabase-only users
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    downloads = db.relationship('DownloadHistory', backref='user', lazy=True, cascade="all, delete-orphan")
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade="all, delete-orphan")

    from werkzeug.security import generate_password_hash, check_password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)
