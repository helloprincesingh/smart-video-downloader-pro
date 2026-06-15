from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from app.services.download_service import DownloadService, queue_manager
from app.models.download import DownloadHistory
from app.models.favorite import Favorite
from app.models.analytics import Analytics
from app.database.db import db
from app.utils.security import rate_limit, is_valid_youtube_url

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/info', methods=['POST'])
@rate_limit(limit=30, period=60)
def info():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid video or playlist link.'}), 400
        
    try:
        info_dict = DownloadService.get_video_info(url)
        return jsonify(info_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/download', methods=['POST'])
@rate_limit(limit=15, period=60)
def download():
    data = request.get_json() or {}
    url = data.get('url')
    quality = data.get('quality', '720')
    audio_only = data.get('audio_only', False)
    subtitle = data.get('subtitle', False)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL.'}), 400
        
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
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
    task = queue_manager.get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    return jsonify(task)

@api_bp.route('/api/queue', methods=['GET'])
def get_queue():
    user_id = current_user.id if current_user.is_authenticated else None
    tasks = queue_manager.get_all_tasks(user_id=user_id)
    
    return jsonify([{
        'id': t['id'],
        'title': t['title'],
        'status': t['status'],
        'percent': t['percent'],
        'speed': t['speed'],
        'eta': t['eta'],
        'downloaded_size_mb': t['downloaded_size_mb'],
        'total_size_mb': t['total_size_mb'],
        'filename': t['filename'],
        'error': t['error']
    } for t in tasks])

@api_bp.route('/api/queue/pause/<task_id>', methods=['POST'])
def pause_task(task_id):
    success = queue_manager.pause_task(task_id)
    if success:
        return jsonify({'message': 'Task paused successfully'})
    return jsonify({'error': 'Could not pause task'}), 400

@api_bp.route('/api/queue/resume/<task_id>', methods=['POST'])
def resume_task(task_id):
    app = current_app._get_current_object()
    success = queue_manager.resume_task(app, task_id)
    if success:
        return jsonify({'message': 'Task resumed successfully'})
    return jsonify({'error': 'Could not resume task'}), 400

@api_bp.route('/api/queue/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    success = queue_manager.cancel_task(task_id)
    if success:
        return jsonify({'message': 'Task cancelled successfully'})
    return jsonify({'error': 'Could not cancel task'}), 400

@api_bp.route('/api/queue/retry/<task_id>', methods=['POST'])
def retry_task(task_id):
    app = current_app._get_current_object()
    success = queue_manager.retry_task(app, task_id)
    if success:
        return jsonify({'message': 'Task queued for retry successfully'})
    return jsonify({'error': 'Could not retry task. It must be in a failed or cancelled status.'}), 400

@api_bp.route('/api/queue/remove/<task_id>', methods=['POST'])
def remove_task(task_id):
    success = queue_manager.remove_task(task_id)
    if success:
        return jsonify({'message': 'Task removed successfully'})
    return jsonify({'error': 'Could not remove task. It must be in a completed, failed, or cancelled status.'}), 400

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
        
        # Log to Analytics
        analytics = Analytics(user_id=current_user.id, event_type='favorite_add', video_url=url)
        db.session.add(analytics)
        
        db.session.commit()
        return jsonify({'message': 'Added to favorites', 'id': fav.id}), 201

@api_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
def delete_favorite(fav_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    fav = Favorite.query.filter_by(id=fav_id, user_id=current_user.id).first()
    if not fav:
        return jsonify({'error': 'Favorite not found'}), 404
        
    url = fav.video_url
    db.session.delete(fav)
    
    analytics = Analytics(user_id=current_user.id, event_type='favorite_remove', video_url=url)
    db.session.add(analytics)
    
    db.session.commit()
    return jsonify({'message': 'Favorite removed'})

@api_bp.route('/api/history', methods=['GET'])
def history():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    search = request.args.get('search', '').strip()
    file_format = request.args.get('format', '').strip()
    
    query = DownloadHistory.query.filter_by(user_id=current_user.id)
    
    if search:
        query = query.filter(DownloadHistory.video_title.ilike(f"%{search}%"))
    if file_format:
        query = query.filter(DownloadHistory.file_format == file_format)
        
    hist = query.order_by(DownloadHistory.downloaded_at.desc()).all()
    
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

@api_bp.route('/api/history/<int:hist_id>', methods=['DELETE'])
def delete_history(hist_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    hist = DownloadHistory.query.filter_by(id=hist_id, user_id=current_user.id).first()
    if not hist:
        return jsonify({'error': 'History item not found'}), 404
        
    db.session.delete(hist)
    db.session.commit()
    return jsonify({'message': 'History item deleted'})
