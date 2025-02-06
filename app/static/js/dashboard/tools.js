// Make graphs object globally available
window.graphs = {};

// Initialize Chart.js graph
export function initializeGraph(containerId, type) {
    const canvas = document.querySelector(`#${containerId} canvas`);
    const ctx = canvas.getContext('2d');
    
    window.graphs[containerId] = new Chart(ctx, {
        type: type,
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Tool Life',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    tension: 0.1,
                    fill: true
                },
                {
                    label: 'Trendline',
                    data: [],
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Mean',
                    data: [],
                    borderColor: 'rgba(255, 206, 86, 1)',
                    borderWidth: 2,
                    borderDash: [2, 2],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Mean ± Std Dev',
                    data: [],
                    borderColor: 'rgba(255, 206, 86, 0.3)',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    fill: 1,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: false,
                        text: 'Reached Life',
                        color: '#fff'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#fff'
                    }
                },
                x: {
                    title: {
                        display: false,
                        text: 'Time',
                        color: '#fff'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#fff'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const datasetLabel = context.dataset.label;
                            const value = context.parsed.y;
                            if (datasetLabel === 'Tool Life') {
                                return `Life: ${value.toFixed(1)}`;
                            } else if (datasetLabel === 'Mean') {
                                return `Mean: ${value.toFixed(1)}`;
                            } else if (datasetLabel === 'Trendline') {
                                return `Trend: ${value.toFixed(1)}`;
                            }
                            return `${datasetLabel}: ${value.toFixed(1)}`;
                        }
                    }
                }
            }
        }
    });
}

// WebSocket connection and management
let ws = null;
const statusDiv = document.getElementById('connection-status');

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/dashboard/ws/tools`);
    console.log('tools ws', ws);
    
    ws.onopen = function() {
        statusDiv.className = 'hidden';
        // Send initial filter state if available
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
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = function() {
        statusDiv.textContent = 'Connection Error';
        statusDiv.className = 'fixed bottom-4 right-4 px-4 py-2 rounded-full text-white bg-red-500/100';
    };

    return ws;
}

function handleWebSocketMessage(event) {
    const response = JSON.parse(event.data);
    const { graphs, data } = response;
    
    // Update graph container
    const mainContent = document.querySelector('.p-2 > .mx-auto');
    
    // Save modal template
    const modalTemplate = mainContent.querySelector('#toolDetailsModal');
    
    // Clear main content but preserve modal
    mainContent.innerHTML = '';
    if (modalTemplate) {
        mainContent.appendChild(modalTemplate);
    }
    
    // Show no data message if no graphs
    if (!graphs || graphs.length === 0) {
        const noDataDiv = document.createElement('div');
        noDataDiv.className = 'text-center py-12';
        noDataDiv.innerHTML = '<p class="text-gray-400 text-lg">No tool life data available. Add tools and record tool life measurements to see graphs.</p>';
        mainContent.appendChild(noDataDiv);
        
        // Destroy any existing charts
        Object.values(window.graphs).forEach(chart => chart.destroy());
        window.graphs = {};
        return;
    }
    
    // Create new grid container
    const graphContainer = document.createElement('div');
    graphContainer.className = 'grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-4';
    mainContent.appendChild(graphContainer);
    
    const currentGraphs = new Set(Object.keys(window.graphs));
    const newGraphs = new Set(graphs.map(g => g.id));
    
    // Destroy removed graphs
    currentGraphs.forEach(graphId => {
        if (!newGraphs.has(graphId) && window.graphs[graphId]) {
            window.graphs[graphId].destroy();
            delete window.graphs[graphId];
        }
    });
    
    // Add/update all graphs
    graphs.forEach(graph => {
        // Create new graph element
        const graphElement = document.createElement('div');
        graphElement.className = 'bg-gray-800 rounded-lg shadow p-4 cursor-pointer hover:bg-gray-700 transition-colors graph-card';
        graphElement.dataset.graphId = graph.id;
        graphElement.innerHTML = `
            <h3 class="text-lg font-medium text-gray-300 mb-2">${graph.title}</h3>
            <div class="flex">
                <div class="flex-1 -mr-16">
                    <div id="${graph.id}" class="graph-container" data-type="${graph.type}">
                        <canvas></canvas>
                    </div>
                </div>
                <div class="text-sm font-mono text-gray-400 whitespace-nowrap pl-20 w-44" id="stats_${graph.id}">
                    <div>Slope: --</div>
                    <div>Mean: --</div>
                    <div>σ: ±--</div>
                </div>
            </div>
        `;
        graphContainer.appendChild(graphElement);
        initializeGraph(graph.id, graph.type);
    });

    // Setup click handlers for newly created graph cards
    setupGraphCardClickHandlers();
    
    // Update data for all current graphs
    Object.entries(data).forEach(([graphId, graphData]) => {
        const graph = window.graphs[graphId];
        if (graph) {
            // Update scales if provided
            if (graphData.scales) {
                graph.options.scales = {
                    ...graph.options.scales,
                    ...graphData.scales,
                    // Preserve grid and tick colors
                    ...(Object.fromEntries(
                        Object.entries(graphData.scales).map(([key, value]) => [
                            key,
                            {
                                ...value,
                                grid: { ...(value.grid || {}), color: 'rgba(255, 255, 255, 0.1)' },
                                ticks: { ...(value.ticks || {}), color: '#fff' }
                            }
                        ])
                    ))
                };
            }

            graph.data.labels = graphData.labels;
            // Tool life data
            graph.data.datasets[0].data = graphData.values;
            // Trendline
            graph.data.datasets[1].data = graphData.trendline;
            // Mean line
            const meanArray = Array(graphData.labels.length).fill(graphData.mean);
            graph.data.datasets[2].data = meanArray;
            // Standard deviation band
            graph.data.datasets[3].data = Array(graphData.labels.length).fill(graphData.mean + graphData.std);
            graph.data.datasets[3].data2 = Array(graphData.labels.length).fill(graphData.mean - graphData.std);
            
            // Update stats display
            const statsDiv = document.getElementById(`stats_${graphId}`);
            if (statsDiv) {
                const slope = (graphData.trendline[graphData.trendline.length - 1] - graphData.trendline[0]) / graphData.trendline.length;
                statsDiv.innerHTML = `
                    <div>Slope: ${slope.toFixed(2)}</div>
                    <div>Mean: ${graphData.mean.toFixed(2)}</div>
                    <div>σ: ±${graphData.std.toFixed(2)}</div>
                `;
            }
            
            graph.update();
        }
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
        card.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const graphId = card.dataset.graphId;
            const graphDiv = document.getElementById(graphId);
            if (graphDiv && window.graphs[graphId]) {
                const dateRange = {
                    startDate: localStorage.getItem('startDate'),
                    endDate: localStorage.getItem('endDate')
                };
                openToolModal(graphId, dateRange);
            } else {
                console.error('Graph element or data not found:', graphId);
            }
        });
    });
}

// Initialize components in the correct order
export function initializeComponents() {
    console.log('initialize components...');
    // Initialize graphs
    document.querySelectorAll('.graph-container').forEach(container => {
        const id = container.id;
        const type = container.dataset.type;
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

// Cleanup function
export function cleanup() {
    if (ws) {
        ws.close();
    }
}
