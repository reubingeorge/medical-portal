/**
 * Unified document upload functionality with improved cross-browser drag and drop support
 */

// Create and add styles to make the drop zone more prominent and prevent browser defaults
const style = document.createElement('style');
style.textContent = `
    /* Prevent browser from showing files as links during drag */
    [draggable=true] {
        user-select: none;
        -moz-user-select: none;
        -webkit-user-select: none;
        -ms-user-select: none;
    }
    
    /* Enhance drop zone styles */
    #file-drop-zone {
        position: relative;
        z-index: 10;
    }
    
    #file-drop-zone.dragover {
        border-color: #3b82f6 !important;
        background-color: #e0f2fe !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
    }
`;
document.head.appendChild(style);

// Add a stronger global drop prevention at the beginning
document.addEventListener('DOMContentLoaded', function() {
    // Prevent the default browser behavior of navigating to the file
    window.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
    }, true);

    window.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    }, true);

    // Also add to document.body for additional protection
    document.body.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);

    document.body.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);
});

// Main initialization function
function initializeDocumentUpload() {
    console.log('Initializing enhanced document upload system');

    // Find required elements
    const fileDropZone = document.getElementById('file-drop-zone');
    const fileInput = document.querySelector('input[type="file"]');
    const form = fileInput ? fileInput.closest('form') : null;

    // Exit if required elements aren't found
    if (!fileDropZone || !fileInput || !form) {
        console.log('Required elements not found, will retry in 100ms');
        setTimeout(initializeDocumentUpload, 100);
        return;
    }

    console.log('All required elements found, setting up handlers');

    // Setup global drag and drop prevention - capture phase is crucial
    document.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false; // Explicitly return false
    }, true); // Use capture phase

    document.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false; // Explicitly return false
    }, true); // Use capture phase

    // Setup drop zone highlight effects
    fileDropZone.addEventListener('dragenter', function(e) {
        e.preventDefault();
        e.stopPropagation();
        highlightDropZone(this);
    }, false);

    fileDropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        highlightDropZone(this);
    }, false);

    fileDropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        unhighlightDropZone(this);
    }, false);

    // Handle file drop with capture phase
    fileDropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        unhighlightDropZone(this);
        console.log('File dropped on drop zone');

        try {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (!files || files.length === 0) {
                console.log('No files in drop event');
                return false;
            }

            const file = files[0];
            console.log('Dropped file:', file.name, file.type);

            // Validate file type
            const isPdf = file.type === 'application/pdf' ||
                          file.name.toLowerCase().endsWith('.pdf');

            if (!isPdf) {
                alert('Only PDF files are allowed.');
                return false;
            }

            // Set the file using the best approach for each browser
            try {
                // Modern browsers approach (Chrome, Edge, Safari)
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('File assigned to input using DataTransfer');
            } catch (error) {
                console.warn('DataTransfer approach failed, using fallback method:', error);
                // Fallback for Firefox and other browsers
                window.droppedFile = file;
                updateFileDisplay(file.name);
                console.log('File stored in window.droppedFile');
            }
        } catch (err) {
            console.error('Error in drop handler:', err);
        }

        return false; // Explicitly return false
    }, true); // Use capture phase

    // Handle file selection via the file input
    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            console.log('File selected via input:', this.files[0].name);
            updateFileDisplay(this.files[0].name);
        }
    }, false);

    // Handle the remove file button
    const removeButton = document.getElementById('remove-file');
    if (removeButton) {
        removeButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            // Reset file input
            fileInput.value = '';
            window.droppedFile = null;

            // Reset UI
            const placeholder = document.getElementById('file-upload-placeholder');
            const fileDisplay = document.getElementById('selected-file-display');

            if (placeholder && fileDisplay) {
                placeholder.classList.remove('hidden');
                fileDisplay.classList.add('hidden');
            }
        }, false);
    }

    // Handle form submission when a file was dropped (for HTMX)
    form.addEventListener('htmx:beforeRequest', function(event) {
        if (window.droppedFile) {
            console.log('Intercepting HTMX request to add dropped file');
            const config = event.detail;

            // Create and populate FormData with all form fields
            const formData = new FormData();

            // Add all form elements except file input
            new FormData(form).forEach((value, key) => {
                if (key !== fileInput.name) {
                    formData.append(key, value);
                }
            });

            // Add the dropped file
            formData.append(fileInput.name, window.droppedFile);

            // Replace HTMX's formData
            config.formData = formData;
            console.log('HTMX form enhanced with dropped file');
        }
    });

    // Also attach to standard form submission for non-HTMX fallback
    form.addEventListener('submit', function(e) {
        // Validate that a file is selected
        const hasFile = (fileInput.files && fileInput.files.length > 0) || window.droppedFile;

        if (!hasFile) {
            e.preventDefault();
            alert('Please select a file before uploading.');
            return;
        }

        console.log('Form submission validated, file is present');

        // For normal form submission with dropped file
        if (window.droppedFile && !fileInput.files.length) {
            console.log('Using dropped file for standard form submission');

            // Only for non-HTMX forms
            if (!form.hasAttribute('hx-post') && !form.hasAttribute('hx-get')) {
                e.preventDefault();

                const formData = new FormData(form);
                formData.set(fileInput.name, window.droppedFile);

                fetch(form.action, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (response.ok) {
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error submitting form:', error);
                });
            }
        }
    });

    console.log('Document upload system fully initialized');
}

// Function to apply highlight styles to the drop zone
function highlightDropZone(dropZone) {
    dropZone.classList.add('border-blue-500');
    dropZone.classList.add('bg-blue-100');
    dropZone.classList.add('border-2');
    dropZone.classList.add('shadow-lg');
    dropZone.classList.add('dragover'); // Add class for CSS targeting

    // Add a visual indicator text
    const placeholder = document.getElementById('file-upload-placeholder');
    if (placeholder && !document.getElementById('drop-here-message')) {
        const dropMsg = document.createElement('div');
        dropMsg.id = 'drop-here-message';
        dropMsg.className = 'text-blue-600 font-medium text-lg animate-pulse';
        dropMsg.textContent = 'Drop PDF here';
        placeholder.insertBefore(dropMsg, placeholder.firstChild);
    }
}

// Function to remove highlight styles from the drop zone
function unhighlightDropZone(dropZone) {
    dropZone.classList.remove('border-blue-500');
    dropZone.classList.remove('bg-blue-100');
    dropZone.classList.remove('shadow-lg');
    dropZone.classList.remove('dragover'); // Remove class for CSS targeting

    // Remove the drop message
    const dropMsg = document.getElementById('drop-here-message');
    if (dropMsg) {
        dropMsg.remove();
    }
}

// Update the UI to show selected file
function updateFileDisplay(filename) {
    const placeholder = document.getElementById('file-upload-placeholder');
    const fileDisplay = document.getElementById('selected-file-display');
    const filenameElement = document.getElementById('selected-filename');

    if (placeholder && fileDisplay && filenameElement) {
        filenameElement.textContent = filename;
        placeholder.classList.add('hidden');
        fileDisplay.classList.remove('hidden');
    } else {
        console.error('Could not find UI elements to display file');
    }
}

// Initialize on load and after DOM content is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing document upload system');
    // Short delay to ensure modal content is available
    setTimeout(initializeDocumentUpload, 100);
});

// Run immediately as well
setTimeout(initializeDocumentUpload, 50);

// Also reinitialize when modals are opened
document.addEventListener('click', function(e) {
    if (e.target.hasAttribute('hx-get') || e.target.hasAttribute('hx-post')) {
        // Wait for HTMX to load content
        setTimeout(initializeDocumentUpload, 300);
    }
});