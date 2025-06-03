/**
 * Simplified chat functionality that works
 */

// Initialize marked for markdown processing
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: false,
        smartLists: true,
        smartypants: true
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messagesSection = document.getElementById('messages-section');
    const messagesWrapper = messagesSection.querySelector('.messages-wrapper');
    let typingIndicator = document.getElementById('typing-indicator');
    const sendButton = document.getElementById('chat-submit');
    
    // Auto-resize textarea functionality
    function autoResize(textarea) {
        textarea.style.height = '44px';
        textarea.style.height = Math.max(44, Math.min(textarea.scrollHeight, 120)) + 'px';
    }
    
    // Scroll to bottom of messages
    function scrollToBottom() {
        messagesSection.scrollTop = messagesSection.scrollHeight;
    }
    
    // Create user message element
    function createUserMessage(content) {
        const messageRow = document.createElement('div');
        messageRow.className = 'message-row user';
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar user';
        avatar.textContent = 'U';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;
        
        messageRow.appendChild(avatar);
        messageRow.appendChild(bubble);
        
        return messageRow;
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        typingIndicator.style.display = 'flex';
        scrollToBottom();
    }
    
    // Process markdown content
    function processMarkdown() {
        document.querySelectorAll('[data-markdown="true"]:not(.processed)').forEach(element => {
            const content = element.textContent;
            if (typeof marked !== 'undefined') {
                element.innerHTML = marked.parse(content || '');
            }
            element.classList.add('processed');
        });
    }
    
    // Configure htmx for the form
    if (chatForm) {
        // Configure form for proper POST submission
        chatForm.setAttribute('hx-post', '/chat/message/');
        chatForm.setAttribute('hx-target', '#typing-indicator');
        chatForm.setAttribute('hx-swap', 'outerHTML');
        chatForm.setAttribute('hx-indicator', ''); // No loading indicator
        
        // Process htmx
        htmx.process(chatForm);
        
        // Handle textarea input event
        chatInput.addEventListener('input', function() {
            autoResize(this);
        });
        
        // Handle Enter key (submit) vs Shift+Enter (new line)
        chatInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                if (chatInput.value.trim()) {
                    // Add user message immediately
                    const messageText = chatInput.value.trim();
                    const userMessage = createUserMessage(messageText);
                    messagesWrapper.insertBefore(userMessage, typingIndicator);
                    
                    // Clear input
                    chatInput.value = '';
                    autoResize(chatInput);
                    
                    // Show typing indicator
                    showTypingIndicator();
                    
                    // Submit the form
                    const formData = new FormData(chatForm);
                    formData.set('message', messageText);
                    
                    // Use htmx to submit
                    htmx.ajax('POST', '/chat/message/', {
                        values: {
                            message: messageText,
                            csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        target: '#typing-indicator',
                        swap: 'outerHTML'
                    });
                }
            }
        });
    }
    
    // Listen for htmx events
    htmx.on('htmx:afterSwap', function(event) {
        console.log('Response received');
        
        // Process markdown content
        processMarkdown();

        // Update typing indicator reference after swap
        typingIndicator = document.getElementById('typing-indicator');

        // Scroll to bottom
        scrollToBottom();

        // Re-enable input and focus
        chatInput.disabled = false;
        if (sendButton) sendButton.disabled = false;
        chatInput.focus();
    });
    
    // Initial setup
    if (messagesSection) {
        scrollToBottom();
    }
});