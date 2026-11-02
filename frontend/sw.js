// Guarda la app en el teléfono para que abra al instante y funcione sin internet.
// Los datos (/api) NO pasan por aquí: la app los guarda por su cuenta.
const V = "gimnasio-v2";
const BASE = ["/", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(BASE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// Primero lo guardado (rápido); en segundo plano se actualiza para la próxima vez que abras.
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;
  e.respondWith(caches.open(V).then(async c => {
    const guardado = await c.match(r, { ignoreSearch: true });
    const red = fetch(r).then(x => { if (x.ok) c.put(r, x.clone()); return x; }).catch(() => guardado);
    return guardado || red;
  }));
});
