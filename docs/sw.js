// Service worker di PDF Suite. Rete per prima, cache come ripiego: con la rete l'app si aggiorna da sola,
// senza rete si apre dalla copia salvata. Per forzare un aggiornamento della cache cambiare VERSIONE.
const VERSIONE = "pdf-suite-1";
const FILE = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "icon-180.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSIONE).then((c) => c.addAll(FILE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== VERSIONE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const r = e.request;
  if (r.method !== "GET" || new URL(r.url).origin !== location.origin) return;
  e.respondWith(
    fetch(r).then((risposta) => {
      if (risposta.ok) {
        const copia = risposta.clone();
        caches.open(VERSIONE).then((c) => c.put(r, copia));
      }
      return risposta;
    }).catch(() => caches.match(r, { ignoreSearch: true }).then((c) => c || caches.match("index.html")))
  );
});
