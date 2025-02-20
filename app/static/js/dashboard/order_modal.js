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
    } else {

    }

    document.getElementById('orderId').innerText = order.id ? order.id : null;
    document.getElementById('modalTitle').innerText = order.order_number ? `Order Details - ${order.tool.name}` : 'Create New (World) Order';

    document.getElementById('order-number').value = order.order_number || '';
    document.getElementById('order-number-display').innerText = order.order_number || '';

    document.getElementById('quantity').value = order.quantity || '';
    document.getElementById('quantity-display').innerText = order.quantity || '';

    document.getElementById('gross-price').value = order.gross_price || '';
    document.getElementById('gross-price-display').innerText = order.gross_price || '';
    
    document.getElementById('tool-price').value = order.tool_price || '';
    document.getElementById('tool-price-display').innerText = order.tool_price || '';

    document.getElementById('order-date').innerText = `Order Date: ${order.order_date}` || null;
    document.getElementById('order-date').value = order.order_date

    document.getElementById('estimated-delivery-date').value = order.estimated_delivery_date || null;
    document.getElementById('estimated-delivery-date-display').innerText = order.estimated_delivery_date || 'None given';

    document.getElementById('tracking-number').value = order.tracking_number || '';
    document.getElementById('tracking-number-display').innerText = order.tracking_number || ' - ';

    document.getElementById('shipping-company').value = order.shipping_company || '';
    document.getElementById('shipping-company-display').innerText = order.shipping_company || ' - ';

    const deliveriesList = document.getElementById('deliveries-list').getElementsByTagName('tbody')[0];
    deliveriesList.innerHTML = ''; // Clear existing table rows

    const notesList = document.getElementById('notes-list').getElementsByTagName('tbody')[0];
    notesList.innerHTML = ''; // Clear existing table rows

    if (orderId && order.delivery_notes) {
        order.delivery_notes.forEach(delivery => {
            const row = deliveriesList.insertRow();
            const dateCell = row.insertCell();
            const quantityCell = row.insertCell();
            const notesCell = row.insertCell();

            const deliveryDate = new Date(delivery.delivery_date).toLocaleDateString();
            dateCell.textContent = deliveryDate;
            quantityCell.textContent = delivery.quantity;
            notesCell.textContent = delivery.notes;
        });
    } else {
        const row = deliveriesList.insertRow();
        const noDeliveriesCell = row.insertCell();
        noDeliveriesCell.colSpan = 3;
        noDeliveriesCell.textContent = 'No deliveries yet.';
    }

    if (orderId && order.notes) {
        order.notes.forEach(note => {
            const row = notesList.insertRow();
            const dateCell = row.insertCell();
            const notesCell = row.insertCell();

            const noteDate = new Date(note.createt_at).toLocaleDateString();
            dateCell.textContent = noteDate;
            notesCell.textContent = note.note;
        });
    } else {
        const row = notesList.insertRow();
        const nonotesCell = row.insertCell();
        nonotesCell.colSpan = 3;
        nonotesCell.textContent = 'No notes.';
    }

    if (orderId) {
        document.getElementById('fulfilled').innerHTML = `<span class="${order.fulfilled ? 'text-green-500 font-bold' : 'text-red-500 font-bold'}">${order.fulfilled ? 'Order Fulfilled' : 'Delivery Pending...'}</span>`;
        document.getElementById('add-delivery-button').classList.remove('hidden');
        setToolCard(order.tool);
    } else {
        document.getElementById('fulfilled').innerHTML = `<span></span>`;
        document.getElementById('tool-card').innerHTML = '<h2 class="text-lg font-semibold">Select Tool</h2> <p class="text-sm">(click here)</p>';
        document.getElementById('add-delivery-button').classList.add('hidden');
        document.getElementById('orderId').innerText = null
        enableEdit();
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

function openDeliveryModal() {
    const deliveryModal = document.getElementById('deliveryModal');
    if (deliveryModal) {
        const delivered = window.order.delivery_notes ? window.order.delivery_notes.reduce((sum, delivery) => sum + delivery.quantity, 0) : 0;
        const quantity = window.order.quantity;

        deliveryModal.dataset.delivered = delivered;
        deliveryModal.dataset.quantity = quantity;

        const deliveredQuantityInput = document.getElementById('delivered_quantity');
        deliveredQuantityInput.min = -delivered;
        deliveredQuantityInput.max = quantity - delivered;

        deliveredQuantityInput.addEventListener('blur', function() {
            let value = parseInt(deliveredQuantityInput.value);
            if (isNaN(value)) {
                deliveredQuantityInput.value = 0;
            } else if (value < parseInt(deliveredQuantityInput.min)) {
                deliveredQuantityInput.value = deliveredQuantityInput.min;
            } else if (value > parseInt(deliveredQuantityInput.max)) {
                deliveredQuantityInput.value = deliveredQuantityInput.max;
            }
        });

        deliveryModal.style.removeProperty('display');
        deliveryModal.classList.remove('hidden');
        toggleBodyScroll(true);
    } else {
        console.error('Delivery modal element not found');
    }
}

function closeDeliveryModal() {
    const deliveryModal = document.getElementById('deliveryModal');
    if (deliveryModal) {
        deliveryModal.classList.add('hidden');
        toggleBodyScroll(false);
    } else {
        console.error('Delivery modal element not found in closeDeliveryModal');
    }
}

function openNoteModal() {
    const noteModal = document.getElementById('noteModal');
    if (noteModal) {
        noteModal.style.removeProperty('display');
        noteModal.classList.remove('hidden');
        toggleBodyScroll(true);
    } else {
        console.error('Note modal element not found');
    }
}

function closeNoteModal() {
    const noteModal = document.getElementById('noteModal');
    if (noteModal) {
        noteModal.classList.add('hidden');
        toggleBodyScroll(false);
    } else {
        console.error('Note modal element not found in closeNoteModal');
    }
}

async function saveNote() {
    const note = document.getElementById('note').value;
    const orderId = document.getElementById('orderId').innerText;

    // Send note to server
    try {
        const response = await fetch(`/dashboard/orders/${orderId}/addNote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ note })
        });
        if (response.ok) {
            closeNoteModal();
            // window.location.reload();
        } else {
            console.error('Error saving note:', response.status);
            alert('Error saving note. Please check the console for details.');
        }
    } catch (error) {
        console.error('Error saving note:', error);
        alert('Error saving note. Please check the console for details.');
    }
}


async function createDelivery() {
    const deliveryDate = document.getElementById('delivery-date').value;
    const quantity = document.getElementById('delivered_quantity').value;
    const deliveryNotes = document.getElementById('delivery-notes').value;
    const orderId = document.getElementById('orderId').innerText;

    const deliveryData = {
        delivery_date: deliveryDate,
        quantity: quantity,
        delivery_notes: deliveryNotes
    };

    try {
        const response = await fetch(`/dashboard/orders/${orderId}/createDelivery`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(deliveryData)
        });

        if (response.ok) {
            closeDeliveryModal();
            window.location.reload();
        } else {
            console.error('Error creating delivery:', response.status);
            alert('Error creating delivery. Please check the console for details.');
        }
    } catch (error) {
        console.error('Error creating delivery:', error);
        alert('Error creating delivery. Please check the console for details.');
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


async function loadToolTypes(tool_type_id, tool_id) {
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
    document.getElementById('tool-card').innerHTML = `
        <div class="hidden" id="current-tool-type-id">${tool.tool_type_id}</div>
        <div class="hidden" id="current-tool-id">${tool.id}</div>
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
        <div class="hidden" id="current-tool-type-id">${tool.tool_type_id}</div>
        <div class="hidden" id="current-tool-id">${tool.id}</div>
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
    const shipping_company = document.getElementById('shipping-company').value;
    const tracking_number = document.getElementById('tracking-number').value;

    // Get the selected tool ID from the data attribute
    // const toolId = document.getElementById('orderDetailsModal').dataset.toolId;
    const toolId = document.getElementById('current-tool-id').innerText
    

    const orderData = {
        tool_id: toolId,
        order_number: orderNumber,
        quantity: quantity,
        gross_price: grossPrice,
        tool_price: toolPrice,
        order_date: orderDate,
        estimated_delivery_date: estimatedDeliveryDate,
        shipping_company: shipping_company,
        tracking_number: tracking_number
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

    const current_tool_type_id = document.getElementById('current-tool-type-id').innerText
    const current_tool_id = document.getElementById('current-tool-id').innerText

    if (current_tool_type_id && current_tool_id) {
        loadToolTypes(current_tool_type_id, current_tool_id);
    } else {
        loadToolTypes(null, null);
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

async function deleteOrder() {
    const orderId = window.order.id;

    try {
        const response = await fetch(`/dashboard/orders/deleteOrder/${orderId}`, {
            method: 'DELETE',
        });

        if (response.ok) {
            alert('Order deleted successfully!');
            closeOrderModal();
            window.location.reload();
        } else {
            console.error('Error deleting order:', response.status);
            alert('Error deleting order. Please check the console for details.');
        }
    } catch (error) {
        console.error('Error deleting order:', error);
        alert('Error deleting order. Please check the console for details.');
    }
}

function enableEdit() {
    document.getElementById('editButton').classList.add('hidden');
    document.getElementById('saveButton').classList.remove('hidden');
    document.getElementById('deleteOrderButton').classList.remove('hidden');

    document.getElementById('order-number-display').classList.add('hidden');
    document.getElementById('order-number').classList.remove('hidden');

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

    document.getElementById('shipping-company-display').classList.add('hidden');
    document.getElementById('shipping-company').classList.remove('hidden');

    document.getElementById('tracking-number-display').classList.add('hidden');
    document.getElementById('tracking-number').classList.remove('hidden');
}

function disableEdit() {
    document.getElementById('editButton').classList.remove('hidden');
    document.getElementById('saveButton').classList.add('hidden');
    document.getElementById('deleteOrderButton').classList.add('hidden');

    document.getElementById('order-number-display').classList.remove('hidden');
    document.getElementById('order-number').classList.add('hidden');

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

    document.getElementById('shipping-company-display').classList.remove('hidden');
    document.getElementById('shipping-company').classList.add('hidden');

    document.getElementById('tracking-number-display').classList.remove('hidden');
    document.getElementById('tracking-number').classList.add('hidden');
}
