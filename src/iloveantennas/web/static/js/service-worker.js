const CACHE_NAME = "antennasim-cache-v9";
const OFFLINE_URLS = [
  "/",
  "/static/css/style.css",
  "/static/js/app.core.js",
  "/static/js/app.events.js",
  "/static/js/app.sim.core.js",
  "/static/js/app.simulation.js",
  "/static/js/app.ui.js",
  "/static/js/engine.theme.js",
  "/static/js/renderer.core.js",
  "/static/js/renderer.antenna.js",
  "/static/js/renderer.field.js",
  "/static/js/renderer.radiation.js",
  "/static/js/renderer.camera.js",
  "/static/js/renderer.settings.js",
  "/static/js/charts.core.js",
  "/static/js/charts.smith.js",
  "/static/js/charts.radiation.js",
  "/static/js/charts.sparams.js",
  "/static/js/charts.modal.js"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(OFFLINE_URLS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          return null;
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET") {
    return;
  }
  if (url.origin !== self.location.origin) {
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    return;
  }
  event.respondWith(
    fetch(request).then(networkResponse => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== "basic") {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(request, responseToCache);
        });
        return networkResponse;
    }).catch(() => {
      return caches.match(request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        if (url.pathname === "/") {
          return caches.match("/");
        }
        return new Response("Offline", { status: 503, statusText: "Offline" });
      });
    })
  );
});
