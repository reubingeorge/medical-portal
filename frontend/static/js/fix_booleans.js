/**
 * Fix Python boolean values in rendered HTML
 * 
 * Django templates render Python's True/False as literal text,
 * but JavaScript requires lowercase true/false.
 * This script runs after the page loads to fix this issue.
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Running Python boolean fix');
    
    // First look for scripts with the data-fix-booleans attribute
    const markedScripts = document.querySelectorAll('script[data-fix-booleans]');
    
    if (markedScripts.length > 0) {
        markedScripts.forEach(script => {
            // Get the script content
            let content = script.textContent;
            
            // Replace Python True/False with JavaScript true/false
            content = content.replace(/\bTrue\b/g, 'true')
                             .replace(/\bFalse\b/g, 'false')
                             .replace(/\bNone\b/g, 'null');
            
            // Create a new script element
            const fixedScript = document.createElement('script');
            fixedScript.setAttribute('data-fixed', 'true');
            fixedScript.textContent = content;
            
            // Replace the old script with the fixed one
            script.parentNode.replaceChild(fixedScript, script);
        });
    } else {
        // No marked scripts found, try to find any with Python literals
        // This is a fallback for scripts that aren't explicitly marked
        const allScripts = document.querySelectorAll('script:not([data-fixed])');
        
        allScripts.forEach(script => {
            // Only process if it contains Python literals
            if (script.textContent.includes('True') || 
                script.textContent.includes('False') || 
                script.textContent.includes('None')) {
                
                let content = script.textContent;
                
                // Replace Python literals with JavaScript equivalents
                content = content.replace(/\bTrue\b/g, 'true')
                                 .replace(/\bFalse\b/g, 'false')
                                 .replace(/\bNone\b/g, 'null');
                
                // Create a new script element
                const fixedScript = document.createElement('script');
                fixedScript.setAttribute('data-fixed', 'true');
                fixedScript.textContent = content;
                
                // Replace the old script with the fixed one
                if (script.parentNode) {
                    script.parentNode.replaceChild(fixedScript, script);
                }
            }
        });
    }
});