import { initializeDateRange } from './rangeSlider.js';
import { initializeSelections, setupFilterClickHandlers, loadFilterOptions } from './filterUtils.js';
import { setupEventListeners } from './modalUtils.js';

// Initialize all functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded in base template, initializing dashboard...');
    
    // Initialize date range slider
    initializeDateRange();
    
    // Initialize filter selections
    initializeSelections();
    
    // Setup filter click handlers
    setupFilterClickHandlers();
    
    // Setup all event listeners
    setupEventListeners();

    // Load filter options dynamically
    loadFilterOptions();
});
