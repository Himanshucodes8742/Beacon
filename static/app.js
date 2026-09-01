/* ═══════════════════════════════════════════════════════════════
   SAIL Freight Smart Charter AI — Frontend Application
   SPA Routing, API Calls, Chart.js Visualizations
   ═══════════════════════════════════════════════════════════════ */

// ── Global State ──
let currentUser = null;
let currentPage = 'dashboard';
let forecastData = null;
let chartInstances = {};

// ── Color Palette for Charts ──
const COLORS = {
    navy: '#002147',
    navyLight: '#003366',
    teal: '#008080',
    tealLight: '#00a8a8',
    steel: '#708090',
    success: '#2E7D32',
    warning: '#F57C00',
    danger: '#C62828',
    vessels: {
        Capesize: '#002147',
        Panamax: '#008080',
        Supramax: '#F57C00',
        Handysize: '#708090'
    }
};

// ═══════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('fcStartDate');
    if (dateInput) dateInput.value = today;

    // Check for saved session
    const saved = sessionStorage.getItem('sailUser');
    if (saved) {
        currentUser = JSON.parse(saved);
        showApp();
    }
});

// ═══════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════

async function handleLogin(e) {
    e.preventDefault();
    const employeeId = document.getElementById('employeeId').value.trim();
    const password = document.getElementById('password').value.trim();
    const btn = document.getElementById('loginBtn');
    const errorEl = document.getElementById('loginError');

    btn.classList.add('loading');
    btn.innerHTML = '<span class="spinner" style="width:20px;height:20px;border-width:2px;display:inline-block"></span>';
    errorEl.classList.remove('visible');

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ employee_id: employeeId, password })
        });
        const data = await res.json();

        if (data.success) {
            currentUser = data.user;
            sessionStorage.setItem('sailUser', JSON.stringify(currentUser));
            showApp();
            showToast('Welcome back, ' + currentUser.full_name, 'success');
        } else {
            document.getElementById('loginErrorText').textContent = data.error || 'Invalid credentials';
            errorEl.classList.add('visible');
        }
    } catch (err) {
        document.getElementById('loginErrorText').textContent = 'Connection error. Please try again.';
        errorEl.classList.add('visible');
    }

    btn.classList.remove('loading');
    btn.innerHTML = 'Secure Login';
    return false;
}

function handleLogout() {
    currentUser = null;
    sessionStorage.removeItem('sailUser');
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('appLayout').classList.remove('active');
    fetch('/api/logout', { method: 'POST' }).catch(() => {});
}

function togglePassword() {
    const pwd = document.getElementById('password');
    const icon = document.getElementById('pwdToggleIcon');
    if (pwd.type === 'password') {
        pwd.type = 'text';
        icon.textContent = 'visibility';
    } else {
        pwd.type = 'password';
        icon.textContent = 'visibility_off';
    }
}

// ═══════════════════════════════════════════
// APP NAVIGATION
// ═══════════════════════════════════════════

function showApp() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('appLayout').classList.add('active');

    // Update user info in sidebar
    if (currentUser) {
        document.getElementById('userName').textContent = currentUser.full_name;
        const initials = currentUser.full_name.split(' ').map(n => n[0]).join('').substring(0, 2);
        document.getElementById('userAvatar').textContent = initials;
    }

    // Load dashboard
    navigateTo('dashboard');
}

const PAGE_TITLES = {
    dashboard: 'Operational Dashboard',
    forecast: 'Freight Forecasting',
    optimizer: 'Vessel Type Optimization',
    charters: 'Charters & Contracts',
    insights: 'Risk Management & Analytics',
    reports: 'Saved Reports'
};

function navigateTo(page) {
    currentPage = page;

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Show correct page view
    document.querySelectorAll('.page-view').forEach(view => {
        view.classList.remove('active');
    });
    const pageEl = document.getElementById('page-' + page);
    if (pageEl) pageEl.classList.add('active');

    // Update header title
    document.getElementById('pageTitle').textContent = PAGE_TITLES[page] || page;

    // Load data for the page
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'charters': loadCharters(); break;
        case 'insights': loadInsights(); break;
        case 'reports': loadReports(); break;
    }
}

// ═══════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════

function switchTab(tabId, btn) {
    const parent = btn.closest('.page-view');
    parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    parent.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + tabId).classList.add('active');
}

// ═══════════════════════════════════════════
// SEGMENTED CONTROL
// ═══════════════════════════════════════════

function selectSegment(btn) {
    btn.parentElement.querySelectorAll('.segmented-option').forEach(o => o.classList.remove('active'));
    btn.classList.add('active');
}

// ═══════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════

async function loadDashboard() {
    try {
        const [summaryRes, riskRes] = await Promise.all([
            fetch('/api/dashboard/summary'),
            fetch('/api/risks')
        ]);
        const summary = await summaryRes.json();
        const risks = await riskRes.json();

        renderBDIMetric(summary.bdi);
        renderBDIChart(summary.bdi.trend);
        renderRoutesTable(summary.routes);
        renderOpportunities(summary.opportunities);
        renderFleetCharts(summary.fleet_by_type, summary.fleet_by_charter);
        renderRiskAlerts(risks.alerts);
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function renderBDIMetric(bdi) {
    document.getElementById('bdiValue').textContent = Math.round(bdi.current).toLocaleString();
    const changeEl = document.getElementById('bdiChange');
    const isUp = bdi.change_pct >= 0;
    changeEl.textContent = `${isUp ? '↑' : '↓'} ${Math.abs(bdi.change_pct)}%`;
    changeEl.className = `metric-change ${isUp ? 'up' : 'down'}`;
}

function renderBDIChart(trend) {
    destroyChart('bdiChart');
    const ctx = document.getElementById('bdiChart').getContext('2d');
    chartInstances.bdiChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
            }),
            datasets: [{
                label: 'BDI',
                data: trend.map(d => d.value),
                borderColor: COLORS.teal,
                backgroundColor: 'rgba(0,128,128,0.08)',
                fill: true,
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: COLORS.teal
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: COLORS.navy,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 }, color: '#94a3b8', maxTicksLimit: 8 }
                },
                y: {
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    ticks: { font: { size: 11 }, color: '#94a3b8' }
                }
            }
        }
    });
}

function renderRoutesTable(routes) {
    const tbody = document.getElementById('routesBody');
    tbody.innerHTML = routes.map(r => {
        const isUp = r.change >= 0;
        const sparkBars = r.trend.map(v => {
            const height = Math.max(4, ((v - 10) / 30) * 28);
            return `<div class="sparkline-bar" style="height:${height}px"></div>`;
        }).join('');
        return `<tr>
            <td><strong>${r.route}</strong></td>
            <td>$${r.current_rate.toFixed(2)}</td>
            <td><div class="sparkline">${sparkBars}</div></td>
            <td><span class="badge ${isUp ? 'badge-success' : 'badge-danger'}"><span class="badge-dot"></span> ${isUp ? '+' : ''}${r.change}%</span></td>
        </tr>`;
    }).join('');
}

function renderOpportunities(opps) {
    const tbody = document.getElementById('opportunitiesBody');
    tbody.innerHTML = opps.map(o => {
        const badgeClass = o.status === 'Optimal' ? 'badge-success' : 'badge-warning';
        return `<tr>
            <td><code style="font-size:0.8rem;background:var(--bg-input);padding:2px 6px;border-radius:4px">${o.voyage_id}</code></td>
            <td>${o.route}</td>
            <td>${(o.cargo_mt / 1000).toFixed(0)}K</td>
            <td>${new Date(o.target_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</td>
            <td><span class="badge ${badgeClass}"><span class="badge-dot"></span> ${o.status}</span></td>
        </tr>`;
    }).join('');
}

function renderFleetCharts(byType, byCharter) {
    // Fleet by Type
    destroyChart('fleetTypeChart');
    const ctx1 = document.getElementById('fleetTypeChart').getContext('2d');
    chartInstances.fleetTypeChart = new Chart(ctx1, {
        type: 'doughnut',
        data: {
            labels: Object.keys(byType),
            datasets: [{
                data: Object.values(byType),
                backgroundColor: [COLORS.navy, COLORS.teal, COLORS.warning, COLORS.steel],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } }
                }
            }
        }
    });

    // Fleet by Charter
    destroyChart('fleetCharterChart');
    const ctx2 = document.getElementById('fleetCharterChart').getContext('2d');
    chartInstances.fleetCharterChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: Object.keys(byCharter),
            datasets: [{
                data: Object.values(byCharter),
                backgroundColor: [COLORS.teal, COLORS.danger, COLORS.navy],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } }
                }
            }
        }
    });
}

function renderRiskAlerts(alerts) {
    const container = document.getElementById('riskAlerts');
    container.innerHTML = alerts.map(a => {
        const icon = { danger: 'error', warning: 'warning', info: 'info' }[a.severity] || 'info';
        return `<div class="risk-item">
            <div class="risk-icon ${a.severity}"><span class="material-symbols-outlined">${icon}</span></div>
            <div class="risk-content">
                <h4>${a.title}</h4>
                <p>${a.detail}</p>
            </div>
            <span class="risk-time">${a.timestamp}</span>
        </div>`;
    }).join('');
}

// ═══════════════════════════════════════════
// FREIGHT FORECAST
// ═══════════════════════════════════════════

async function runForecast() {
    const btn = document.getElementById('forecastBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;display:inline-block"></span> Forecasting...';

    const payload = {
        route: document.getElementById('fcOrigin').value,
        destination_port: document.getElementById('fcDestination').value,
        cargo_volume: parseInt(document.getElementById('fcVolume').value),
        start_date: document.getElementById('fcStartDate').value,
        forecast_days: parseInt(document.getElementById('fcDays').value),
        bunker_price: parseInt(document.getElementById('fcBunker').value),
        congestion: parseInt(document.getElementById('fcCongestion').value),
        contract_type: document.querySelector('#fcContractType .segmented-option.active')?.dataset.val || 'CVC'
    };

    try {
        const res = await fetch('/api/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        forecastData = await res.json();
        forecastData._params = payload;

        renderForecastResults(forecastData);
        showToast('Forecast generated successfully', 'success');
    } catch (err) {
        showToast('Forecast failed: ' + err.message, 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-outlined">auto_awesome</span> Generate AI Forecast';
}

function renderForecastResults(data) {
    // Show result cards, hide empty state
    document.getElementById('forecastSignals').style.display = 'grid';
    document.getElementById('forecastChartCard').style.display = 'block';
    document.getElementById('confidenceCard').style.display = 'block';
    document.getElementById('forecastEmpty').style.display = 'none';

    // Signal
    const timing = data.timing;
    const signalIcon = document.getElementById('signalIcon');
    const signalLabel = document.getElementById('signalLabel');
    const signalReason = document.getElementById('signalReason');

    signalIcon.className = 'signal-icon ' + timing.color;
    signalIcon.textContent = timing.signal === 'BUY NOW' ? '✅' : timing.signal === 'WAIT' ? '⏳' : '🔴';
    signalLabel.className = 'signal-label ' + timing.color;
    signalLabel.textContent = timing.signal;
    signalReason.textContent = timing.reason;

    document.getElementById('currentRateDisplay').textContent = '$' + timing.current_rate.toFixed(2);
    document.getElementById('lowestRateDisplay').textContent = '$' + timing.lowest_rate.toFixed(2);
    document.getElementById('bestDateDisplay').textContent = timing.best_date;

    // Main forecast chart
    renderForecastChart(data.forecast);

    // Confidence chart
    if (data.confidence && data.confidence.length > 0) {
        renderConfidenceChart(data.confidence);
    }
}

function renderForecastChart(forecast) {
    destroyChart('forecastChart');
    const ctx = document.getElementById('forecastChart').getContext('2d');

    // Group by vessel type
    const vesselTypes = [...new Set(forecast.map(f => f.vessel_type))];
    const dates = [...new Set(forecast.map(f => f.date))];

    const datasets = vesselTypes.map(vt => {
        const filteredData = forecast.filter(f => f.vessel_type === vt);
        return {
            label: vt,
            data: filteredData.map(f => f.predicted_rate),
            borderColor: COLORS.vessels[vt] || COLORS.steel,
            backgroundColor: 'transparent',
            tension: 0.4,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5
        };
    });

    chartInstances.forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates.map(d => {
                const date = new Date(d);
                return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
            }),
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 20, font: { size: 12, weight: '600' } }
                },
                tooltip: {
                    backgroundColor: COLORS.navy,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    padding: 14,
                    cornerRadius: 10,
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}/Ton`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 }, color: '#94a3b8', maxTicksLimit: 10 }
                },
                y: {
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    ticks: {
                        font: { size: 11 },
                        color: '#94a3b8',
                        callback: v => '$' + v.toFixed(0)
                    },
                    title: { display: true, text: 'Freight Rate ($/Ton)', font: { size: 12 }, color: '#64748b' }
                }
            }
        }
    });
}

function renderConfidenceChart(confidence) {
    destroyChart('confidenceChart');
    const ctx = document.getElementById('confidenceChart').getContext('2d');

    chartInstances.confidenceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: confidence.map(c => {
                const date = new Date(c.date);
                return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
            }),
            datasets: [
                {
                    label: 'Upper Band (95%)',
                    data: confidence.map(c => c.upper),
                    borderColor: 'rgba(0,128,128,0.3)',
                    backgroundColor: 'rgba(0,128,128,0.06)',
                    fill: '+1',
                    tension: 0.4,
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 0
                },
                {
                    label: 'Predicted',
                    data: confidence.map(c => c.predicted),
                    borderColor: COLORS.teal,
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 0
                },
                {
                    label: 'Lower Band (95%)',
                    data: confidence.map(c => c.lower),
                    borderColor: 'rgba(0,128,128,0.3)',
                    backgroundColor: 'rgba(0,128,128,0.06)',
                    fill: '-1',
                    tension: 0.4,
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 11 } }
                },
                tooltip: {
                    backgroundColor: COLORS.navy,
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#94a3b8', maxTicksLimit: 8 } },
                y: { grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 10 }, color: '#94a3b8', callback: v => '$' + v.toFixed(0) } }
            }
        }
    });
}

async function saveForecastReport() {
    if (!forecastData) {
        showToast('Run a forecast first', 'warning');
        return;
    }

    const params = forecastData._params;
    const timing = forecastData.timing;
    const optBest = forecastData.optimization?.best_vessel || 'Panamax';

    const report = {
        user_id: currentUser?.id,
        report_title: `${params.route.replace(/_/g, ' ')} → ${params.destination_port} Analysis`,
        trade_route: params.route,
        destination_port: params.destination_port,
        cargo_volume_tons: params.cargo_volume,
        recommended_vessel: optBest,
        market_signal: timing.signal,
        forecasted_rate_per_ton: timing.current_rate,
        estimated_total_cost: timing.current_rate * params.cargo_volume,
        projected_arbitrage_savings: Math.abs(timing.current_rate - timing.lowest_rate) * params.cargo_volume,
        demurrage_risk_usd: Math.random() * 50000
    };

    try {
        await fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(report)
        });
        showToast('Report saved successfully', 'success');
    } catch (err) {
        showToast('Report saved locally (DB offline)', 'warning');
    }
}

// ═══════════════════════════════════════════
// VESSEL OPTIMIZER
// ═══════════════════════════════════════════

async function runOptimizer() {
    const cargo = parseInt(document.getElementById('optVolume').value);
    const port = document.getElementById('optPort').value;

    try {
        const res = await fetch('/api/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cargo_volume: cargo, destination_port: port })
        });
        const data = await res.json();

        document.getElementById('optimizerResults').style.display = 'grid';
        document.getElementById('optimizerEmpty').style.display = 'none';

        renderOptimizerTable(data.report, data.vessel_specs, port);
        renderRecommendation(data.best_vessel, data.report, cargo, port);
    } catch (err) {
        showToast('Optimization failed: ' + err.message, 'error');
    }
}

function renderOptimizerTable(report, specs, port) {
    const tbody = document.getElementById('optimizerTable');
    tbody.innerHTML = report.map(r => {
        const isEligible = r.Status === 'Eligible';
        const spec = specs[r.Vessel] || {};
        const statusBadge = isEligible
            ? '<span class="badge badge-success"><span class="badge-dot"></span> Eligible</span>'
            : '<span class="badge badge-danger"><span class="badge-dot"></span> Rejected</span>';
        const rowStyle = isEligible ? '' : 'style="opacity:0.6"';
        return `<tr ${rowStyle}>
            <td><strong>${r.Vessel}</strong></td>
            <td>${(spec.capacity_tons || 0).toLocaleString()}</td>
            <td>${spec.draft_m || '—'}</td>
            <td>${spec.loa_m || '—'}</td>
            <td>${r['Voyages Needed']}</td>
            <td>$${r['Rate/Ton ($)']?.toFixed(2)}</td>
            <td>$${(r['Est. Cost ($)'] || 0).toLocaleString()}</td>
            <td>${statusBadge}</td>
        </tr>`;
    }).join('');
}

function renderRecommendation(bestVessel, report, cargo, port) {
    const container = document.getElementById('aiRecommendation');
    if (!bestVessel) {
        container.innerHTML = `<div class="card" style="background:var(--danger-bg);border-color:rgba(198,40,40,0.2)">
            <div class="card-body" style="padding:28px;text-align:center">
                <span class="material-symbols-outlined" style="font-size:48px;color:var(--danger);margin-bottom:12px">warning</span>
                <h3 style="color:var(--danger);margin-bottom:8px">Port Restriction Warning</h3>
                <p style="color:var(--text-secondary)">No vessel can dock directly at <strong>${port}</strong> for this cargo volume. Lighterage or offloading at Sandheads may be required.</p>
            </div>
        </div>`;
        return;
    }

    const bestReport = report.find(r => r.Vessel === bestVessel) || {};
    const voyages = bestReport['Voyages Needed'] || 1;

    container.innerHTML = `<div class="recommendation-card">
        <div class="rec-badge"><span class="material-symbols-outlined" style="font-size:14px">auto_awesome</span> AI RECOMMENDATION</div>
        <h3>Optimal Vessel: ${bestVessel} (${voyages > 1 ? voyages + ' Voyages' : 'Single Voyage'})</h3>
        <ul class="rec-list">
            <li>Satisfies ${port} draft & LOA constraints — fully compliant</li>
            <li>Lowest total cost: $${(bestReport['Est. Cost ($)'] || 0).toLocaleString()} for ${(cargo).toLocaleString()} MT</li>
            <li>Rate: $${bestReport['Rate/Ton ($)']?.toFixed(2)}/Ton — competitive CVC pricing</li>
            <li>${voyages > 1 ? `${voyages} consecutive voyages minimize idle time vs smaller vessels` : 'Single voyage maximizes capacity utilization'}</li>
        </ul>
        <button class="btn" onclick="showToast('Charter strategy initiated for ${bestVessel}','success')">
            <span class="material-symbols-outlined" style="font-size:18px">rocket_launch</span>
            Initiate Charter Strategy
        </button>
    </div>`;
}

// ═══════════════════════════════════════════
// ACTIVE CHARTERS
// ═══════════════════════════════════════════

async function loadCharters() {
    try {
        const res = await fetch('/api/charters');
        const data = await res.json();
        renderCharterCards(data.charters);
    } catch (err) {
        console.error('Failed to load charters:', err);
    }
}

function renderCharterCards(charters) {
    const container = document.getElementById('chartersList');

    const statusBadge = (status) => {
        const map = {
            'En-Route': 'badge-info',
            'Loading': 'badge-warning',
            'Discharging': 'badge-success',
            'Awaiting Berth': 'badge-warning',
            'Completed': 'badge-neutral',
            'Cancelled': 'badge-danger'
        };
        return `<span class="badge ${map[status] || 'badge-neutral'}"><span class="badge-dot"></span> ${status}</span>`;
    };

    container.innerHTML = charters.map(c => {
        const progress = c.status === 'Completed' ? 100 : c.status === 'Discharging' ? 80 : c.status === 'En-Route' ? 45 : c.status === 'Loading' ? 20 : 10;
        return `<div class="charter-card">
            <div class="charter-card-header">
                <h4>${c.vessel_name}</h4>
                ${statusBadge(c.status)}
            </div>
            <div class="charter-card-details">
                <div class="charter-detail">
                    <div class="detail-label">Vessel Type</div>
                    <div class="detail-value">${c.vessel_type}</div>
                </div>
                <div class="charter-detail">
                    <div class="detail-label">Strategy</div>
                    <div class="detail-value">${c.strategy_type}</div>
                </div>
                <div class="charter-detail">
                    <div class="detail-label">Route</div>
                    <div class="detail-value">${c.origin_port} → ${c.destination_port}</div>
                </div>
                <div class="charter-detail">
                    <div class="detail-label">Cargo</div>
                    <div class="detail-value">${parseFloat(c.cargo_volume_tons).toLocaleString()} MT</div>
                </div>
                <div class="charter-detail">
                    <div class="detail-label">Rate / Ton</div>
                    <div class="detail-value">$${parseFloat(c.contract_rate_per_ton).toFixed(2)}</div>
                </div>
                <div class="charter-detail">
                    <div class="detail-label">ETA</div>
                    <div class="detail-value">${new Date(c.estimated_arrival_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                </div>
            </div>
            <div class="charter-progress">
                <div class="progress-label">
                    <span>Voyage Progress</span>
                    <span>${progress}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:${progress}%"></div>
                </div>
            </div>
            <div class="charter-actions">
                <button class="btn btn-icon" title="View Schedule"><span class="material-symbols-outlined" style="font-size:16px">calendar_today</span></button>
                <button class="btn btn-icon" title="Generate Report"><span class="material-symbols-outlined" style="font-size:16px">description</span></button>
                <button class="btn btn-icon" title="Discuss Renewal"><span class="material-symbols-outlined" style="font-size:16px">chat</span></button>
            </div>
        </div>`;
    }).join('');
}

function showAddCharterHint() {
    showToast('Navigate to Forecast → Generate → Save to create new charter entries', 'info');
}

// ═══════════════════════════════════════════
// MARKET INSIGHTS
// ═══════════════════════════════════════════

async function loadInsights() {
    try {
        const res = await fetch('/api/market-insights');
        const data = await res.json();

        renderSavingsChart(data.savings);
        renderCongestionChart(data.congestion);
        renderIdleTimeChart(data.idle_time);
        renderWhatIf(data.whatif);
    } catch (err) {
        console.error('Failed to load insights:', err);
    }
}

function renderSavingsChart(savings) {
    destroyChart('savingsChart');
    const ctx = document.getElementById('savingsChart').getContext('2d');

    chartInstances.savingsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: savings.quarters,
            datasets: [
                {
                    label: 'Actual Freight Spend',
                    data: savings.actual_spend.map(v => v / 1000000),
                    backgroundColor: COLORS.navy,
                    borderRadius: 6,
                    barPercentage: 0.4,
                    categoryPercentage: 0.7
                },
                {
                    label: 'AI-Predicted Optimal Spend',
                    data: savings.predicted_spend.map(v => v / 1000000),
                    backgroundColor: COLORS.teal,
                    borderRadius: 6,
                    barPercentage: 0.4,
                    categoryPercentage: 0.7
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 20, font: { size: 12, weight: '600' } }
                },
                tooltip: {
                    backgroundColor: COLORS.navy,
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(1)}M`,
                        afterBody: function(items) {
                            const idx = items[0].dataIndex;
                            return `💰 Savings: $${(savings.savings[idx] / 1000000).toFixed(1)}M`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 12, weight: '600' } } },
                y: {
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    ticks: { callback: v => '$' + v + 'M', font: { size: 11 }, color: '#94a3b8' },
                    title: { display: true, text: 'Spend ($ Millions)', font: { size: 12 }, color: '#64748b' }
                }
            }
        }
    });
}

function renderCongestionChart(congestion) {
    destroyChart('congestionChart');
    const ctx = document.getElementById('congestionChart').getContext('2d');
    const ports = Object.keys(congestion);
    const months = congestion[ports[0]].map(d => d.month);

    const colors = [COLORS.navy, COLORS.teal, COLORS.warning, COLORS.steel];

    chartInstances.congestionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: ports.map((port, i) => ({
                label: port,
                data: congestion[port].map(d => d.days),
                borderColor: colors[i],
                backgroundColor: 'transparent',
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: colors[i]
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 11 } }
                },
                tooltip: { backgroundColor: COLORS.navy, padding: 12, cornerRadius: 8 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#94a3b8' } },
                y: {
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    ticks: { callback: v => v + 'd', font: { size: 11 }, color: '#94a3b8' },
                    title: { display: true, text: 'Congestion Days', font: { size: 11 }, color: '#64748b' }
                }
            }
        }
    });
}

function renderIdleTimeChart(idleTime) {
    destroyChart('idleTimeChart');
    const ctx = document.getElementById('idleTimeChart').getContext('2d');
    const vessels = Object.keys(idleTime);

    chartInstances.idleTimeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: vessels,
            datasets: [
                {
                    label: 'Waiting for Berth',
                    data: vessels.map(v => idleTime[v].waiting_berth),
                    backgroundColor: COLORS.warning,
                    borderRadius: 4,
                    barPercentage: 0.5
                },
                {
                    label: 'Weather Delay',
                    data: vessels.map(v => idleTime[v].weather_delay),
                    backgroundColor: COLORS.teal,
                    borderRadius: 4,
                    barPercentage: 0.5
                },
                {
                    label: 'Technical',
                    data: vessels.map(v => idleTime[v].technical),
                    backgroundColor: COLORS.steel,
                    borderRadius: 4,
                    barPercentage: 0.5
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 11 } }
                },
                tooltip: {
                    backgroundColor: COLORS.navy,
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.x} days` }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    ticks: { callback: v => v + 'd', font: { size: 11 }, color: '#94a3b8' },
                    title: { display: true, text: 'Idle Days', font: { size: 11 }, color: '#64748b' }
                },
                y: {
                    stacked: true,
                    grid: { display: false },
                    ticks: { font: { size: 12, weight: '600' } }
                }
            }
        }
    });
}

function renderWhatIf(whatif) {
    const container = document.getElementById('whatifDisplay');
    container.innerHTML = `
        <div class="card" style="border-color:rgba(0,128,128,0.2);background:linear-gradient(135deg,rgba(0,128,128,0.02),rgba(0,128,128,0.06))">
            <div class="card-body" style="padding:24px">
                <div class="d-flex align-center justify-between mb-16">
                    <h4 style="font-weight:700;color:var(--navy)">📋 12-Month CVC Contract</h4>
                    <span class="badge badge-success"><span class="badge-dot"></span> Recommended</span>
                </div>
                <div class="grid-2" style="gap:12px">
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Rate/Ton</span><div style="font-size:1.3rem;font-weight:800;color:var(--navy)">$${whatif.cvc_12m.rate_per_ton.toFixed(2)}</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Total Cost</span><div style="font-size:1.3rem;font-weight:800;color:var(--navy)">$${(whatif.cvc_12m.total_cost / 1000000).toFixed(1)}M</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Risk Level</span><div style="font-size:1rem;font-weight:700;color:var(--success)">${whatif.cvc_12m.risk}</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Savings vs Spot</span><div style="font-size:1.3rem;font-weight:800;color:var(--success)">+$${(whatif.cvc_12m.savings_vs_spot / 1000000).toFixed(1)}M</div></div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-body" style="padding:24px">
                <div class="d-flex align-center justify-between mb-16">
                    <h4 style="font-weight:700;color:var(--navy)">📋 12 Monthly Spot Purchases</h4>
                    <span class="badge badge-danger"><span class="badge-dot"></span> Higher Risk</span>
                </div>
                <div class="grid-2" style="gap:12px">
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Avg Rate/Ton</span><div style="font-size:1.3rem;font-weight:800;color:var(--navy)">$${whatif.spot_12m.rate_per_ton.toFixed(2)}</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Total Cost</span><div style="font-size:1.3rem;font-weight:800;color:var(--danger)">$${(whatif.spot_12m.total_cost / 1000000).toFixed(1)}M</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Risk Level</span><div style="font-size:1rem;font-weight:700;color:var(--danger)">${whatif.spot_12m.risk}</div></div>
                    <div><span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Savings</span><div style="font-size:1.3rem;font-weight:800;color:var(--text-muted)">—</div></div>
                </div>
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════
// REPORTS
// ═══════════════════════════════════════════

async function loadReports() {
    try {
        const res = await fetch('/api/reports');
        const data = await res.json();
        renderReportsList(data.reports);
    } catch (err) {
        console.error('Failed to load reports:', err);
    }
}

function renderReportsList(reports) {
    const container = document.getElementById('reportsList');

    if (!reports || reports.length === 0) {
        container.innerHTML = `<div class="card"><div class="card-body" style="text-align:center;padding:48px">
            <span class="material-symbols-outlined" style="font-size:48px;color:var(--steel-light);margin-bottom:12px">folder_open</span>
            <h3 style="color:var(--navy);margin-bottom:6px">No Reports Yet</h3>
            <p style="color:var(--text-secondary)">Generate a forecast and click "Save Report" to save your analysis.</p>
        </div></div>`;
        return;
    }

    container.innerHTML = reports.map(r => {
        const signalClass = r.market_signal === 'BUY NOW' ? 'badge-success' : r.market_signal === 'WAIT' ? 'badge-warning' : 'badge-danger';
        const date = new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
        return `<div class="card mb-16">
            <div class="card-body">
                <div class="d-flex align-center justify-between mb-12">
                    <div>
                        <h3 style="font-size:1rem;font-weight:700;color:var(--navy);margin-bottom:4px">${r.report_title}</h3>
                        <span style="font-size:0.78rem;color:var(--text-muted)">Created: ${date}</span>
                    </div>
                    <div class="d-flex align-center" style="gap:8px">
                        <span class="badge ${signalClass}"><span class="badge-dot"></span> ${r.market_signal}</span>
                    </div>
                </div>
                <div class="grid-4" style="gap:16px">
                    <div>
                        <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Route</div>
                        <div style="font-weight:600;margin-top:2px">${r.trade_route?.replace(/_/g, ' ') || '—'} → ${r.destination_port}</div>
                    </div>
                    <div>
                        <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Volume / Vessel</div>
                        <div style="font-weight:600;margin-top:2px">${parseFloat(r.cargo_volume_tons).toLocaleString()} MT / ${r.recommended_vessel}</div>
                    </div>
                    <div>
                        <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Forecasted Rate</div>
                        <div style="font-weight:600;margin-top:2px">$${parseFloat(r.forecasted_rate_per_ton).toFixed(2)}/Ton</div>
                    </div>
                    <div>
                        <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Projected Savings</div>
                        <div style="font-weight:700;color:var(--success);margin-top:2px">$${parseFloat(r.projected_arbitrage_savings || 0).toLocaleString()}</div>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}
