document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("opportunities-list");
    if (!container) return;

    try {
        const selectedOperations = localStorage.getItem('selectedOperations') || "";
        const selectedProducts = localStorage.getItem('selectedProducts') || "";
        const startDate = localStorage.getItem('startDate') || "";
        let endDate = localStorage.getItem('endDate') || "";
        if (endDate == null || endDate === "null") {
            endDate = new Date().toISOString();
        }
        const response = await fetch(`http://${window.location.host}/dashboard/opportunities/api/ranked?selected_operations=${selectedOperations}&selected_products=${selectedProducts}&start_date=${startDate}&end_date=${endDate}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const opportunities = data.opportunities || [];

        if (opportunities.length === 0) {
            const emptyMessage = document.createElement("p");
            emptyMessage.className = "text-gray-400 italic";
            emptyMessage.textContent = "No cost-saving opportunities available.";
            container.appendChild(emptyMessage);
        } else {
            opportunities.forEach((op, index) => {
                const card = document.createElement("div");
                card.className = "p-4 bg-gray-800 rounded shadow";

                const title = document.createElement("h3");
                title.className = "text-lg font-semibold text-teal-300";
                title.textContent = `${index + 1}. ${op.name || "Opportunity"}`;

                const details = document.createElement("p");
                details.className = "text-gray-300 mt-2";
                details.textContent = op.description || "Description placeholder";

                card.appendChild(title);
                card.appendChild(details);
                container.appendChild(card);
            });
        }
    } catch (error) {
        console.error("Failed to load opportunities:", error);
        const errorMessage = document.createElement("p");
        errorMessage.className = "text-red-500";
        errorMessage.textContent = "Error loading opportunities.";
        container.appendChild(errorMessage);
    }
});
