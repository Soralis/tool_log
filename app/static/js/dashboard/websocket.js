

// WebSocket connection
export function connectWebSocket(socket, update_function, open_function = () => {}) {
    const statusDiv = document.getElementById('connection-status');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const websocket = new WebSocket(`${protocol}//${window.location.host}/dashboard/ws/${socket}`);

    websocket.onopen = function() {
        statusDiv.className = 'hidden';
        open_function(websocket)
    };    

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        update_function(data);
    };

    websocket.onclose = function() {
        statusDiv.textContent = 'Reconnecting...';
        statusDiv.className = 'fixed bottom-4 right-4 px-4 py-2 rounded-full text-white bg-yellow-500/100';
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000, socket, update_function);
    };

    websocket.onerror = function(error) {
        console.error("WebSocket error:", error);
    };

    return websocket
}
