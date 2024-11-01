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
                    // Only add decimal point if it's a number input and doesn't already contain a decimal point
                    if (currentInput.type === 'number' && !currentValue.includes('.')) {
                        currentValue = currentValue ? currentValue + '.' : '0.';
                    }
                    break;
                default:
                    currentValue += keyValue;
            }

            // Update the data-value attribute
            currentInput.dataset.value = currentValue;

            // Update the actual input value only if it's a valid number
            if (currentInput.type === 'number') {
                const numberValue = parseFloat(currentValue);
                if (!isNaN(numberValue)) {
                    currentInput.value = numberValue;
                } else if (currentValue === '' || currentValue === '-' || currentValue.endsWith('.')) {
                    currentInput.value = currentValue;
                }
            } else {
                currentInput.value = currentValue;
            }

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