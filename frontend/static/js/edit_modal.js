/**
 * Simple modal system for document editing
 */

document.addEventListener('DOMContentLoaded', function() {
    // Setup edit button click - using direct DOM element
    const editBtn = document.getElementById('edit-document-btn');
    if (editBtn) {
        editBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Set the flag to ignore iframe load messages
            modalJustOpened = true;
            
            // Clear the flag after a short delay (after iframe has loaded)
            setTimeout(() => {
                modalJustOpened = false;
            }, 1000);
            
            // Get the document ID from the button's data attribute
            const documentId = this.getAttribute('data-document-id');
            if (!documentId) {
                return;
            }
            
            // Store current document ID
            currentEditDocumentId = documentId;
            
            // Create or get modal
            let modal = document.getElementById('edit-document-modal');
            if (modal) {
                // If the modal already exists, remove it first to avoid issues
                modal.remove();
            }
            
            // Create modal container
            modal = document.createElement('div');
            modal.id = 'edit-document-modal';
            modal.className = 'fixed inset-0 z-50 overflow-auto bg-black bg-opacity-50 flex items-center justify-center';
            
            // Create modal content
            const modalContent = document.createElement('div');
            modalContent.className = 'bg-white rounded-lg overflow-hidden shadow-xl transform transition-all sm:max-w-lg sm:w-full';
            
            // Create modal header
            const modalHeader = document.createElement('div');
            modalHeader.className = 'bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center';
            
            const modalTitle = document.createElement('h3');
            modalTitle.className = 'text-lg font-medium text-gray-900';
            modalTitle.textContent = 'Edit Document';
            
            const closeButton = document.createElement('button');
            closeButton.type = 'button';
            closeButton.className = 'text-gray-400 hover:text-gray-500 text-xl font-bold';
            closeButton.innerHTML = '&times;';
            closeButton.addEventListener('click', function() {
                modal.style.display = 'none';
                setTimeout(() => {
                    modal.remove(); // Remove from DOM completely
                }, 100);
            });
            
            modalHeader.appendChild(modalTitle);
            modalHeader.appendChild(closeButton);
            
            // Create modal body
            const modalBody = document.createElement('div');
            modalBody.className = 'px-4 py-5 sm:p-6';
            
            // Create iframe
            const iframe = document.createElement('iframe');
            iframe.src = `/medical/document/${documentId}/review/?format=modal`;
            iframe.className = 'w-full';
            iframe.style.height = '600px';
            iframe.style.border = 'none';
            iframe.style.overflow = 'auto';
            iframe.name = 'edit-form-iframe';
            
            // Add onload event before appending to DOM
            iframe.onload = function() {
                // Give the iframe content a moment to fully initialize
                setTimeout(() => {
                    try {
                        // Check if we can access the iframe document
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (!iframeDoc) {
                            return;
                        }
                        
                        // Adjust iframe height to match content
                        try {
                            const iframeBody = iframeDoc.body;
                            const scrollHeight = Math.max(iframeBody.scrollHeight, 600);
                            iframe.style.height = `${scrollHeight + 20}px`;
                        } catch (e) {
                            // Silently handle errors
                        }
                    } catch (err) {
                        // Silently handle access errors
                    }
                }, 500);
            };
            
            modalBody.appendChild(iframe);
            
            // Assemble modal
            modalContent.appendChild(modalHeader);
            modalContent.appendChild(modalBody);
            modal.appendChild(modalContent);
            
            // Add modal to body
            document.body.appendChild(modal);
            
            // Close modal when clicking outside
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    modal.style.display = 'none';
                    setTimeout(() => {
                        modal.remove(); // Remove from DOM completely
                    }, 100);
                }
            });
        });
    }
    
    // Flag to avoid responding to the iframe's initial load
    let modalJustOpened = false;
    
    // Store the current edit document ID to validate messages
    let currentEditDocumentId = null;
    
    // Handle messages from iframe
    window.addEventListener('message', function(event) {
        // Ignore messages if we just opened the modal
        if (modalJustOpened) {
            return;
        }
        
        // Check if this is a JSON message for errors
        let jsonData = null;
        try {
            if (typeof event.data === 'string' && event.data.startsWith('{')) {
                jsonData = JSON.parse(event.data);
            }
        } catch (e) {
            // Silently handle parsing errors
        }
        
        // Handle error messages
        if (jsonData && jsonData.type === 'error') {
            // Remove any existing indicators
            const existingIndicator = document.getElementById('parent-saving-indicator');
            if (existingIndicator) {
                existingIndicator.remove();
            }
            
            // Show error message
            const errorIndicator = document.createElement('div');
            errorIndicator.id = 'save-error-indicator';
            errorIndicator.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
            
            // Format error details if available
            let errorDetails = '';
            if (jsonData.details && jsonData.details.length > 0) {
                errorDetails = '<ul class="text-left mt-4 bg-red-50 p-3 rounded text-sm">';
                jsonData.details.forEach(failure => {
                    errorDetails += `
                        <li class="mb-2 pb-2 border-b border-red-200">
                            <strong>Field:</strong> ${failure.field}<br>
                            <strong>Submitted:</strong> ${failure.submitted}<br>
                            <strong>Stored:</strong> ${failure.stored || 'Not saved'}
                        </li>
                    `;
                });
                errorDetails += '</ul>';
            }
            
            errorIndicator.innerHTML = `
                <div class="bg-white p-6 rounded-lg shadow-xl text-center max-w-lg">
                    <div class="mx-auto mb-4 text-red-500 text-4xl">⚠</div>
                    <p class="text-xl font-medium text-gray-800">${jsonData.message}</p>
                    <p class="text-sm text-gray-500 mt-2">Please edit the document again and retry.</p>
                    ${errorDetails}
                    <button id="dismiss-error" class="mt-6 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                        Dismiss
                    </button>
                </div>
            `;
            
            document.body.appendChild(errorIndicator);
            
            // Add event listener to dismiss button
            setTimeout(() => {
                const dismissBtn = document.getElementById('dismiss-error');
                if (dismissBtn) {
                    dismissBtn.addEventListener('click', function() {
                        errorIndicator.remove();
                    });
                }
            }, 100);
            
        } else if (event.data === 'document_saved') {
            console.log('Document saved message received, closing modal and showing confirmation');
            
            // Show success message before reloading
            const successIndicator = document.createElement('div');
            successIndicator.id = 'save-success-indicator';
            successIndicator.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
            successIndicator.innerHTML = `
                <div class="bg-white p-6 rounded-lg shadow-xl text-center">
                    <div class="mx-auto mb-4 text-green-500 text-4xl">✓</div>
                    <p class="text-xl font-medium text-gray-800">Changes saved!</p>
                    <p class="text-sm text-gray-500 mt-2">Reloading page...</p>
                </div>
            `;
            document.body.appendChild(successIndicator);
            
            // Close any open modals using multiple methods to ensure closure
            const modal = document.getElementById('edit-document-modal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.add('hidden');
                setTimeout(() => {
                    try {
                        modal.remove(); // Remove from DOM completely
                    } catch (e) {
                        // Silently handle any errors
                    }
                }, 100);
            }
            
            // Also hide the modal container if it exists
            const modalContainer = document.getElementById('modal-container');
            if (modalContainer) {
                modalContainer.classList.add('hidden');
                modalContainer.style.display = 'none';
            }
            
            // Close all elements with "modal" in their ID just to be thorough
            document.querySelectorAll('[id*="modal"]').forEach(el => {
                el.classList.add('hidden');
                el.style.display = 'none';
            });
            
            // Reload the page after a brief delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else if (event.data === 'document_saving') {
            
            // Show saving indicator
            const savingIndicator = document.createElement('div');
            savingIndicator.id = 'parent-saving-indicator';
            savingIndicator.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
            savingIndicator.innerHTML = `
                <div class="bg-white p-6 rounded-lg shadow-xl text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p class="text-xl font-medium text-gray-800">Saving changes...</p>
                    <p class="text-sm text-gray-500 mt-2">Verifying changes are saved to database...</p>
                </div>
            `;
            document.body.appendChild(savingIndicator);
            
            // Close the modal and parent container
            const modal = document.getElementById('edit-document-modal');
            if (modal) {
                modal.style.display = 'none';
                setTimeout(() => {
                    modal.remove(); // Remove from DOM completely
                }, 100);
            }
            
            // Also hide the modal container if it exists
            const modalContainer = document.getElementById('modal-container');
            if (modalContainer) {
                modalContainer.classList.add('hidden');
            }
            
            // Set a fallback in case the save message never comes
            setTimeout(() => {
                // Check if the indicator still exists
                const indicator = document.getElementById('parent-saving-indicator');
                if (indicator) {
                    // Replace indicator with an error message
                    indicator.innerHTML = `
                        <div class="bg-white p-6 rounded-lg shadow-xl text-center">
                            <div class="mx-auto mb-4 text-orange-500 text-4xl">⚠</div>
                            <p class="text-xl font-medium text-gray-800">Verification Timeout</p>
                            <p class="text-sm text-gray-500 mt-2">Unable to verify if changes were saved.</p>
                            <button id="continue-anyway" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                                Continue Anyway
                            </button>
                        </div>
                    `;
                    
                    // Add event listener to continue button
                    setTimeout(() => {
                        const continueBtn = document.getElementById('continue-anyway');
                        if (continueBtn) {
                            continueBtn.addEventListener('click', function() {
                                window.location.reload();
                            });
                        }
                    }, 100);
                }
            }, 10000); // 10 second timeout
        } else if (event.data === 'close_modal') {
            console.log('Close modal message received');
            
            // Close modal on cancel using multiple methods to ensure closure
            const modal = document.getElementById('edit-document-modal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.add('hidden');
                setTimeout(() => {
                    try {
                        modal.remove(); // Remove from DOM completely
                    } catch (e) {
                        // Silently handle any errors
                    }
                }, 100);
            }
            
            // Also hide the modal container if it exists
            const modalContainer = document.getElementById('modal-container');
            if (modalContainer) {
                modalContainer.classList.add('hidden');
                modalContainer.style.display = 'none';
            }
            
            // Close all elements with "modal" in their ID just to be thorough
            document.querySelectorAll('[id*="modal"]').forEach(el => {
                el.classList.add('hidden');
                el.style.display = 'none';
            });
        }
    });
});