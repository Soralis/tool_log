async function openOrderModal(orderId) {
    const modal = document.getElementById('orderDetailsModal');
    let order = {}
    if (!modal) {
        console.error('Modal element not found in openOrderModal');
        return;
    }

    if (orderId) {
        const response = await fetch(`/dashboard/orders/order_details/${orderId}`);
        order = await response.json(); 
        window.order = order;
        console.log(window.order)
    }

    document.getElementById('orderId').innerText = order.id ? order.id : null;
    document.getElementById('modalTitle').innerText = order.order_number ? `Order Details - ${order.tool.name}` : 'Create New (World) Order';
    document.getElementById('order-number').value = order.order_number || '';

    document.getElementById('quantity').value = order.quantity || '';
    document.getElementById('gross-price').value = order.gross_price || '';
    document.getElementById('tool-price').value = order.tool_price || '';
    document.getElementById('order-date').innerText = `Order Date: ${order.order_date}` || null;
    document.getElementById('estimated-delivery-date').value = order.estimated_delivery_date || null;

    document.getElementById('order-number-display').innerText = order.order_number || '';
    document.getElementById('description-display').innerText = order.description || ' - ';
    document.getElementById('quantity-display').innerText = order.quantity || '';
    document.getElementById('gross-price-display').innerText = order.gross_price || '';
    document.getElementById('estimated-delivery-date-display').innerText = order.estimated_delivery_date || 'None given';
    document.getElementById('tool-price-display').innerText = order.tool_price || '';

    if (orderId) {
        document.getElementById('fulfilled').innerHTML = `<span class="${order.fulfilled ? 'text-green-500 font-bold' : 'text-red-500 font-bold'}">${order.fulfilled ? 'Order Fulfilled' : 'Delivery Pending...'}</span>`;
        console.log(`edit order`, order);
        setToolCard(order.tool)
    } else {
        document.getElementById('fulfilled').innerHTML = `<span></span>`;
        document.getElementById('tool-card').innerHTML = '<h2 class="text-lg font-semibold">Select Tool</h2> <p class="text-sm">(click here)</p>';
        enableEdit()
    }
    
    modal.style.removeProperty('display');
    modal.classList.remove('hidden');
    toggleBodyScroll(true);
}

function closeOrderModal() {
    const modal = document.getElementById('orderDetailsModal');
    if (modal) {
        modal.classList.add('hidden');
        toggleBodyScroll(false);
        disableEdit();
    } else {
        console.error('Modal element not found in closeOrderModal');
    }
}

// Function to toggle body scroll
function toggleBodyScroll(lock) {
    if (lock) {
        document.body.classList.add('modal-open');
    } else {
        document.body.classList.remove('modal-open');
    }
}


async function loadToolTypes(tool) {
    const toolTypeSelect = document.getElementById('tool-type-select');
    toolTypeSelect.innerHTML = '<option>Loading...</option>';

    try {
        const response = await fetch('/dashboard/orders/tool_types');
        const toolTypes = await response.json();

        toolTypeSelect.innerHTML = '';
        toolTypes.forEach(toolType => {
            const option = document.createElement('option');
            option.value = toolType.id;
            option.textContent = toolType.name;
            toolTypeSelect.appendChild(option);
        });

        if (tool) {
            tool_id = tool.id;
            tool_type_id = tool.tool_type_id
        } else {
            tool_type_id = null;
            tool_id = null;
        }

        if (tool_type_id) {
            toolTypeSelect.value = tool_type_id;
        }

        // Load tools for the first tool type
        loadTools(tool_type_id, tool_id);
    } catch (error) {
        console.error('Error loading tool types:', error);
        toolTypeSelect.innerHTML = '<option>Error loading tool types</option>';
    }
}

async function loadTools(toolTypeId, selectedToolId) {
    console.log("loadTools toolTypeId:", toolTypeId, tool_id);
    const toolSelect = document.getElementById('tool-select');
    toolSelect.innerHTML = '<option>Loading...</option>';

    let url = '/dashboard/orders/tools';
    if (toolTypeId) {
        url += `?tool_type_id=${toolTypeId}`;
    }

    try {
        const response = await fetch(url);
        const tools = await response.json();

        toolSelect.innerHTML = '';
        tools.forEach(tool => {
            const option = document.createElement('option');
            option.value = tool.id;
            option.textContent = tool.name;
            toolSelect.appendChild(option);
        });

        if (selectedToolId) {
            toolSelect.value = selectedToolId;
        }
    } catch (error) {
        console.error('Error loading tools:', error);
        toolSelect.innerHTML = '<option>Error loading tools</option>';
    }
}

async function selectTool() {
    const toolId = document.getElementById('tool-select').value;

    try {
        const response = await fetch(`/dashboard/orders/tools/${toolId}`);
        const tool = await response.json();

        // Set the selected tool ID in a data attribute of the modal
        document.getElementById('orderDetailsModal').dataset.toolId = tool.id;

        setToolCard(tool)
        closeToolSelectModal();
    } catch (error) {
        console.error('Error loading tool details:', error);
        alert('Error loading tool details. Please check the console for details.');
    }
}


function setToolCard(tool) {
    window.order.tool = tool;
    console.log(window.order)
    document.getElementById('tool-card').innerHTML = `
        <div class="grid grid-cols-2 gap-2">
            <h2 class="text-lg font-semibold col-span-2">${tool.name} <span class="text-sm">(${tool.tool_type}) - ${tool.number} ${tool.regrind ? ' - Regrind' : ''}</span></h2>
            <hr class="col-span-2 bg-slate-300" />
            <div><p>Manufacturer: ${tool.manufacturer}</p></div>
            <div><p>Current Inventory: ${tool.inventory}</p></div>
            <div><p>CPN Number: ${tool.cpn_number}</p></div>
            <div><p>ERP Number: ${tool.erp_number}</p></div>
            <hr class="col-span-2 bg-gray-700" />
            <div class="col-span-2 text-sm"><p>${tool.description}</p></div>
        </div>
    `;
    document.getElementById('tool-card-display').innerHTML = `
        <div class="grid grid-cols-2 gap-2">
            <h2 class="text-lg font-semibold col-span-2">${tool.name} <span class="text-sm">(${tool.tool_type}) - ${tool.number} ${tool.regrind ? ' - Regrind' : ''}</span></h2>
            <hr class="col-span-2 bg-slate-300" />
            <div><p>Manufacturer: ${tool.manufacturer}</p></div>
            <div><p>Current Inventory: ${tool.inventory}</p></div>
            <div><p>CPN Number: ${tool.cpn_number}</p></div>
            <div><p>ERP Number: ${tool.erp_number}</p></div>
            <hr class="col-span-2 bg-gray-700" />
            <div class="col-span-2 text-sm"><p>${tool.description}</p></div>
        </div>
    `;
}

async function saveOrder() {
    const orderId = document.getElementById('orderId').innerText;
    const orderNumber = document.getElementById('order-number').value;
    const quantity = document.getElementById('quantity').value;
    const grossPrice = document.getElementById('gross-price').value;
    const toolPrice = document.getElementById('tool-price').value;
    const orderDate = document.getElementById('order-date').value;
    const estimatedDeliveryDate = document.getElementById('estimated-delivery-date').value;

    // Get the selected tool ID from the data attribute
    const toolId = document.getElementById('orderDetailsModal').dataset.toolId;

    const orderData = {
        tool_id: toolId,
        order_number: orderNumber,
        quantity: quantity,
        gross_price: grossPrice,
        tool_price: toolPrice,
        order_date: orderDate,
        estimated_delivery_date: estimatedDeliveryDate
    };

    const url = orderId ? `/dashboard/orders/updateOrder/${orderId}` : '/dashboard/orders/createOrder';
    const method = orderId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });

        if (response.ok) {
            closeOrderModal();
            // Reload the page to refresh the order list
            window.location.reload();
        } else {
            console.error('Error saving order:', response.status);
            alert('Error saving order. Please check the console for details.');
        }
    } catch (error) {
        console.error('Error saving order:', error);
        alert('Error saving order. Please check the console for details.');
    }
}

function openToolSelectModal() {
    // if there is an order, select the order.tool
    const toolSelectModal = document.getElementById('toolSelectModal');
    toolSelectModal.classList.remove('hidden');

    const orderId = document.getElementById('orderId').innerText;

    if (orderId) {
        order = window.order;
        if (order) {
            loadToolTypes(order.tool);
        } else {
            console.error('Order not found in window.order');
            loadToolTypes(null);
        }
    } else {
        loadToolTypes(null);
    }

    document.getElementById('tool-type-select').addEventListener('change', function() {
        const toolTypeId = this.value;
        const selectedToolId = document.getElementById('orderDetailsModal').dataset.toolId;
        if (toolTypeId) {
            loadTools(toolTypeId, selectedToolId);
        }
    });
}

function closeToolSelectModal() {
    const toolSelectModal = document.getElementById('toolSelectModal');
    toolSelectModal.classList.add('hidden');
}

function enableEdit() {
    document.getElementById('editButton').classList.add('hidden');
    document.getElementById('saveButton').classList.remove('hidden');

    document.getElementById('order-number-display').classList.add('hidden');
    document.getElementById('order-number').classList.remove('hidden');

    document.getElementById('description-display').classList.add('hidden');
    document.getElementById('description').classList.remove('hidden');

    document.getElementById('quantity-display').classList.add('hidden');
    document.getElementById('quantity').classList.remove('hidden');

    document.getElementById('gross-price-display').classList.add('hidden');
    document.getElementById('gross-price').classList.remove('hidden');

    document.getElementById('estimated-delivery-date-display').classList.add('hidden');
    document.getElementById('estimated-delivery-date').classList.remove('hidden');

    document.getElementById('tool-price-display').classList.add('hidden');
    document.getElementById('tool-price').classList.remove('hidden');

    document.getElementById('tool-card-display').classList.add('hidden');
    document.getElementById('tool-card').classList.remove('hidden');
}

function disableEdit() {
    document.getElementById('editButton').classList.remove('hidden');
    document.getElementById('saveButton').classList.add('hidden');

    document.getElementById('order-number-display').classList.remove('hidden');
    document.getElementById('order-number').classList.add('hidden');

    document.getElementById('description-display').classList.remove('hidden');
    document.getElementById('description').classList.add('hidden');

    document.getElementById('quantity-display').classList.remove('hidden');
    document.getElementById('quantity').classList.add('hidden');

    document.getElementById('gross-price-display').classList.remove('hidden');
    document.getElementById('gross-price').classList.add('hidden');

    document.getElementById('estimated-delivery-date-display').classList.remove('hidden');
    document.getElementById('estimated-delivery-date').classList.add('hidden');

    document.getElementById('tool-price-display').classList.remove('hidden');
    document.getElementById('tool-price').classList.add('hidden');

    document.getElementById('tool-card').classList.add('hidden');
    document.getElementById('tool-card-display').classList.remove('hidden');
}
