// Global object to store ECharts instances
window.echartsInstances = {};

// WebSocket connection variable
let ws = null;
const statusDiv = document.getElementById('connection-status');

// Function to initialize an individual EChart
export function initializeGraph(containerId, chartType) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Initialize chart using ECharts (assumed to be loaded globally)
    const chartInstance = echarts.init(container);
    
    // Set an initial empty option (to be updated later by backend data via websocket)
    const initialOption = {
        title: { text: '' },
        tooltip: {},
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: []
    };
    chartInstance.setOption(initialOption);
    
    window.echartsInstances[containerId] = chartInstance;
}

// Function to update an existing EChart instance with new configuration (option)
// The newOption is expected to be a complete ECharts option object provided by the backend.
function updateChart(chartInstance, newOption, chartId) {
    // Add better date formatting to the x-axis
    if (newOption && newOption.xAxis && newOption.xAxis.axisLabel) {
        newOption.xAxis.axisLabel.formatter = function(value) {
            // Format date to MM/DD HH:MM
            const date = new Date(value);
            return date.toLocaleDateString('en-US', { 
                month: 'numeric', 
                day: 'numeric'
            });
        };
    }
    
    // Ensure the chart uses the full container width and height
    newOption.grid = {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '8%',
        containLabel: true
    };
    
    // Apply the chart options
    chartInstance.setOption(newOption, true);
    chartInstance.resize();
}

// Function to handle incoming WebSocket messages and update charts accordingly
function handleWebSocketMessage(event) {
    const response = JSON.parse(event.data);
    const { graphs, data } = response;
    
    // If no graphs are present, clear out any existing charts
    if (!graphs || graphs.length === 0) {
        Object.values(window.echartsInstances).forEach(instance => instance.dispose());
        window.echartsInstances = {};
        return;
    }
    
    // First, make sure all chart containers exist in the DOM
    createChartContainers(graphs);
    
    // Iterate over each graph received from the backend
    graphs.forEach(graph => {
        let chartInstance = window.echartsInstances[graph.id];
        
        // If the chart instance doesn't exist, create it
        if (!chartInstance) {
            initializeGraph(graph.id, graph.type);
            chartInstance = window.echartsInstances[graph.id];
        }
        
        // Update the chart with the data
        if (chartInstance && data[graph.id]) {
            updateChart(chartInstance, data[graph.id], graph.id);
        }
    });

    setupGraphCardClickHandlers()
}

// Function to create chart containers if they don't already exist
function createChartContainers(graphs) {
    // Target the main grid container specifically, not any grid in filter modals
    const graphCardsContainer = document.querySelector('.p-2 > .mx-auto > .grid');
    if (!graphCardsContainer) {
        console.error('Main chart grid container not found!');
        return;
    }
    
    // Get existing container IDs
    const existingContainers = Array.from(document.querySelectorAll('.graph-container')).map(el => el.id);
    
    // Create containers for graphs that don't have one
    graphs.forEach(graph => {
        if (existingContainers.includes(graph.id)) return;
        
        // Create the graph card
        const graphCard = document.createElement('div');
        graphCard.className = 'bg-gray-800 rounded-lg shadow p-4 cursor-pointer hover:bg-gray-700 transition-colors graph-card';
        graphCard.setAttribute('data-graph-id', graph.id);
        
        // Add title
        const title = document.createElement('h3');
        title.className = 'text-lg font-medium text-gray-300 mb-2';
        title.textContent = graph.title;
        graphCard.appendChild(title);
        
        // Add flex container
        const flexDiv = document.createElement('div');
        flexDiv.className = 'flex';
        
        // Add chart container
        const chartContainer = document.createElement('div');
        chartContainer.className = 'flex-1';
        
        const graphContainer = document.createElement('div');
        graphContainer.className = 'graph-container';
        graphContainer.id = graph.id;
        graphContainer.setAttribute('data-type', graph.type || 'line');
        
        chartContainer.appendChild(graphContainer);
        flexDiv.appendChild(chartContainer);
        graphCard.appendChild(flexDiv);
        
        // Add to DOM
        graphCardsContainer.appendChild(graphCard);
    });
}

// WebSocket connection and management
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/dashboard/ws/tools`);
    
    ws.onopen = function() {
        statusDiv.classList.add('hidden');
        // Optionally, send initial state if needed
        if (ws.readyState === WebSocket.OPEN) {
            const startDate = localStorage.getItem('startDate');
            const endDate = localStorage.getItem('endDate');
            const selectedOperations = localStorage.getItem('selectedOperations');
            const selectedProducts = localStorage.getItem('selectedProducts');
            if (startDate || endDate || selectedOperations || selectedProducts) {
                ws.send(JSON.stringify({
                    startDate: startDate,
                    endDate: endDate,
                    selectedOperations: JSON.parse(selectedOperations || '[]'),
                    selectedProducts: JSON.parse(selectedProducts || '[]')
                }));
            }
        }
    };
    
    ws.onmessage = handleWebSocketMessage;
    
    ws.onclose = function() {
        statusDiv.textContent = 'Reconnecting...';
        statusDiv.className = 'fixed bottom-4 right-4 px-4 py-2 rounded-full text-white bg-yellow-500/100';
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
    };
    
    ws.onerror = function() {
        statusDiv.textContent = 'Connection Error';
        statusDiv.className = 'fixed bottom-4 right-4 px-4 py-2 rounded-full text-white bg-red-500/100';
    };
}

// Handle filter changes from any source
function handleFilterChange(event) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        const filterData = {
            startDate: event.detail?.startDate || localStorage.getItem('startDate') || null,
            endDate: event.detail?.endDate || localStorage.getItem('endDate') || null,
            selectedOperations: event.detail?.selectedOperations || 
                (localStorage.getItem('selectedOperations') ? JSON.parse(localStorage.getItem('selectedOperations')) : []),
            selectedProducts: event.detail?.selectedProducts || 
                (localStorage.getItem('selectedProducts') ? JSON.parse(localStorage.getItem('selectedProducts')) : [])
        };
        console.log('Sending filter data to websocket:', filterData);
        ws.send(JSON.stringify(filterData));
    }
}

// Handle graph card clicks
function setupGraphCardClickHandlers() {
    // Wait for openToolModal to be available
    if (typeof window.openToolModal !== 'function') {
        console.warn('openToolModal not available yet, retrying in 100ms...');
        setTimeout(setupGraphCardClickHandlers, 100);
        return;
    }
    document.querySelectorAll('.graph-card').forEach(card => {
        if (!card.dataset.listenerAdded) {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const graphId = card.dataset.graphId;
                const dateRange = {
                    startDate: localStorage.getItem('startDate'),
                    endDate: localStorage.getItem('endDate')
                };
                openToolModal(graphId, dateRange);
            });
            card.dataset.listenerAdded = "true";
        }
    });
}

// Function to initialize ECharts on all graph containers in the page
export function initializeComponents() {
    // Initialize charts for each container with class "graph-container"
    document.querySelectorAll('.graph-container').forEach(container => {
        const id = container.getAttribute('id');
        const type = container.getAttribute('data-type') || 'line';
        initializeGraph(id, type);
    });

    // Setup graph card click handlers
    setupGraphCardClickHandlers();

    // Listen for filter changes
    document.addEventListener('filterChanged', handleFilterChange);
    document.addEventListener('dateRangeChanged', handleFilterChange);

    // Start WebSocket connection
    connectWebSocket();
}

// Cleanup function to close WebSocket connection on page unload
export function cleanup() {
    if (ws) {
        ws.close();
    }
    // Dispose all ECharts instances
    Object.values(window.echartsInstances).forEach(instance => instance.dispose());
    window.echartsInstances = {};
}
