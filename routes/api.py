from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from services.download_service import DownloadService, progress_data, progress_lock
from models import DownloadHistory, Favorite
from database import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/info', methods=['POST'])
def info():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    try:
        info_dict = DownloadService.get_video_info(url)
        return jsonify(info_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/download', methods=['POST'])
def download():
    data = request.get_json() or {}
    url = data.get('url')
    quality = data.get('quality', '720')
    audio_only = data.get('audio_only', False)
    subtitle = data.get('subtitle', False)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
        # Get reference to the actual Flask application to pass context to background thread
        app = current_app._get_current_object()
        
        task_id = DownloadService.start_download_thread(
            app=app,
            url=url,
            quality=quality,
            audio_only=audio_only,
            subtitle=subtitle,
            user_id=user_id
        )
        return jsonify({'task_id': task_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/progress/<task_id>', methods=['GET'])
def progress(task_id):
    with progress_lock:
        task = progress_data.get(task_id)
        
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    return jsonify(task)

@api_bp.route('/api/favorites', methods=['GET', 'POST'])
def manage_favorites():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    if request.method == 'GET':
        favs = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.added_at.desc()).all()
        return jsonify([{
            'id': f.id,
            'title': f.video_title,
            'url': f.video_url,
            'thumbnail': f.thumbnail_url,
            'channel': f.channel_name,
            'duration': f.duration
        } for f in favs])
        
    if request.method == 'POST':
        data = request.get_json() or {}
        url = data.get('url')
        title = data.get('title')
        thumbnail = data.get('thumbnail')
        channel = data.get('channel')
        duration = data.get('duration')
        
        if not url or not title:
            return jsonify({'error': 'URL and Title are required'}), 400
            
        # Check if already in favorites
        existing = Favorite.query.filter_by(user_id=current_user.id, video_url=url).first()
        if existing:
            return jsonify({'message': 'Already in favorites', 'id': existing.id})
            
        fav = Favorite(
            user_id=current_user.id,
            video_url=url,
            video_title=title,
            thumbnail_url=thumbnail,
            channel_name=channel,
            duration=duration
        )
        db.session.add(fav)
        db.session.commit()
        return jsonify({'message': 'Added to favorites', 'id': fav.id}), 201

@api_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
def delete_favorite(fav_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    fav = Favorite.query.filter_by(id=fav_id, user_id=current_user.id).first()
    if not fav:
        return jsonify({'error': 'Favorite not found'}), 404
        
    db.session.delete(fav)
    db.session.commit()
    return jsonify({'message': 'Favorite removed'})

@api_bp.route('/api/history', methods=['GET'])
def history():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    hist = DownloadHistory.query.filter_by(user_id=current_user.id).order_by(DownloadHistory.downloaded_at.desc()).limit(20).all()
    return jsonify([{
        'id': h.id,
        'title': h.video_title,
        'url': h.video_url,
        'thumbnail': h.thumbnail_url,
        'quality': h.quality,
        'format': h.file_format,
        'size_mb': h.file_size_mb,
        'downloaded_at': h.downloaded_at.strftime('%Y-%m-%d %H:%M')
    } for h in hist])
