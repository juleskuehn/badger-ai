

function sendNotification() {
  // Query the database for Items
  fetch('/get_random_item')
    .then(response => response.json())
    .then(item => {
      if (item.body === null) return;
      // Show the notification
      if ('Notification' in window) {
        if (Notification.permission === 'granted') {
          new Notification(item.title, {
            body: item.body,
            badge: item.badge,
            icon: item.icon,
            image: item.image,
            requireInteraction: item.requireInteraction,
          });
        } else if (Notification.permission !== 'denied') {
          Notification.requestPermission().then((permission) => {
            if (permission === 'granted') {
              new Notification(item.title, {
                body: item.body,
                badge: item.badge,
                icon: item.icon,
                image: item.image,
                requireInteraction: item.requireInteraction,
              });
            }
          });
        }
      }
    });
}

// Send a notification every minute
setInterval(sendNotification, 20 * 1000);
