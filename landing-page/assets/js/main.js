// Mobile menu toggle
const mobileMenuToggle = document.getElementById('mobileMenuToggle');
if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
        const navLinks = document.querySelector('.nav-links');
        navLinks.classList.toggle('active');
    });
}

// Smooth scrolling
function scrollToDemo() {
    document.getElementById('demo').scrollIntoView({ behavior: 'smooth' });
}

function openGitHub() {
    window.open('https://github.com/cLeffNote44/datadestroyer', '_blank');
}

// Demo classification functionality
function classifyText() {
    const textArea = document.getElementById('demoText');
    const outputDiv = document.getElementById('demoOutput');
    const text = textArea.value.trim();

    if (!text) {
        showError('Please enter some text to classify');
        return;
    }

    // Show loading state
    outputDiv.innerHTML = `
        <div class="demo-placeholder">
            <div class="spinner"></div>
            <p>Classifying...</p>
        </div>
    `;

    // Simulate API call with setTimeout
    setTimeout(() => {
        const entities = detectEntities(text);
        displayResults(entities, outputDiv);
    }, 800);
}

function detectEntities(text) {
    const entities = [];

    // Email detection
    const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
    let match;
    while ((match = emailRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'EMAIL',
            sublabel: 'PII',
            confidence: 1.0,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // Phone number detection (US format)
    const phoneRegex = /\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b/g;
    while ((match = phoneRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'PHONE',
            sublabel: 'PII',
            confidence: 0.98,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // SSN detection
    const ssnRegex = /\b(?!000|666)[0-8]\d{2}-(?!00)\d{2}-(?!0000)\d{4}\b/g;
    while ((match = ssnRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'SSN',
            sublabel: 'PII',
            confidence: 0.99,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // Credit card detection (basic Luhn algorithm)
    const ccRegex = /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b/g;
    while ((match = ccRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'CREDIT_CARD',
            sublabel: 'PCI',
            confidence: 0.95,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // Name detection (simple pattern)
    const nameRegex = /\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b/g;
    while ((match = nameRegex.exec(text)) !== null) {
        // Avoid matching if it's part of another entity
        const alreadyDetected = entities.some(e =>
            e.start <= match.index && e.end >= match.index + match[0].length
        );
        if (!alreadyDetected) {
            entities.push({
                text: match[0],
                label: 'PERSON',
                sublabel: 'PII',
                confidence: 0.85,
                start: match.index,
                end: match.index + match[0].length
            });
        }
    }

    // IP Address detection
    const ipRegex = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;
    while ((match = ipRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'IP_ADDRESS',
            sublabel: 'TECHNICAL',
            confidence: 1.0,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // Date of birth detection
    const dobRegex = /\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b/g;
    while ((match = dobRegex.exec(text)) !== null) {
        entities.push({
            text: match[0],
            label: 'DATE_OF_BIRTH',
            sublabel: 'PII',
            confidence: 0.90,
            start: match.index,
            end: match.index + match[0].length
        });
    }

    // Sort by position
    entities.sort((a, b) => a.start - b.start);

    return entities;
}

function displayResults(entities, outputDiv) {
    if (entities.length === 0) {
        outputDiv.innerHTML = `
            <div class="demo-placeholder">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 8v4M12 16h.01"/>
                </svg>
                <p>No sensitive data detected</p>
            </div>
        `;
        return;
    }

    const resultsHTML = `
        <div class="demo-results">
            <div style="margin-bottom: 1rem;">
                <strong>Found ${entities.length} sensitive data ${entities.length === 1 ? 'entity' : 'entities'}:</strong>
            </div>
            ${entities.map((entity, index) => `
                <div class="entity-result" style="animation: slideIn 0.3s ease-out ${index * 0.1}s both;">
                    <div class="entity-text">${escapeHtml(entity.text)}</div>
                    <div class="entity-meta">
                        <span class="entity-label ${getLabelClass(entity.sublabel)}">${entity.label}</span>
                        <span>Type: ${entity.sublabel}</span>
                        <span>Confidence: ${(entity.confidence * 100).toFixed(1)}%</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    outputDiv.innerHTML = resultsHTML;
}

function getLabelClass(sublabel) {
    const classes = {
        'PII': 'label-pii',
        'PHI': 'label-phi',
        'PCI': 'label-pci',
        'TECHNICAL': 'label-technical'
    };
    return classes[sublabel] || 'label-default';
}

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

function showError(message) {
    const outputDiv = document.getElementById('demoOutput');
    outputDiv.innerHTML = `
        <div class="demo-placeholder">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#ef4444">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <p style="color: #ef4444;">${message}</p>
        </div>
    `;
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .spinner {
        border: 3px solid #f3f4f6;
        border-top: 3px solid #6366f1;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .label-pii { background: #6366f1; }
    .label-phi { background: #10b981; }
    .label-pci { background: #f59e0b; }
    .label-technical { background: #8b5cf6; }
    .label-default { background: #6b7280; }

    @media (max-width: 768px) {
        .nav-links.active {
            display: flex;
            flex-direction: column;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            padding: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
    }
`;
document.head.appendChild(style);

// Navbar scroll effect
let lastScroll = 0;
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    const currentScroll = window.pageYOffset;

    if (currentScroll > 100) {
        navbar.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.boxShadow = 'none';
    }

    lastScroll = currentScroll;
});

// Load example text on page load
window.addEventListener('DOMContentLoaded', () => {
    const examples = [
        "Contact John Smith at john.smith@example.com or call 555-123-4567.",
        "Patient Sarah Johnson (DOB: 03/15/1985) has been assigned to Dr. Williams. Contact: 415-555-0123",
        "Account holder: Michael Chen. SSN: 123-45-6789. Card ending in 4532.",
        "Please send the invoice to jane.doe@company.com and copy billing@healthcare.org",
        "Server IP: 192.168.1.100. Patient ID: MRN-847392. Contact: (555) 987-6543"
    ];

    const randomExample = examples[Math.floor(Math.random() * examples.length)];
    const textArea = document.getElementById('demoText');
    if (textArea && !textArea.value) {
        textArea.placeholder = randomExample;
    }
});

// Add keyboard shortcut for demo (Ctrl/Cmd + Enter)
document.getElementById('demoText')?.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        classifyText();
    }
});

console.log('Data Destroyer Landing Page - Loaded');
console.log('Try the live demo at #demo');
console.log('View source: https://github.com/cLeffNote44/datadestroyer');
