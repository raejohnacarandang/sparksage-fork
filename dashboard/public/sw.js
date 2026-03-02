const CACHE_NAME = "sparksage-v1";
const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/dashboard/analytics",
  "/dashboard/providers",
  "/dashboard/settings",
];

// Install — cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener("fetch", (event) => {
  // Skip non-GET and API/WebSocket requests
  if (
    event.request.method !== "GET" ||
    event.request.url.includes("/api/") ||
    event.request.url.includes("/ws/")
  ) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache fresh responses
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline fallback — return cached version
        return caches.match(event.request).then(
          (cached) => cached || caches.match("/dashboard")
        );
      })
  );
});