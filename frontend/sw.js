/**
 * SEMS Progressive Web App (PWA) Service Worker
 * Feature 20: Offline-first caching strategy & background sync queue
 */

const CACHE_NAME = 'sems-pwa-v2.6.0';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/api.js',
    '/static/js/ui.js',
    '/static/js/charts.js',
    '/static/js/dashboard.js',
    '/static/js/sems_features.js',
    '/static/js/enterprise_features.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.log('PWA cache pre-fill deferred:', err);
            });
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Only cache GET requests, bypass API calls to allow live WebSocket and REST
    if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseClone);
                });
                return response;
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});
