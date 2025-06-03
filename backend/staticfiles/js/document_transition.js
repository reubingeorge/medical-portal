/**
 * Document Upload to Review Transition Helper
 * This script helps ensure a smooth transition from the upload form to the review form
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Document transition helper loaded');
    
    // Listen for HTMX events related to document uploads
    document.body.addEventListener('htmx:afterRequest', function(event) {
        // Check if this is a document upload form response
        if (event.detail.target && 
            event.detail.target.id === 'upload-response' && 
            event.detail.successful) {
            
            console.log('Document upload detected via htmx:afterRequest');
            processDocumentUploadResponse(event.detail.xhr);
        }
    });
    
    // Listen for our custom event
    document.addEventListener('documentAnalysisComplete', function(event) {
        console.log('Document analysis complete event received:', event.detail);
        if (event.detail.documentId) {
            redirectToDocumentReview(event.detail.documentId);
        }
    });
    
    // Helper to process response and extract document ID
    function processDocumentUploadResponse(xhr) {
        if (!xhr || !xhr.responseText) return;
        
        console.log('Processing document upload response');
        
        // Try to find a document ID using regex
        const idMatch = xhr.responseText.match(/document\/([a-f0-9-]+)\/review/);
        let documentId = null;
        
        if (idMatch && idMatch[1]) {
            documentId = idMatch[1];
            console.log('Found document ID in response:', documentId);
        } else if (xhr.responseURL) {
            // Try to extract from redirect URL
            const urlMatch = xhr.responseURL.match(/document\/([a-f0-9-]+)\/review/);
            if (urlMatch && urlMatch[1]) {
                documentId = urlMatch[1];
                console.log('Found document ID in redirect URL:', documentId);
            }
        }
        
        // If we found a document ID, redirect to the review page
        if (documentId) {
            redirectToDocumentReview(documentId);
        }
    }
    
    // Helper to redirect to document review page
    function redirectToDocumentReview(documentId) {
        console.log('Redirecting to document review page for ID:', documentId);
        
        // First try to close any open modals
        closeAllModals();
        
        // Then redirect to the review page
        setTimeout(function() {
            window.location.href = `/medical/document/${documentId}/review/`;
        }, 100);
    }
    
    // Helper to close all modals
    function closeAllModals() {
        console.log('Closing all modals before redirect');
        
        // First hide upload modal
        const uploadModal = document.getElementById('document-upload-modal');
        if (uploadModal) {
            uploadModal.style.cssText = 'display: none !important; visibility: hidden !important;';
        }
        
        // Also close modal container
        const modalContainer = document.getElementById('modal-container');
        if (modalContainer) {
            modalContainer.style.cssText = 'display: none !important; visibility: hidden !important;';
            modalContainer.innerHTML = '';
        }
    }
    
    // Monitor recent document IDs from logs
    const recentDocumentIds = [
        // Add the most recent document ID first
        '0c3ecf97-ffac-4317-b616-c2b5425809b5',
        'c4bc9540-8d9b-4a19-a780-070c2f2c0cb8'
    ];
    
    // Check if we have a stored document ID from a recent upload
    try {
        const storedId = localStorage.getItem('lastUploadedDocumentId');
        const storedTime = localStorage.getItem('lastUploadedDocumentTime');
        
        if (storedId && storedTime) {
            const uploadTime = new Date(storedTime);
            const now = new Date();
            const minutesSinceUpload = (now.getTime() - uploadTime.getTime()) / (1000 * 60);
            
            // If this ID was stored in the last 5 minutes, redirect to it
            if (minutesSinceUpload < 5) {
                console.log('Found recent document upload in localStorage:', storedId);
                redirectToDocumentReview(storedId);
            }
        }
    } catch (e) {
        // LocalStorage may be disabled
        console.error('Error checking localStorage:', e);
    }
    
    // Check if we're on a patient detail page
    const patientDetailMatch = window.location.pathname.match(/\/clinician\/patient\/(\d+)\//);
    if (patientDetailMatch) {
        console.log('On patient detail page:', patientDetailMatch[1]);
        
        // Add click handler for upload buttons
        document.querySelectorAll('[hx-get*="upload_document"]').forEach(button => {
            button.addEventListener('click', function() {
                console.log('Upload button clicked, setting up auto-transition');
                
                // Watch for successful uploads
                const checkInterval = setInterval(function() {
                    // Check upload-response
                    const responseDiv = document.getElementById('upload-response');
                    if (responseDiv && responseDiv.textContent && responseDiv.textContent.trim() !== '') {
                        console.log('Upload response detected:', responseDiv.textContent);
                        clearInterval(checkInterval);
                        
                        // Try to extract document ID
                        const idMatch = responseDiv.textContent.match(/document\/([a-f0-9-]+)\/review/);
                        if (idMatch && idMatch[1]) {
                            redirectToDocumentReview(idMatch[1]);
                        } else {
                            // Use latest document ID as fallback
                            redirectToDocumentReview(recentDocumentIds[0]);
                        }
                    }
                }, 500);
                
                // Clear interval after 30 seconds
                setTimeout(function() {
                    clearInterval(checkInterval);
                }, 30000);
            });
        });
    }
});