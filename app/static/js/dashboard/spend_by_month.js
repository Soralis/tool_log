// Function to update the spend by and month table
async function updateSpendByMonthTable() {
    // Get selections from localStorage
    const selectedProducts = JSON.parse(localStorage.getItem('selectedProducts')) || [];
    const selectedOperations = JSON.parse(localStorage.getItem('selectedOperations')) || [];
    
    // Get dates from localStorage
    let startDate = localStorage.getItem('startDate');
    let endDate = localStorage.getItem('endDate');

    try {
        const response = await fetch('/dashboard/monetary/api/spend_by_month', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                selected_products: selectedProducts,
                selected_operations: selectedOperations,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const data = await response.json();
        
        // Update the spend by part table
        const partTableBody = document.querySelector('#spendByPartTable tbody');
        if (partTableBody) {
            // Clear existing content except summary row
            Array.from(partTableBody.children).forEach(row => {
                if (!row.classList.contains('bg-blue-600')) {
                    row.remove();
                }
            });
            
            // Add new data rows
            data.workpiece.rows.forEach(row => {
                const tr = document.createElement('tr');
                tr.className = 'border-b border-gray-600 hover:bg-gray-650';
                row.forEach(cell => {
                    const td = document.createElement('td');
                    td.className = 'px-4 py-2';
                    td.textContent = cell;
                    tr.appendChild(td);
                });
                partTableBody.appendChild(tr);
            });
            
            // Update summary row if it exists
            const partSummaryRow = partTableBody.querySelector('.bg-blue-600');
            if (partSummaryRow && data.workpiece.summary) {
                Array.from(partSummaryRow.children).forEach((cell, index) => {
                    if (index < data.workpiece.summary.length) {
                        cell.textContent = data.workpiece.summary[index];
                    }
                });
            }
        }
        
        // Update the spend by machine table
        const machineTableBody = document.querySelector('#spendByMachineTable tbody');
        if (machineTableBody) {
            // Clear existing content except summary row
            Array.from(machineTableBody.children).forEach(row => {
                if (!row.classList.contains('bg-blue-600')) {
                    row.remove();
                }
            });
            
            // Add new data rows
            data.operation.rows.forEach(row => {
                const tr = document.createElement('tr');
                tr.className = 'border-b border-gray-600 hover:bg-gray-650';
                row.forEach(cell => {
                    const td = document.createElement('td');
                    td.className = 'px-4 py-2';
                    td.textContent = cell;
                    tr.appendChild(td);
                });
                machineTableBody.appendChild(tr);
            });
            
            // Update summary row if it exists
            const machineSummaryRow = machineTableBody.querySelector('.bg-blue-600');
            if (machineSummaryRow && data.operation.summary) {
                Array.from(machineSummaryRow.children).forEach((cell, index) => {
                    if (index < data.operation.summary.length) {
                        cell.textContent = data.operation.summary[index];
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error updating spend by month table:', error);
    }
}

// Initialize the table on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if the spend by month tables exist
    if (document.getElementById('spendByPartTable') || document.getElementById('spendByMachineTable')) {
        updateSpendByMonthTable();
    }
});

// Listen for filter changes and update the table
document.addEventListener('filtersUpdated', function() {
    if (document.getElementById('spendByPartTable') || document.getElementById('spendByMachineTable')) {
        updateSpendByMonthTable();
    }
});
