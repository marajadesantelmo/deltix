const CACHE = 'deltix-v4';
const STATIC_ASSETS = ['/img/bot_icon.png'];

// Imágenes dinámicas que se actualizan en el servidor — nunca cachear
const DYNAMIC_IMGS = ['/img/marea.png', '/img/windguru.png'];

// Instalación: solo pre-cachear imágenes estáticas, nunca el HTML
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

// Activación: eliminar cachés viejas
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // No interceptar POSTs ni llamadas al backend
  if (e.request.method !== 'GET') return;
  if (['/chat', '/suggest', '/join', '/data-request'].some(p => url.pathname.startsWith(p))) return;

  // HTML (incluyendo '/') → siempre network-first, sin caché
  if (url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  // Imágenes dinámicas (marea, windguru) → siempre red, nunca caché
  if (DYNAMIC_IMGS.some(p => url.pathname === p)) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Imágenes estáticas y demás → cache-first
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return response;
      });
    })
  );
});
