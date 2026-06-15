from app.database.db import db
from datetime import datetime, timezone

class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    video_title = db.Column(db.String(256), nullable=False)
    video_url = db.Column(db.String(1024), nullable=False)
    thumbnail_url = db.Column(db.String(1024), nullable=True)
    channel_name = db.Column(db.String(256), nullable=True)
    duration = db.Column(db.String(50), nullable=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
