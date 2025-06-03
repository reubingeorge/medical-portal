/**
 * Enhanced cancer type search with live search functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Focus the search input when the page loads if it has a value
    const searchInput = document.getElementById('cancer-search');
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
    const DEBOUNCE_TIME = 500; // ms
    let lastSearchValue = searchInput.value.trim(); // Track the last value we searched for

    // Add input event listener for live search with debounce
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
        const pageSizeSelect = document.getElementById('itemsPerPage');
        const pageSize = pageSizeSelect ? pageSizeSelect.value : '5';

        // Create a loading clone to avoid flicker
        const tableContainer = document.querySelector('.table-container');
        
        // Set a new timeout
        searchTimeout = setTimeout(() => {
            // Update the last search value
            lastSearchValue = searchValue;
            
            // Build the URL for the request
            let searchUrl = `?q=${encodeURIComponent(searchValue)}`;
            if (pageSize) {
                searchUrl += `&items_per_page=${pageSize}`;
            }

            // Use fetch for smooth transition
            tableContainer.style.opacity = '0.6';
            
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
                    const newTableContainer = doc.querySelector('.table-container');
                    
                    if (newTableContainer) {
                        // Apply a smooth transition
                        tableContainer.style.transition = 'opacity 0.2s ease-in-out';
                        
                        // Insert the new content
                        tableContainer.innerHTML = newTableContainer.innerHTML;
                        
                        // Update no results message if needed
                        const emptyCancerTypes = tableContainer.querySelector('.empty-state');
                        if (emptyCancerTypes && searchValue) {
                            emptyCancerTypes.innerHTML = `<p>No cancer types found matching "${searchValue}"</p>`;
                        }
                        
                        // Fade back in
                        setTimeout(() => {
                            tableContainer.style.opacity = '1';
                            
                            // Update URL for browser history without reloading
                            const url = new URL(window.location);
                            if (searchValue) {
                                url.searchParams.set('q', searchValue);
                            } else {
                                url.searchParams.delete('q');
                            }
                            window.history.replaceState({}, '', url);
                            
                            // Re-initialize any event listeners
                            reattachEventListeners();
                        }, 50);
                    }
                })
                .catch(error => {
                    // Just silently fail and maintain the current UI state
                    tableContainer.style.opacity = '1';
                    console.log("Search error occurred, maintaining current UI state");
                });
            
        }, DEBOUNCE_TIME);
    });

    // Handle form submission (if any)
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

    // Clear search button functionality
    const clearSearchButtons = document.querySelectorAll('a[href*="?"]');
    clearSearchButtons.forEach(button => {
        if (button.querySelector('svg[d*="M6 18L18 6M6 6l12 12"]')) {
            button.addEventListener('click', function(e) {
                e.preventDefault();

                // Clear the search input
                searchInput.value = '';
                lastSearchValue = '';
                
                // Get the current page size
                const pageSizeSelect = document.getElementById('itemsPerPage');
                const pageSize = pageSizeSelect ? pageSizeSelect.value : '5';
                let clearUrl = '?';
                if (pageSize) {
                    clearUrl += `items_per_page=${pageSize}`;
                }
                
                // Get the table container
                const tableContainer = document.querySelector('.table-container');
                
                // Apply smooth fade out
                tableContainer.style.transition = 'opacity 0.2s ease-in-out';
                tableContainer.style.opacity = '0.6';
                
                // Use fetch for smooth transition
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
                        const newTableContainer = doc.querySelector('.table-container');
                        
                        if (newTableContainer) {
                            // Insert new content
                            tableContainer.innerHTML = newTableContainer.innerHTML;
                            
                            // Fade back in
                            setTimeout(() => {
                                tableContainer.style.opacity = '1';
                                
                                // Update URL for browser history
                                const url = new URL(window.location);
                                url.searchParams.delete('q');
                                window.history.replaceState({}, '', url);
                                
                                // Re-initialize event listeners
                                reattachEventListeners();
                            }, 50);
                        }
                    })
                    .catch(error => {
                        // Just silently fail and restore UI
                        tableContainer.style.opacity = '1';
                    });
            });
        }
    });
});

// Function to re-attach event handlers after content changes
function reattachEventListeners() {
    // Re-attach pagination handlers
    document.querySelectorAll('[onclick^="goToPage"]').forEach(element => {
        const originalOnclick = element.getAttribute('onclick');
        element.addEventListener('click', function(e) {
            e.preventDefault();
            eval(originalOnclick);
        });
    });

    // Re-attach items per page dropdown handler
    const itemsPerPageDropdown = document.getElementById('itemsPerPage');
    if (itemsPerPageDropdown) {
        itemsPerPageDropdown.addEventListener('change', function() {
            changeItemsPerPage(this.value);
        });
    }

    // Re-attach sort handlers
    document.querySelectorAll('[onclick^="sortTable"]').forEach(element => {
        const originalOnclick = element.getAttribute('onclick');
        element.addEventListener('click', function(e) {
            e.preventDefault();
            eval(originalOnclick);
        });
    });

    // Re-attach delete confirmation handlers
    document.querySelectorAll('[onclick^="showDeleteConfirmation"]').forEach(element => {
        const originalOnclick = element.getAttribute('onclick');
        element.addEventListener('click', function(e) {
            e.preventDefault();
            eval(originalOnclick);
        });
    });
}