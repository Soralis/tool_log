import { updateSelectedFilters } from './filterUtils.js';

const printBtn = document.getElementById('print-btn');
if (printBtn) {
  printBtn.addEventListener('click', () => {
    window.print();
  });
}

async function fetchReports() {
  try {
    const selectedLine = localStorage.getItem('selectedLine') || 'all';
    const selectedProducts = localStorage.getItem('selectedProducts') || '[]';
    const selectedOperations = localStorage.getItem('selectedOperations') || '[]';
    const startDate = localStorage.getItem('startDate') || '';
    let endDate = localStorage.getItem('endDate') || '';
    if (!endDate || endDate === 'null') {
      endDate = new Date().toISOString();
    }

    const params = new URLSearchParams({
      selected_line: selectedLine,
      selected_products: selectedProducts,
      selected_operations: selectedOperations,
      start_date: startDate,
      end_date: endDate,
    });

    const response = await fetch(`${window.location.origin}/dashboard/reports/api/data?${params.toString()}`);
    const result = await response.json();
    populateTable(result.data);
  } catch (error) {
    console.error('Error fetching reports data:', error);
  }
}

function populateTable(rows) {
  const tbody = document.querySelector('#reports-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  // Group by line and product
  const data = {};
  rows.forEach(r => {
    if (!data[r.line]) data[r.line] = {};
    if (!data[r.line][r.product]) data[r.line][r.product] = [];
    data[r.line][r.product].push(r);
  });

  Object.entries(data).forEach(([line, products]) => {
    Object.entries(products).forEach(([product, ops]) => {
      // Compute summary metrics
      const totalCost = ops.reduce((sum, op) => sum + op.cost_per_piece, 0);
      const totalPreviousCost = ops.reduce((sum, op) => sum + (op.previous_cost_per_piece || 0), 0);
      console.log(totalCost, totalPreviousCost);
      const totalPercentChange = totalPreviousCost > 0 ? ((totalCost - totalPreviousCost) / totalPreviousCost * 100).toFixed(2) : null;
      console.log(`Total cost for ${line} - ${product}: $${totalCost.toFixed(2)}`);
      console.log(`Total previous cost for ${line} - ${product}: $${totalPreviousCost.toFixed(2)}`);
      console.log(`Total percent change for ${line} - ${product}: ${totalPercentChange !== null ? totalPercentChange + '%' : 'N/A'}`);
      const CurrentProduction = ops[0].workpieces_produced || 0;


      // Summary row
      const summaryRow = document.createElement('tr');
      summaryRow.classList.add('border-b', 'border-gray-700', 'cursor-pointer');
      summaryRow.innerHTML = `
        <td class="px-4 py-2">${line}</td>
        <td class="px-4 py-2"><span class="expand-icon mr-2">+</span>${product}</td>
        <td class="px-4 py-2">${CurrentProduction}</td>
        <td class="px-4 py-2">Combined</td>
        <td class="px-4 py-2">$${totalCost.toFixed(2)}</td>
        <td class="px-4 py-2">${totalPercentChange !== null ? totalPercentChange + '%' : ''}</td>
        <td class="px-4 py-2"></td>
      `;
      tbody.appendChild(summaryRow);

      // Detail rows (hidden by default)
      const detailRows = ops.map(op => {
        const tr = document.createElement('tr');
        const percent_change = op.cost_per_piece !== 0 && op.previous_cost_per_piece ?
          ((op.cost_per_piece - op.previous_cost_per_piece) / op.previous_cost_per_piece * 100).toFixed(2) : null;
        tr.classList.add('border-b', 'border-gray-700', 'detail-row', 'hidden');
        tr.innerHTML = `
          <td></td>
          <td></td>
          <td></td>
          <td class="px-4 py-2">${op.operation}</td>
          <td class="px-4 py-2">$${op.cost_per_piece.toFixed(2)}</td>
          <td class="px-4 py-2">${percent_change !== null ? percent_change + '%' : ''}</td>
          <td class="px-4 py-2">${op.reason}</td>
        `;
        tbody.appendChild(tr);
        return tr;
      });

      // Toggle on click
      summaryRow.addEventListener('click', () => {
        const icon = summaryRow.querySelector('.expand-icon');
        const expanded = icon.textContent === '-';
        icon.textContent = expanded ? '+' : '-';
        detailRows.forEach(dr => dr.classList.toggle('hidden'));
      });
    });
  });
}

// Listen for filter and date changes
document.addEventListener('filterChanged', fetchReports);
document.addEventListener('dateRangeChanged', fetchReports);

// Initial load
window.addEventListener('DOMContentLoaded', () => {
  updateSelectedFilters();
  fetchReports();
});
