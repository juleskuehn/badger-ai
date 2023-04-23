self.addEventListener('install', event => {
    console.log('Service worker installing...');
});

self.addEventListener('activate', event => {
    console.log('Service worker activating...');
});

self.addEventListener('fetch', event => {
    console.log('Fetching:', event.request.url);
});

self.registration.showNotification('Hello!', {
    body: 'This is a notification from your service worker.',
    icon: '/path/to/icon.png'
});

console.log('Hello from service worker');