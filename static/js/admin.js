/* TransitSight - Admin Dashboard */

let authToken = '';

function adminLogin() {
    const user = document.getElementById('admin-user').value;
    const pass = document.getElementById('admin-pass').value;
    authToken = 'Basic ' + btoa(user + ':' + pass);

    fetchAdminData();
}

async function fetchAdminData() {
    loadConfig();
    const resp = await fetch('/api/admin/dashboard', {
        headers: { 'Authorization': authToken }
    });

    if (resp.status === 401) {
        document.getElementById('login-error').style.display = 'block';
        return;
    }

    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('admin-panel').style.display = 'block';

    const data = await resp.json();
    renderAdminStats(data);
    renderCrowdDist(data.crowd_distribution || {});
    renderRecentFeedback(data.recent_feedback || []);
    renderAccuracyChart(data.stats?.recent_accuracy || []);

    // Load API health
    loadApiHealth();
}

async function loadApiHealth() {
    const resp = await fetch('/api/admin/api-health', {
        headers: { 'Authorization': authToken }
    });
    if (!resp.ok) return;
    const data = await resp.json();
    renderApiHealth(data.services || []);
}

function renderAdminStats(data) {
    const grid = document.getElementById('admin-stats');
    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="bar-chart-3"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.predictions_today || 0}</div>
                <div class="stat-label">Predictions Today</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="trending-up"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.predictions_total || 0}</div>
                <div class="stat-label">Total Predictions</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="train-track"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.routes_total || 0}</div>
                <div class="stat-label">Active Routes</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="message-square"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.stats?.total_feedback || 0}</div>
                <div class="stat-label">Feedback Reports</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="users"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.stats?.total_users || 0}</div>
                <div class="stat-label">Unique Users</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="check-circle"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.stats?.total_accuracy || '—'}${data.stats?.total_accuracy ? '%' : ''}</div>
                <div class="stat-label">Prediction Accuracy</div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

function renderCrowdDist(dist) {
    const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
    const container = document.getElementById('crowd-dist');

    if (Object.keys(dist).length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">No data yet.</p>';
        return;
    }

    container.innerHTML = `
        <div class="dist-bar">
            ${['Low', 'Medium', 'Full'].map(level => {
                const count = dist[level] || 0;
                const pct = (count / total * 100).toFixed(0);
                if (count === 0) return '';
                return `<div class="dist-segment dist-${level.toLowerCase()}" style="width: ${pct}%">${pct}%</div>`;
            }).join('')}
        </div>
        <div style="display: flex; gap: 20px; justify-content: center; margin-top: 8px; font-size: 0.85em;">
            <span>🟢 Low: ${dist.Low || 0}</span>
            <span>🟡 Medium: ${dist.Medium || 0}</span>
            <span>🔴 Full: ${dist.Full || 0}</span>
        </div>
    `;
}

function renderApiHealth(services) {
    const container = document.getElementById('api-health');
    container.innerHTML = `
        <div class="table-wrapper">
        <table class="data-table">
            <thead><tr><th>Service</th><th>Status</th><th>Response Time</th></tr></thead>
            <tbody>
                ${services.map(s => `
                    <tr>
                        <td>${s.service}</td>
                        <td><span class="status-${s.status}">● ${s.status}</span></td>
                        <td style="color: var(--text-secondary);">${s.response_time_ms ? s.response_time_ms + 'ms' : (s.note || '—')}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        </div>
    `;
}

function renderRecentFeedback(feedback) {
    const container = document.getElementById('recent-feedback');
    if (feedback.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">No feedback yet.</p>';
        return;
    }

    container.innerHTML = `
        <div class="table-wrapper">
        <table class="data-table">
            <thead><tr><th>Route</th><th>Predicted</th><th>Reported</th><th>User</th><th>Time</th></tr></thead>
            <tbody>
                ${feedback.map(f => `
                    <tr>
                        <td>${f.route_name || f.route_id}</td>
                        <td><span class="crowd-badge ${crowdClass(f.predicted_level)}">${f.predicted_level}</span></td>
                        <td><span class="crowd-badge ${crowdClass(f.reported_level)}">${f.reported_level}</span></td>
                        <td style="color: var(--text-secondary);">${(f.user_id || 'anonymous').substring(0, 10)}</td>
                        <td style="color: var(--text-secondary);">${formatTime(f.created_at)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        </div>
    `;
}

function renderAccuracyChart(data) {
    const container = document.getElementById('accuracy-chart');
    if (!data || data.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">Not enough data yet.</p>';
        return;
    }

    container.innerHTML = `
        <div class="table-wrapper">
        <table class="data-table">
            <thead><tr><th>Date</th><th>Reports</th><th>Accuracy</th></tr></thead>
            <tbody>
                ${data.map(d => `
                    <tr>
                        <td>${d.date}</td>
                        <td>${d.count}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="flex: 1; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                    <div style="width: ${d.accuracy || 0}%; height: 100%; background: var(--accent); border-radius: 4px;"></div>
                                </div>
                                <span style="font-size: 0.85em;">${(d.accuracy || 0).toFixed(0)}%</span>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        </div>
    `;
}

function refreshAdmin() {
    fetchAdminData();
    showToast('Admin dashboard refreshed!');
}

/* ---- Config management (UC005) ---- */
async function loadConfig() {
    const data = await apiGet('/admin/config');
    if (!data) return;

    // Pre-fill form with stored overrides or env defaults
    const cfg = data.config || {};
    const env = data.env_defaults || {};

    document.getElementById('cfg-gemini-model').value =
        cfg.gemini_model?.value || env.gemini_model || 'gemini-2.0-flash';

    document.getElementById('cfg-key-status').textContent =
        env.gemini_key_configured ? 'Configured ✓' : 'Not set ⚠️';
    document.getElementById('cfg-key-status').style.color =
        env.gemini_key_configured ? 'var(--crowd-low)' : 'var(--crowd-full)';
}

async function saveConfig() {
    const model = document.getElementById('cfg-gemini-model').value.trim();
    const pass = document.getElementById('cfg-admin-pass').value.trim();
    const status = document.getElementById('config-status');

    if (!model && !pass) {
        status.textContent = 'No changes to save';
        status.style.color = 'var(--text-muted)';
        return;
    }

    const updates = [];
    if (model) {
        const r = await apiPost('/admin/config', { key: 'gemini_model', value: model });
        if (r) updates.push('model');
    }
    if (pass) {
        const r = await apiPost('/admin/config', { key: 'admin_password', value: pass });
        if (r) updates.push('password');
        document.getElementById('cfg-admin-pass').value = '';
    }

    if (updates.length > 0) {
        status.textContent = `Saved: ${updates.join(', ')} ✓`;
        status.style.color = 'var(--crowd-low)';
    } else {
        status.textContent = 'Save failed';
        status.style.color = 'var(--crowd-full)';
    }
    setTimeout(() => { status.textContent = ''; }, 4000);
}

// Allow Enter key to login
document.addEventListener('DOMContentLoaded', () => {
    const passInput = document.getElementById('admin-pass');
    if (passInput) {
        passInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') adminLogin();
        });
    }
});
