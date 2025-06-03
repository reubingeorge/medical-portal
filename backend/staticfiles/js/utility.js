/**
 * General utility functions for the application
 */

// Format a date in the user's locale
function formatDate(dateString, options = {}) {
    if (!dateString) return '';

    const date = new Date(dateString);

    // Default options
    const defaultOptions = {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };

    // Merge options
    const mergedOptions = { ...defaultOptions, ...options };

    // Get current language
    const language = document.documentElement.lang || 'en';

    return date.toLocaleDateString(language, mergedOptions);
}

// Format a time in the user's locale
function formatTime(timeString, options = {}) {
    if (!timeString) return '';

    const date = new Date(timeString);

    // Default options
    const defaultOptions = {
        hour: 'numeric',
        minute: 'numeric'
    };

    // Merge options
    const mergedOptions = { ...defaultOptions, ...options };

    // Get current language
    const language = document.documentElement.lang || 'en';

    return date.toLocaleTimeString(language, mergedOptions);
}

// Format a datetime in the user's locale
function formatDateTime(dateTimeString, options = {}) {
    if (!dateTimeString) return '';

    const date = new Date(dateTimeString);

    // Default options
    const defaultOptions = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric'
    };

    // Merge options
    const mergedOptions = { ...defaultOptions, ...options };

    // Get current language
    const language = document.documentElement.lang || 'en';

    return date.toLocaleString(language, mergedOptions);
}

// Format a number in the user's locale
function formatNumber(number, options = {}) {
    if (number === null || number === undefined) return '';

    // Get current language
    const language = document.documentElement.lang || 'en';

    return number.toLocaleString(language, options);
}

// Format currency in the user's locale
function formatCurrency(amount, currencyCode = 'USD', options = {}) {
    if (amount === null || amount === undefined) return '';

    // Default options
    const defaultOptions = {
        style: 'currency',
        currency: currencyCode
    };

    // Merge options
    const mergedOptions = { ...defaultOptions, ...options };

    // Get current language
    const language = document.documentElement.lang || 'en';

    return Number(amount).toLocaleString(language, mergedOptions);
}

// Truncate text with ellipsis
function truncateText(text, maxLength = 100) {
    if (!text) return '';

    if (text.length <= maxLength) return text;

    return text.substring(0, maxLength) + '...';
}

// Copy text to clipboard
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text)
        .then(() => {
            // Success message
            const event = new CustomEvent('showToast', {
                detail: {
                    message: 'Copied to clipboard',
                    type: 'success',
                    duration: 3000
                }
            });
            document.dispatchEvent(event);
            return true;
        })
        .catch(error => {
            console.error('Failed to copy text: ', error);
            return false;
        });
}

// Generate a random ID
function generateId(prefix = 'id') {
    return `${prefix}-${Math.random().toString(36).substring(2, 9)}`;
}

// Format a file size for display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Get file extension from filename
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

// Check if file is an image
function isImage(filename) {
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
    const extension = getFileExtension(filename);

    return imageExtensions.includes(extension);
}

// Check if file is a document
function isDocument(filename) {
    const docExtensions = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'];
    const extension = getFileExtension(filename);

    return docExtensions.includes(extension);
}

// Get file icon based on extension
function getFileIcon(filename) {
    const extension = getFileExtension(filename);

    const iconMap = {
        // Images
        'jpg': 'image',
        'jpeg': 'image',
        'png': 'image',
        'gif': 'image',
        'webp': 'image',
        'svg': 'image',

        // Documents
        'pdf': 'file-pdf',
        'doc': 'file-word',
        'docx': 'file-word',
        'txt': 'file-text',
        'rtf': 'file-text',
        'odt': 'file-text',

        // Spreadsheets
        'xls': 'file-excel',
        'xlsx': 'file-excel',
        'csv': 'file-excel',

        // Presentations
        'ppt': 'file-presentation',
        'pptx': 'file-presentation',

        // Archives
        'zip': 'file-archive',
        'rar': 'file-archive',
        '7z': 'file-archive',
        'tar': 'file-archive',
        'gz': 'file-archive',

        // Audio
        'mp3': 'file-audio',
        'wav': 'file-audio',
        'aac': 'file-audio',

        // Video
        'mp4': 'file-video',
        'mov': 'file-video',
        'avi': 'file-video',

        // Default
        'default': 'file'
    };

    return iconMap[extension] || iconMap.default;
}

// Debounce function to limit how often a function can be called
function debounce(func, wait) {
    let timeout;

    return function(...args) {
        const context = this;
        clearTimeout(timeout);

        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}

// Format a phone number
function formatPhoneNumber(phoneNumber) {
    if (!phoneNumber) return '';

    // Remove all non-digits
    const cleaned = phoneNumber.replace(/\D/g, '');

    // Check if number matches US format
    const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);

    if (match) {
        return `(${match[1]}) ${match[2]}-${match[3]}`;
    }

    // If not a US number format, return as is
    return phoneNumber;
}

// Export utility functions for use in other scripts
window.utils = {
    formatDate,
    formatTime,
    formatDateTime,
    formatNumber,
    formatCurrency,
    truncateText,
    copyToClipboard,
    generateId,
    formatFileSize,
    getFileExtension,
    isImage,
    isDocument,
    getFileIcon,
    debounce,
    formatPhoneNumber
};