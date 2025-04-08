/* eslint-disable no-restricted-globals */

// This service worker can be customized!
// See https://developers.google.com/web/tools/workbox/modules
// for the list of available Workbox modules

const CACHE_NAME = 'formiq-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/static/js/main.chunk.js',
  '/static/js/0.chunk.js',
  '/static/js/bundle.js',
  '/manifest.json',
  '/logo192.png',
  '/logo512.png',
  '/favicon.ico'
];

// Install a service worker
self.addEventListener('install', (event) => {
  // Perform install steps
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
  self.skipWaiting();
});

// Cache and return requests
self.addEventListener('fetch', (event) => {
  // Skip cross-origin requests
  if (event.request.url.startsWith(self.location.origin)) {
    event.respondWith(
      caches.match(event.request)
        .then((response) => {
          // Cache hit - return response
          if (response) {
            return response;
          }
          
          return fetch(event.request).then(
            (response) => {
              // Check if we received a valid response
              if (!response || response.status !== 200 || response.type !== 'basic') {
                return response;
              }

              // Clone the response since we need to use it twice:
              // 1. to return it as the fetch response
              // 2. to put it in the cache
              const responseToCache = response.clone();

              // Don't cache API calls
              if (!event.request.url.includes('/api/')) {
                caches.open(CACHE_NAME)
                  .then((cache) => {
                    cache.put(event.request, responseToCache);
                  });
              }

              return response;
            }
          );
        })
    );
  }
});

// Update a service worker
self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
          return null;
        })
      );
    })
  );
  self.clients.claim();
});

// Handle push notifications (for future implementation)
self.addEventListener('push', (event) => {
  const data = event.data.json();
  const title = data.title || 'FormIQ';
  const options = {
    body: data.body || 'New notification from FormIQ',
    icon: '/logo192.png',
    badge: '/favicon.ico'
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow('/')
  );
}); 