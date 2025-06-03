/**
 * Fixed Chat Interface JavaScript for interface_new.html
 */

document.addEventListener('DOMContentLoaded', function() {
    // Element references matching interface_new.html IDs
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('chat-messages');
    
    // Scroll to bottom of messages
    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    // Process markdown content
    function processMarkdown() {
        document.querySelectorAll('.markdown-content').forEach(element => {
            if (!element.hasAttribute('data-processed') && typeof marked !== 'undefined') {
                const content = element.textContent;
                element.innerHTML = marked.parse(content);
                element.setAttribute('data-processed', 'true');
            }
        });
    }
    
    // Handle form submission
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const messageText = messageInput.value.trim();
            if (!messageText) return;
            
            // Add user message to UI immediately
            const userMessage = document.createElement('div');
            userMessage.className = 'message message-user';
            userMessage.innerHTML = `
                <div class="message-avatar">
                    <span>U</span>
                </div>
                <div class="message-content">${escapeHtml(messageText)}</div>
            `;
            messagesContainer.appendChild(userMessage);
            
            // Clear input
            messageInput.value = '';
            scrollToBottom();
            
            // Show loading message
            const loadingMessage = document.createElement('div');
            loadingMessage.className = 'message message-assistant';
            loadingMessage.id = 'loading-message';
            loadingMessage.innerHTML = `
                <div class="message-avatar">
                    <span>AI</span>
                </div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
            messagesContainer.appendChild(loadingMessage);
            scrollToBottom();
            
            // Send request
            const formData = new FormData();
            formData.append('message', messageText);
            formData.append('csrfmiddlewaretoken', getCsrfToken());
            
            fetch('/chat/new/message/', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text();
            })
            .then(html => {
                // Remove loading message
                const loadingMsg = document.getElementById('loading-message');
                if (loadingMsg) loadingMsg.remove();
                
                // Add AI response
                messagesContainer.insertAdjacentHTML('beforeend', html);
                
                // Process markdown and scroll
                processMarkdown();
                scrollToBottom();
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Remove loading message
                const loadingMsg = document.getElementById('loading-message');
                if (loadingMsg) loadingMsg.remove();
                
                // Show error message
                const errorMessage = document.createElement('div');
                errorMessage.className = 'message message-assistant';
                errorMessage.innerHTML = `
                    <div class="message-avatar">
                        <span>AI</span>
                    </div>
                    <div class="message-content">Sorry, there was an error processing your request. Please try again.</div>
                `;
                messagesContainer.appendChild(errorMessage);
                scrollToBottom();
            });
        });
    }
    
    // Handle Enter key (send) vs Shift+Enter (new line)
    if (messageInput) {
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }
    
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
    
    // Initialize
    processMarkdown();
    scrollToBottom();
});