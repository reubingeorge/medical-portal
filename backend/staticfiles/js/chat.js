/**
 * Simple chat functionality - NO ANIMATIONS OR SPINNERS
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get references to elements
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const messagesArea = document.getElementById('messages-area');
    
    // Auto-resize textarea
    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    // Scroll to bottom of messages
    function scrollToBottom() {
        if (messagesArea) {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
    }
    
    // Initialize
    if (messageInput) {
        // Auto-resize on input
        messageInput.addEventListener('input', function() {
            autoResize(this);
        });
        
        // Handle Enter key (submit) vs Shift+Enter (new line)
        messageInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                if (chatForm) {
                    chatForm.dispatchEvent(new Event('submit'));
                }
            }
        });
    }
    
    // Handle form submission
    if (chatForm) {
        // Clear input after successful submission
        document.body.addEventListener('htmx:afterRequest', function(event) {
            if (event.detail.elt === chatForm && event.detail.successful) {
                // Clear input
                messageInput.value = '';
                autoResize(messageInput);
                
                // Scroll to bottom to see new messages
                setTimeout(scrollToBottom, 100);
            }
        });
    }
    
    // Initial scroll to bottom
    scrollToBottom();
});