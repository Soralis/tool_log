document.addEventListener('DOMContentLoaded', function() {
    const virtualKeyboard = document.getElementById('virtual-keyboard');
    const fullKeyboard = document.getElementById('full-keyboard');
    const numpad = document.getElementById('numpad');
    const keys = virtualKeyboard.querySelectorAll('.key');
    let currentInput = null;

    // Show keyboard when an input is focused
    document.addEventListener('focusin', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            currentInput = e.target;
            virtualKeyboard.style.display = 'block';
            
            // Check if the input type is number
            if (e.target.type === 'number' || e.target.inputMode === 'numeric') {
                fullKeyboard.style.display = 'none';
                numpad.style.display = 'block';
            } else {
                fullKeyboard.style.display = 'block';
                numpad.style.display = 'none';
            }
        }
    });

    // Handle key presses
    keys.forEach(key => {
        key.addEventListener('click', function() {
            if (!currentInput) return;

            const keyValue = this.textContent;

            switch(keyValue) {
                case '⌫':
                    currentInput.value = currentInput.value.slice(0, -1);
                    break;
                case 'Space':
                    currentInput.value += ' ';
                    break;
                case 'Close':
                    virtualKeyboard.style.display = 'none';
                    currentInput.blur();
                    break;
                case '.':
                    // Only add decimal point if it's a number input and doesn't already contain a decimal point
                    if (currentInput.type === 'number' && !currentInput.value.includes('.')) {
                        currentInput.value += keyValue;
                    }
                    break;
                default:
                    currentInput.value += keyValue;
            }

            // Trigger input event to ensure any listeners are notified
            const event = new Event('input', { bubbles: true });
            currentInput.dispatchEvent(event);
        });
    });

    // Close keyboard when clicking outside
    document.addEventListener('click', function(e) {
        if (!virtualKeyboard.contains(e.target) && e.target !== currentInput) {
            virtualKeyboard.style.display = 'none';
            if (currentInput) {
                currentInput.blur();
            }
        }
    });
});