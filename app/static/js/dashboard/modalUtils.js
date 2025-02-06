import { loadFilterOptions, AllCheckboxes } from './filterUtils.js';
import { updateTimeUnit } from './rangeSlider.js';

function toggleModal() {
    const modal = document.getElementById('dateRangeModal');
    const isHidden = modal.classList.contains('hidden');
    modal.classList.toggle('hidden');
    
    // Load filter options when opening the modal
    if (isHidden) {
        loadFilterOptions();
    }
}

function toggleMenu() {
    const menuItems = document.querySelector('.menu-items');
    menuItems.classList.toggle('show');
}

function hardReload() {
    console.log('Hard reloading...');
    location.reload(true);
}

// Setup all event listeners
export function setupEventListeners() {
    // Modal open/close
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const filterBtn = document.getElementById('filter-btn');
    
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', toggleModal);
    if (filterBtn) filterBtn.addEventListener('click', toggleModal);

    // Close modal when clicking outside
    window.onclick = function(event) {
        const modal = document.getElementById('dateRangeModal');
        const modalOverlay = modal.querySelector('.flex.items-center.justify-center');
        if (event.target === modalOverlay) {
            modal.classList.add('hidden');
        }
    };

    // Time unit select
    const timeUnitSelect = document.getElementById('time-unit');
    if (timeUnitSelect) {
        timeUnitSelect.addEventListener('change', updateTimeUnit);
    }

    // Select/Clear All buttons
    document.querySelectorAll('.select-all-btn').forEach(btn => {
        btn.addEventListener('click', () => AllCheckboxes(btn, true));
    });
    document.querySelectorAll('.clear-all-btn').forEach(btn => {
        btn.addEventListener('click', () => AllCheckboxes(btn, false));
    });

    // Burger menu
    const burgerMenuBtn = document.getElementById('burger-menu-btn');
    if (burgerMenuBtn) {
        burgerMenuBtn.addEventListener('click', toggleMenu);
    }

    // Reload button
    const reloadButton = document.getElementById('reload-button');
    if (reloadButton) {
        reloadButton.addEventListener('click', hardReload);
    }
}
