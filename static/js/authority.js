/* TransitSight - Transit Authority Dashboard */

const userId = 'user_' + Date.now();

async function loadAuthorityDashboard() {
    const spinner = document.getElementById('loading-spinner');
    const content = document.getElementById('authority-content');
    if (!content) return;

    spinner.style.display = 'block';

    const data = await apiGet('/authority/dashboard');
    if (!data) {
        spinner.style.display = 'none';
        document.getElementById('route-summaries').innerHTML =
            '<p style="color: var(--red);">Failed to load authority data.</p>';
        return;
    }

    renderStats(data);
    renderRouteSummaries(data.route_summaries || []);
    renderPeakHours(data.peak_hours || []);
    renderCrowdDist(data.crowd_distribution || {});
    renderAccuracyTrend(data.accuracy_trend || []);

    spinner.style.display = 'none';
    content.style.display = 'block';
}

function renderStats(data) {
    const grid = document.getElementById('authority-stats');
    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="bar-chart-3"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.predictions_today || 0}</div>
                <div class="stat-label">Predictions Today</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="train-track"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.total_routes || 0}</div>
                <div class="stat-label">Active Routes</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="trending-up"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.total_predictions || 0}</div>
                <div class="stat-label">Total Predictions</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i data-lucide="message-square"></i></div>
            <div class="stat-body">
                <div class="stat-value">${data.total_feedback || 0}</div>
                <div class="stat-label">Crowd Reports</div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

function renderRouteSummaries(routes) {
    const container = document.getElementById('route-summaries');
    if (routes.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">No data yet.</p>';
        return;
    }

    container.innerHTML = `
        <div class="table-wrapper">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Route</th>
                    <th>Agency</th>
                    <th>Predictions</th>
                    <th>Avg Crowding</th>
                    <th>Latest</th>
                </tr>
            </thead>
            <tbody>
                ${routes.map(r => {
                    const scoreColor = r.avg_crowd_score > 0.6 ? 'var(--red)' : r.avg_crowd_score > 0.3 ? 'var(--yellow)' : 'var(--green)';
                    const cls = r.latest_level ? crowdClass(r.latest_level) : '';
                    return `
                        <tr style="cursor: pointer;" onclick="window.location.href='/route?route_id=${r.route_id}'">
                            <td>
                                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${r.color || '#2196F3'}; margin-right:8px;"></span>
                                ${r.route_name}
                            </td>
                            <td style="color: var(--text-secondary);">${r.agency || '—'}</td>
                            <td>${r.prediction_count}</td>
                            <td style="color: ${scoreColor}; font-weight: 600;">
                                ${(r.avg_crowd_score * 100).toFixed(0)}%
                            </td>
                            <td>${r.latest_level ? `<span class="crowd-badge ${cls}">${crowdEmoji(r.latest_level)} ${r.latest_level}</span>` : '—'}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
        </div>
    `;
}

function renderPeakHours(hours) {
    const container = document.getElementById('peak-hours');
    if (hours.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">Not enough data yet.</p>';
        return;
    }

    const maxVal = Math.max(...hours.map(h => h.crowded_pct), 1);
    const labels = ['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20','21','22','23'];
    const dataMap = {};
    hours.forEach(h => { dataMap[h.hour] = h; });

    container.innerHTML = `
        <div class="peak-chart">
        <div class="peak-chart-inner">
        <div style="display: flex; align-items: flex-end; gap: 4px; height: 120px; padding: 0 4px; margin-bottom: 8px;">
            ${labels.map(h => {
                const d = dataMap[h];
                const pct = d ? d.crowded_pct : 0;
                const barH = (pct / maxVal) * 100;
                return `
                    <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px;">
                        <div style="width: 100%; height: ${barH}%; background: ${pct > 60 ? 'var(--red)' : pct > 30 ? 'var(--yellow)' : 'var(--green)'}; border-radius: 3px 3px 0 0; min-height: ${pct > 0 ? 4 : 0}px; transition: height 0.3s;"
                             title="${h}:00 — ${pct}% crowded"></div>
                        <span style="font-size: 0.6em; color: var(--text-secondary);">${h}</span>
                    </div>
                `;
            }).join('')}
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75em; color: var(--text-secondary); padding: 0 4px;">
            <span>🕐 Hour (24h)</span>
            <span>% Crowded (Medium + Full)</span>
        </div>
        </div>
        </div>
    `;
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

function renderAccuracyTrend(data) {
    const container = document.getElementById('accuracy-trend');
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

document.addEventListener('DOMContentLoaded', loadAuthorityDashboard);