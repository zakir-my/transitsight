/* TransitSight - Shared JavaScript utilities */

const API_BASE = '/api';

function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), duration);
}

function crowdClass(level) {
    const map = { 'Low': 'low', 'Medium': 'medium', 'Full': 'full' };
    return map[level] || 'low';
}

function crowdColor(level) {
    const map = { 'Low': '#4CAF50', 'Medium': '#FFC107', 'Full': '#F44336' };
    return map[level] || '#4CAF50';
}

function crowdEmoji(level) {
    const map = { 'Low': '🟢', 'Medium': '🟡', 'Full': '🔴' };
    return map[level] || '⚪';
}

function formatTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-MY', { day: 'numeric', month: 'short' });
}

async function apiGet(path) {
    try {
        const resp = await fetch(`${API_BASE}${path}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (e) {
        console.error(`API GET ${path} failed:`, e);
        return null;
    }
}

async function apiPost(path, body) {
    try {
        const resp = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (e) {
        console.error(`API POST ${path} failed:`, e);
        return null;
    }
}

/* Mobile hamburger menu toggle */
function toggleNav() {
    const links = document.querySelector('.nav-links');
    if (links) {
        links.classList.toggle('open');
    }
}

// Close mobile nav when a link is clicked
document.addEventListener('click', function(e) {
    if (e.target.closest('.nav-links a')) {
        const links = document.querySelector('.nav-links');
        if (links && links.classList.contains('open')) {
            links.classList.remove('open');
        }
    }
});
