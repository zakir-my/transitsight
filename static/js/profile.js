/* TransitSight - User Profile */

const userId = 'user_' + Date.now();

async function loadProfile() {
    const spinner = document.getElementById('loading-spinner');
    const content = document.getElementById('profile-content');
    if (!content) return;

    spinner.style.display = 'block';

    const data = await apiGet(`/profile/${userId}`);
    if (!data) {
        spinner.style.display = 'none';
        document.getElementById('feedback-history').innerHTML =
            '<p style="color: var(--red);">Failed to load profile.</p>';
        return;
    }

    renderStats(data);
    renderFeedbackHistory(data.feedback_history || []);

    spinner.style.display = 'none';
    content.style.display = 'block';
}

function renderStats(data) {
    const grid = document.getElementById('profile-stats');
    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="message-square"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.total_feedback}</div>
                <div class="stat-label">Crowd Reports</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="flame"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.streak > 0 ? data.streak : '0'}</div>
                <div class="stat-label">Feedback Streak</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="check-circle"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.accuracy_pct !== null ? data.accuracy_pct + '%' : '—'}</div>
                <div class="stat-label">Prediction Accuracy</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="user"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.role || 'commuter'}</div>
                <div class="stat-label">Role</div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

function renderFeedbackHistory(feedbacks) {
    const container = document.getElementById('feedback-history');
    if (feedbacks.length === 0) {
        container.innerHTML = `
            <p style="color: var(--text-secondary); font-size: 0.85em;">
                No feedback yet. Head to the <a href="/dashboard" style="color: var(--accent);">Dashboard</a>
                to submit your first crowd report!
            </p>
        `;
        return;
    }

    container.innerHTML = feedbacks.map(f => {
        const predCls = crowdClass(f.predicted_level);
        const repCls = crowdClass(f.reported_level);
        const matched = f.predicted_level === f.reported_level;
        return `
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <div style="flex: 1;">
                    <div style="font-weight: 600;">${f.route_name || f.route_id}</div>
                    <div style="color: var(--text-secondary); font-size: 0.8em; margin-top: 2px;">
                        ${formatDate(f.created_at)} · ${formatTime(f.created_at)}
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 0.8em; color: var(--text-secondary);">Predicted</span>
                    <span class="crowd-badge ${predCls}">${f.predicted_level}</span>
                    <span style="color: var(--text-secondary);">→</span>
                    <span class="crowd-badge ${repCls}">${f.reported_level}</span>
                    <span style="font-size: 1em;">${matched ? '✅' : '❌'}</span>
                </div>
            </div>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', loadProfile);