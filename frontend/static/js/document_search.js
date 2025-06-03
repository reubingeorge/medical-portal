/**
 * Enhanced document search with live search functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Focus the search input when the page loads if it has a value
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;

    // If there's a value, focus and position cursor at the end
    if (searchInput.value) {
        searchInput.focus();
        const val = searchInput.value;
        searchInput.value = '';
        searchInput.value = val;
    }

    // Setup variables for debounce function
    let searchTimeout = null;
    const DEBOUNCE_TIME = 800; // ms - significantly increased for seamless experience
    let lastSearchValue = searchInput.value.trim(); // Track the last value we searched for

    // Add input event listener for live search with debounce and smoothness
    searchInput.addEventListener('input', function(e) {
        // Clear any pending timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Get current value
        const searchValue = this.value.trim();
        
        // Skip if the value hasn't changed from the last search
        if (searchValue === lastSearchValue) {
            return;
        }
        
        // Get current page size
        const pageSizeSelect = document.getElementById('pageSize');
        const pageSize = pageSizeSelect ? pageSizeSelect.value : '5';

        // Create a loading clone to avoid flicker
        const documentContainer = document.getElementById('document-list-container');
        
        // Set a new timeout with longer delay for a more seamless experience
        searchTimeout = setTimeout(() => {
            // Update the last search value
            lastSearchValue = searchValue;
            
            // Build the URL for the HTMX request
            let searchUrl = `?q=${encodeURIComponent(searchValue)}`;
            if (pageSize) {
                searchUrl += `&size=${pageSize}`;
            }

            // Disable indicators and add the progress class
            document.body.classList.add('search-in-progress');
            
            // OPTION 1: Use fetch for even more control (smoother)
            fetch(searchUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.text();
                })
                .then(html => {
                    // Parse the HTML response
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    
                    // Get the content we want to insert
                    const newContent = doc.querySelector('#document-list-container');
                    
                    if (newContent) {
                        // Apply a smooth transition
                        documentContainer.style.transition = 'opacity 0.15s ease-in-out';
                        documentContainer.style.opacity = '0';
                        
                        // Insert the new content after a brief fade
                        setTimeout(() => {
                            documentContainer.innerHTML = newContent.innerHTML;
                            
                            // Fade back in
                            setTimeout(() => {
                                documentContainer.style.opacity = '1';
                                
                                // Clean up
                                document.body.classList.remove('search-in-progress');
                                
                                // Update URL for browser history without reloading
                                const url = new URL(window.location);
                                if (searchValue) {
                                    url.searchParams.set('q', searchValue);
                                } else {
                                    url.searchParams.delete('q');
                                }
                                window.history.replaceState({}, '', url);
                                
                                // Re-initialize any event listeners
                                initializeEventListeners();
                            }, 50);
                        }, 150);
                    }
                })
                .catch(error => {
                    // Just silently fail and maintain the current UI state
                    document.body.classList.remove('search-in-progress');
                    console.log("Search error occurred, maintaining current UI state");
                });
            
        }, DEBOUNCE_TIME);
    });
});

// Function to re-initialize event handlers after content changes
function initializeEventListeners() {
    // Re-attach page size dropdown handler
    const pageSizeDropdown = document.getElementById('pageSize');
    if (pageSizeDropdown) {
        pageSizeDropdown.addEventListener('change', function() {
            const size = this.value;
            const url = new URL(window.location);
            url.searchParams.set('size', size);
            window.history.replaceState({}, '', url);
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize event handlers on page load
    initializeEventListeners();
    
    // Get the search input again in case we're in a new DOM context
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;
    
    // Handle form submission to prevent default behavior and use our live search instead
    const searchForm = searchInput.closest('form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent form submission
            // Input event will handle the search

            // Specifically trigger input event in case Enter was pressed with no change
            const event = new Event('input', { bubbles: true });
            searchInput.dispatchEvent(event);
        });
    }

    // Clear search button functionality - using the smooth approach
    const clearSearchButtons = document.querySelectorAll('a[href*="?"]');
    clearSearchButtons.forEach(button => {
        if (button.querySelector('svg[d*="M6 18L18 6M6 6l12 12"]')) {
            button.addEventListener('click', function(e) {
                e.preventDefault();

                // Clear the search input
                searchInput.value = '';
                lastSearchValue = '';
                
                // Create URL for direct request to clear the search
                const pageSizeSelect = document.getElementById('pageSize');
                const pageSize = pageSizeSelect ? pageSizeSelect.value : '5';
                let clearUrl = '?';
                if (pageSize) {
                    clearUrl += `size=${pageSize}`;
                }
                
                // Get the document container
                const documentContainer = document.getElementById('document-list-container');
                
                // Add search-in-progress class
                document.body.classList.add('search-in-progress');
                
                // Apply smooth fade out
                documentContainer.style.transition = 'opacity 0.15s ease-in-out';
                documentContainer.style.opacity = '0';
                
                // Use fetch for smooth transition instead of HTMX
                setTimeout(() => {
                    fetch(clearUrl)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error('Network response was not ok');
                            }
                            return response.text();
                        })
                        .then(html => {
                            // Parse the HTML response
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            
                            // Get the content we want to insert
                            const newContent = doc.querySelector('#document-list-container');
                            
                            if (newContent) {
                                // Insert new content
                                documentContainer.innerHTML = newContent.innerHTML;
                                
                                // Fade back in
                                setTimeout(() => {
                                    documentContainer.style.opacity = '1';
                                    
                                    // Clean up
                                    document.body.classList.remove('search-in-progress');
                                    
                                    // Update URL for browser history
                                    const url = new URL(window.location);
                                    url.searchParams.delete('q');
                                    window.history.replaceState({}, '', url);
                                    
                                    // Re-initialize event listeners
                                    initializeEventListeners();
                                }, 50);
                            }
                        })
                        .catch(error => {
                            // Just silently fail and restore UI
                            documentContainer.style.opacity = '1';
                            document.body.classList.remove('search-in-progress');
                        });
                }, 150);
            });
        }
    });
});

// Aggressively disable ALL indicators
document.addEventListener('DOMContentLoaded', function() {
    // Function to forcefully hide any indicator that might appear
    function hideAllIndicators() {
        // Hide the main indicator
        var mainIndicator = document.getElementById('loading-indicator');
        if (mainIndicator) {
            mainIndicator.style.display = 'none';
            mainIndicator.style.visibility = 'hidden';
            mainIndicator.style.opacity = '0';
        }
        
        // Hide any htmx indicators
        var indicators = document.querySelectorAll('.htmx-indicator');
        indicators.forEach(function(indicator) {
            indicator.style.display = 'none';
            indicator.style.visibility = 'hidden';
            indicator.style.opacity = '0';
        });
    }
    
    // Run on page load
    hideAllIndicators();
    
    // Run at intervals to ensure indicators stay hidden
    setInterval(hideAllIndicators, 100);
    
    // Run before and after any HTMX request
    document.addEventListener('htmx:beforeRequest', hideAllIndicators);
    document.addEventListener('htmx:afterRequest', hideAllIndicators);
});

// Handle HTMX errors
document.addEventListener('htmx:responseError', function() {
    document.body.classList.remove('search-in-progress');
});

document.addEventListener('htmx:sendError', function() {
    document.body.classList.remove('search-in-progress');
});

// Re-attach event handlers after HTMX content swaps
document.addEventListener('htmx:afterSwap', function(event) {
    // Re-attach page size dropdown handler
    const pageSizeDropdown = document.getElementById('pageSize');
    if (pageSizeDropdown) {
        pageSizeDropdown.addEventListener('change', function() {
            const size = this.value;
            // HTMX will handle the actual request, but we'll update the URL for consistency
            const url = new URL(window.location);
            url.searchParams.set('size', size);
            window.history.replaceState({}, '', url);
        });
    }

    // Re-attach clear search button functionality
    const searchInput = document.querySelector('input[name="q"]');
    const clearSearchButtons = document.querySelectorAll('a[href*="?"]');
    clearSearchButtons.forEach(button => {
        if (button.querySelector('svg[d*="M6 18L18 6M6 6l12 12"]') && searchInput) {
            button.addEventListener('click', function(e) {
                e.preventDefault();

                // Clear the search input
                searchInput.value = '';
                
                // Add search-in-progress class for this action too
                document.body.classList.add('search-in-progress');

                // Create URL for direct request to clear the search
                const pageSizeSelect = document.getElementById('pageSize');
                const pageSize = pageSizeSelect ? pageSizeSelect.value : '5';
                let clearUrl = '?';
                if (pageSize) {
                    clearUrl += `size=${pageSize}`;
                }
                
                // Make direct HTMX request to clear search without any indicators
                htmx.ajax('GET', clearUrl, {
                    target: '#document-list-container',
                    swap: 'innerHTML',
                    indicator: null,
                    showIndicator: false,
                    timeout: 5000, // 5 second timeout
                    afterSwap: function() {
                        document.body.classList.remove('search-in-progress');
                        return true;
                    },
                    error: function(xhr, status) {
                        // Silently handle errors - simply remove the search-in-progress class
                        document.body.classList.remove('search-in-progress');
                        
                        // Don't return any response to maintain the current UI state
                        return false;
                    }
                });
                
                // Update URL for browser history
                const url = new URL(window.location);
                url.searchParams.delete('q');
                window.history.replaceState({}, '', url);
            });
        }
    });
});