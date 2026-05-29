/* TransitSight - Dashboard page */

let allRoutes = [];
let predictions = {};
let activeFilter = 'all';

async function loadRoutes() {
    const skeleton = document.getElementById('loading-skeleton');
    const list = document.getElementById('route-list');
    if (!list) return;

    skeleton.style.display = 'grid';
    list.innerHTML = '';

    const data = await apiGet('/routes');
    if (!data || !data.routes) {
        skeleton.style.display = 'none';
        list.innerHTML = '<div class="empty-state">Failed to load routes. Check server status.</div>';
        return;
    }

    allRoutes = data.routes;
    document.getElementById('last-updated').textContent =
        `Updated ${new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' })}`;

    applyFilter();
    skeleton.style.display = 'none';

    // Load predictions lazily, one by one
    loadPredictionsLazy(allRoutes);
}

async function loadPredictionsLazy(routes) {
    for (const route of routes) {
        const data = await apiGet(`/predict?route_id=${route.route_id}`);
        if (data && data.prediction) {
            predictions[route.route_id] = data.prediction;
            updateRouteCard(route.route_id, data.prediction);
        } else {
            // Show unavailable state
            updateRouteCardError(route.route_id);
        }
    }
}

function updateRouteCard(routeId, pred) {
    const card = document.querySelector(`.route-card[data-route="${routeId}"]`);
    if (!card) return;

    const level = pred.crowd_level;
    const cls = crowdClass(level);
    const confPct = pred.confidence ? Math.round(pred.confidence * 100) : 70;
    const source = pred.source === 'gemini_api' ? 'Gemini AI' : 'Rule-based';
    const weather = pred.weather_context || 'Clear';
    const timeLabel = formatTimeLabel(pred.time_context);
    const dayLabel = pred.day_context || '';

    // Map crowd level to density percentage for the bar
    const densityMap = { 'Low': 25, 'Medium': 55, 'Full': 88 };
    const densityPct = densityMap[level] || 50;

    // Update status badge
    const badgeEl = card.querySelector('.route-status-badge');
    if (badgeEl) {
        badgeEl.className = `route-status-badge badge-${cls}`;
        badgeEl.textContent = level;
    }

    // Replace loading placeholder with full prediction
    const predEl = card.querySelector('.route-prediction');
    if (!predEl) return;

    predEl.innerHTML = `
        <div class="density-section">
            <div class="density-header">
                <span class="density-label">Est. Congestion Density</span>
                <span class="density-value ${cls}">${densityPct}% (${level})</span>
            </div>
            <div class="density-bar">
                <div class="density-fill ${cls}" style="width: ${densityPct}%"></div>
            </div>
        </div>
        <div class="route-card-footer">
            <span>${timeLabel} · ${dayLabel} · ${weather}</span>
            <span style="color: var(--text-muted);">${source} · ${confPct}%</span>
        </div>
    `;
}

function renderRoutes(routes) {
    const list = document.getElementById('route-list');
    if (routes.length === 0) {
        list.innerHTML = '<div class="empty-state">No routes found matching your filter.</div>';
        return;
    }

    list.innerHTML = routes.map(route => {
        const color = route.color || '#3b82f6';
        const routeType = getRouteType(route.route_id, route.route_type);
        const agency = route.agency || '';

        return `
            <div class="route-card" data-route="${route.route_id}" data-type="${routeType}"
                 onclick="window.location.href='/route?route_id=${route.route_id}'">
                <div class="route-card-color" style="background: ${color};"></div>
                <div class="route-card-body">
                    <div class="route-card-top">
                        <div class="route-card-info">
                            <div>
                                <span class="route-code" style="color: ${color}; background: ${color}15; border: 1px solid ${color}30;">
                                    ${route.route_id}
                                </span>
                                <span class="route-type-badge">${routeType}</span>
                            </div>
                            <div class="route-name">${route.route_name}</div>
                        </div>
                        <div class="route-status-badge">—</div>
                    </div>
                    <div class="route-meta">
                        ${agency ? `<span>${agency}</span>` : ''}
                    </div>
                    <div class="route-prediction">
                        <div class="rp-loading">
                            <span class="rp-loading-dot"></span>
                            <span class="rp-loading-dot"></span>
                            <span class="rp-loading-dot"></span>
                            <span style="font-size: 0.72em; color: var(--text-muted); margin-left: 6px;">loading prediction...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function getRouteType(routeId, routeType) {
    // Use GTFS route_type: 0=light rail, 1=subway, 2=rail
    // But KTMB classifies komuter as type=0 — treat KTMB routes as 'KTM'
    const ktmPrefixes = ['KC', 'KA', 'KB', 'ETS', 'ES', 'ERT', 'SH', 'ST', 'EP', 'EG', '100'];
    const isKTM = ktmPrefixes.some(p => routeId.startsWith(p));

    if (isKTM) return 'KTM';
    if (routeId.startsWith('KJL')) return 'LRT';
    if (routeId.startsWith('MRT') || routeId.startsWith('KG') || routeId.startsWith('PY')) return 'MRT';
    if (routeId.startsWith('MON') || routeId.startsWith('MR')) return 'Monorail';
    if (routeId.startsWith('BRT') || routeId.startsWith('SJ')) return 'BRT';

    // GTFS type fallback
    if (routeType !== undefined && routeType !== null && routeType !== '') {
        const map = { '0': 'LRT', '1': 'MRT', '2': 'KTM', '3': 'Bus' };
        if (map[String(routeType)]) return map[String(routeType)];
    }
    return 'Transit';
}

function formatTimeLabel(timeStr) {
    if (!timeStr) return 'Now';
    const h = parseInt(timeStr.split(':')[0]);
    if (h < 6) return 'Late Night';
    if (h < 12) return 'Morning';
    if (h < 14) return 'Midday';
    if (h < 17) return 'Afternoon';
    if (h < 20) return 'Evening';
    return 'Night';
}

function updateRouteCardError(routeId) {
    const card = document.querySelector(`.route-card[data-route="${routeId}"]`);
    if (!card) return;
    const badgeEl = card.querySelector('.route-status-badge');
    if (badgeEl) {
        badgeEl.textContent = '—';
    }
    const predEl = card.querySelector('.route-prediction');
    if (predEl) {
        predEl.innerHTML = `
            <div style="padding: 10px 0; color: var(--text-muted); font-size: 0.78em;">
                Prediction unavailable — try refreshing
            </div>
        `;
    }
}

/* ---- Filter tabs ---- */
function applyFilter() {
    let filtered = allRoutes;
    if (activeFilter !== 'all') {
        filtered = allRoutes.filter(r => getRouteType(r.route_id, r.route_type) === activeFilter);
    }
    renderRoutes(filtered);
    // Re-apply loaded predictions
    for (const [id, pred] of Object.entries(predictions)) {
        updateRouteCard(id, pred);
    }
}

document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', function(e) {
        e.stopPropagation();
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        activeFilter = this.dataset.filter;
        applyFilter();
    });
});

/* ---- Search ---- */
function searchRoutes(query) {
    if (!query.trim()) {
        applyFilter();
        return;
    }
    let filtered = allRoutes;
    if (activeFilter !== 'all') {
        filtered = filtered.filter(r => getRouteType(r.route_id, r.route_type) === activeFilter);
    }
    const q = query.toLowerCase();
    filtered = filtered.filter(r =>
        r.route_name.toLowerCase().includes(q) ||
        r.route_id.toLowerCase().includes(q) ||
        (r.agency || '').toLowerCase().includes(q)
    );
    renderRoutes(filtered);
    for (const [id, pred] of Object.entries(predictions)) {
        updateRouteCard(id, pred);
    }
}

/* ---- Refresh ---- */
async function refreshAll() {
    predictions = {};
    document.querySelectorAll('.route-status-badge').forEach(b => {
        b.textContent = '—';
        b.className = 'route-status-badge';
    });
    await loadRoutes();
    showToast('Dashboard refreshed');
}

document.addEventListener('DOMContentLoaded', loadRoutes);
