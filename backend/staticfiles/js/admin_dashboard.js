/**
 * Admin Dashboard functionality for Medical Portal
 * Provides charts, data tables, and admin-specific functionality
 */

// Avoid any jQuery usage - rewritten to use vanilla JavaScript
document.addEventListener('DOMContentLoaded', function() {
  console.log('Admin dashboard loaded - running in vanilla JS mode');
  
  // Initialize components that don't require jQuery
  equalizeCardHeights();
  
  // Add window resize handler
  window.addEventListener('resize', debounce(equalizeCardHeights, 200));
  
  // Set up event listeners
  setupEventListeners();
});

/**
 * Equalize the heights of dashboard stat cards in each row
 */
function equalizeCardHeights() {
  // Get all stats cards
  const cards = document.querySelectorAll('.stats-card');
  if (cards.length === 0) return;
  
  // Reset heights
  cards.forEach(card => {
    card.style.height = 'auto';
  });
  
  // Get the row groups (4 cards per row on large screens, 2 on medium, 1 on small)
  const viewportWidth = window.innerWidth;
  let cardsPerRow = 1;
  
  if (viewportWidth >= 1024) { // lg breakpoint
    cardsPerRow = 4;
  } else if (viewportWidth >= 768) { // md breakpoint
    cardsPerRow = 2;
  }
  
  // Process each row
  for (let i = 0; i < cards.length; i += cardsPerRow) {
    const rowCards = Array.from(cards).slice(i, i + cardsPerRow);
    
    // Find tallest card in this row
    let maxHeight = 0;
    rowCards.forEach(card => {
      maxHeight = Math.max(maxHeight, card.offsetHeight);
    });
    
    // Set all cards in this row to the height of the tallest
    rowCards.forEach(card => {
      card.style.height = maxHeight + 'px';
    });
  }
}

/**
 * Set up event listeners for admin dashboard components
 */
function setupEventListeners() {
  // User role change
  const userRoleSelects = document.querySelectorAll('.user-role-select');
  userRoleSelects.forEach(select => {
    select.addEventListener('change', function() {
      const userId = this.dataset.userId;
      const role = this.value;
      
      // Confirm change
      if (window.confirm(`Are you sure you want to change this user's role to ${role}?`)) {
        updateUserRole(userId, role);
      } else {
        // Reset select to previous value
        this.value = this.dataset.originalRole;
      }
    });
  });
  
  // User account status toggle
  const userStatusToggles = document.querySelectorAll('.user-status-toggle');
  userStatusToggles.forEach(toggle => {
    toggle.addEventListener('change', function() {
      const userId = this.dataset.userId;
      const isActive = this.checked;
      
      // Confirm change
      if (window.confirm(`Are you sure you want to ${isActive ? 'activate' : 'deactivate'} this user account?`)) {
        updateUserStatus(userId, isActive);
      } else {
        // Reset toggle to previous state
        this.checked = !isActive;
      }
    });
  });
  
  // Document delete buttons
  const documentDeleteButtons = document.querySelectorAll('.document-delete-btn');
  documentDeleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      const documentId = this.dataset.documentId;
      const documentTitle = this.dataset.documentTitle || 'this document';
      
      // Confirm deletion
      if (window.confirm(`Are you sure you want to delete "${documentTitle}"? This action cannot be undone.`)) {
        deleteDocument(documentId);
      }
    });
  });
  
  // Date range filters
  const dateRangeForm = document.getElementById('date-range-form');
  if (dateRangeForm) {
    dateRangeForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const startDate = document.getElementById('filter-start-date').value;
      const endDate = document.getElementById('filter-end-date').value;
      
      // Validate dates
      if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
        alert('Start date must be before end date');
        return;
      }
      
      // Apply filter - add query params and reload
      const currentUrl = new URL(window.location.href);
      
      if (startDate) {
        currentUrl.searchParams.set('start_date', startDate);
      } else {
        currentUrl.searchParams.delete('start_date');
      }
      
      if (endDate) {
        currentUrl.searchParams.set('end_date', endDate);
      } else {
        currentUrl.searchParams.delete('end_date');
      }
      
      window.location.href = currentUrl.toString();
    });
  }
  
  // Reset filters button
  const resetFiltersButton = document.getElementById('reset-filters-btn');
  if (resetFiltersButton) {
    resetFiltersButton.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Clear all filter fields
      const filterInputs = document.querySelectorAll('.filter-input');
      filterInputs.forEach(input => {
        input.value = '';
      });
      
      // Remove all query params and reload
      window.location.href = window.location.pathname;
    });
  }
}

/**
 * Update a user's role via API
 */
function updateUserRole(userId, role) {
  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  
  // Send update request
  fetch(`/api/admin/users/${userId}/role/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ role: role })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Show success notification
      showNotification('User role updated successfully', 'success');
      
      // Update data attribute
      const select = document.querySelector(`.user-role-select[data-user-id="${userId}"]`);
      if (select) {
        select.dataset.originalRole = role;
      }
    } else {
      // Show error notification
      showNotification(data.message || 'Failed to update user role', 'error');
      
      // Reset select to original value
      const select = document.querySelector(`.user-role-select[data-user-id="${userId}"]`);
      if (select) {
        select.value = select.dataset.originalRole;
      }
    }
  })
  .catch(error => {
    console.error('Error updating user role:', error);
    showNotification('An error occurred while updating the user role', 'error');
    
    // Reset select to original value
    const select = document.querySelector(`.user-role-select[data-user-id="${userId}"]`);
    if (select) {
      select.value = select.dataset.originalRole;
    }
  });
}

/**
 * Update a user's account status via API
 */
function updateUserStatus(userId, isActive) {
  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  
  // Send update request
  fetch(`/api/admin/users/${userId}/status/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ is_active: isActive })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Show success notification
      showNotification(`User account ${isActive ? 'activated' : 'deactivated'} successfully`, 'success');
      
      // Update UI if needed
      const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
      if (userRow) {
        if (isActive) {
          userRow.classList.remove('bg-red-50');
        } else {
          userRow.classList.add('bg-red-50');
        }
      }
    } else {
      // Show error notification
      showNotification(data.message || 'Failed to update user status', 'error');
      
      // Reset toggle
      const toggle = document.querySelector(`.user-status-toggle[data-user-id="${userId}"]`);
      if (toggle) {
        toggle.checked = !isActive;
      }
    }
  })
  .catch(error => {
    console.error('Error updating user status:', error);
    showNotification('An error occurred while updating the user status', 'error');
    
    // Reset toggle
    const toggle = document.querySelector(`.user-status-toggle[data-user-id="${userId}"]`);
    if (toggle) {
      toggle.checked = !isActive;
    }
  });
}

/**
 * Delete a document via API
 */
function deleteDocument(documentId) {
  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  
  // Send delete request
  fetch(`/api/admin/documents/${documentId}/`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrfToken
    }
  })
  .then(response => {
    if (response.ok) {
      // Show success notification
      showNotification('Document deleted successfully', 'success');
      
      // Remove row from table
      const documentRow = document.querySelector(`tr[data-document-id="${documentId}"]`);
      if (documentRow) {
        documentRow.remove();
      }
    } else {
      return response.json().then(data => {
        throw new Error(data.message || 'Failed to delete document');
      });
    }
  })
  .catch(error => {
    console.error('Error deleting document:', error);
    showNotification(error.message || 'An error occurred while deleting the document', 'error');
  });
}

/**
 * Display a notification message
 */
function showNotification(message, type = 'info') {
  // Check if notification container exists, create if not
  let notificationContainer = document.getElementById('notification-container');
  if (!notificationContainer) {
    notificationContainer = document.createElement('div');
    notificationContainer.id = 'notification-container';
    notificationContainer.className = 'fixed top-4 right-4 z-50 space-y-4';
    document.body.appendChild(notificationContainer);
  }
  
  // Create notification element
  const notification = document.createElement('div');
  notification.className = 'p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-0 opacity-0 flex items-start';
  
  // Set style based on notification type
  if (type === 'success') {
    notification.classList.add('bg-green-50', 'text-green-800', 'border', 'border-green-200');
  } else if (type === 'error') {
    notification.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
  } else if (type === 'warning') {
    notification.classList.add('bg-yellow-50', 'text-yellow-800', 'border', 'border-yellow-200');
  } else {
    notification.classList.add('bg-blue-50', 'text-blue-800', 'border', 'border-blue-200');
  }
  
  // Create icon based on type
  const iconWrapper = document.createElement('div');
  iconWrapper.className = 'flex-shrink-0 mr-3';
  
  let iconSvg = '';
  if (type === 'success') {
    iconSvg = '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>';
  } else if (type === 'error') {
    iconSvg = '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>';
  } else if (type === 'warning') {
    iconSvg = '<svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>';
  } else {
    iconSvg = '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>';
  }
  
  iconWrapper.innerHTML = iconSvg;
  
  // Create message content
  const contentWrapper = document.createElement('div');
  contentWrapper.className = 'flex-1';
  contentWrapper.textContent = message;
  
  // Create close button
  const closeButton = document.createElement('button');
  closeButton.className = 'ml-4 flex-shrink-0 h-5 w-5 text-gray-400 hover:text-gray-500 focus:outline-none';
  closeButton.innerHTML = '<svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
  closeButton.addEventListener('click', () => {
    removeNotification(notification);
  });
  
  // Assemble notification
  notification.appendChild(iconWrapper);
  notification.appendChild(contentWrapper);
  notification.appendChild(closeButton);
  
  // Add to container
  notificationContainer.appendChild(notification);
  
  // Animate in
  setTimeout(() => {
    notification.classList.remove('translate-x-0', 'opacity-0');
    notification.classList.add('translate-x-0', 'opacity-100');
  }, 10);
  
  // Auto-remove after delay
  setTimeout(() => {
    removeNotification(notification);
  }, 5000);
}

/**
 * Remove a notification with animation
 */
function removeNotification(notification) {
  notification.classList.remove('translate-x-0', 'opacity-100');
  notification.classList.add('translate-x-full', 'opacity-0');
  
  setTimeout(() => {
    notification.remove();
  }, 300);
}

/**
 * Debounce function to limit how often a function can be called
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}