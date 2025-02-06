// Update selected filters display in nav
export function updateSelectedFilters() {
    const filtersDisplay = document.getElementById('selectedFilters');
    
    // Get counts from either active checkboxes or stored selections
    let productCount = 0;
    let operationCount = 0;
    
    const activeProducts = document.querySelectorAll('#product-select input:checked');
    const activeOperations = document.querySelectorAll('#operation-select input:checked');
    
    if (activeProducts.length > 0 || activeOperations.length > 0) {
        productCount = activeProducts.length;
        operationCount = activeOperations.length;
    } else {
        // Fallback to stored selections
        const params = new URLSearchParams(window.location.search);
        const storedProducts = params.getAll('selected_products').length > 0 
            ? params.getAll('selected_products')
            : JSON.parse(localStorage.getItem('selectedProducts') || '[]');
        const storedOperations = params.getAll('selected_operations').length > 0
            ? params.getAll('selected_operations')
            : JSON.parse(localStorage.getItem('selectedOperations') || '[]');
        
        productCount = storedProducts.length;
        operationCount = storedOperations.length;
    }
    
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

// Save selections to localStorage
export function saveSelections() {
    const selectedProducts = Array.from(document.querySelectorAll('#product-select input:checked'))
        .map(checkbox => checkbox.value);
    const selectedOperations = Array.from(document.querySelectorAll('#operation-select input:checked'))
        .map(checkbox => checkbox.value);
    
    localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
    localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));
}

// Handle select all functionality
export function AllCheckboxes(button, value) {
    const container = button.closest('.space-y-2');
    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    const labels = container.querySelectorAll('label[data-value]');
    
    // Set all checkbox values and update button states
    checkboxes.forEach((checkbox, index) => {
        checkbox.checked = value;
        const label = labels[index];
        label.classList.toggle('bg-indigo-600', value);
        label.classList.toggle('hover:bg-indigo-700', value);
        label.classList.toggle('hover:bg-gray-600', !value);
    });

    // Initialize HTMX on the checkboxes
    checkboxes.forEach(checkbox => htmx.process(checkbox));

    // Update filters display and save selections
    updateSelectedFilters();
    saveSelections();

    // Find the first checkbox and trigger its HTMX request
    const firstCheckbox = checkboxes[0];
    if (firstCheckbox) {
        htmx.trigger(firstCheckbox, 'change');
    }
}

// Initialize selections on page load
export function initializeSelections() {
    // Get selections from URL parameters and localStorage
    const params = new URLSearchParams(window.location.search);
    const selectedProducts = params.getAll('selected_products').length > 0 
        ? params.getAll('selected_products')
        : JSON.parse(localStorage.getItem('selectedProducts') || '[]');
    const selectedOperations = params.getAll('selected_operations').length > 0
        ? params.getAll('selected_operations')
        : JSON.parse(localStorage.getItem('selectedOperations') || '[]');

    // Save current selections to localStorage
    localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
    localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));

    // Update filters display
    updateSelectedFilters();
}

// Handle individual checkbox clicks
export function setupFilterClickHandlers() {
    document.addEventListener('click', function(event) {
        const label = event.target.closest('label[data-value]');
        if (label) {
            const checkbox = label.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                label.classList.toggle('bg-indigo-600', checkbox.checked);
                label.classList.toggle('hover:bg-indigo-700', checkbox.checked);
                label.classList.toggle('hover:bg-gray-600', !checkbox.checked);
                updateSelectedFilters();
                saveSelections();
                htmx.trigger(checkbox, 'change');
            }
        }
    });
}

// Load filter options into the modal
export async function loadFilterOptions() {
    try {
        // Get selections from URL parameters and localStorage
        const params = new URLSearchParams(window.location.search);
        const selectedProducts = params.getAll('selected_products').length > 0 
            ? params.getAll('selected_products')
            : JSON.parse(localStorage.getItem('selectedProducts') || '[]');
        const selectedOperations = params.getAll('selected_operations').length > 0
            ? params.getAll('selected_operations')
            : JSON.parse(localStorage.getItem('selectedOperations') || '[]');

        // Save current selections to localStorage
        localStorage.setItem('selectedProducts', JSON.stringify(selectedProducts));
        localStorage.setItem('selectedOperations', JSON.stringify(selectedOperations));

        const response = await fetch('/dashboard/api/filter-options');
        const data = await response.json();
        
        // Populate products
        const productSelect = document.getElementById('product-select');
        productSelect.innerHTML = Object.entries(data.products)
            .map(([name, id]) => `
                <label class="px-4 py-2 text-left rounded-md bg-gray-700 text-gray-100 hover:bg-gray-600 transition-colors cursor-pointer ${selectedProducts.includes(id.toString()) ? 'bg-indigo-600 hover:bg-indigo-700' : ''}" data-value="${id}">
                    <input type="checkbox" 
                           name="selected_products" 
                           value="${id}" 
                           class="hidden"
                           ${selectedProducts.includes(id.toString()) ? 'checked' : ''}>
                    ${name}
                </label>
            `).join('');
        
        // Populate operations
        const operationSelect = document.getElementById('operation-select');
        operationSelect.innerHTML = Object.entries(data.operations)
            .map(([name, id]) => `
                <label class="px-4 py-2 text-left rounded-md bg-gray-700 text-gray-100 hover:bg-gray-600 transition-colors cursor-pointer ${selectedOperations.includes(id.toString()) ? 'bg-indigo-600 hover:bg-indigo-700' : ''}" data-value="${id}">
                    <input type="checkbox" 
                           name="selected_operations" 
                           value="${id}" 
                           class="hidden"
                           ${selectedOperations.includes(id.toString()) ? 'checked' : ''}>
                    ${name}
                </label>
            `).join('');

        // Update filters display
        updateSelectedFilters();
    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}
