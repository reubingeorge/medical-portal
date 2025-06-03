/**
 * Translation utilities for client-side text
 * This helps with dynamic content that is added after page load
 */

// Get current language from HTML lang attribute
function getCurrentLanguage() {
    return document.documentElement.lang || 'en';
}

// Translation cache
const translationCache = {};

// Load translations for the current language
async function loadTranslations(language = null) {
    const lang = language || getCurrentLanguage();

    // Return from cache if available
    if (translationCache[lang]) {
        return translationCache[lang];
    }

    try {
        const response = await fetch(`/static/translations/${lang}.json`);
        if (!response.ok) {
            throw new Error(`Failed to load translations for ${lang}`);
        }

        const translations = await response.json();
        translationCache[lang] = translations;
        return translations;
    } catch (error) {
        console.error('Error loading translations:', error);
        return {};
    }
}

// Translate a string
async function translate(key, defaultText = null) {
    const translations = await loadTranslations();
    return translations[key] || defaultText || key;
}

// Translate all elements with data-translate attribute
async function translatePage() {
    const elements = document.querySelectorAll('[data-translate]');
    const translations = await loadTranslations();

    elements.forEach(element => {
        const key = element.getAttribute('data-translate');
        if (translations[key]) {
            element.textContent = translations[key];
        }
    });
}

// Initialize translation functionality
document.addEventListener('DOMContentLoaded', function() {
    // Translate on page load
    translatePage();

    // Listen for language changes
    document.addEventListener('languageChanged', function(event) {
        const newLanguage = event.detail.language;
        translatePage(newLanguage);
    });

    // Listen for HTMX content loaded
    document.addEventListener('htmx:afterSwap', function() {
        translatePage();
    });
});

// Export functions for use in other scripts
window.translateUtils = {
    translate,
    translatePage,
    getCurrentLanguage,
    loadTranslations
};