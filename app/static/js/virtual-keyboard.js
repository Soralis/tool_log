document.addEventListener('DOMContentLoaded', function() {
    const virtualKeyboard = document.getElementById('virtual-keyboard'); // The container
    const fullKeyboard = document.getElementById('full-keyboard');
    const numpad = document.getElementById('numpad');
    const keys = virtualKeyboard.querySelectorAll('.key'); // Simplified selector
    let currentInput = null;

    // Show keyboard when an input is focused
    document.addEventListener('focusin', function(e) {
        console.log(e.target.tagName, e.target.type)
        if ((e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') && e.target.type !== 'checkbox') {
            currentInput = e.target;
            virtualKeyboard.classList.add('active'); // Show the main container

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
            let currentValue = currentInput.value;

            switch(keyValue) {
                case '⌫':
                    currentValue = currentValue.slice(0, -1);
                    break;
                case 'Space':
                    currentValue += ' ';
                    break;
                case 'Close':
                case 'Exit':
                    virtualKeyboard.classList.remove('active');
                    currentInput.blur();
                    break;
                case '.':
                    if (currentInput.type === 'number') {
                        // For number inputs, handle decimal point specially
                        if (!currentValue.includes('.')) {
                            // If empty or just a minus sign, add a leading zero
                            if (currentValue === '' || currentValue === '-') {
                                currentValue += '0.';
                            } else {
                                currentValue += '.';
                            }
                        }
                    } else {
                        // For non-number inputs, just append the decimal
                        currentValue += '.';
                    }
                    break;
                default:
                    currentValue += keyValue;
            }

            // Update the input value
            if (currentInput.type === 'number') {
                // For number inputs, we need to handle the value specially
                if (currentValue === '' || currentValue === '-' || currentValue === '.' || currentValue === '0.' || 
                    currentValue.endsWith('.') || !isNaN(parseFloat(currentValue))) {
                    currentInput.value = currentValue;
                }
            } else {
                // For non-number inputs, update directly
                currentInput.value = currentValue;
            }

            // Update the data-value attribute
            currentInput.dataset.value = currentValue;

            // Trigger the 'input' event manually
            const inputEvent = new Event('input', { bubbles: true });
            currentInput.dispatchEvent(inputEvent);
        });
    });

    // Close keyboard when clicking outside OR clicking close
    document.addEventListener('click', function(e) {
        // Simplified close logic
         if (!virtualKeyboard.contains(e.target) && e.target !== currentInput || e.target.textContent === 'Close') {
             virtualKeyboard.classList.remove('active');
             if (currentInput) {
                 currentInput.blur();
             }
         }
     });
});
