/**
 * Handle data for the document modal
 * 
 * This script provides helper functions for the document edit modal
 * to manage data without causing variable redeclaration issues
 */
 
/**
 * Safely get document data from the iframe content
 */
function getDocumentDataFromIframe(iframeDoc) {
    // Get data from the document-data element
    try {
        const dataDiv = iframeDoc.getElementById('document-data');
        if (dataDiv) {
            return {
                id: dataDiv.dataset.id,
                title: dataDiv.dataset.title,
                documentType: dataDiv.dataset.documentType,
                cancerType: {
                    name: dataDiv.dataset.cancerTypeName
                },
                language: {
                    code: dataDiv.dataset.languageCode
                },
                isPathologyReport: dataDiv.dataset.isPathologyReport === 'true',
                hasExtractedText: dataDiv.dataset.hasExtractedText === 'true',
                uploadedAt: dataDiv.dataset.uploadedAt
            };
        }
    } catch (error) {
        console.error('Error getting document data from iframe:', error);
    }
    
    return null;
}

/**
 * Get the current cancer type ID and organ ID
 */
function getCurrentCancerTypeInfo(iframeDoc) {
    try {
        const currentCancerTypeInput = iframeDoc.querySelector('input[name="current_cancer_type"]');
        if (currentCancerTypeInput && currentCancerTypeInput.value) {
            return {
                typeId: currentCancerTypeInput.value,
                organId: currentCancerTypeInput.dataset.organId,
                name: currentCancerTypeInput.dataset.name
            };
        }
    } catch (e) {
        console.error("Error getting current cancer type:", e);
    }
    
    return {
        typeId: null,
        organId: null,
        name: null
    };
}

/**
 * Update cancer subtypes dropdown
 */
function updateCancerSubtypes(iframeDoc, organId, selectedTypeId = null) {
    if (!organId) return;
    console.log("Updating cancer subtypes for organ ID:", organId);
    
    // Get the cancer type dropdown from iframe
    const cancerTypeSelect = iframeDoc.getElementById('id_cancer_type');
    if (!cancerTypeSelect) {
        console.error("Cancer type select not found in iframe");
        return;
    }
    
    // Clear current options
    cancerTypeSelect.innerHTML = '<option value="">--- Select a cancer type ---</option>';
    
    // Fetch subtypes for this organ
    fetch('/medical/get_subtypes/?organ_id=' + organId, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        console.log("Subtypes HTML received:", html.substring(0, 100) + "...");
        
        // Clean up the received HTML to remove any "--------" options
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Remove any options with dashes only
        tempDiv.querySelectorAll('option').forEach(option => {
            if (option.textContent.trim().match(/^-+$/)) {
                option.remove();
            }
        });
        
        // Set the cleaned HTML
        cancerTypeSelect.innerHTML = tempDiv.innerHTML;
        
        // Auto-select the cancer type if we have the ID and it matches an option
        if (selectedTypeId) {
            console.log("Trying to auto-select cancer type:", selectedTypeId);
            const options = cancerTypeSelect.querySelectorAll('option');
            for (let option of options) {
                if (option.value === selectedTypeId) {
                    console.log("Auto-selecting option:", option.text);
                    option.selected = true;
                    break;
                }
            }
        }
    })
    .catch(error => {
        console.error('Error fetching cancer subtypes:', error);
        // If fetch fails, add a warning and show all cancer types
        
        // Add an error message after the select
        const errorMsg = document.createElement('div');
        errorMsg.className = 'text-red-600 text-xs mt-1';
        errorMsg.textContent = 'Error loading cancer types. Using all available options instead.';
        cancerTypeSelect.parentNode.appendChild(errorMsg);
        
        // Try to get fallback cancer types
        fetch('/medical/get_subtypes/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            cancerTypeSelect.innerHTML = html;
            
            // Select the current cancer type if there is one
            try {
                const cancerInfo = getCurrentCancerTypeInfo(iframeDoc);
                if (cancerInfo.typeId) {
                    const options = cancerTypeSelect.querySelectorAll('option');
                    for (let option of options) {
                        if (option.value === cancerInfo.typeId) {
                            option.selected = true;
                            break;
                        }
                    }
                }
            } catch (e) {
                console.error('Error selecting current cancer type:', e);
            }
        })
        .catch(err => {
            console.error('Error fetching all cancer types:', err);
            // Fallback to just showing the current cancer type if available
            try {
                const cancerInfo = getCurrentCancerTypeInfo(iframeDoc);
                if (cancerInfo.typeId) {
                    const option = document.createElement('option');
                    option.value = cancerInfo.typeId;
                    option.text = "Current: " + cancerInfo.name;
                    option.selected = true;
                    cancerTypeSelect.appendChild(option);
                }
            } catch (e) {
                console.error('Error adding fallback option:', e);
            }
        });
    });
}