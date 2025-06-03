/**
 * Modern Chat Interface JavaScript
 * Handles chat functionality including messaging, session management, renaming, and deletion
 */

document.addEventListener('DOMContentLoaded', function() {
    // Element references
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages-container');
    const sendButton = document.querySelector('.send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Modal references
    const renameModal = document.getElementById('rename-modal');
    const deleteModal = document.getElementById('delete-modal');
    const renameInput = document.getElementById('rename-title');
    
    // Sidebar references
    const sidebar = document.querySelector('.chat-sidebar');
    const menuToggle = document.getElementById('menu-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebarCollapse = document.getElementById('sidebar-collapse');
    
    // Check if sidebar should be collapsed (desktop)
    const isDesktop = window.innerWidth > 768;
    const sidebarState = localStorage.getItem('sidebarCollapsed');
    
    if (isDesktop && sidebarState === 'true') {
        sidebar.classList.add('collapsed');
    }
    
    // Mobile sidebar toggle
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.add('open');
            sidebarOverlay.classList.add('show');
        });
    }
    
    // Close mobile sidebar when clicking overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('show');
        });
    }
    
    // Desktop sidebar collapse
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            const isCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebarCollapsed', isCollapsed);
        });
    }
    
    // Auto-close sidebar on mobile when selecting a chat
    const sessionLinks = document.querySelectorAll('.session-link');
    sessionLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('show');
            }
        });
    });
    
    // Swipe gesture support for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    function handleSwipe() {
        const swipeDistance = touchEndX - touchStartX;
        const threshold = 50; // minimum distance for swipe
        
        if (Math.abs(swipeDistance) > threshold) {
            if (swipeDistance > 0 && touchStartX < 20) {
                // Swipe right from left edge - open sidebar
                sidebar.classList.add('open');
                sidebarOverlay.classList.add('show');
            } else if (swipeDistance < 0 && sidebar.classList.contains('open')) {
                // Swipe left - close sidebar
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('show');
            }
        }
    }
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    // Resize handler to adjust sidebar state
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            const isNowDesktop = window.innerWidth > 768;
            
            // Reset mobile states when switching to desktop
            if (isNowDesktop) {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('show');
                
                // Restore collapsed state if it was saved
                const savedState = localStorage.getItem('sidebarCollapsed');
                if (savedState === 'true') {
                    sidebar.classList.add('collapsed');
                }
            } else {
                // Remove collapsed state when switching to mobile
                sidebar.classList.remove('collapsed');
            }
        }, 250);
    });
    
    // Auto-resize textarea
    function autoResizeTextarea(textarea) {
        // Reset height to recalculate
        textarea.style.height = '44px';
        
        // Get the scroll height
        const scrollHeight = textarea.scrollHeight;
        const maxHeight = 200;
        
        // Set new height
        if (scrollHeight <= maxHeight) {
            textarea.style.height = scrollHeight + 'px';
            textarea.style.overflowY = 'hidden';
        } else {
            textarea.style.height = maxHeight + 'px';
            textarea.style.overflowY = 'auto';
        }
        
        // Scroll to bottom of messages when textarea expands
        if (scrollHeight > 44) {
            scrollToBottom();
        }
    }
    
    // Scroll to bottom of messages
    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    // Enable/disable send button based on input
    function updateSendButton() {
        if (sendButton && messageInput) {
            sendButton.disabled = !messageInput.value.trim();
        }
    }
    
    // Process markdown content
    function processMarkdown() {
        document.querySelectorAll('.message-content[data-markdown="true"]').forEach(element => {
            if (!element.hasAttribute('data-processed')) {
                const content = element.textContent;
                if (typeof marked !== 'undefined') {
                    element.innerHTML = marked.parse(content);
                    element.setAttribute('data-processed', 'true');
                }
            }
        });
    }
    
    // Handle message submission through HTMX
    document.body.addEventListener('htmx:configRequest', function(evt) {
        // Only handle our chat form
        if (evt.detail.elt.id === 'chat-form') {
            const messageText = messageInput.value.trim();
            
            if (!messageText) {
                evt.preventDefault();
                return;
            }
            
            // Add user message to UI immediately
            const userMessage = document.createElement('div');
            userMessage.className = 'message message-user';
            userMessage.innerHTML = `
                <div class="message-avatar">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="message-content">${escapeHtml(messageText)}</div>
            `;
            messagesContainer.querySelector('.messages-wrapper').appendChild(userMessage);
            
            // Clear input and reset height
            messageInput.value = '';
            messageInput.style.height = '44px';
            updateSendButton();
            scrollToBottom();
            
            // Show typing indicator
            typingIndicator.style.display = 'flex';
            scrollToBottom();
        }
    });
    
    // Handle HTMX after request
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        if (evt.detail.elt.id === 'chat-form') {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Process markdown and scroll
            setTimeout(() => {
                processMarkdown();
                scrollToBottom();
            }, 50);
        }
    });
    
    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        if (evt.detail.elt.id === 'chat-form') {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'message message-ai';
            errorMessage.innerHTML = `
                <div class="message-avatar">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M9.504 1.132a1 1 0 01.992 0l1.75 1a1 1 0 11-.992 1.736L10 3.152l-1.254.716a1 1 0 11-.992-1.736l1.75-1zM5.618 4.504a1 1 0 01-.372 1.364L5.016 6l.23.132a1 1 0 11-.992 1.736L4 7.723V8a1 1 0 01-2 0V6a.996.996 0 01.52-.878l1.734-.99a1 1 0 011.364.372zm8.764 0a1 1 0 011.364-.372l1.733.99A1.002 1.002 0 0118 6v2a1 1 0 11-2 0v-.277l-.254.145a1 1 0 11-.992-1.736l.23-.132-.23-.132a1 1 0 01-.372-1.364zm-7 4a1 1 0 011.364-.372L10 8.848l1.254-.716a1 1 0 11.992 1.736L11 10.58V12a1 1 0 11-2 0v-1.42l-1.246-.712a1 1 0 01-.372-1.364z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="message-content">Sorry, there was an error processing your request. Please try again.</div>
            `;
            messagesContainer.querySelector('.messages-wrapper').appendChild(errorMessage);
            scrollToBottom();
        }
    });
    
    // Handle textarea input
    if (messageInput) {
        // Set initial height
        messageInput.style.height = '44px';
        messageInput.style.overflowY = 'hidden';
        
        messageInput.addEventListener('input', function() {
            autoResizeTextarea(this);
            updateSendButton();
        });
        
        // Also resize on change events (for paste, etc.)
        messageInput.addEventListener('change', function() {
            autoResizeTextarea(this);
        });
        
        // Handle Enter key (send) vs Shift+Enter (new line)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendButton.click();
            }
        });
        
        // Handle paste events
        messageInput.addEventListener('paste', function() {
            setTimeout(() => autoResizeTextarea(this), 0);
        });
    }
    
    // Copy message functionality
    window.copyMessage = function(button) {
        const messageContent = button.closest('.message').querySelector('.message-content');
        const text = messageContent.innerText || messageContent.textContent;
        
        navigator.clipboard.writeText(text).then(() => {
            // Show temporary success state
            const originalHtml = button.innerHTML;
            button.innerHTML = `
                <svg fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
            `;
            button.style.color = 'var(--success-color)';
            
            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.style.color = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text:', err);
        });
    };
    
    // Modal functions
    window.openRenameModal = function(sessionId, currentTitle) {
        document.getElementById('rename-session-id').value = sessionId;
        document.getElementById('rename-title').value = currentTitle;
        renameModal.style.display = 'flex';
        document.getElementById('rename-title').focus();
    };
    
    window.closeRenameModal = function() {
        renameModal.style.display = 'none';
    };
    
    window.openDeleteModal = function(sessionId, sessionTitle) {
        document.getElementById('delete-session-id').value = sessionId;
        document.getElementById('delete-session-title').textContent = sessionTitle;
        deleteModal.style.display = 'flex';
    };
    
    window.closeDeleteModal = function() {
        deleteModal.style.display = 'none';
    };
    
    // Rename chat
    window.renameChat = function(event) {
        event.preventDefault();
        
        const sessionId = document.getElementById('rename-session-id').value;
        const newTitle = document.getElementById('rename-title').value.trim();
        
        if (!newTitle) return;
        
        fetch(`/chat/session/${sessionId}/update/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken(),
            },
            body: `title=${encodeURIComponent(newTitle)}`
        })
        .then(response => {
            if (response.ok) {
                // Update UI
                const sessionItem = document.querySelector(`[data-session-id="${sessionId}"]`);
                if (sessionItem) {
                    sessionItem.querySelector('.session-title').textContent = newTitle;
                    sessionItem.querySelector('.session-title').title = newTitle;
                }
                
                // Update header if it's the current session
                const chatTitle = document.querySelector('.chat-title');
                if (chatTitle && sessionItem && sessionItem.classList.contains('active')) {
                    chatTitle.textContent = newTitle;
                }
                
                closeRenameModal();
            } else {
                alert('Failed to rename chat');
            }
        })
        .catch(error => {
            console.error('Error renaming chat:', error);
            alert('Error renaming chat');
        });
    };
    
    // Delete chat
    window.deleteChat = function(event) {
        event.preventDefault();
        
        const sessionId = document.getElementById('delete-session-id').value;
        
        fetch(`/chat/session/${sessionId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        })
        .then(response => {
            if (response.ok) {
                // If deleting current session, redirect to new chat
                const sessionItem = document.querySelector(`[data-session-id="${sessionId}"]`);
                if (sessionItem && sessionItem.classList.contains('active')) {
                    window.location.href = '/chat/';
                } else {
                    // Just remove from list
                    if (sessionItem) {
                        sessionItem.remove();
                    }
                }
                
                closeDeleteModal();
            } else {
                alert('Failed to delete chat');
            }
        })
        .catch(error => {
            console.error('Error deleting chat:', error);
            alert('Error deleting chat');
        });
    };
    
    // Helper function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    // Helper function to escape HTML
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal-backdrop')) {
            if (renameModal.style.display === 'flex') closeRenameModal();
            if (deleteModal.style.display === 'flex') closeDeleteModal();
        }
    });
    
    // Handle escape key to close modals
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (renameModal.style.display === 'flex') closeRenameModal();
            if (deleteModal.style.display === 'flex') closeDeleteModal();
        }
    });
    
    // Initialize
    if (messageInput) {
        updateSendButton();
        autoResizeTextarea(messageInput);
    }
    processMarkdown();
    scrollToBottom();
});