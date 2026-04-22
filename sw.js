const CACHE_NAME = 'hermes-v3';
const urlsToCache = [
  '/login.html',
  '/ver_vehiculos.html',
  '/index.html',
  '/manifest.json',
  '/deprisa.png',
  '/ala.png',
  '/favicon.ico'
];

// Al instalar: limpiar cachés viejos y pre-cachear estáticos
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

// Al activar: eliminar cachés anteriores (borra entradas http cacheadas)
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Nunca interceptar: peticiones HTTP (solo HTTPS), métodos no-GET, ni llamadas API
  if (
    url.protocol !== 'https:' ||
    event.request.method !== 'GET' ||
    url.pathname.startsWith('/vehiculos') ||
    url.pathname.startsWith('/historial') ||
    url.pathname.startsWith('/preoperacional') ||
    url.pathname.startsWith('/admin') ||
    url.pathname.startsWith('/auth') ||
    url.pathname.startsWith('/uploads') ||
    url.pathname.startsWith('/proveedores')
  ) {
    return; // deja pasar sin interceptar
  }

  // Solo servir desde caché archivos estáticos conocidos
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
