/**
 * Document editing functionality for admin document management
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize edit functionality
    initializeEditFunctionality();

    // Add event listener to handle dynamic content
    document.body.addEventListener('htmx:afterSwap', function() {
        // Re-initialize after content changes
        initializeEditFunctionality();
    });

    /**
     * Set up all edit-related functionality
     */
    function initializeEditFunctionality() {
        // Setup edit buttons
        setupEditButtons();
        
        // Setup close button handlers
        setupCloseHandlers();
        
        // Setup HTMX event handlers
        setupHTMXHandlers();
    }

    /**
     * Setup all edit buttons with event handlers
     */
    function setupEditButtons() {
        document.querySelectorAll('[data-edit-button]').forEach(button => {
            // Remove existing listeners to prevent duplicates
            button.removeEventListener('click', handleEditButtonClick);
            // Add fresh click handler
            button.addEventListener('click', handleEditButtonClick);
        });
    }

    /**
     * Handle edit button click
     */
    function handleEditButtonClick() {
        const documentId = this.getAttribute('data-id');
        const editModal = document.getElementById('editModal');
        
        if (!editModal) {
            console.error('Edit modal not found in the DOM');
            return;
        }
        
        // Get the form container
        const formContainer = document.getElementById('editFormContainer');
        if (!formContainer) {
            console.error('Edit form container not found');
            return;
        }
        
        // Show the modal with loading state
        showModal(editModal);
        
        // Create the URL to fetch the edit form
        const editUrl = `/chat/admin/documents/${documentId}/edit/`;
        
        // Fetch the edit form using HTMX
        htmx.ajax('GET', editUrl, {
            target: '#editFormContainer',
            swap: 'innerHTML',
            headers: {
                'HX-Request': 'true'
            }
        });
    }

    /**
     * Setup various close handlers for the edit modal
     */
    function setupCloseHandlers() {
        // Close button click handler
        document.addEventListener('click', function(event) {
            if (event.target.matches('[data-close-edit-modal]')) {
                const editModal = document.getElementById('editModal');
                if (editModal) {
                    closeModal(editModal);
                }
            }
        });
        
        // Close when clicking outside modal
        const editModal = document.getElementById('editModal');
        if (editModal) {
            editModal.addEventListener('click', function(event) {
                if (event.target === this) {
                    closeModal(this);
                }
            });
        }
        
        // Close with ESC key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const editModal = document.getElementById('editModal');
                if (editModal && editModal.style.display === 'flex') {
                    closeModal(editModal);
                }
            }
        });
    }

    /**
     * Setup HTMX-related event handlers
     */
    function setupHTMXHandlers() {
        // Handle successful document updates
        document.body.addEventListener('htmx:beforeSwap', function(event) {
            // Check if this is a document update response
            if (event.detail.xhr.getAllResponseHeaders().indexOf('HX-Trigger: documentUpdated') >= 0) {
                // Only handle events for the edit form container
                if (event.detail.target && event.detail.target.id === 'editFormContainer') {
                    // Close the modal
                    const editModal = document.getElementById('editModal');
                    if (editModal) {
                        closeModal(editModal);
                    }
                    
                    // Reload the page to show the updated document
                    window.location.reload();
                    
                    // Prevent the default swap
                    event.preventDefault();
                }
            }
        });
        
        // Handle errors by showing notification
        document.body.addEventListener('htmx:responseError', function(event) {
            if (event.detail.target && event.detail.target.id === 'editFormContainer') {
                console.error('Error in form submission:', event.detail.xhr.status);
                // Error will be displayed in the form
            }
        });
    }
    
    /**
     * Show a modal dialog with animation
     */
    function showModal(modal) {
        modal.style.display = 'flex';
        
        // Add animation class
        setTimeout(() => {
            const modalContainer = modal.querySelector('.modal-container');
            if (modalContainer) {
                modalContainer.classList.add('modal-enter');
            }
        }, 10);
    }
    
    /**
     * Close a modal dialog with animation
     */
    function closeModal(modal) {
        const modalContainer = modal.querySelector('.modal-container');
        if (modalContainer) {
            modalContainer.classList.remove('modal-enter');
            modalContainer.classList.add('modal-leave');
            
            // Hide modal after animation
            setTimeout(() => {
                modal.style.display = 'none';
                modalContainer.classList.remove('modal-leave');
            }, 200);
        } else {
            modal.style.display = 'none';
        }
    }
    
    // Expose closeModal function globally for inline handlers
    window.closeEditModal = function() {
        const editModal = document.getElementById('editModal');
        if (editModal) {
            closeModal(editModal);
        }
    };
});