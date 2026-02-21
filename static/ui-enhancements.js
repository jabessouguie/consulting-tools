/**
 * UI Enhancements for Consulting Tools Consulting Tools
 * Toast notifications, modals, email validation, LinkedIn status
 */

// === TOAST NOTIFICATIONS ===

let toastContainer = null;

function initToastContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
}

/**
 * Show toast notification
 * @param {string} message - Main message
 * @param {string} type - 'success', 'error', 'warning', 'info'
 * @param {string} title - Optional title
 * @param {number} duration - Duration in ms (default: 4000)
 */
function showToast(message, type = 'info', title = '', duration = 4000) {
    const container = initToastContainer();

    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${title}</div>` : ''}
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this.parentElement)">×</button>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            closeToast(toast);
        }, duration);
    }

    return toast;
}

function closeToast(toast) {
    toast.classList.add('removing');
    setTimeout(() => {
        toast.remove();
    }, 300);
}

// === MODALS ===

let currentModal = null;

/**
 * Show confirmation modal
 * @param {string} title - Modal title
 * @param {string} message - Modal message
 * @param {function} onConfirm - Callback when confirmed
 * @param {object} options - Optional settings {confirmText, cancelText, confirmClass}
 */
function showConfirmModal(title, message, onConfirm, options = {}) {
    const defaults = {
        confirmText: 'Confirmer',
        cancelText: 'Annuler',
        confirmClass: 'btn-primary'
    };
    const opts = { ...defaults, ...options };

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.onclick = () => closeModal();

    const card = document.createElement('div');
    card.className = 'modal-card';
    card.onclick = (e) => e.stopPropagation();
    card.innerHTML = `
        <h3>${title}</h3>
        <p>${message}</p>
        <div class="modal-actions">
            <button onclick="closeModal()" class="btn btn-secondary">
                ${opts.cancelText}
            </button>
            <button onclick="confirmModalAction()" class="btn ${opts.confirmClass}">
                ${opts.confirmText}
            </button>
        </div>
    `;

    overlay.appendChild(card);
    document.body.appendChild(overlay);
    currentModal = { overlay, onConfirm };

    // ESC to close
    document.addEventListener('keydown', handleModalEscape);

    return overlay;
}

function confirmModalAction() {
    if (currentModal && currentModal.onConfirm) {
        currentModal.onConfirm();
    }
    closeModal();
}

function closeModal() {
    if (currentModal) {
        currentModal.overlay.remove();
        currentModal = null;
        document.removeEventListener('keydown', handleModalEscape);
    }
}

function handleModalEscape(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
}

// === EMAIL VALIDATION ===

/**
 * Validate email input with real-time feedback
 * @param {HTMLInputElement} input - Email input element
 */
function validateEmailInput(input) {
    const feedbackId = input.id + '-feedback';
    let feedback = document.getElementById(feedbackId);

    if (!feedback) {
        feedback = document.createElement('div');
        feedback.id = feedbackId;
        feedback.className = 'input-feedback';
        input.parentNode.insertBefore(feedback, input.nextSibling);
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!input.value) {
        feedback.innerHTML = '';
        input.classList.remove('valid', 'invalid');
    } else if (emailRegex.test(input.value)) {
        feedback.innerHTML = '<span class="text-green">✓ Email valide</span>';
        input.classList.add('valid');
        input.classList.remove('invalid');
    } else {
        feedback.innerHTML = '<span class="text-red">✗ Format email invalide</span>';
        input.classList.add('invalid');
        input.classList.remove('valid');
    }
}

// === ENHANCED SHARE EMAIL (Meeting) ===

async function confirmAndShareEmail() {
    const emailInput = document.getElementById('recipient-email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
        showToast('Veuillez entrer une adresse email', 'warning', 'Email manquant');
        return;
    }

    if (!currentResult || !currentResult.minutes) {
        showToast('Aucun compte rendu disponible à envoyer', 'error', 'Erreur');
        return;
    }

    // Show confirmation modal
    showConfirmModal(
        '📧 Envoyer par email',
        `Envoyer le compte rendu à <strong>${email}</strong> ?`,
        () => shareByEmail(),
        { confirmText: 'Envoyer', confirmClass: 'btn-email' }
    );
}

// === ENHANCED LINKEDIN PUBLISH ===

async function confirmAndPublishToLinkedIn(index) {
    const postElement = document.getElementById('post-' + index);
    if (!postElement) {
        showToast('Post introuvable', 'error', 'Erreur');
        return;
    }

    const postText = postElement.innerText.trim();
    const preview = postText.substring(0, 100) + (postText.length > 100 ? '...' : '');

    // Show confirmation modal
    showConfirmModal(
        '🔗 Publier sur LinkedIn',
        `Publier ce post en <strong>PUBLIC</strong> sur LinkedIn ?<br><br><em>"${preview}"</em>`,
        () => publishToLinkedIn(index),
        { confirmText: 'Publier', confirmClass: 'btn-linkedin' }
    );
}

// === LINKEDIN STATUS CHECK ===

async function checkLinkedInStatus() {
    try {
        const response = await fetch('/api/linkedin/status');
        if (response.ok) {
            const data = await response.json();
            updateLinkedInStatusBadge(data.connected);
        }
    } catch (error) {
        console.error('Failed to check LinkedIn status:', error);
    }
}

function updateLinkedInStatusBadge(connected) {
    const connectedBadge = document.getElementById('linkedin-connected');
    const notConnectedBadge = document.getElementById('linkedin-not-connected');

    if (!connectedBadge || !notConnectedBadge) return;

    if (connected) {
        connectedBadge.classList.remove('hidden');
        notConnectedBadge.classList.add('hidden');
    } else {
        connectedBadge.classList.add('hidden');
        notConnectedBadge.classList.remove('hidden');
    }
}

// === LOADING OVERLAY ===

/**
 * Show loading overlay on element
 * @param {HTMLElement} element - Element to show loading on
 * @param {string} message - Loading message
 */
function showLoading(element, message = 'Chargement en cours...', submessage = '') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
        <p class="loading-message">${message}</p>
        ${submessage ? `<p class="loading-sub">${submessage}</p>` : ''}
    `;

    element.style.position = 'relative';
    element.appendChild(overlay);
    return overlay;
}

/**
 * Hide loading overlay
 * @param {HTMLElement} element - Element with loading overlay
 */
function hideLoading(element) {
    const overlay = element.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// === SUCCESS ANIMATION ===

/**
 * Trigger success animation on element
 * @param {HTMLElement} element - Element to animate
 */
function triggerSuccessAnimation(element) {
    element.classList.add('success-animation');
    setTimeout(() => {
        element.classList.remove('success-animation');
    }, 400);
}

// === AUTO-INIT ===

document.addEventListener('DOMContentLoaded', function() {
    // Auto-check LinkedIn status if on LinkedIn page
    if (window.location.pathname.includes('/linkedin')) {
        checkLinkedInStatus();
    }

    // Add email validation to all email inputs
    document.querySelectorAll('input[type="email"]').forEach(input => {
        input.addEventListener('input', () => validateEmailInput(input));
    });
});

// === ENHANCED SHAREBYEMAIL (Override original) ===

// Backup original shareByEmail if exists
if (typeof window.originalShareByEmail === 'undefined' && typeof shareByEmail !== 'undefined') {
    window.originalShareByEmail = shareByEmail;
}

// Override with enhanced version (will be called by confirmAndShareEmail)
async function shareByEmail() {
    const emailInput = document.getElementById('recipient-email');
    const statusEl = document.getElementById('email-status');

    if (!emailInput || !statusEl) {
        showToast('Éléments UI manquants', 'error', 'Erreur système');
        return;
    }

    const recipientEmail = emailInput.value.trim();

    // Validation already done by confirmAndShareEmail
    if (!currentResult || !currentResult.minutes) {
        showToast('Aucun compte rendu disponible', 'error', 'Erreur');
        return;
    }

    // Show loading
    statusEl.innerHTML = '<span style="color: var(--noir-profond);">📧 Envoi en cours...</span>';

    try {
        const response = await fetch('/api/meeting/share-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                to_email: recipientEmail,
                meeting_summary: currentResult.minutes,
                meeting_title: currentResult.email?.subject || 'Reunion'
            })
        });

        const data = await response.json();

        if (response.ok) {
            statusEl.innerHTML = '<span style="color: #22c55e;">✅ Email envoyé !</span>';
            emailInput.value = '';
            emailInput.classList.remove('valid');
            showToast(`Email envoyé avec succès à ${recipientEmail}`, 'success', '✓ Envoyé');
            triggerSuccessAnimation(statusEl);
        } else {
            statusEl.innerHTML = `<span style="color: var(--corail);">❌ ${data.error || 'Erreur'}</span>`;
            showToast(data.error || 'Erreur lors de l\'envoi', 'error', 'Erreur');
        }
    } catch (error) {
        statusEl.innerHTML = `<span style="color: var(--corail);">❌ Erreur: ${error.message}</span>`;
        showToast('Erreur de connexion', 'error', 'Échec');
    }
}

// === ENHANCED PUBLISHTOLINKEDIN (Override original) ===

// Backup original if exists
if (typeof window.originalPublishToLinkedIn === 'undefined' && typeof publishToLinkedIn !== 'undefined') {
    window.originalPublishToLinkedIn = publishToLinkedIn;
}

// Override with enhanced version (will be called by confirmAndPublishToLinkedIn)
async function publishToLinkedIn(index) {
    const postElement = document.getElementById('post-' + index);
    const statusElement = document.getElementById('publish-status-' + index);

    if (!postElement || !statusElement) {
        showToast('Éléments introuvables', 'error', 'Erreur');
        return;
    }

    const postText = postElement.innerText.trim();

    // Show loading
    statusElement.innerHTML = '<span style="color: var(--noir-profond);">🔗 Publication en cours...</span>';

    try {
        const response = await fetch('/api/linkedin/publish', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: postText,
                visibility: 'PUBLIC'
            })
        });

        const data = await response.json();

        if (response.ok) {
            const url = data.url || '#';
            statusElement.innerHTML = `<span style="color: #22c55e;">✅ <a href="${url}" target="_blank" style="color: #22c55e; text-decoration: underline;">Publié sur LinkedIn</a></span>`;
            showToast('Post publié avec succès !', 'success', '✓ Publié sur LinkedIn');
            triggerSuccessAnimation(statusElement);
        } else {
            statusElement.innerHTML = `<span style="color: var(--corail);">❌ ${data.error || 'Erreur'}</span>`;
            showToast(data.error || 'Erreur lors de la publication', 'error', 'Échec LinkedIn');
        }
    } catch (error) {
        statusElement.innerHTML = `<span style="color: var(--corail);">❌ ${error.message}</span>`;
        showToast('Erreur de connexion', 'error', 'Échec');
    }
}

// Export functions for global access
window.showToast = showToast;
window.showConfirmModal = showConfirmModal;
window.closeModal = closeModal;
window.validateEmailInput = validateEmailInput;
window.confirmAndShareEmail = confirmAndShareEmail;
window.confirmAndPublishToLinkedIn = confirmAndPublishToLinkedIn;
window.checkLinkedInStatus = checkLinkedInStatus;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.triggerSuccessAnimation = triggerSuccessAnimation;
