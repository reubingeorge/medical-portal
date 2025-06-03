/**
 * AI Debug Logging Functionality
 * Provides consistent console logging for AI analysis results across the application
 */

function logAIAnalysisResults(label, data) {
    console.group(`=== ${label} ===`);
    
    if (data) {
        console.log("Data:", data);
        
        // Log specific fields if they exist
        if (data.cancer_type) {
            console.log("Cancer Type:", data.cancer_type);
        }
        
        if (data.figo_stage) {
            console.log("FIGO Stage:", data.figo_stage);
        }
        
        if (data.final_pathologic_stage) {
            console.log("Final Pathologic Stage:", data.final_pathologic_stage);
        }
    } else {
        console.log("No data available");
    }
    
    console.groupEnd();
}

function logDocumentMetadata(document) {
    if (!document) {
        console.log("No document metadata available");
        return;
    }
    
    console.group("=== DOCUMENT METADATA ===");
    
    // Basic document information
    console.log("ID:", document.id || "N/A");
    console.log("Title:", document.title || "N/A");
    console.log("Document Type:", document.document_type || "N/A");
    console.log("Upload Date:", document.uploaded_at || "N/A");
    
    // Medical information
    console.log("Cancer Type:", document.cancer_type?.name || "None");
    console.log("Language:", document.language?.code || "None");
    console.log("Is Pathology Report:", document.is_pathology_report ? "Yes" : "No");
    
    // Text analysis
    if (document.extracted_text) {
        const textLength = document.extracted_text.length;
        console.log("Extracted Text:", 
            textLength > 100 
                ? `${document.extracted_text.substring(0, 100)}... (${textLength} chars)` 
                : document.extracted_text
        );
    } else {
        console.log("Extracted Text: None");
    }
    
    console.groupEnd();
}

function logSessionData(session) {
    if (!session || Object.keys(session).length === 0) {
        console.log("No session data available");
        return;
    }
    
    console.group("=== SESSION DATA ===");
    
    // AI processing results
    if (session.ai_processing_results) {
        console.log("AI Processing Results:", session.ai_processing_results);
    }
    
    // Cancer type matching
    if (session.cancer_type_matching) {
        console.log("Cancer Type Matching:", session.cancer_type_matching);
    }
    
    console.groupEnd();
}