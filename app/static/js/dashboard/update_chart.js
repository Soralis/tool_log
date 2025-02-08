export function update_data(chart, option, api_url) {
    // Get selections from localStorage
    const selectedProducts = JSON.parse(localStorage.getItem('selectedProducts'));
    const selectedOperations = JSON.parse(localStorage.getItem('selectedOperations'));

    // Get dates from localStorage
    let startDate = localStorage.getItem('startDate');
    let endDate = localStorage.getItem('endDate');

    fetch(`${api_url}?selected_products=${selectedProducts}&selected_operations=${selectedOperations}&start_date=${startDate}&end_date=${endDate}`)
        .then(response => response.json())
        .then(data => {
            // Update both the series data and labels
            option.dataset = data
            chart.setOption(option);
        });
}
