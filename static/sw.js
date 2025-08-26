// BoatraceOpenAPI PWA Service Worker
// キャッシュ最適化とオフライン対応

const CACHE_NAME = 'boatrace-v1.0.0';
const STATIC_CACHE = 'boatrace-static-v1.0.0';
const API_CACHE = 'boatrace-api-v1.0.0';

// キャッシュするリソース
const STATIC_RESOURCES = [
  '/',
  '/static/manifest.json',
  '/static/sw.js',
  '/test'
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/races',
  '/api/cache/stats',
  '/api/accuracy/report'
];

// Install event - キャッシュ初期化
self.addEventListener('install', event => {
  console.log('[SW] Install event');
  
  event.waitUntil(
    Promise.all([
      // Static resources cache
      caches.open(STATIC_CACHE).then(cache => {
        console.log('[SW] Caching static resources');
        return cache.addAll(STATIC_RESOURCES);
      }),
      
      // API cache initialization
      caches.open(API_CACHE).then(cache => {
        console.log('[SW] API cache initialized');
        return Promise.resolve();
      })
    ]).then(() => {
      console.log('[SW] Installation complete');
      return self.skipWaiting();
    })
  );
});

// Activate event - 古いキャッシュ削除
self.addEventListener('activate', event => {
  console.log('[SW] Activate event');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && 
              cacheName !== API_CACHE && 
              cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - リクエスト処理
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle different types of requests
  if (url.pathname.startsWith('/api/')) {
    // API requests - Network First with cache fallback
    event.respondWith(handleApiRequest(request));
  } else if (url.pathname.startsWith('/static/') || 
             url.pathname === '/' || 
             url.pathname === '/test') {
    // Static resources - Cache First
    event.respondWith(handleStaticRequest(request));
  } else if (url.pathname.startsWith('/predict/')) {
    // Prediction pages - Network First
    event.respondWith(handleNetworkFirst(request));
  }
});

// API request handler - Network First
async function handleApiRequest(request) {
  const cache = await caches.open(API_CACHE);
  const url = new URL(request.url);
  
  try {
    // Try network first
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      // Cache successful responses (except real-time data)
      if (!url.pathname.includes('/verify') && 
          !url.pathname.includes('/alert')) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    }
    
    // Network failed, try cache
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('[SW] Serving from API cache:', request.url);
      return cachedResponse;
    }
    
    // No cache available, return error response
    return new Response(JSON.stringify({
      success: false,
      error: 'Network unavailable',
      cached: false
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.log('[SW] Network error, checking cache:', error);
    
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('[SW] Serving from API cache:', request.url);
      return cachedResponse;
    }
    
    return new Response(JSON.stringify({
      success: false,
      error: 'Service unavailable',
      cached: false
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Static request handler - Cache First
async function handleStaticRequest(request) {
  const cache = await caches.open(STATIC_CACHE);
  
  // Try cache first
  const cachedResponse = await cache.match(request);
  if (cachedResponse) {
    console.log('[SW] Serving from static cache:', request.url);
    return cachedResponse;
  }
  
  // Cache miss, fetch from network
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Static resource unavailable:', error);
    
    // Return offline page for main routes
    if (request.url.endsWith('/')) {
      return new Response(
        createOfflinePage(),
        { headers: { 'Content-Type': 'text/html' } }
      );
    }
    
    return new Response('Resource unavailable', { status: 503 });
  }
}

// Network First handler
async function handleNetworkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network unavailable for:', request.url);
    
    // Return offline page
    return new Response(
      createOfflinePage(),
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

// Create offline page
function createOfflinePage() {
  return `
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>オフライン - BoatraceOpenAPI</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }
            .offline-container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .icon {
                font-size: 4em;
                margin-bottom: 20px;
            }
            h1 { color: #666; }
            p { color: #999; }
            .retry-btn {
                background: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                margin-top: 20px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="icon">🚫</div>
            <h1>オフライン</h1>
            <p>インターネット接続を確認してください</p>
            <p>キャッシュされたデータを表示しています</p>
            <button class="retry-btn" onclick="location.reload()">再試行</button>
        </div>
    </body>
    </html>
  `;
}

// Background sync for predictions
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync-predictions') {
    console.log('[SW] Background sync: predictions');
    event.waitUntil(syncPredictions());
  }
});

// Sync predictions when online
async function syncPredictions() {
  try {
    const response = await fetch('/api/accuracy/verify');
    if (response.ok) {
      console.log('[SW] Background prediction sync successful');
    }
  } catch (error) {
    console.log('[SW] Background sync failed:', error);
  }
}

// Push notifications (future feature)
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    console.log('[SW] Push notification:', data);
    
    const options = {
      body: data.body || '新しい予想結果が利用可能です',
      icon: '/static/icon-192.png',
      badge: '/static/icon-192.png',
      tag: 'prediction-update',
      requireInteraction: false,
      actions: [
        {
          action: 'view',
          title: '確認する'
        },
        {
          action: 'dismiss',
          title: '閉じる'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(
        data.title || 'BoatraceOpenAPI', 
        options
      )
    );
  }
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

console.log('[SW] Service Worker loaded successfully');