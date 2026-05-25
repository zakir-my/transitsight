/* TransitSight - Route Detail page */

let currentRoute = null;
let currentPrediction = null;
const userId = 'user_' + Date.now();

async function loadRouteDetail() {
    const params = new URLSearchParams(window.location.search);
    const routeId = params.get('route_id');
    if (!routeId) {
        document.getElementById('loading-spinner').style.display = 'none';
        document.getElementById('route-detail').style.display = 'block';
        document.getElementById('route-name').textContent = 'No route specified';
        return;
    }

    // Update back link
    document.getElementById('back-link').href = '/dashboard';

    const data = await apiGet(`/routes/${routeId}`);
    if (!data || !data.route) {
        document.getElementById('loading-spinner').style.display = 'none';
        document.getElementById('route-detail').style.display = 'block';
        document.getElementById('route-name').textContent = 'Route not found';
        return;
    }

    currentRoute = data.route;
    document.getElementById('loading-spinner').style.display = 'none';
    document.getElementById('route-detail').style.display = 'block';

    // Route info
    document.getElementById('route-name').textContent = data.route.route_name;
    document.getElementById('route-meta').textContent =
        `${data.route.route_id} · ${data.route.agency || ''} · ${data.route.route_type || 'Rail'}`;
    document.getElementById('route-color-badge').style.background =
        (data.route.color || '#2196F3') + '33';

    // Get prediction
    await loadPrediction();

    // Load travel recommendation
    loadTravelRecommendation(routeId);

    // Recent predictions
    renderRecentPredictions(data.recent_predictions || []);
}

async function loadPrediction() {
    if (!currentRoute) return;

    const data = await apiGet(`/predict?route_id=${currentRoute.route_id}`);
    if (!data || !data.prediction) {
        document.getElementById('prediction-level').textContent = 'Unavailable';
        return;
    }

    currentPrediction = data.prediction;
    const pred = data.prediction;
    const level = pred.crowd_level;
    const cls = crowdClass(level);
    const color = crowdColor(level);

    document.getElementById('prediction-level').textContent = `${crowdEmoji(level)} ${level}`;
    document.getElementById('prediction-level').className = `prediction-level ${cls}-text`;

    document.getElementById('prediction-context').textContent =
        `${pred.day_context} at ${pred.time_context} · ${pred.weather_context} · ${pred.temperature || '—'}°C`;

    if (pred.confidence) {
        document.getElementById('confidence-container').style.display = 'block';
        document.getElementById('confidence-fill').style.width = `${pred.confidence * 100}%`;
        document.getElementById('confidence-fill').style.background = color;
        document.getElementById('confidence-label').textContent =
            `AI Confidence: ${Math.round(pred.confidence * 100)}% · Source: ${pred.source}`;
    }
}

async function submitFeedback(level) {
    if (!currentRoute || !currentPrediction) {
        showToast('Please wait for prediction to load first.');
        return;
    }

    const result = await apiPost('/feedback', {
        route_id: currentRoute.route_id,
        predicted_level: currentPrediction.crowd_level,
        reported_level: level,
        user_id: userId,
    });

    if (result && result.status === 'submitted') {
        document.getElementById('feedback-msg').textContent = result.message || 'Thank you! 🎉';
        showToast('✅ Feedback submitted! Thank you for helping improve predictions.');

        // Show streak
        const streakData = await apiGet(`/feedback/user/${userId}`);
        if (streakData) {
            document.getElementById('streak-msg').textContent =
                `🔥 You've submitted feedback! Keep going to build your streak.`;
        }
    } else {
        showToast('Failed to submit feedback. Try again.');
    }
}

function renderRecentPredictions(predictions) {
    const container = document.getElementById('recent-predictions');
    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85em;">No predictions yet.</p>';
        return;
    }

    container.innerHTML = predictions.map(p => {
        const cls = crowdClass(p.crowd_level);
        return `
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span>
                    <span class="crowd-dot ${cls}"></span>
                    <span class="crowd-badge ${cls}" style="margin-left: 6px;">${p.crowd_level}</span>
                </span>
                <span style="color: var(--text-secondary); font-size: 0.8em;">
                    ${p.day_context} ${p.time_context} · ${p.weather_context || '—'}
                </span>
            </div>
        `;
    }).join('');
}

// Load on page ready
document.addEventListener('DOMContentLoaded', loadRouteDetail);


async function loadTravelRecommendation(routeId) {
    const loading = document.getElementById('travel-recommendation-loading');
    const content = document.getElementById('travel-recommendation-content');
    const bestEl = document.getElementById('travel-best');
    const slotsEl = document.getElementById('travel-slots');
    if (!loading || !content) return;

    const data = await apiGet(`/recommend?route_id=${routeId}`);
    if (!data || !data.recommendation) {
        loading.textContent = 'Recommendation unavailable.';
        return;
    }

    loading.style.display = 'none';
    content.style.display = 'block';

    // Best slot
    const best = data.recommendation;
    const emoji = crowdEmoji(best.crowd_level);
    const cls = crowdClass(best.crowd_level);
    const slotLabels = {
        'morning': '🌅 Morning (7:30 AM)',
        'midday': '☀️ Midday (12:30 PM)',
        'afternoon': '🌤️ Afternoon (3:00 PM)',
        'evening': '🌆 Evening (6:00 PM)',
        'late_night': '🌙 Late Night (9:30 PM)',
    };
    bestEl.innerHTML = `
        <div style="font-size: 0.85em; color: var(--text-secondary); margin-bottom: 6px;">🌟 Recommended Time</div>
        <div style="font-size: 1.3em; font-weight: 700; color: var(--accent);">
            ${slotLabels[best.slot] || best.time}
        </div>
        <div style="margin-top: 6px;">
            <span class="crowd-badge ${cls}" style="font-size: 1em; padding: 4px 16px;">
                ${emoji} ${best.crowd_level}
            </span>
        </div>
    `;

    // All slots
    const levelOrder = { 'Low': 0, 'Medium': 1, 'Full': 2 };
    const sorted = [...data.time_slots].sort((a, b) => levelOrder[a.crowd_level] - levelOrder[b.crowd_level]);

    slotsEl.innerHTML = sorted.map(s => {
        const scls = crowdClass(s.crowd_level);
        const semoji = crowdEmoji(s.crowd_level);
        const isBest = s.slot === best.slot;
        return `
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 8px 12px; margin-bottom: 4px; border-radius: 8px;
                        background: ${isBest ? 'rgba(0,212,255,0.08)' : 'transparent'};
                        border: ${isBest ? '1px solid rgba(0,212,255,0.3)' : '1px solid transparent'};">
                <span style="font-weight: ${isBest ? '700' : '400'};">
                    ${slotLabels[s.slot] || s.time}
                    ${isBest ? '<span style="color: var(--accent); margin-left: 6px; font-size: 0.8em;">★ Best</span>' : ''}
                </span>
                <span class="crowd-badge ${scls}" style="font-size: 0.8em;">
                    ${semoji} ${s.crowd_level}
                </span>
            </div>
        `;
    }).join('');
}
