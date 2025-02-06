export function configureHtmxRequest(evt, apiPath) {
    console.log('--------------------------------------')
    console.log('Htmx request:', evt.detail, apiPath);
    if (evt.detail.path === apiPath) {
        // Get selections from localStorage
        const selectedProducts = JSON.parse(localStorage.getItem('selectedProducts') || '[]');
        const selectedOperations = JSON.parse(localStorage.getItem('selectedOperations') || '[]');

        // Get dates from localStorage
        let startDate = localStorage.getItem('startDate');
        let endDate = localStorage.getItem('endDate');

        // Handle the case where endDate is "null"
        if (endDate === 'null') {
            endDate = 'Now';
        }

        console.log('Filter data:', {
            selectedProducts,
            selectedOperations,
            startDate,
            endDate
        });

        // Add to request parameters
        evt.detail.parameters = {
            ...evt.detail.parameters,
            selected_products: selectedProducts,
            selected_operations: selectedOperations,
            start_date: startDate,
            end_date: endDate
        };
    }
}
