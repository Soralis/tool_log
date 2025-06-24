import { connectWebSocket } from '/static/js/dashboard/websocket.js';

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
    const chartInstance = echarts.init(container, null, { renderer: 'svg' });
    
    // Set an initial empty option (to be updated later by backend data via websocket)
    const initialOption = {
        title: { text: '' },
        tooltip: {},
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [],
        aria: {
            enabled: true,
            decal: {
                show: true
            }
        }
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
function handleWebSocketMessage(response) {
    const { graphs, data } = response;
    
    // First, make sure all chart containers exist in the DOM
    createChartContainers(graphs);
    
    // Iterate over each graph received from the backend
    graphs.forEach(graph => {
        // let chartInstance = window.echartsInstances[graph.id];
        
        // If the chart instance doesn't exist, create it
        // if (!chartInstance) {
        initializeGraph(graph.id, graph.type);
        let chartInstance = window.echartsInstances[graph.id];
        // }
        
        // Update the chart with the data
        if (chartInstance && data[graph.id]) {
            updateChart(chartInstance, data[graph.id], graph.id);
        }
    });

    setupGraphCardClickHandlers()
}

function onWebsocketOpen(websocket) {
    const startDate = localStorage.getItem('startDate');
    const endDate = localStorage.getItem('endDate');
    const selectedOperations = localStorage.getItem('selectedOperations');
    const selectedProducts = localStorage.getItem('selectedProducts');
    if (startDate || endDate || selectedOperations || selectedProducts) {
        websocket.send(JSON.stringify({
            startDate: startDate,
            endDate: endDate,
            selectedOperations: JSON.parse(selectedOperations || '[]'),
            selectedProducts: JSON.parse(selectedProducts || '[]')
        }));
    }
}

// Function to create chart containers if they don't already exist
function createChartContainers(graphs) {
    // Target the main grid container specifically
    const graphCardsContainer = document.querySelector('.p-2 > .mx-auto > .grid');
    if (!graphCardsContainer) {
        console.error('Main chart grid container not found!');
        return;
    }
    
    // Rebuild the graph cards container in the same order as the graphs received from the server
    const newCards = graphs.map(graph => {
        // Try to find an existing graph card by its data-graph-id
        let existingCard = document.querySelector(`.graph-card[data-graph-id="${graph.id}"]`);

        if (existingCard) {return existingCard;}

        // Create a new graph card if it doesn't exist
        const graphCard = document.createElement('div');
        graphCard.className = 'bg-stone-800 rounded-lg shadow p-4 cursor-pointer hover:bg-stone-700 transition-colors graph-card';
        graphCard.setAttribute('data-graph-id', graph.id);
        
        // Add title
        const title = document.createElement('h3');
        title.className = 'text-lg font-medium text-stone-300 mb-2';
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
        return graphCard;
    });
    
    // Clear the existing container and append cards in the correct order.
    graphCardsContainer.innerHTML = '';
    newCards.forEach(card => {
        graphCardsContainer.appendChild(card);
    });
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
                // Extract numeric ID from the tool_X format
                const numericId = graphId.split('_')[1];
                // Build URL with date range parameters
                const params = new URLSearchParams({
                    start_date: localStorage.getItem('startDate') || '',
                    end_date: localStorage.getItem('endDate') || '',
                    selected_operations: localStorage.getItem('selectedOperations') || '',
                    selected_products: localStorage.getItem('selectedProducts') || ''
                });
                openToolModal(`api/toolLifes/${numericId}/details`, params)
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
    ws = connectWebSocket('toolLifes', handleWebSocketMessage, onWebsocketOpen);
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
