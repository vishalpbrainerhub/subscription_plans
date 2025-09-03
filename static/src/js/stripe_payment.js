/**
 * Stripe Payment Integration for Subscription Plans
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOM CONTENT LOADED ===');
    console.log('Document ready state:', document.readyState);
    
    // Only initialize on the payment page
    const publishableKeyElement = document.getElementById('stripe-publishable-key');
    console.log('Stripe publishable key element:', publishableKeyElement);
    
    if (publishableKeyElement) {
        console.log('Publishable key found, initializing Stripe payment...');
        initializeStripePayment();
    } else {
        console.log('Stripe publishable key element not found - not a payment page');
    }
});

// Also try to initialize if DOM is already loaded
if (document.readyState === 'loading') {
    console.log('Document still loading, waiting for DOMContentLoaded...');
} else {
    console.log('Document already loaded, checking for Stripe elements...');
    const publishableKeyElement = document.getElementById('stripe-publishable-key');
    if (publishableKeyElement && !window.stripeInitialized) {
        console.log('Late initialization of Stripe payment...');
        initializeStripePayment();
    }
}

function initializeStripePayment() {
    console.log('=== INITIALIZING STRIPE PAYMENT ===');
    
    // Prevent multiple initializations
    if (window.stripeInitialized) {
        console.log('Stripe already initialized, skipping...');
        return;
    }
    
    // Check if Stripe is loaded
    if (typeof Stripe === 'undefined') {
        console.error('Stripe library not loaded');
        return;
    }
    
    // Debug: Check required elements exist
    const requiredElements = [
        'stripe-publishable-key',
        'plan-id', 
        'payment-form',
        'card-number',
        'card-expiry', 
        'card-cvc',
        'cardholder-name',
        'terms',
        'submit-payment'
    ];
    
    console.log('Checking required elements...');
    for (const elementId of requiredElements) {
        const element = document.getElementById(elementId);
        console.log(`Element ${elementId}:`, element ? 'FOUND' : 'MISSING');
        if (element) {
            console.log(`  - Type: ${element.tagName}, Value: ${element.value || 'N/A'}`);
        }
        if (!element && elementId === 'payment-form') {
            console.error('Critical: Payment form not found - cannot proceed');
            return;
        }
    }
    
    // Mark as initialized
    window.stripeInitialized = true;
    console.log('Stripe initialization proceeding...');
    
    // Get configuration from hidden inputs
    const publishableKey = document.getElementById('stripe-publishable-key').value;
    const planId = document.getElementById('plan-id').value;
    console.log('publishableKey getting------------', publishableKey);
    if (!publishableKey) {
        console.error('Stripe publishable key not found');
        return;
    }
    
    // Initialize Stripe
    const stripe = Stripe(publishableKey);
    const elements = stripe.elements();
    
    // Initialize submit button state
    const submitButtonEl = document.getElementById('submit-payment');
    if (submitButtonEl) {
        submitButtonEl.disabled = true; // Start disabled until form is valid
    }
    
    // Make stripe instance available globally for payment processing
    window.stripe = stripe;
    
    // Create separate Stripe Elements for better UX
    const elementStyle = {
        base: {
            fontSize: '14px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            color: '#495057',
            fontWeight: '400',
            '::placeholder': {
                color: '#6c757d',
            },
            iconColor: '#0d6efd',
        },
        invalid: {
            color: '#dc3545',
            iconColor: '#dc3545',
        },
        complete: {
            color: '#198754',
            iconColor: '#198754',
        }
    };
    
    // Create individual elements
    const cardNumberElement = elements.create('cardNumber', {
        style: elementStyle,
        placeholder: '1234 1234 1234 1234'
    });
    
    const cardExpiryElement = elements.create('cardExpiry', {
        style: elementStyle,
        placeholder: 'MM / YY'
    });
    
    const cardCvcElement = elements.create('cardCvc', {
        style: elementStyle,
        placeholder: 'CVC'
    });
    
    // Mount the elements to their containers
    cardNumberElement.mount('#card-number');
    cardExpiryElement.mount('#card-expiry');
    cardCvcElement.mount('#card-cvc');
    
    // Make card elements available globally for payment processing
    window.cardNumberElement = cardNumberElement;
    
    // Debug: Check if elements mounted successfully
    cardNumberElement.on('ready', function() {
        console.log('Stripe card number element ready');
        const cardContainer = document.getElementById('card-number');
        cardContainer.style.cursor = 'text';
    });
    
    cardExpiryElement.on('ready', function() {
        console.log('Stripe card expiry element ready');
        const cardContainer = document.getElementById('card-expiry');
        cardContainer.style.cursor = 'text';
    });
    
    cardCvcElement.on('ready', function() {
        console.log('Stripe card CVC element ready');
        const cardContainer = document.getElementById('card-cvc');
        cardContainer.style.cursor = 'text';
    });
    
    // Initialize card completion states
    window.cardNumberComplete = false;
    window.cardExpiryComplete = false;
    window.cardCvcComplete = false;
    
    // Handle real-time validation errors from the card Elements
    function handleCardChange(event, elementName) {
        const displayError = document.getElementById('card-errors');
        const form = document.getElementById('payment-form');
        
        // Update completion state for this element
        window[elementName + 'Complete'] = event.complete;
        
        if (event.error) {
            displayError.textContent = event.error.message;
            displayError.style.display = 'block';
            updateSubmitButtonState(false);
        } else {
            // Clear errors if no current error
            if (!displayError.textContent || displayError.textContent === event.error?.message) {
                displayError.textContent = '';
                displayError.style.display = 'none';
            }
            
            // Update button state based on form validity and all card elements completeness
            const allCardElementsComplete = window.cardNumberComplete && window.cardExpiryComplete && window.cardCvcComplete;
            updateSubmitButtonState(isFormValid(form) && allCardElementsComplete);
        }
    }
    
    // Add event listeners to all card elements
    cardNumberElement.on('change', function(event) {
        handleCardChange(event, 'cardNumber');
    });
    
    cardExpiryElement.on('change', function(event) {
        handleCardChange(event, 'cardExpiry');
    });
    
    cardCvcElement.on('change', function(event) {
        handleCardChange(event, 'cardCvc');
    });
    
    // Add form validation
    setupFormValidation();
    
    // Handle form submission
    const form = document.getElementById('payment-form');
    if (!form) {
        console.error('Payment form not found');
        return;
    }
    
    console.log('Attaching form submit event listener to form:', form);
    console.log('Form current action:', form.action);
    console.log('Form current method:', form.method);
    console.log('Form tag name:', form.tagName);
    console.log('Form id:', form.id);
    console.log('Form class:', form.className);
    
    // Ensure form doesn't have default submission behavior
    form.setAttribute('novalidate', 'true'); // Disable browser validation
    
    // Remove action attribute to prevent fallback submission
    if (form.hasAttribute('action')) {
        console.log('Removing form action attribute to prevent default submission');
        form.removeAttribute('action');
    }
    
    // Remove any existing event listeners to prevent duplicates
    const existingHandler = form.onsubmit;
    if (existingHandler) {
        console.log('Found existing submit handler, removing it');
        form.onsubmit = null;
    }
    
    // Initialize processing flag
    let isProcessingPayment = false;
    
    // Prevent normal form submission behavior
    form.addEventListener('submit', async function(event) {
        console.log('=== STRIPE PAYMENT FORM SUBMIT EVENT TRIGGERED ===');
        console.log('Event type:', event.type);
        console.log('Event target:', event.target);
        console.log('Form action:', form.action);
        console.log('Form method:', form.method);
        
        // CRITICAL: Prevent any form submission
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        
        console.log('Form submission prevented successfully');
        
        // Prevent multiple submissions
        if (isProcessingPayment) {
            console.log('Payment already being processed, ignoring duplicate submission');
            return false;
        }
        
        isProcessingPayment = true;
        console.log('Setting processing flag to true');
        
        // Validate form first
        console.log('Validating form...');
        const formValid = isFormValid(form);
        console.log('Form validation result:', formValid);
        
        if (!formValid) {
            console.log('Form validation failed - stopping submission');
            form.classList.add('was-validated');
            showError('Please fill in all required fields correctly.');
            isProcessingPayment = false; // Reset processing flag
            return false; // Explicitly return false
        }
        
        console.log('Form validation passed - proceeding with payment');
        
        const submitButton = document.getElementById('submit-payment');
        const buttonText = document.getElementById('button-text');
        const spinner = document.getElementById('spinner');
        
        console.log('Submit button:', submitButton);
        console.log('Button text element:', buttonText);
        console.log('Spinner element:', spinner);
        
        // Show payment processing status
        console.log('Showing payment processing status...');
        showPaymentStatus('processing', 'Processing your payment...');
        
        // Disable submit button and show loading
        console.log('Disabling submit button and showing spinner...');
        updateSubmitButtonState(false);
        if (buttonText) buttonText.style.display = 'none';
        if (spinner) spinner.style.display = 'inline-block';
        
        try {
            // Get plan ID
            const currentPlanId = document.getElementById('plan-id').value;
            console.log('Processing payment for plan ID:', currentPlanId);
            
            if (!currentPlanId) {
                throw new Error('Plan ID not found');
            }
            
            // Create payment intent
            console.log('Creating payment intent...');
            showPaymentStatus('processing', 'Creating payment session...');
            const intentResponse = await createPaymentIntent(currentPlanId);
            console.log('Payment intent response:', intentResponse);
            
            if (intentResponse.error) {
                throw new Error(intentResponse.error);
            }
            
            // Collect billing details
            const billingDetails = getBillingDetails();
            console.log('Billing details:', billingDetails);
            
            // Confirm payment with Stripe
            console.log('Confirming payment with Stripe...');
            showPaymentStatus('processing', 'Confirming payment with your bank...');
            
            if (!window.stripe) {
                throw new Error('Stripe instance not available');
            }
            
            if (!window.cardNumberElement) {
                throw new Error('Card element not available');
            }
            
            const {error, paymentIntent} = await window.stripe.confirmCardPayment(
                intentResponse.client_secret,
                {
                    payment_method: {
                        card: window.cardNumberElement,
                        billing_details: billingDetails
                    }
                }
            );
            
            console.log('Stripe payment confirmation result:', {error, paymentIntent});
            
            if (error) {
                // Show error to customer
                console.error('Stripe payment error:', error);
                showPaymentStatus('error', error.message);
                showError(error.message);
            } else {
                // Payment succeeded
                console.log('Payment succeeded! Payment Intent ID:', paymentIntent.id);
                showPaymentStatus('success', 'Payment successful! Activating your subscription...');
                await handlePaymentSuccess(paymentIntent.id);
            }
            
        } catch (error) {
            console.error('Payment processing error:', error);
            console.error('Error stack:', error.stack);
            showPaymentStatus('error', error.message || 'An unexpected error occurred.');
            showError(error.message || 'An unexpected error occurred.');
        } finally {
            // Always reset processing flag and re-enable submit button if there was an error (not success)
            if (!document.querySelector('#payment-status.alert-success')) {
                console.log('Re-enabling submit button after error...');
                isProcessingPayment = false; // Reset processing flag
                updateSubmitButtonState(true);
                if (buttonText) buttonText.style.display = 'inline';
                if (spinner) spinner.style.display = 'none';
            } else {
                console.log('Payment successful - keeping form disabled');
            }
        }
        
        // Explicitly return false to prevent any form submission
        console.log('Form submission handler completed - returning false');
        return false;
    }, false); // Use capture=false to ensure our handler runs first
    
    // ADDITIONAL DEBUG: Also add click handler to submit button as fallback
    const submitButton = document.getElementById('submit-payment');
    if (submitButton) {
        console.log('Adding click handler to submit button:', submitButton);
        console.log('Submit button type:', submitButton.type);
        console.log('Submit button form:', submitButton.form);
        
        submitButton.addEventListener('click', function(event) {
            console.log('=== SUBMIT BUTTON CLICKED ===');
            console.log('Button event:', event);
            console.log('Button type:', submitButton.type);
            
            // If it's a submit button, let the form handle it
            if (submitButton.type === 'submit') {
                console.log('Button is submit type - letting form handle submission');
                return; // Let the form submit event fire
            } else {
                console.log('Button is not submit type - triggering form submission manually');
                // Manually trigger form submission
                const formEvent = new Event('submit', { bubbles: true, cancelable: true });
                form.dispatchEvent(formEvent);
            }
        });
    } else {
        console.error('Submit button not found!');
    }
}

function setupFormValidation() {
    const form = document.getElementById('payment-form');
    
    // Add real-time validation to name field
    const nameField = document.getElementById('cardholder-name');
    nameField.addEventListener('input', function() {
        updateSubmitButtonState(isFormValid(form));
        validateField(nameField);
    });
    
    nameField.addEventListener('blur', function() {
        validateField(nameField);
    });
    
    // Terms checkbox validation
    const termsCheckbox = document.getElementById('terms');
    termsCheckbox.addEventListener('change', function() {
        updateSubmitButtonState(isFormValid(form));
    });
}

function isFormValid(form) {
    // Check required fields
    const nameField = document.getElementById('cardholder-name');
    const termsCheckbox = document.getElementById('terms');
    
    let isValid = true;
    
    // Check name field
    if (!nameField || !nameField.value.trim()) {
        isValid = false;
    }
    
    // Check terms checkbox
    if (!termsCheckbox || !termsCheckbox.checked) {
        isValid = false;
    }
    
    // Check if all card elements are complete
    const allCardElementsComplete = window.cardNumberComplete && window.cardExpiryComplete && window.cardCvcComplete;
    if (!allCardElementsComplete) {
        isValid = false;
    }
    
    return isValid;
}

function validateField(field) {
    const isValid = field.value.trim() !== '';
    
    if (field.type === 'email') {
        const emailValid = isValidEmail(field.value);
        field.classList.toggle('is-valid', emailValid);
        field.classList.toggle('is-invalid', !emailValid);
    } else {
        field.classList.toggle('is-valid', isValid);
        field.classList.toggle('is-invalid', !isValid);
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function updateSubmitButtonState(enabled) {
    const submitButton = document.getElementById('submit-payment');
    submitButton.disabled = !enabled;
}

function getBillingDetails() {
    return {
        name: document.getElementById('cardholder-name').value,
    };
}

async function createPaymentIntent(planId) {
    console.log('=== CREATE PAYMENT INTENT ===');
    console.log('Plan ID:', planId);
    
    try {
        const requestBody = {
            jsonrpc: "2.0",
            method: "call",
            params: {
                plan_id: planId
            }
        };
        
        console.log('Request body:', requestBody);
        
        const response = await fetch('/subscription/payment/create-intent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Payment intent response data:', data);
        
        if (data.error) {
            console.error('Server returned error:', data.error);
            throw new Error(data.error);
        }
        
        if (!data.result) {
            throw new Error('No result in response');
        }
        
        console.log('Payment intent created successfully:', data.result);
        return data.result;
        
    } catch (error) {
        console.error('Error creating payment intent:', error);
        console.error('Error details:', error.message);
        throw error;
    }
}

async function handlePaymentSuccess(paymentIntentId) {
    console.log('=== HANDLE PAYMENT SUCCESS ===');
    console.log('Payment Intent ID:', paymentIntentId);
    
    try {
        const requestBody = {
            jsonrpc: "2.0",
            method: "call",
            params: {
                payment_intent_id: paymentIntentId
            }
        };
        
        console.log('Confirmation request body:', requestBody);
        
        const response = await fetch('/subscription/payment/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Confirmation response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Confirmation response data:', data);
        
        if (data.error) {
            console.error('Server returned error during confirmation:', data.error);
            throw new Error(data.error);
        }
        
        if (data.result && data.result.success) {
            console.log('Payment confirmed successfully! Redirecting to:', data.result.redirect_url);
            // Redirect to success page
            window.location.href = data.result.redirect_url;
        } else {
            console.error('Payment confirmation failed - no success flag');
            throw new Error('Payment confirmation failed');
        }
        
    } catch (error) {
        console.error('Error confirming payment:', error);
        console.error('Error details:', error.message);
        showError('Payment was processed but confirmation failed. Please contact support.');
    }
}

function showError(message) {
    const errorElement = document.getElementById('card-errors');
    if (errorElement) {
        errorElement.textContent = message;
    } else {
        // Fallback: show alert
        alert('Payment Error: ' + message);
    }
}

function showPaymentStatus(type, message) {
    const statusElement = document.getElementById('payment-status');
    
    // Remove all existing classes first
    statusElement.classList.remove('alert-info', 'alert-success', 'alert-danger');
    
    // Set styling and content based on type
    switch (type) {
        case 'processing':
            statusElement.classList.add('alert', 'alert-info');
            statusElement.innerHTML = `<i class="fa fa-spinner fa-spin me-2"></i> <strong>Processing:</strong> ${message}`;
            break;
        case 'success':
            statusElement.classList.add('alert', 'alert-success');
            statusElement.innerHTML = `<i class="fa fa-check-circle me-2"></i> <strong>Success!</strong> ${message}`;
            break;
        case 'error':
            statusElement.classList.add('alert', 'alert-danger');
            statusElement.innerHTML = `<i class="fa fa-exclamation-circle me-2"></i> <strong>Error:</strong> ${message}`;
            break;
    }
    
    // Show the status element
    statusElement.style.display = 'block';
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 5000);
    }
}

// Utility function to show success messages
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success mt-3';
    successDiv.innerHTML = '<i class="fa fa-check-circle"></i> ' + message;
    
    const form = document.getElementById('payment-form');
    form.parentNode.insertBefore(successDiv, form.nextSibling);
    
    // Remove success message after 5 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
        }
    }, 5000);
}

// Export functions for testing
window.StripePayment = {
    createPaymentIntent,
    handlePaymentSuccess,
    showError,
    showSuccess
};
