/**
 * Authentication related JavaScript functions
 */

// Password strength validation
function validatePasswordStrength(password) {
    // Minimum length
    const minLength = password.length >= 10;

    // Has uppercase letter
    const hasUppercase = /[A-Z]/.test(password);

    // Has lowercase letter
    const hasLowercase = /[a-z]/.test(password);

    // Has number
    const hasNumber = /[0-9]/.test(password);

    // Has special character
    const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

    return {
        valid: minLength && hasUppercase && hasLowercase && hasNumber && hasSpecialChar,
        minLength,
        hasUppercase,
        hasLowercase,
        hasNumber,
        hasSpecialChar
    };
}

// Update password strength meter
function updatePasswordStrengthMeter(password, meterElement, requirementsList) {
    const result = validatePasswordStrength(password);

    // Update strength meter
    if (!password) {
        meterElement.style.width = '0%';
        meterElement.classList.remove('bg-red-500', 'bg-yellow-500', 'bg-green-500');
    } else if (result.valid) {
        meterElement.style.width = '100%';
        meterElement.classList.remove('bg-red-500', 'bg-yellow-500');
        meterElement.classList.add('bg-green-500');
    } else if (result.minLength && (result.hasUppercase || result.hasLowercase) && (result.hasNumber || result.hasSpecialChar)) {
        meterElement.style.width = '66%';
        meterElement.classList.remove('bg-red-500', 'bg-green-500');
        meterElement.classList.add('bg-yellow-500');
    } else {
        meterElement.style.width = '33%';
        meterElement.classList.remove('bg-yellow-500', 'bg-green-500');
        meterElement.classList.add('bg-red-500');
    }

    // Update requirements list if provided
    if (requirementsList) {
        const requirements = [
            { id: 'req-length', valid: result.minLength, text: 'At least 10 characters' },
            { id: 'req-uppercase', valid: result.hasUppercase, text: 'At least one uppercase letter' },
            { id: 'req-lowercase', valid: result.hasLowercase, text: 'At least one lowercase letter' },
            { id: 'req-number', valid: result.hasNumber, text: 'At least one number' },
            { id: 'req-special', valid: result.hasSpecialChar, text: 'At least one special character' }
        ];

        // Clear existing list
        requirementsList.innerHTML = '';

        // Add requirements
        requirements.forEach(req => {
            const li = document.createElement('li');
            li.id = req.id;
            li.className = 'text-xs flex items-center';

            const icon = document.createElement('span');
            icon.className = 'mr-2';
            icon.innerHTML = req.valid ?
                '<svg class="h-4 w-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>' :
                '<svg class="h-4 w-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>';

            const text = document.createElement('span');
            text.className = req.valid ? 'text-green-600' : 'text-gray-600';
            text.textContent = req.text;

            li.appendChild(icon);
            li.appendChild(text);
            requirementsList.appendChild(li);
        });
    }

    return result.valid;
}

// Password confirmation validation
function validatePasswordConfirmation(password, confirmation, feedbackElement) {
    if (!confirmation) {
        if (feedbackElement) {
            feedbackElement.textContent = '';
            feedbackElement.classList.add('hidden');
        }
        return false;
    }

    const isValid = password === confirmation;

    if (feedbackElement) {
        if (isValid) {
            feedbackElement.textContent = 'Passwords match';
            feedbackElement.classList.remove('text-red-600', 'hidden');
            feedbackElement.classList.add('text-green-600');
        } else {
            feedbackElement.textContent = 'Passwords do not match';
            feedbackElement.classList.remove('text-green-600', 'hidden');
            feedbackElement.classList.add('text-red-600');
        }
    }

    return isValid;
}

// Initialize password validation UI elements
function initPasswordValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const passwordInput = form.querySelector('input[type="password"][name="password1"]');
    const confirmInput = form.querySelector('input[type="password"][name="password2"]');

    if (!passwordInput) return;

    // Create and append meter container if it doesn't exist
    let meterContainer = form.querySelector('.password-strength-meter');
    if (!meterContainer) {
        meterContainer = document.createElement('div');
        meterContainer.className = 'password-strength-meter mt-1';

        const meterBg = document.createElement('div');
        meterBg.className = 'h-2 bg-gray-200 rounded-full overflow-hidden';

        const meter = document.createElement('div');
        meter.className = 'h-full transition-all duration-300';
        meter.id = 'password-strength-meter';
        meter.style.width = '0%';

        meterBg.appendChild(meter);
        meterContainer.appendChild(meterBg);

        // Create requirements list
        const requirementsList = document.createElement('ul');
        requirementsList.className = 'password-requirements mt-2 space-y-1';
        requirementsList.id = 'password-requirements';
        meterContainer.appendChild(requirementsList);

        // Add after password input
        passwordInput.parentNode.appendChild(meterContainer);
    }

    const meter = document.getElementById('password-strength-meter');
    const requirementsList = document.getElementById('password-requirements');

    // Create feedback element for confirmation
    let confirmFeedback = form.querySelector('.password-confirmation-feedback');
    if (!confirmFeedback && confirmInput) {
        confirmFeedback = document.createElement('p');
        confirmFeedback.className = 'password-confirmation-feedback mt-2 text-sm hidden';
        confirmFeedback.id = 'password-confirmation-feedback';
        confirmInput.parentNode.appendChild(confirmFeedback);
    }

    // Update on password input
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            updatePasswordStrengthMeter(this.value, meter, requirementsList);

            // Also check confirmation if it has a value
            if (confirmInput && confirmInput.value) {
                validatePasswordConfirmation(
                    this.value,
                    confirmInput.value,
                    document.getElementById('password-confirmation-feedback')
                );
            }
        });
    }

    // Update on confirmation input
    if (confirmInput) {
        confirmInput.addEventListener('input', function() {
            validatePasswordConfirmation(
                passwordInput.value,
                this.value,
                document.getElementById('password-confirmation-feedback')
            );
        });
    }

    // Validate form submission
    form.addEventListener('submit', function(event) {
        let isValid = true;

        // Check password strength
        if (passwordInput && passwordInput.value) {
            const strengthValid = updatePasswordStrengthMeter(
                passwordInput.value,
                meter,
                requirementsList
            );

            isValid = isValid && strengthValid;
        }

        // Check password confirmation
        if (confirmInput && confirmInput.value) {
            const confirmationValid = validatePasswordConfirmation(
                passwordInput.value,
                confirmInput.value,
                document.getElementById('password-confirmation-feedback')
            );

            isValid = isValid && confirmationValid;
        }

        if (!isValid) {
            event.preventDefault();

            // Scroll to the first error
            const firstError = form.querySelector('.text-red-600');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}

// Initialize date of birth field validation
function initDobValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const dobInput = form.querySelector('input[type="date"][name="date_of_birth"]');
    if (!dobInput) return;

    // Create feedback element
    let dobFeedback = form.querySelector('.dob-feedback');
    if (!dobFeedback) {
        dobFeedback = document.createElement('p');
        dobFeedback.className = 'dob-feedback mt-2 text-sm text-red-600 hidden';
        dobFeedback.id = 'dob-feedback';
        dobInput.parentNode.appendChild(dobFeedback);
    }

    // Set max date to today
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    dobInput.max = `${year}-${month}-${day}`;

    // Validate on input
    dobInput.addEventListener('input', function() {
        const dob = new Date(this.value);
        const today = new Date();
        const eighteenYearsAgo = new Date(today);
        eighteenYearsAgo.setFullYear(today.getFullYear() - 18);

        const feedback = document.getElementById('dob-feedback');

        if (dob > today) {
            feedback.textContent = 'Date of birth cannot be in the future';
            feedback.classList.remove('hidden');
            this.setCustomValidity('Date of birth cannot be in the future');
        } else if (dob > eighteenYearsAgo) {
            feedback.textContent = 'You must be at least 18 years old to register';
            feedback.classList.remove('hidden');
            this.setCustomValidity('You must be at least 18 years old to register');
        } else {
            feedback.classList.add('hidden');
            this.setCustomValidity('');
        }
    });
}

// Initialize on document load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize password validation for signup form
    initPasswordValidation('signup-form');

    // Initialize date of birth validation for signup form
    initDobValidation('signup-form');

    // Initialize password validation for password reset form
    initPasswordValidation('password-reset-form');
});