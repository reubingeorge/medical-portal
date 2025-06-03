/**
 * Form validation and verification helpers
 */

// Simple string hashing function for comparing form values
function hashString(str) {
    let hash = 0;
    if (str.length === 0) return hash;
    
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
}

// Hash form data to a string for comparison
function hashFormData(form) {
    if (!form || !form.elements) return null;
    
    const formData = {};
    const formElements = form.elements;
    
    for (let i = 0; i < formElements.length; i++) {
        const element = formElements[i];
        
        // Skip buttons and hidden fields except those we specifically want to include
        if (
            (element.type === 'button' || 
             element.type === 'submit' || 
             element.type === 'reset' || 
             (element.type === 'hidden' && element.name !== 'current_cancer_type')) || 
            !element.name
        ) {
            continue;
        }
        
        // Handle different form element types
        if (element.type === 'checkbox' || element.type === 'radio') {
            formData[element.name] = element.checked;
        } else if (element.type === 'select-one' || element.type === 'select-multiple') {
            formData[element.name] = Array.from(element.selectedOptions).map(opt => opt.value).join(',');
        } else {
            formData[element.name] = element.value.trim();
        }
    }
    
    // Create a stable string representation and hash it
    const dataString = JSON.stringify(formData, Object.keys(formData).sort());
    return {
        hash: hashString(dataString),
        data: formData
    };
}

// Verify if form was saved correctly by checking values
function verifyFormSaved(beforeHash, formData, verifyUrl) {
    return fetch(verifyUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch current data');
            }
            return response.json();
        })
        .then(currentData => {
            // Compare important fields
            const criticalFields = ['title', 'description', 'patient_notes', 'cancer_type'];
            const failures = [];
            
            for (const field of criticalFields) {
                if (formData[field] !== undefined && 
                    currentData[field] !== undefined &&
                    formData[field] !== currentData[field]) {
                    failures.push({
                        field,
                        submitted: formData[field],
                        stored: currentData[field]
                    });
                }
            }
            
            if (failures.length > 0) {
                console.error('Form save verification failed:', failures);
                return {
                    success: false,
                    failures
                };
            }
            
            return {
                success: true
            };
        });
}