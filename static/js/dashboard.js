/* TransitSight - Dashboard page */

let allRoutes = [];
let predictions = {};

async function loadRoutes() {
    const spinner = document.getElementById('loading-spinner');
    const list = document.getElementById('route-list');
    if (!list) return;

    spinner.style.display = 'block';

    const data = await apiGet('/routes');
    if (!data || !data.routes) {
        spinner.style.display = 'none';
        list.innerHTML = '<p style="color: var(--red);">Failed to load routes. Make sure the server is running.</p>';
        return;
    }

    allRoutes = data.routes;
    document.getElementById('last-updated').textContent =
        `Updated ${new Date().toLocaleTimeString('en-MY')}`;

    // Load predictions for all routes
    await loadAllPredictions();
    renderRoutes(allRoutes);
    spinner.style.display = 'none';
}

async function loadAllPredictions() {
    predictions = {};
    const batch = allRoutes.map(async (route) => {
        const data = await apiGet(`/predict?route_id=${route.route_id}`);
        if (data && data.prediction) {
            predictions[route.route_id] = data.prediction;
        }
    });
    await Promise.allSettled(batch);
}

function renderRoutes(routes) {
    const list = document.getElementById('route-list');
    if (routes.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary);">No routes found.</p>';
        return;
    }

    list.innerHTML = routes.map(route => {
        const pred = predictions[route.route_id] || {};
        const level = pred.crowd_level || '—';
        const cls = crowdClass(level);
        const color = route.color || '#2196F3';
        const agency = route.agency || '';

        return `
            <div class="route-card" onclick="window.location.href='/route?route_id=${route.route_id}'">
                <div class="route-color" style="background: ${color};"></div>
                <div class="route-info">
                    <div class="route-name">${route.route_name}</div>
                    <div class="route-meta">
                        <span>${route.route_id}</span>
                        ${agency ? `<span>${agency}</span>` : ''}
                    </div>
                </div>
                <div class="route-actions">
                    ${level !== '—' ? `
                        <span class="crowd-badge ${cls}">
                            <span class="crowd-dot ${cls}"></span>
                            ${crowdEmoji(level)} ${level}
                        </span>
                    ` : '<span class="crowd-badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">Loading...</span>'}
                    <button class="btn btn-outline btn-small" onclick="event.stopPropagation(); window.location.href='/route?route_id=${route.route_id}'">
                        View →
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function searchRoutes(query) {
    if (!query.trim()) {
        renderRoutes(allRoutes);
        return;
    }
    const q = query.toLowerCase();
    const filtered = allRoutes.filter(r =>
        r.route_name.toLowerCase().includes(q) ||
        r.route_id.toLowerCase().includes(q) ||
        (r.agency || '').toLowerCase().includes(q)
    );
    renderRoutes(filtered);
}

async function refreshAll() {
    await loadRoutes();
    showToast('Routes refreshed!');
}

// Load on page ready
document.addEventListener('DOMContentLoaded', loadRoutes);
