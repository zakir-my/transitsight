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

    // Render routes immediately with "Loading..." badges
    renderRoutes(allRoutes);
    spinner.style.display = 'none';

    // Load predictions lazily — one by one, updating cards as results arrive
    loadPredictionsLazy(allRoutes);
}

async function loadPredictionsLazy(routes) {
    // Load predictions sequentially so the user sees them appear one at a time
    for (const route of routes) {
        const data = await apiGet(`/predict?route_id=${route.route_id}`);
        if (data && data.prediction) {
            predictions[route.route_id] = data.prediction;
            updateRouteCard(route.route_id, data.prediction);
        }
    }
}

function updateRouteCard(routeId, pred) {
    // Update a single route card's crowd badge without re-rendering everything
    const card = document.querySelector(`.route-card[data-route="${routeId}"]`);
    if (!card) return;
    const badgeEl = card.querySelector('.crowd-badge');
    if (!badgeEl) return;

    const level = pred.crowd_level;
    const cls = crowdClass(level);

    // Update badge content
    badgeEl.className = `crowd-badge ${cls}`;
    badgeEl.innerHTML = `<span class="crowd-dot ${cls}"></span> ${crowdEmoji(level)} ${level}`;
}

function renderRoutes(routes) {
    const list = document.getElementById('route-list');
    if (routes.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary);">No routes found.</p>';
        return;
    }

    list.innerHTML = routes.map(route => {
        const color = route.color || '#2196F3';
        const agency = route.agency || '';

        return `
            <div class="route-card" data-route="${route.route_id}" onclick="window.location.href='/route?route_id=${route.route_id}'">
                <div class="route-color" style="background: ${color};"></div>
                <div class="route-info">
                    <div class="route-name">${route.route_name}</div>
                    <div class="route-meta">
                        <span>${route.route_id}</span>
                        ${agency ? `<span>${agency}</span>` : ''}
                    </div>
                </div>
                <div class="route-actions">
                    <span class="crowd-badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">
                        Loading...
                    </span>
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
        // Re-apply predictions that are already loaded
        for (const [id, pred] of Object.entries(predictions)) {
            updateRouteCard(id, pred);
        }
        return;
    }
    const q = query.toLowerCase();
    const filtered = allRoutes.filter(r =>
        r.route_name.toLowerCase().includes(q) ||
        r.route_id.toLowerCase().includes(q) ||
        (r.agency || '').toLowerCase().includes(q)
    );
    renderRoutes(filtered);
    // Re-apply predictions
    for (const [id, pred] of Object.entries(predictions)) {
        updateRouteCard(id, pred);
    }
}

async function refreshAll() {
    predictions = {};
    await loadRoutes();
    showToast('Routes refreshed!');
}

// Load on page ready
document.addEventListener('DOMContentLoaded', loadRoutes);