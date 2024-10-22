// Burger Menu
function toggleMenu() {
    const menuItems = document.querySelector('.menu-items');
    menuItems.classList.toggle('show');
}

document.body.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.xhr.status === 200) {
        document.body.dispatchEvent(new Event(`Loaded`))
    } else if (event.detail.xhr.status === 201) {
        showToast('Added successfully!');
        closeModal(`createModal`);
        document.querySelector(`#createModal form`).reset();
        document.body.dispatchEvent(new Event(`Added`));
    } else if (event.detail.xhr.status === 202) {
        showToast('Updated successfully!');
        closeModal(`editModal`);
        document.body.dispatchEvent(new Event(`Edited`));
    } else if (event.detail.xhr.status === 204) {
        document.body.dispatchEvent(new Event(`Deleted`));
    } else {
        showToast('Error: ' + event.detail.xhr.responseText, 'error');
    }
});

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }, 100);
}

// Open modal
document.getElementById('createButton').addEventListener('click', function() {
    openModal('create');
});

// Close modals
document.querySelectorAll('.close').forEach(function(closeButton) {
    closeButton.addEventListener('click', function() {
        closeModal(this.getAttribute('data-modal'));
    });
});

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = "none";
    }
});

    
function openModal(type) {
    console.log(type)
    const modalId = `${type}Modal`;
    console.log('Opening modal:', modalId);
    document.getElementById(modalId).style.display = "flex";
}

function closeModal(modalId) {
    console.log('Closing modal:', modalId);
    document.getElementById(modalId).style.display = "none";
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = "none";
    }
}