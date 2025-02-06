import { getUnitMax, unitsToDate } from './dateUtils.js';

// Global references
let startRange, endRange, range, rangeValues;

export function handleSliderInput(slider, isStart) {
    const startVal = parseInt(startRange.value);
    const endVal = parseInt(endRange.value);
    
    if (isStart && startVal >= endVal) {
        startRange.value = endVal;
    } else if (!isStart && endVal <= startVal) {
        endRange.value = startVal;
    }
    
    const unit = document.getElementById('time-unit').value;
    const max = getUnitMax(unit);
    
    // Save to localStorage
    localStorage.setItem('startRange', startRange.value);
    localStorage.setItem('endRange', endRange.value);
    
    // Update date range in localStorage
    const startDate = unitsToDate(parseInt(startRange.value), unit, max, false);
    const endDate = unitsToDate(parseInt(endRange.value), unit, max, true);
    localStorage.setItem('startDate', startDate.toISOString());
    localStorage.setItem('endDate', endDate ? endDate.toISOString() : 'null');
    
    setRangeValues();
}

export function updateTimeUnit() {
    const unit = document.getElementById('time-unit').value;
    const max = getUnitMax(unit);
    
    // Get current values as percentages of their max
    const oldMax = parseInt(startRange.max);
    const startPercent = parseInt(startRange.value) / oldMax;
    const endPercent = parseInt(endRange.value) / oldMax;
    
    // Update slider ranges
    startRange.max = max;
    endRange.max = max;
    
    // Convert percentages to new values
    startRange.value = Math.round(startPercent * max);
    endRange.value = Math.round(endPercent * max);
    
    // Save to localStorage
    localStorage.setItem('timeUnit', unit);
    localStorage.setItem('startRange', startRange.value);
    localStorage.setItem('endRange', endRange.value);
    
    // Update date range in localStorage
    const startDate = unitsToDate(parseInt(startRange.value), unit, max, false);
    const endDate = unitsToDate(parseInt(endRange.value), unit, max, true);
    localStorage.setItem('startDate', startDate.toISOString());
    localStorage.setItem('endDate', endDate ? endDate.toISOString() : 'null');
    
    console.log('Updated time unit:', {
        unit,
        max,
        startValue: startRange.value,
        endValue: endRange.value
    });
    
    setRangeValues();
    emitDateRangeChange();
}

function setRangeValues() {
    const unit = document.getElementById('time-unit').value;
    const startUnits = parseInt(startRange.value);
    const endUnits = parseInt(endRange.value);
    const max = getUnitMax(unit);
    
    // Convert slider values to dates
    const startDate = unitsToDate(startUnits, unit, max, false);
    const endDate = unitsToDate(endUnits, unit, max, true);
    
    // Update range bar position and width
    const startPercent = (startUnits / max) * 100;
    const endPercent = (endUnits / max) * 100;
    
    // Adjust percentages to account for handle offsets
    const handleWidth = 16; // Total handle width
    const containerWidth = range.parentElement.offsetWidth;
    const offsetPercent = (handleWidth / containerWidth) * 100;

    // Adjust the range bar position and width
    range.style.left = startPercent + '%';
    range.style.width = (endPercent - startPercent) + '%';
    
    // Update display text with unit-specific formatting
    let dateFormat;
    switch(unit) {
        case 'day':
            dateFormat = new Intl.DateTimeFormat('default', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            break;
        case 'week':
            dateFormat = new Intl.DateTimeFormat('default', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            rangeValues.textContent = endDate ? 
                `Week of ${dateFormat.format(startDate)} - ${dateFormat.format(endDate)}` :
                `Week of ${dateFormat.format(startDate)} - Now`;
            return;
        case 'month':
            dateFormat = new Intl.DateTimeFormat('default', {
                year: 'numeric',
                month: 'long'
            });
            break;
        case 'quarter':
            dateFormat = new Intl.DateTimeFormat('default', { year: 'numeric' });
            rangeValues.textContent = endDate ? 
                `${getQuarterName(startDate)} ${dateFormat.format(startDate)} - ${getQuarterName(endDate)} ${dateFormat.format(endDate)}` :
                `${getQuarterName(startDate)} ${dateFormat.format(startDate)} - Now`;
            return;
        case 'year':
            dateFormat = new Intl.DateTimeFormat('default', {
                year: 'numeric'
            });
            break;
    }
    
    rangeValues.textContent = endDate ? 
        `${dateFormat.format(startDate)} - ${dateFormat.format(endDate)}` :
        `${dateFormat.format(startDate)} - Now`;
}

function emitDateRangeChange() {
    const unit = document.getElementById('time-unit').value;
    const startUnits = parseInt(startRange.value);
    const endUnits = parseInt(endRange.value);
    const max = getUnitMax(unit);
    
    const startDate = unitsToDate(startUnits, unit, max, false);
    const endDate = unitsToDate(endUnits, unit, max, true);

    // Update the selected range display in nav
    const selectedRange = document.getElementById('selectedRange');
    const dateFormat = new Intl.DateTimeFormat('default', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    selectedRange.textContent = endDate ? 
        `${dateFormat.format(startDate)} - ${dateFormat.format(endDate)}` :
        `${dateFormat.format(startDate)} - Now`;

    // Log the date range update
    console.log('Date range updated:', {
        unit,
        startDate: startDate.toISOString(),
        endDate: endDate ? endDate.toISOString() : 'Now',
        startUnits,
        endUnits,
        max
    });

    const dateRangeEvent = new CustomEvent('dateRangeChanged', {
        detail: {
            startDate: startDate.toISOString(),
            endDate: endDate ? endDate.toISOString() : null
        }
    });
    document.dispatchEvent(dateRangeEvent);
}

export function initializeDateRange() {
    console.log('Initializing date range...');
    
    // Initialize references
    startRange = document.getElementById('start-range');
    endRange = document.getElementById('end-range');
    range = document.querySelector('.slider-range');
    rangeValues = document.getElementById('range-values');

    if (!startRange || !endRange || !range || !rangeValues) {
        console.warn('Date range elements not found, skipping initialization');
        return;
    }

    // Load saved preferences from localStorage
    const savedUnit = localStorage.getItem('timeUnit');
    const savedStartRange = localStorage.getItem('startRange');
    const savedEndRange = localStorage.getItem('endRange');
    
    console.log('Loaded from localStorage:', {
        savedUnit,
        savedStartRange,
        savedEndRange
    });

    // Set the time unit first (this will set max values)
    const timeUnitSelect = document.getElementById('time-unit');
    if (timeUnitSelect) {
        timeUnitSelect.value = savedUnit || 'day';
    }

    // Get max value for the current unit
    const max = getUnitMax(timeUnitSelect.value);
    
    // Set range values
    if (savedStartRange !== null && savedEndRange !== null) {
        startRange.max = max;
        endRange.max = max;
        startRange.value = savedStartRange;
        endRange.value = savedEndRange;
    } else {
        startRange.max = max;
        endRange.max = max;
        endRange.value = max;
        startRange.value = Math.max(max - 1, 0);
    }

    // Add event listeners for sliders
    ['input'].forEach(event => {
        startRange.addEventListener(event, () => handleSliderInput(startRange, true));
        endRange.addEventListener(event, () => handleSliderInput(endRange, false));
    });
    
    // Add event listeners for slider release
    ['mouseup', 'touchend'].forEach(event => {
        startRange.addEventListener(event, emitDateRangeChange);
        endRange.addEventListener(event, emitDateRangeChange);
    });

    // Add change listener for time unit
    timeUnitSelect.addEventListener('change', updateTimeUnit);

    // Update display
    setRangeValues();
    emitDateRangeChange();

    console.log('Date range initialized with:', {
        unit: timeUnitSelect.value,
        startValue: startRange.value,
        endValue: endRange.value
    });

    // Dispatch event to notify that date range is initialized
    console.log('Date range initialization complete, dispatching event');
    document.dispatchEvent(new Event('dateRangeInitialized'));
}
