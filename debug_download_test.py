from app import app
from services.download_service import DownloadService, progress_data, progress_lock
import time, json

url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
print('Starting download for', url)
task_id=DownloadService.start_download_thread(app, url, quality=360, audio_only=False)
print('Task ID:', task_id)
for i in range(180):
    with progress_lock:
        t = progress_data.get(task_id, {})
    print(f"[{i}]", json.dumps({
        'status': t.get('status'),
        'percent': t.get('percent'),
        'error': t.get('error'),
        'title': t.get('title'),
        'filename': t.get('filename')
    }, indent=2))
    if t.get('status') in ('finished','error'):
        break
    time.sleep(1)
print('Done')
