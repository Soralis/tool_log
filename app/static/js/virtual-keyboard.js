document.addEventListener('DOMContentLoaded', function() {
    const virtualKeyboard = document.getElementById('virtual-keyboard');
    const fullKeyboard = document.getElementById('full-keyboard');
    const numpad = document.getElementById('numpad');
    const keys = virtualKeyboard.querySelectorAll('.key');
    let currentInput = null;
    let tempNumericValue = '';

    // Show keyboard when an input is focused
    document.addEventListener('focusin', function(e) {
        if ((e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') && e.target.type !== 'checkbox') {
            currentInput = e.target;
            // Initialize tempNumericValue with current input value
            tempNumericValue = currentInput.value;
            virtualKeyboard.classList.add('active');

            if (e.target.type === 'number' || e.target.inputMode === 'numeric') {
                fullKeyboard.style.display = 'none';
                numpad.style.display = 'block';
            } else {
                numpad.style.display = 'none';
                fullKeyboard.style.display = 'block';
            }
        }
    });

    // Handle key presses
    keys.forEach(key => {
        key.addEventListener('click', function() {
            if (!currentInput) return;

            const keyValue = this.textContent;

            if (currentInput.type === 'number') {
                // Special handling for number inputs
                switch(keyValue) {
                    case '⌫':
                        tempNumericValue = tempNumericValue.slice(0, -1);
                        break;
                    case 'Close':
                    case 'Exit':
                        virtualKeyboard.classList.remove('active');
                        currentInput.blur();
                        return;
                    case '.':
                        if (!tempNumericValue.includes('.')) {
                            if (tempNumericValue === '') {
                                tempNumericValue = '0.';
                            } else {
                                tempNumericValue += '.';
                            }
                        }
                        break;
                    default:
                        // Only allow digits for number input
                        if (/[0-9]/.test(keyValue)) {
                            tempNumericValue += keyValue;
                        }
                }

                // Update the input value
                if (tempNumericValue === '') {
                    currentInput.value = '';
                } else {
                    // If we're in the middle of typing a decimal number
                    if (tempNumericValue.endsWith('.')) {
                        // Store the in-progress decimal in a data attribute
                        currentInput.dataset.inProgressValue = tempNumericValue;
                        // Show the value up to the decimal point
                        currentInput.value = tempNumericValue.slice(0, -1);
                    } else if (tempNumericValue.includes('.')) {
                        // We have a complete decimal number
                        currentInput.value = tempNumericValue;
                        delete currentInput.dataset.inProgressValue;
                    } else {
                        // We have a whole number
                        currentInput.value = tempNumericValue;
                        delete currentInput.dataset.inProgressValue;
                    }
                }
            } else {
                // Regular text input handling
                switch(keyValue) {
                    case '⌫':
                        currentInput.value = currentInput.value.slice(0, -1);
                        break;
                    case 'Space':
                        currentInput.value += ' ';
                        break;
                    case 'Close':
                    case 'Exit':
                        virtualKeyboard.classList.remove('active');
                        currentInput.blur();
                        break;
                    default:
                        currentInput.value += keyValue;
                }
            }

            // Update the data-value attribute
            currentInput.dataset.value = currentInput.value;

            // Trigger the input event
            const inputEvent = new Event('input', { bubbles: true });
            currentInput.dispatchEvent(inputEvent);
        });
    });

    // Close keyboard when clicking outside OR clicking close
    document.addEventListener('click', function(e) {
        if (!virtualKeyboard.contains(e.target) && e.target !== currentInput || e.target.textContent === 'Close') {
            virtualKeyboard.classList.remove('active');
            if (currentInput) {
                // Ensure we have a valid final value
                if (currentInput.type === 'number') {
                    // If we have an in-progress decimal, complete it with a zero
                    if (currentInput.dataset.inProgressValue && currentInput.dataset.inProgressValue.endsWith('.')) {
                        currentInput.value = currentInput.dataset.inProgressValue + '0';
                    }
                    delete currentInput.dataset.inProgressValue;
                }
                currentInput.blur();
            }
        }
    });
});
