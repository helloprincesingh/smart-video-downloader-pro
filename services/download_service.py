import os
import uuid
import threading
import yt_dlp
from datetime import datetime

# Global dictionary to track progress of task_ids
# Structure: { task_id: { 'status': 'pending/downloading/finished/error', 'percent': 0, 'speed': '0 MB/s', 'eta': '00:00', 'error': None, 'filename': None, 'title': None } }
progress_data = {}
progress_lock = threading.Lock()

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


class DownloadService:

    @staticmethod
    def _is_playlist(url):
        """Quick check if URL looks like a playlist."""
        return 'list=' in url and 'watch?v=' not in url

    @staticmethod
    def get_video_info(url):
        """
        Fetch video/playlist metadata, thumbnail, title, channel, duration, and qualities.
        Uses extract_flat only for playlists; full extraction for single videos.
        """
        try:
            # ── Step 1: Quick probe to decide playlist vs single ──────────────
            probe_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,     # fast, no format details yet
            }
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                probe = ydl.extract_info(url, download=False)

            is_playlist = 'entries' in probe

            # ── Step 2a: Playlist path ────────────────────────────────────────
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

            # ── Step 2b: Single video — full extraction for formats ───────────
            full_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get('formats', [])
            qualities = []
            seen_heights = set()

            for f in formats:
                height = f.get('height')
                if height and height in [144, 240, 360, 480, 720, 1080, 1440, 2160]:
                    if height not in seen_heights:
                        seen_heights.add(height)
                        filesize = f.get('filesize') or f.get('filesize_approx')
                        size_str = f"{filesize / (1024*1024):.1f} MB" if filesize else "N/A"
                        qualities.append({
                            'height': height,
                            'resolution': f"{height}p",
                            'ext': f.get('ext', 'mp4'),
                            'estimated_size': size_str,
                        })

            # Descending order (best first)
            qualities = sorted(qualities, key=lambda x: x['height'], reverse=True)

            # If no standard heights found, provide sensible defaults
            if not qualities:
                qualities = [
                    {'height': 1080, 'resolution': '1080p', 'ext': 'mp4', 'estimated_size': 'N/A'},
                    {'height': 720,  'resolution': '720p',  'ext': 'mp4', 'estimated_size': 'N/A'},
                    {'height': 480,  'resolution': '480p',  'ext': 'mp4', 'estimated_size': 'N/A'},
                    {'height': 360,  'resolution': '360p',  'ext': 'mp4', 'estimated_size': 'N/A'},
                ]

            # Best audio-only size estimate
            audio_formats = [f for f in formats
                             if f.get('vcodec') == 'none' and f.get('acodec') not in (None, 'none')]
            audio_size = "N/A"
            if audio_formats:
                best_audio = max(audio_formats, key=lambda f: f.get('abr') or 0)
                af_size = best_audio.get('filesize') or best_audio.get('filesize_approx')
                if af_size:
                    audio_size = f"{af_size / (1024*1024):.1f} MB"

            return {
                'is_playlist': False,
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail'),
                'channel': info.get('uploader') or info.get('channel', 'Unknown Channel'),
                'duration': format_duration(info.get('duration')),
                'url': url,
                'qualities': qualities,
                'audio_size': audio_size,
            }

        except Exception as e:
            raise Exception(f"Failed to fetch video information: {str(e)}")

    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def start_download_thread(app, url, quality, audio_only=False, subtitle=False, user_id=None):
        """Create a background thread for downloading and return a task_id."""
        task_id = str(uuid.uuid4())

        with progress_lock:
            progress_data[task_id] = {
                'status': 'pending',
                'percent': 0,
                'speed': 'N/A',
                'eta': 'N/A',
                'error': None,
                'filename': None,
                'title': 'Preparing download...',
            }

        thread = threading.Thread(
            target=DownloadService._run_download,
            args=(app, task_id, url, quality, audio_only, subtitle, user_id),
            daemon=True,
        )
        thread.start()
        return task_id

    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _run_download(app, task_id, url, quality, audio_only, subtitle, user_id):
        """Internal: run yt-dlp download in background thread."""
        output_path = app.config['DOWNLOAD_FOLDER']
        os.makedirs(output_path, exist_ok=True)

        # ── Progress hook ─────────────────────────────────────────────────────
        def hook(d):
            if d['status'] == 'downloading':
                raw = d.get('_percent_str', '0%').strip().replace('%', '')
                try:
                    pct = float(raw)
                except ValueError:
                    pct = 0.0
                with progress_lock:
                    progress_data[task_id].update({
                        'status': 'downloading',
                        'percent': round(pct, 1),
                        'speed': d.get('_speed_str', 'N/A'),
                        'eta': d.get('_eta_str', 'N/A'),
                    })
            elif d['status'] == 'finished':
                with progress_lock:
                    progress_data[task_id].update({
                        'status': 'processing',
                        'percent': 100,
                    })

        # ── yt-dlp options ────────────────────────────────────────────────────
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': True,
        }

        if audio_only:
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
                'format': (
                    f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]'
                    f'/bestvideo[height<={quality}]+bestaudio'
                    f'/best[height<={quality}]/best'
                ),
                'merge_output_format': 'mp4',
            })

        if subtitle:
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                # Correct extension after post-processing
                if audio_only:
                    filename = os.path.splitext(filename)[0] + '.mp3'
                else:
                    filename = os.path.splitext(filename)[0] + '.mp4'

                basename = os.path.basename(filename)
                filepath = os.path.join(output_path, basename)

                # File size
                file_size_mb = 0.0
                if os.path.exists(filepath):
                    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

                # ── Save history to DB inside app context ─────────────────────
                with app.app_context():
                    from database import db
                    from models import DownloadHistory
                    hist = DownloadHistory(
                        user_id=user_id,
                        video_title=info.get('title', 'Unknown Video'),
                        video_url=url,
                        thumbnail_url=info.get('thumbnail'),
                        quality='Audio (MP3)' if audio_only else f"{info.get('height', quality)}p",
                        file_format='audio' if audio_only else 'video',
                        file_size_mb=round(file_size_mb, 2),
                    )
                    db.session.add(hist)
                    db.session.commit()

            with progress_lock:
                progress_data[task_id].update({
                    'status': 'finished',
                    'filename': basename,
                    'title': info.get('title', 'Download complete'),
                    'percent': 100,
                })

        except Exception as exc:
            with progress_lock:
                progress_data[task_id].update({
                    'status': 'error',
                    'error': str(exc),
                })
