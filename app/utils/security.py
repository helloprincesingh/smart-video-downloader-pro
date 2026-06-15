import time
import re
from functools import wraps
from flask import request, jsonify

# In-memory rate limiting store: { ip: [timestamp1, timestamp2, ...] }
rate_limit_store = {}

def rate_limit(limit=15, period=60):
    """
    Decorator to rate limit incoming API calls by client IP address.
    limit: Maximum allowed requests in the time period
    period: Time period in seconds (default: 60)
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            now = time.time()
            
            # Clean up old timestamps
            if ip in rate_limit_store:
                rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < period]
            else:
                rate_limit_store[ip] = []
                
            if len(rate_limit_store[ip]) >= limit:
                return jsonify({'error': f'Rate limit exceeded. Max {limit} requests per {period}s.'}), 429
                
            rate_limit_store[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def is_valid_youtube_url(url):
    """
    Validates if a given URL is a YouTube video or playlist URL.
    """
    if not url:
        return False
        
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})?'
    )
    playlist_regex = r'[&?]list=([^#\&\?]+)'
    
    is_video = bool(re.match(youtube_regex, url))
    is_playlist = 'list=' in url
    
    return is_video or is_playlist
