from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.download import DownloadHistory
from app.models.favorite import Favorite
from app.models.analytics import Analytics
from app.database.db import db
from datetime import datetime, timedelta
import collections

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def home():
    # 1. Basic Stats
    total_downloads = DownloadHistory.query.filter_by(user_id=current_user.id).count()
    total_favorites = Favorite.query.filter_by(user_id=current_user.id).count()
    
    # 2. Sum file sizes in MB
    total_bytes_mb = db.session.query(db.func.sum(DownloadHistory.file_size_mb)).filter(
        DownloadHistory.user_id == current_user.id
    ).scalar() or 0.0
    total_data_gb = round(total_bytes_mb / 1024, 2)
    
    # 3. Download Success Rate
    success_count = Analytics.query.filter_by(
        user_id=current_user.id, event_type='download_success'
    ).count()
    failed_count = Analytics.query.filter_by(
        user_id=current_user.id, event_type='download_failed'
    ).count()
    total_attempts = success_count + failed_count
    
    success_rate = 100.0
    if total_attempts > 0:
        success_rate = round((success_count / total_attempts) * 100, 1)

    # 4. Fetch downloads list
    history = DownloadHistory.query.filter_by(user_id=current_user.id).order_by(
        DownloadHistory.downloaded_at.desc()
    ).limit(15).all()
    
    # 5. Fetch favorites list
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(
        Favorite.added_at.desc()
    ).all()

    # 6. Database-agnostic monthly analytics aggregation (Python-based)
    monthly_counts = collections.defaultdict(int)
    all_downloads = DownloadHistory.query.filter_by(user_id=current_user.id).all()
    
    for d in all_downloads:
        month_key = d.downloaded_at.strftime('%b %Y')
        monthly_counts[month_key] += 1
        
    labels = []
    data_points = []
    
    # Generate labels for the last 6 months
    today = datetime.today()
    for i in range(5, -1, -1):
        # Approximate month subtraction (approx 30 days per month)
        target_month = today - timedelta(days=i * 30)
        label = target_month.strftime('%b %Y')
        labels.append(label)
        data_points.append(monthly_counts[label])

    return render_template(
        'dashboard.html',
        total_downloads=total_downloads,
        total_favorites=total_favorites,
        total_data_gb=total_data_gb,
        success_rate=success_rate,
        history=history,
        favorites=favorites,
        chart_labels=labels,
        chart_data=data_points
    )
