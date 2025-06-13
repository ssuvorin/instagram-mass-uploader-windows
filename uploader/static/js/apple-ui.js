/**
 * Instagram Uploader - Apple UI JavaScript
 * Enhances UI experience and fixes Bootstrap modal issues
 */

document.addEventListener('DOMContentLoaded', function() {
    // Apply fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('animate-fade-in');
    }
    
    // Add subtle hover effects to cards
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.03)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Enhance form controls with subtle feedback
    const formControls = document.querySelectorAll('.form-control, .form-select');
    formControls.forEach(control => {
        control.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        control.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                document.querySelector(targetId).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    });

    // Add subtle hover effect to table rows
    const tableRows = document.querySelectorAll('.table-hover tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(3px)';
            this.style.transition = 'transform 0.2s ease';
        });
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
    
    // Enhance buttons with subtle feedback
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mousedown', function() {
            this.style.transform = 'scale(0.98)';
        });
        button.addEventListener('mouseup', function() {
            this.style.transform = 'scale(1)';
        });
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Fix modal backdrop issues - Ensure no darkening of background
    fixModalBackdrops();
    
    // Handle modal events
    setupModalEventHandlers();
    
    // Ensure all buttons are clickable
    makeAllButtonsClickable();
});

/**
 * Removes backdrop darkening by making modals fully transparent
 */
function fixModalBackdrops() {
    // Remove any existing backdrop elements when page loads
    let existingBackdrops = document.querySelectorAll('.modal-backdrop');
    existingBackdrops.forEach(backdrop => {
        backdrop.parentNode.removeChild(backdrop);
    });
    
    // Override Bootstrap modal backdrop style
    let style = document.createElement('style');
    style.textContent = `
        .modal-backdrop {
            opacity: 0 !important;
            background-color: transparent !important;
            pointer-events: none !important;
        }
        body.modal-open {
            overflow: auto !important;
            padding-right: 0 !important;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Sets up event handlers for modal dialogs
 */
function setupModalEventHandlers() {
    // Intercept modal show events
    document.addEventListener('show.bs.modal', function(e) {
        // Stop any backdrop effects immediately
        setTimeout(() => {
            let backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => {
                backdrop.style.opacity = '0';
                backdrop.style.backgroundColor = 'transparent';
                backdrop.style.pointerEvents = 'none';
            });
            
            // Remove body padding and overflow restrictions
            document.body.style.paddingRight = '0';
            document.body.style.overflow = 'auto';
        }, 0);
    }, true);
    
    // Set up click handlers for modal buttons
    let modalButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
    modalButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            let targetSelector = button.getAttribute('data-bs-target') || 
                                button.getAttribute('href');
            
            if (!targetSelector) return;
            
            let modal = document.querySelector(targetSelector);
            if (!modal) return;
            
            // Set the modal and its contents to be easily clickable
            modal.style.background = 'transparent';
            
            // Make sure all the modal's buttons are clickable
            let modalButtons = modal.querySelectorAll('.btn, button');
            modalButtons.forEach(btn => {
                btn.style.position = 'relative';
                btn.style.zIndex = '5';
            });
        });
    });
}

/**
 * Makes all buttons in the UI easily clickable
 */
function makeAllButtonsClickable() {
    let allButtons = document.querySelectorAll('button, .btn, a.btn, [type="button"], [type="submit"]');
    allButtons.forEach(btn => {
        btn.style.position = 'relative';
        btn.style.zIndex = '1';
    });
} 