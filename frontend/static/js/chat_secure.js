/**
 * Secure Chat Interface JavaScript
 * Ensures CSRF tokens are NEVER included in URLs
 */

document.addEventListener('DOMContentLoaded', function() {
    // Safety check: Remove any CSRF tokens from URL
    function cleanUrl() {
        const url = new URL(window.location);
        const params = url.searchParams;
        
        // Remove sensitive parameters
        const sensitiveParams = ['csrfmiddlewaretoken', 'csrf_token', 'token', 'sessionid'];
        let modified = false;
        
        sensitiveParams.forEach(param => {
            if (params.has(param)) {
                params.delete(param);
                modified = true;
                console.warn(`Removed ${param} from URL for security`);
            }
        });
        
        // Update URL without reload if modified
        if (modified) {
            const cleanUrl = url.origin + url.pathname + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({}, document.title, cleanUrl);
        }
    }
    
    // Clean URL on load
    cleanUrl();
    
    // Ensure all forms use POST
    function secureForm(form) {
        // Force POST method
        if (form.method !== 'post' && form.method !== 'POST') {
            console.warn(`Changing form method from ${form.method} to POST for security`);
            form.method = 'POST';
        }
        
        // Ensure CSRF token is in form data, not URL
        const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!csrfInput) {
            const csrfToken = getCookie('csrftoken');
            if (csrfToken) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'csrfmiddlewaretoken';
                input.value = csrfToken;
                form.appendChild(input);
            }
        }
    }
    
    // Secure all forms
    document.querySelectorAll('form').forEach(secureForm);
    
    // Monitor for dynamically added forms
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeName === 'FORM') {
                    secureForm(node);
                } else if (node.querySelectorAll) {
                    node.querySelectorAll('form').forEach(secureForm);
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Intercept any GET requests that might include tokens
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (typeof url === 'string') {
            const urlObj = new URL(url, window.location.origin);
            const sensitiveParams = ['csrfmiddlewaretoken', 'csrf_token', 'token'];
            
            sensitiveParams.forEach(param => {
                if (urlObj.searchParams.has(param)) {
                    console.error(`SECURITY WARNING: Attempted to send ${param} in URL`);
                    urlObj.searchParams.delete(param);
                }
            });
            
            url = urlObj.toString();
        }
        
        return originalFetch.call(this, url, options);
    };
    
    // Helper to get cookie value
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Log security status
    console.log('Chat security measures active');
});