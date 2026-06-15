from app.database.db import db
from datetime import datetime, timezone

class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True) # Nullable for anonymous/guest downloads
    event_type = db.Column(db.String(100), nullable=False) # e.g. 'download_start', 'download_success', 'download_failed', 'page_view'
    video_url = db.Column(db.String(1024), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
