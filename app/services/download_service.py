import os
import uuid
import threading
import yt_dlp
import logging
from datetime import datetime, timezone
from app.database.db import db
from app.models.download import DownloadHistory
from app.models.analytics import Analytics

# Configure logger to write to download.log in workspace root
logger = logging.getLogger("download_logger")
logger.setLevel(logging.INFO)
logger.handlers.clear()  # Clear existing handlers to prevent duplicates on hot-reload

log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'download.log')
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def format_duration(seconds):
    """Convert seconds to HH:MM:SS or MM:SS string."""
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    hours = mins // 60
    if hours > 0:
        mins = mins % 60
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

class QueueManager:
    def __init__(self):
        self.tasks = {} # task_id -> task details
        self.lock = threading.Lock()
        self.max_concurrent = 2
        self.queued_ids = []
        self.active_ids = []
        
    def add_task(self, app, url, quality, audio_only, subtitle, user_id):
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'url': url,
                'quality': quality,
                'audio_only': audio_only,
                'subtitle': subtitle,
                'user_id': user_id,
                'status': 'queued',
                'percent': 0.0,
                'speed': '0 KB/s',
                'eta': '00:00',
                'downloaded_size_mb': 0.0,
                'total_size_mb': 0.0,
                'error': None,
                'filename': None,
                'title': 'Queued in line...',
                'cancel_flag': False,
                'pause_flag': False
            }
            self.queued_ids.append(task_id)
            logger.info(f"Task {task_id} added to queue. URL: {url}, Quality: {quality}, AudioOnly: {audio_only}")
            
        with app.app_context():
            try:
                event = Analytics(user_id=user_id, event_type='download_queued', video_url=url)
                db.session.add(event)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Queue analytics log error for task {task_id}: {e}")

        # Start queue processing
        threading.Thread(target=self._process_queue, args=(app,), daemon=True).start()
        return task_id

    def get_task(self, task_id):
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self, user_id=None):
        with self.lock:
            if user_id:
                return [t for t in self.tasks.values() if t['user_id'] == user_id]
            return list(self.tasks.values())

    def pause_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task['status'] == 'queued':
                task['status'] = 'paused'
                task['title'] = 'Paused in queue'
                if task_id in self.queued_ids:
                    self.queued_ids.remove(task_id)
                logger.info(f"Task {task_id} paused while in queue.")
                return True
            elif task['status'] == 'downloading':
                task['pause_flag'] = True
                task['title'] = 'Pausing...'
                logger.info(f"Task {task_id} pausing requested.")
                return True
        return False

    def resume_task(self, app, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task['status'] == 'paused':
                task['status'] = 'queued'
                task['title'] = 'Queued...'
                task['pause_flag'] = False
                task['cancel_flag'] = False
                self.queued_ids.append(task_id)
                logger.info(f"Task {task_id} resumed from pause.")
                
        threading.Thread(target=self._process_queue, args=(app,), daemon=True).start()
        return True

    def cancel_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task['status'] == 'queued':
                task['status'] = 'cancelled'
                task['title'] = 'Cancelled'
                if task_id in self.queued_ids:
                    self.queued_ids.remove(task_id)
                logger.info(f"Task {task_id} cancelled while in queue.")
                return True
            elif task['status'] == 'paused':
                task['status'] = 'cancelled'
                task['title'] = 'Cancelled'
                logger.info(f"Task {task_id} cancelled while paused.")
                return True
            elif task['status'] == 'downloading':
                task['cancel_flag'] = True
                task['title'] = 'Cancelling...'
                logger.info(f"Task {task_id} cancellation requested.")
                return True
        return False

    def retry_task(self, app, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task['status'] in ('failed', 'cancelled'):
                task['status'] = 'queued'
                task['title'] = 'Queued for retry...'
                task['percent'] = 0.0
                task['speed'] = '0 KB/s'
                task['eta'] = '00:00'
                task['error'] = None
                task['cancel_flag'] = False
                task['pause_flag'] = False
                if task_id not in self.queued_ids:
                    self.queued_ids.append(task_id)
                logger.info(f"Task {task_id} retried by user.")
                
        threading.Thread(target=self._process_queue, args=(app,), daemon=True).start()
        return True

    def remove_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task['status'] in ('completed', 'failed', 'cancelled'):
                if task_id in self.tasks:
                    del self.tasks[task_id]
                if task_id in self.queued_ids:
                    self.queued_ids.remove(task_id)
                if task_id in self.active_ids:
                    self.active_ids.remove(task_id)
                logger.info(f"Task {task_id} removed from manager history.")
                return True
        return False

    def remove_history(self, task_id):
        return self.remove_task(task_id)

    def _process_queue(self, app):
        with self.lock:
            if len(self.active_ids) >= self.max_concurrent:
                return
            if not self.queued_ids:
                return
                
            task_id = self.queued_ids.pop(0)
            self.active_ids.append(task_id)
            task = self.tasks[task_id]
            task['status'] = 'downloading'
            task['title'] = 'Connecting...'
            logger.info(f"Task {task_id} popped from queue to start downloading.")
            
        threading.Thread(
            target=self._execute_download,
            args=(app, task_id),
            daemon=True
        ).start()

    def _execute_download(self, app, task_id):
        task = self.get_task(task_id)
        if not task:
            return
            
        output_path = app.config['DOWNLOAD_FOLDER']
        os.makedirs(output_path, exist_ok=True)
        
        class DownloadCancelledException(Exception): pass
        class DownloadPausedException(Exception): pass
        
        def hook(d):
            curr_task = self.get_task(task_id)
            if not curr_task:
                return
            if curr_task['cancel_flag']:
                raise DownloadCancelledException("Cancelled by user")
            if curr_task['pause_flag']:
                raise DownloadPausedException("Paused by user")
                
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                
                # Calculate percent manually for higher accuracy
                if total > 0:
                    pct = round((downloaded / total) * 100, 1)
                else:
                    raw = d.get('_percent_str', '0%').strip().replace('%', '')
                    try:
                        pct = float(raw)
                    except ValueError:
                        pct = 0.0
                
                # Format speed manually
                speed_bytes = d.get('speed')
                if speed_bytes:
                    if speed_bytes > 1024 * 1024:
                        speed = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
                    else:
                        speed = f"{speed_bytes / 1024:.1f} KB/s"
                else:
                    speed = d.get('_speed_str', 'N/A')
                
                # Format ETA manually
                eta_secs = d.get('eta')
                if eta_secs is not None:
                    eta = format_duration(eta_secs)
                else:
                    eta = d.get('_eta_str', 'N/A')
                
                # Track last logged progress percent to prevent duplicate spam in file logs
                last_logged = curr_task.get('_last_logged_pct', 0.0)
                should_log = (pct - last_logged >= 10.0) or (pct == 100.0) or (last_logged == 0.0 and pct > 0.0)
                
                with self.lock:
                    self.tasks[task_id].update({
                        'percent': pct,
                        'speed': speed,
                        'eta': eta,
                        'downloaded_size_mb': round(downloaded / (1024 * 1024), 2),
                        'total_size_mb': round(total / (1024 * 1024), 2) if total else 0.0
                    })
                    if should_log:
                        self.tasks[task_id]['_last_logged_pct'] = pct
                
                if should_log:
                    logger.info(f"Task {task_id} progress: {pct}% | Speed: {speed} | Size: {round(downloaded / (1024 * 1024), 2)}MB/{round(total / (1024 * 1024), 2) if total else 'Unknown'}MB | ETA: {eta}")
                    
            elif d['status'] == 'finished':
                with self.lock:
                    self.tasks[task_id].update({
                        'status': 'processing',
                        'percent': 100
                    })
                logger.info(f"Task {task_id} finished downloading. Post-processing/merging formats...")

        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [hook],
            'noprogress': True,
            'quiet': False,
            'no_warnings': True,
            'nocheckcertificate': True,
            'socket_timeout': 30,               # Increased to 30 seconds connection timeout
            'retries': 10,                      # 10 retries
            'fragment_retries': 10,             # 10 fragment retries for DASH/HLS
            'http_chunk_size': 1048576,         # 1MB chunk size (stable, limits throttling)
            'nocachedir': True,                 # Prevent cache lock hangs on Windows
            'ignoreerrors': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Mode': 'navigate',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls'],
                }
            }
        }
        
        if task['audio_only']:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': f"bestvideo[height<={task['quality']}]+bestaudio/best[height<={task['quality']}]/best",
                'merge_output_format': 'mp4',
            })
            
        if task['subtitle']:
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
            })
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task['url'], download=True)
                filename = ydl.prepare_filename(info)
                
                if task['audio_only']:
                    filename = os.path.splitext(filename)[0] + '.mp3'
                else:
                    filename = os.path.splitext(filename)[0] + '.mp4'
                    
                basename = os.path.basename(filename)
                filepath = os.path.join(output_path, basename)
                
                file_size_mb = 0.0
                if os.path.exists(filepath):
                    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    
                with app.app_context():
                    hist = DownloadHistory(
                        user_id=task['user_id'],
                        video_title=info.get('title', 'Unknown Video'),
                        video_url=task['url'],
                        thumbnail_url=info.get('thumbnail'),
                        quality='Audio (MP3)' if task['audio_only'] else f"{info.get('height', task['quality'])}p",
                        file_format='audio' if task['audio_only'] else 'video',
                        file_size_mb=round(file_size_mb, 2)
                    )
                    db.session.add(hist)
                    
                    event = Analytics(
                        user_id=task['user_id'],
                        event_type='download_success',
                        video_url=task['url']
                    )
                    db.session.add(event)
                    db.session.commit()
                    
                with self.lock:
                    self.tasks[task_id].update({
                        'status': 'completed',
                        'filename': basename,
                        'title': info.get('title', 'Download complete'),
                        'percent': 100,
                        'file_size_mb': round(file_size_mb, 2)
                    })
                logger.info(f"Task {task_id} completed successfully. Filename: {basename}, Size: {round(file_size_mb, 2)} MB")
                    
        except DownloadCancelledException:
            with self.lock:
                self.tasks[task_id].update({
                    'status': 'cancelled',
                    'title': 'Download cancelled'
                })
            with app.app_context():
                try:
                    event = Analytics(user_id=task['user_id'], event_type='download_cancelled', video_url=task['url'])
                    db.session.add(event)
                    db.session.commit()
                except Exception:
                    pass
            logger.info(f"Task {task_id} cancelled by user.")
                
        except DownloadPausedException:
            with self.lock:
                self.tasks[task_id].update({
                    'status': 'paused',
                    'title': 'Download paused'
                })
            with app.app_context():
                try:
                    event = Analytics(user_id=task['user_id'], event_type='download_paused', video_url=task['url'])
                    db.session.add(event)
                    db.session.commit()
                except Exception:
                    pass
            logger.info(f"Task {task_id} paused by user.")
                
        except Exception as exc:
            # Generate a cleaner, more descriptive error message
            err_msg = str(exc)
            friendly_err = err_msg
            if "timed out" in err_msg or "ConnectionRefusedError" in err_msg or "Connection timed out" in err_msg:
                friendly_err = "Connection to YouTube timed out. Please try again."
            elif "HTTP Error 403" in err_msg or "Sign in to confirm your age" in err_msg or "AgeRestricted" in err_msg:
                friendly_err = "Access forbidden. This video might be age-restricted, private, or blocked by YouTube bot filters."
            elif "IncompleteRead" in err_msg:
                friendly_err = "Network read interrupted. YouTube throttled the connection. Please retry."
            elif "copyright" in err_msg.lower():
                friendly_err = "Download blocked due to copyright restrictions."
            elif "geo" in err_msg.lower() or "geoblocked" in err_msg.lower() or "not available in your country" in err_msg.lower():
                friendly_err = "This video is geo-restricted and unavailable in this server's region."
            elif "private" in err_msg.lower():
                friendly_err = "This is a private video and cannot be downloaded."
            elif "deleted" in err_msg.lower() or "removed" in err_msg.lower():
                friendly_err = "This video has been deleted or removed from YouTube."
                
            with self.lock:
                self.tasks[task_id].update({
                    'status': 'failed',
                    'error': friendly_err,
                    'title': 'Download failed'
                })
            with app.app_context():
                try:
                    event = Analytics(user_id=task['user_id'], event_type='download_failed', video_url=task['url'])
                    db.session.add(event)
                    db.session.commit()
                except Exception:
                    pass
            logger.error(f"Task {task_id} failed. Friendly Error: {friendly_err}. Details: {err_msg}")
                
        finally:
            with self.lock:
                if task_id in self.active_ids:
                    self.active_ids.remove(task_id)
            self._process_queue(app)

# Global queue manager instance
queue_manager = QueueManager()

class DownloadService:
    @staticmethod
    def get_video_info(url):
        """Fetch video metadata along with merged size estimations."""
        try:
            probe_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                probe = ydl.extract_info(url, download=False)

            is_playlist = 'entries' in probe

            if is_playlist:
                entries = [e for e in probe.get('entries', []) if e]
                return {
                    'is_playlist': True,
                    'title': probe.get('title', 'Playlist'),
                    'channel': probe.get('uploader') or probe.get('channel', 'Unknown'),
                    'url': url,
                    'total_videos': len(entries),
                    'thumbnail': entries[0].get('thumbnail') if entries else None,
                    'videos': [
                        {
                            'title': e.get('title', 'Unknown'),
                            'url': e.get('url') or f"https://www.youtube.com/watch?v={e.get('id')}",
                            'duration': format_duration(e.get('duration')),
                        }
                        for e in entries
                    ],
                }

            full_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get('formats', [])
            
            # Fetch best audio size
            audio_formats = [f for f in formats
                             if f.get('vcodec') == 'none' and f.get('acodec') not in (None, 'none')]
            audio_size_bytes = 0
            audio_size = "N/A"
            if audio_formats:
                best_audio = max(audio_formats, key=lambda f: f.get('abr') or 0)
                af_size = best_audio.get('filesize') or best_audio.get('filesize_approx')
                if af_size:
                    audio_size_bytes = af_size
                    audio_size = f"{af_size / (1024*1024):.1f} MB"

            qualities = []
            seen_heights = set()

            for f in formats:
                height = f.get('height')
                if height and height in [360, 480, 720, 1080]:
                    if height not in seen_heights:
                        seen_heights.add(height)
                        v_size = f.get('filesize') or f.get('filesize_approx') or 0
                        total_bytes = v_size + audio_size_bytes
                        size_str = f"{total_bytes / (1024*1024):.1f} MB" if total_bytes else "N/A"
                        qualities.append({
                            'height': height,
                            'resolution': f"{height}p",
                            'ext': 'mp4',
                            'estimated_size': size_str,
                        })

            qualities = sorted(qualities, key=lambda x: x['height'], reverse=True)

            if not qualities:
                qualities = [
                    {'height': 1080, 'resolution': '1080p', 'ext': 'mp4', 'estimated_size': 'N/A'},
                    {'height': 720,  'resolution': '720p',  'ext': 'mp4', 'estimated_size': 'N/A'},
                    {'height': 480,  'resolution': '480p',  'ext': 'mp4', 'estimated_size': 'N/A'},
                ]

            # Parse upload date, view count, like count if available
            upload_date = info.get('upload_date')
            if upload_date:
                try:
                    upload_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%b %d, %Y')
                except Exception:
                    pass
            else:
                upload_date = "N/A"

            return {
                'is_playlist': False,
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail'),
                'channel': info.get('uploader') or info.get('channel', 'Unknown Channel'),
                'duration': format_duration(info.get('duration')),
                'url': url,
                'qualities': qualities,
                'audio_size': audio_size,
                'upload_date': upload_date,
                'view_count': f"{info.get('view_count', 0):,}" if info.get('view_count') else "N/A",
                'like_count': f"{info.get('like_count', 0):,}" if info.get('like_count') else "N/A"
            }

        except Exception as e:
            raise Exception(f"Failed to fetch video information: {str(e)}")

    @staticmethod
    def start_download_thread(app, url, quality, audio_only=False, subtitle=False, user_id=None):
        return queue_manager.add_task(app, url, quality, audio_only, subtitle, user_id)
