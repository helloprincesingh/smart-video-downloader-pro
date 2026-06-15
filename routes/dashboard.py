from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import DownloadHistory, Favorite

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def home():
    # Fetch stats
    total_downloads = DownloadHistory.query.filter_by(user_id=current_user.id).count()
    total_favorites = Favorite.query.filter_by(user_id=current_user.id).count()
    
    # Fetch history
    history = DownloadHistory.query.filter_by(user_id=current_user.id).order_by(DownloadHistory.downloaded_at.desc()).limit(10).all()
    
    # Fetch favorites
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.added_at.desc()).all()
    
    return render_template(
        'dashboard.html',
        total_downloads=total_downloads,
        total_favorites=total_favorites,
        history=history,
        favorites=favorites
    )
