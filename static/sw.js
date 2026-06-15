const CACHE_NAME = 'downloader-pwa-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/auth.js',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap'
];

// Install Event
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('SW: Pre-caching static app shell');
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('SW: Clearing old cache', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event
self.addEventListener('fetch', (e) => {
  // Do not intercept or cache API endpoints or actual video downloads
  if (e.request.url.includes('/api/') || e.request.url.includes('/file/')) {
    return;
  }
  
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      // Return cache, otherwise fetch from network
      return cachedResponse || fetch(e.request).catch(() => {
        // Fallback for document navigation if offline
        if (e.request.mode === 'navigate') {
          return caches.match('/');
        }
      });
    })
  );
});
