/// <reference types="@sveltejs/kit" />
import { build, files, version } from '$service-worker';

// Static application shell only: versioned build assets plus static/ files.
// No protected API/SSR response is ever written to the cache, and no
// mutation is queued (no background sync, no IndexedDB).
const CACHE_NAME = `static-shell-${version}`;
const STATIC_SHELL = [...build, ...files];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(CACHE_NAME)
			.then((cache) => cache.addAll(STATIC_SHELL))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((names) =>
				Promise.all(
					names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
				)
			)
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	if (event.request.method !== 'GET') return;
	event.respondWith(caches.match(event.request).then((cached) => cached ?? fetch(event.request)));
});
