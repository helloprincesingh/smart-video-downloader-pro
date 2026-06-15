from app.database.db import db
from datetime import datetime, timezone

class DownloadHistory(db.Model):
    __tablename__ = 'download_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True) # Nullable for guest downloads
    video_title = db.Column(db.String(256), nullable=False)
    video_url = db.Column(db.String(1024), nullable=False)
    thumbnail_url = db.Column(db.String(1024), nullable=True)
    quality = db.Column(db.String(50), nullable=True)
    file_format = db.Column(db.String(50), nullable=False) # 'video' or 'audio'
    file_size_mb = db.Column(db.Float, nullable=True)
    downloaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
