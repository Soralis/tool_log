// Update selected filters display in nav
export function updateSelectedFilters() {
    const filtersDisplay = document.getElementById('selectedFilters');
    const productCount = document.querySelectorAll('#product-select input:checked').length;
    const operationCount = document.querySelectorAll('#operation-select input:checked').length;

    let displayText = '';
    if (productCount > 0 || operationCount > 0) {
        const parts = [];
        if (productCount > 0) {
            parts.push(`${productCount} Product${productCount === 1 ? '' : 's'}`);
        }
        if (operationCount > 0) {
            parts.push(`${operationCount} Operation${operationCount === 1 ? '' : 's'}`);
        }
        displayText = parts.join(', ');
    } else {
        displayText = 'No filters';
    }

    filtersDisplay.textContent = displayText;
}

// Save selections to localStorage and dispatch event
export function saveSelections() {
    const selectedLine = document.querySelector('#line-select input:checked')?.value || 'all';
    const selectedProducts = Array.from(document.querySelectorAll('#product-select input:checked'))
        .map(cb => cb.value);
    const selectedOperations = Array.from(document.querySelectorAll('#operation-select input:checked'))
        .map(cb => cb.value);

    localStorage.setItem('selectedLine', selectedLine);
    localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
    localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));

    updateSelectedFilters();

    const event = new CustomEvent('filterChanged', {
        detail: {
            selectedProducts,
            selectedOperations
        },
        bubbles: true
    });
    document.body.dispatchEvent(event);
    console.log('Selections saved:', selectedLine, selectedProducts, selectedOperations);
}

// Handle select all / clear all functionality
export function AllCheckboxes(button, value) {
    const container = button.closest('.space-y-2');
    console.log('Toggling checkboxes in container:', container);
    const allCheckboxes = container.querySelectorAll('input[type="checkbox"]');
    const visibleCheckboxes = Array.from(allCheckboxes).filter(cb => {
    const label = cb.closest('label');
    return label && window.getComputedStyle(label).display !== 'none';
    });

    console.log('Checkboxes found:', visibleCheckboxes.length);

    visibleCheckboxes.forEach(cb => {
        cb.checked = value;
        const lbl = cb.closest('label[data-value]');
        lbl.classList.toggle('bg-indigo-600', value);
        lbl.classList.toggle('hover:bg-indigo-700', value);
        lbl.classList.toggle('hover:bg-gray-600', !value);
    });
    updateSelectedFilters();
    saveSelections();
}

// Initialize selections
export function initializeSelections() {
    const params = new URLSearchParams(window.location.search);
    const selectedLine = params.get('selected_line') || 'all';
    
    const selectedProducts = params.getAll('selected_products').length > 0
        ? params.getAll('selected_products')
        : JSON.parse(localStorage.getItem('selectedProducts') || '[]');
    const selectedOperations = params.getAll('selected_operations').length > 0
        ? params.getAll('selected_operations')
        : JSON.parse(localStorage.getItem('selectedOperations') || '[]');

    localStorage.setItem('selectedLine', selectedLine);
    localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
    localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));

    updateSelectedFilters();
}

// Handle individual checkbox changes
export function setupFilterClickHandlers() {
    const productSelect = document.getElementById('product-select');
    const operationSelect = document.getElementById('operation-select');

    [productSelect, operationSelect].forEach(container => {
        container.addEventListener('change', function(event) {
            if (event.target.matches('input[type="checkbox"]')) {
                const label = event.target.closest('label[data-value]');
                if (label) {
                    label.classList.toggle('bg-indigo-600', event.target.checked);
                    label.classList.toggle('hover:bg-indigo-700', event.target.checked);
                    label.classList.toggle('hover:bg-gray-600', !event.target.checked);
                    saveSelections();
                }
            }
        });
    });
}

// Handle line tab clicks to show/hide products and operations
export function setupLineTabHandlers() {
    const tabs = document.querySelectorAll('#line-select label');
    tabs.forEach(tab => {
        tab.addEventListener('click', function(event) {
            tabs.forEach(t => t.classList.remove('ring-2', 'ring-indigo-500', 'bg-indigo-600', 'hover:bg-indigo-700'));
            this.classList.add('ring-2', 'ring-indigo-500', 'bg-indigo-600', 'hover:bg-indigo-700');
            const lineId = this.getAttribute('data-value');
            if (lineId === 'all') {
                document.querySelectorAll('#product-select label, #operation-select label').forEach(lbl => {
                    lbl.classList.remove('hidden');
                });
            } else {
                document.querySelectorAll('#product-select label[data-lines]').forEach(lbl => {
                    const lineIds = JSON.parse(lbl.getAttribute('data-lines') || '[]');
                    lbl.classList.toggle('hidden', !lineIds.includes(parseInt(lineId)));
                });
                document.querySelectorAll('#operation-select label[data-lines]').forEach(lbl => {
                    const lineIds = JSON.parse(lbl.getAttribute('data-lines') || '[]');
                    lbl.classList.toggle('hidden', !lineIds.includes(parseInt(lineId)));
                });
            }
        });
    });
}

function populateOptions(type_name, selected, data) {
    const Select = document.getElementById(`${type_name}-select`);
    const sortedSelect = data.sort((a, b) => a.name.localeCompare(b.name));
    console.log(`Populating ${type_name} options...`, Select, sortedSelect, selected);
    Select.innerHTML = sortedSelect.map(item => {
        // Handle both single line_id and multiple line_ids
        const lineIds = item.line_ids || (item.line_id ? [item.line_id] : []);
        const lineAttribute = lineIds.length > 0 ? `data-lines='${JSON.stringify(lineIds)}'` : '';
        return `
        <label class="px-4 py-2 text-left rounded-md bg-gray-700 text-gray-100 hover:bg-gray-600 transition-colors cursor-pointer ${selected.includes(item.id.toString()) ? 'bg-indigo-600 hover:bg-indigo-700' : ''}" data-value="${item.id}" ${lineAttribute}>
            <input type="checkbox"
                    name="selected_${type_name}s"
                    value="${item.id}"
                    class="hidden"
                    ${selected.includes(item.id.toString()) ? 'checked' : ''}>
            ${item.name}
        </label>
    `;
    }).join('');
}

// Load filter options into the modal
export async function loadFilterOptions() {
    try {
        const params = new URLSearchParams(window.location.search);
        const selectedLine = params.get('selected_line') || 'all';
        const selectedProducts = params.getAll('selected_products').length > 0
            ? params.getAll('selected_products')
            : JSON.parse(localStorage.getItem('selectedProducts') || '[]');
        const selectedOperations = params.getAll('selected_operations').length > 0
            ? params.getAll('selected_operations')
            : JSON.parse(localStorage.getItem('selectedOperations') || '[]');

        localStorage.setItem('selectedLine', selectedLine);
        localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
        localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));

        const response = await fetch('/dashboard/api/filter-options');
        const data = await response.json();

        // Populate lines (tabs)
        const lineSelect = document.getElementById('line-select');
        console.log("Loading filter options for line select...", lineSelect);
        const sorted_data = data.lines.sort((a, b) => a.name.localeCompare(b.name));
        sorted_data.unshift({ id: 'all', name: 'All Lines' }); // Add "All Lines" option
        lineSelect.innerHTML = sorted_data.map(line => `
            <label class="px-4 py-2 text-left rounded-md bg-gray-700 text-gray-100 hover:bg-gray-600 cursor-pointer transition-colors flex items-center justify-between" data-value="${line.id}">
                <input type="radio"
                       name="selected_line"
                       value="${line.id}"
                       class="hidden"
                       ${line.id == selectedLine ? 'checked' : ''}>
                ${line.name}
            </label>
        `).join('');

        // Populate
        populateOptions('product', selectedProducts, data.products);
        populateOptions('operation', selectedOperations, data.operations);
        setupLineTabHandlers();

        // Initialize first tab
        const firstTab = lineSelect.querySelector('label');
        if (firstTab) firstTab.click();

        updateSelectedFilters();
    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}
