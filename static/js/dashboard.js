// ─────────────────────────────────────────────
// 1. CONNECTION STATUS  (every 30s)
// ─────────────────────────────────────────────
async function checkStatus() {
    try {
        const res  = await fetch('/jenkins/api/status');
        const data = await res.json();
        const dot    = document.getElementById('statusDot');
        const val    = document.getElementById('statusVal');
        const banner = document.getElementById('disconnectedBanner');

        if (data.connected) {
            dot.classList.remove('pulse-dot-error');
            val.textContent = 'Connected';
            val.className   = 'ji-val ok';
            banner.style.display = 'none';
            loadKPIs();
        } else {
            dot.classList.add('pulse-dot-error');
            val.textContent = 'Disconnected';
            val.className   = 'ji-val error';
            banner.style.display = 'flex';
            clearDashboard();
        }
    } catch (e) {
        const val    = document.getElementById('statusVal');
        const banner = document.getElementById('disconnectedBanner');
        if (val)    { val.textContent = 'Unreachable'; val.className = 'ji-val error'; }
        if (banner) { banner.style.display = 'flex'; }
        clearDashboard();
    }
}

// ─────────────────────────────────────────────
// 2. LOAD ALL KPIs
// ─────────────────────────────────────────────
async function loadKPIs() {
    try {
        const res = await fetch(document.body.dataset.kpisUrl);
        const d   = await res.json();
        if (!d.connected) { clearDashboard(); return; }

        // stat cards
        document.getElementById('sv-total').textContent   = d.total_builds ?? '--';
        document.getElementById('sv-success').textContent = d.successful   ?? '--';
        document.getElementById('sv-failed').textContent  = d.failed       ?? '--';
        document.getElementById('sv-aborted').textContent = d.aborted      ?? '--';

        // circles
        updateCircle('health',       d.health_score  ?? 0, 'health-val', 'health-badge');
        updateCircle('success-rate', d.success_rate  ?? 0, 'rate-val',   'rate-badge');

        // active builds
        updateActiveBuilds(d.running ?? 0, d.build_trend ?? []);

        // topbar last build number
        if (d.build_trend && d.build_trend.length > 0) {
            const tag = document.getElementById('latestBuildTag');
            if (tag) tag.textContent = '#' + d.build_trend[0].number;
        }

        // charts
        if (d.build_trend && d.build_trend.length > 0) {
            renderBarChart(d.build_trend);
            renderTrendChart(d.build_trend);
        }
    } catch (e) {
        console.error('KPI fetch error:', e);
    }
}

// ─────────────────────────────────────────────
// 3. CIRCULAR PROGRESS
// ─────────────────────────────────────────────
function updateCircle(cardCls, pct, valId, badgeId) {
    const card = document.querySelector('.kpi-card.' + cardCls);
    if (!card) return;
    const circleEl = card.querySelector('.circle-progress');
    const valEl    = document.getElementById(valId);
    const badgeEl  = document.getElementById(badgeId);
    if (circleEl) circleEl.style.strokeDashoffset = 150.796 * (1 - pct / 100);
    if (valEl)    valEl.textContent = Math.round(pct);
    if (badgeEl) {
        if (pct >= 80)      { badgeEl.className = 'kpi-badge green'; badgeEl.textContent = '↑ Excellent'; }
        else if (pct >= 50) { badgeEl.className = 'kpi-badge blue';  badgeEl.textContent = '~ Fair'; }
        else                { badgeEl.className = 'kpi-badge red';   badgeEl.textContent = '↓ Poor'; }
    }
}

// ─────────────────────────────────────────────
// 4. ACTIVE BUILDS
// ─────────────────────────────────────────────
function updateActiveBuilds(runningCount, builds) {
    const badge     = document.getElementById('activeCountBadge');
    const container = document.getElementById('activeBuildLines');
    if (badge) badge.textContent = runningCount + ' running';
    if (!container) return;
    const active = builds.filter(b => b.result === null);
    if (active.length === 0) {
        container.innerHTML = '<div class="no-builds">No active builds right now</div>';
        return;
    }
    container.innerHTML = active.map(b => {
        const elapsed = Math.round((Date.now() - b.timestamp) / 1000);
        const m = Math.floor(elapsed / 60), s = elapsed % 60;
        return '<div class="build-line">'
            + '<div class="bl-top"><div class="bl-id">#' + b.number + '</div>'
            + '<div class="bl-meta"><div class="bl-duration">' + m + 'm ' + String(s).padStart(2,'0') + 's</div></div></div>'
            + '<div class="bl-progress-track"><div class="bl-progress-fill" style="width:50%"></div></div>'
            + '<div class="bl-footer"><span class="bl-stage">Running...</span><span class="bl-pct">In progress</span></div>'
            + '</div>';
    }).join('');
}

// ─────────────────────────────────────────────
// 5. BAR CHART  (your CSS design, real data)
// ─────────────────────────────────────────────
function renderBarChart(builds) {
    const wrap   = document.getElementById('barsWrap');
    const sumRow = document.getElementById('buildSummaryRow');
    if (!wrap) return;

    const sorted = [...builds].reverse();
    const maxDur = Math.max(...sorted.map(b => b.duration || 1));

    const pass = builds.filter(b => b.result === 'SUCCESS').length;
    const fail = builds.filter(b => b.result === 'FAILURE').length;
    const abrt = builds.filter(b => b.result === 'ABORTED').length;

    if (sumRow) {
        sumRow.innerHTML =
            '<div class="bstat pass"><div class="bstat-dot"></div>' + pass + ' Pass</div>' +
            '<div class="bstat fail"><div class="bstat-dot"></div>' + fail + ' Fail</div>' +
            '<div class="bstat abrt"><div class="bstat-dot"></div>' + abrt + ' Aborted</div>';
    }

    wrap.innerHTML = sorted.map(b => {
        const dur  = b.duration || 0;
        const mins = Math.floor(dur / 60000);
        const secs = Math.floor((dur % 60000) / 1000);
        const pct  = Math.max(5, Math.round((dur / maxDur) * 100));
        const cls  = b.result === 'SUCCESS' ? 'pass' : b.result === 'FAILURE' ? 'fail' : 'abrt';
        const tip  = '#' + b.number + ' · ' + (b.result || 'RUNNING') + ' · ' + mins + 'm ' + secs + 's';
        return '<div class="bar-col">'
            + '<div class="bar-tooltip">' + tip + '</div>'
            + '<div class="bar ' + cls + '" style="height:' + pct + '%"></div>'
            + '<div class="bar-lbl">#' + b.number + '</div>'
            + '</div>';
    }).join('');
}

// ─────────────────────────────────────────────
// 6. SVG TREND CHART  (your exact SVG design, real data)
// ─────────────────────────────────────────────
function renderTrendChart(builds) {
    const sorted = [...builds].reverse();
    const n      = sorted.length;
    const X_MIN  = 36, X_MAX = 412, Y_TOP = 18, Y_BOT = 138;
    const xStep  = n > 1 ? (X_MAX - X_MIN) / (n - 1) : 0;

    const points = sorted.map((b, i) => {
        const val = b.result === 'SUCCESS' ? 1 : 0;
        const x   = n > 1 ? X_MIN + i * xStep : (X_MIN + X_MAX) / 2;
        const y   = Y_BOT - val * (Y_BOT - Y_TOP);
        return { x, y, build: b, val };
    });

    // smooth cubic bezier
    function makePath(pts) {
        if (!pts.length) return '';
        if (pts.length === 1) return 'M' + pts[0].x + ',' + pts[0].y;
        let d = 'M' + pts[0].x + ',' + pts[0].y;
        for (let i = 1; i < pts.length; i++) {
            const prev = pts[i-1], curr = pts[i];
            const cpx  = (prev.x + curr.x) / 2;
            d += ' C' + cpx + ',' + prev.y + ' ' + cpx + ',' + curr.y + ' ' + curr.x + ',' + curr.y;
        }
        return d;
    }

    const linePath = makePath(points);
    const firstPt  = points[0];
    const lastPt   = points[points.length - 1];

    // success area
    document.getElementById('trendSuccessLine').setAttribute('d', linePath);
    document.getElementById('trendSuccessArea').setAttribute('d',
        linePath + ' L' + lastPt.x + ',' + Y_BOT + ' L' + firstPt.x + ',' + Y_BOT + ' Z');

    // fail line — subtle: mirror at 50% success line (y=78)
    const failPoints = points.map(p => ({ x: p.x, y: Y_BOT - (Y_BOT - p.y) * 0.25 + 8 }));
    document.getElementById('trendFailLine').setAttribute('d', makePath(failPoints));
    document.getElementById('trendFailArea').setAttribute('d',
        makePath(failPoints) + ' L' + lastPt.x + ',' + Y_BOT + ' L' + firstPt.x + ',' + Y_BOT + ' Z');

    // dots
    document.getElementById('trendDots').innerHTML = points.map((p, i) => {
        const isLast = i === points.length - 1;
        const color  = p.build.result === 'SUCCESS' ? '#00dba0'
                     : p.build.result === 'FAILURE' ? '#ff4560' : '#ff8c42';
        return isLast
            ? '<circle cx="' + p.x + '" cy="' + p.y + '" r="5" fill="' + color + '" stroke="white" stroke-width="2"/>'
            : '<circle cx="' + p.x + '" cy="' + p.y + '" r="4" fill="' + color + '"/>';
    }).join('');

    // x-axis build labels
    document.getElementById('trendXLabels').innerHTML = points.map(p =>
        '<text x="' + p.x + '" y="158" class="axis-label" text-anchor="middle">#' + p.build.number + '</text>'
    ).join('');

    // trend badge
    const half    = Math.floor(n / 2);
    const oldRate = half > 0 ? points.slice(0, half).filter(p => p.val).length / half * 100 : 0;
    const newRate = points.slice(half).filter(p => p.val).length / Math.max(1, n - half) * 100;
    const diff    = Math.round(newRate - oldRate);
    const badge   = document.getElementById('trendBadge');
    if (badge) {
        badge.textContent = (diff >= 0 ? '↑ +' : '↓ ') + diff + '%';
        badge.style.background = diff >= 0 ? 'rgba(0,219,160,.1)' : 'rgba(255,69,96,.1)';
        badge.style.color      = diff >= 0 ? 'var(--green)' : 'var(--red)';
        badge.style.border     = '1px solid ' + (diff >= 0 ? 'rgba(0,219,160,.2)' : 'rgba(255,69,96,.2)');
    }
}

// ─────────────────────────────────────────────
// 7. CLEAR DASHBOARD
// ─────────────────────────────────────────────
function clearDashboard() {
    ['sv-total','sv-success','sv-failed','sv-aborted'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '--';
    });
    ['health','success-rate'].forEach(cls => {
        const card = document.querySelector('.kpi-card.' + cls);
        if (!card) return;
        const circle = card.querySelector('.circle-progress');
        if (circle) circle.style.strokeDashoffset = '150.796';
    });
    const hv = document.getElementById('health-val'); if (hv) hv.textContent = '0';
    const rv = document.getElementById('rate-val');   if (rv) rv.textContent = '0';
    ['health-badge','rate-badge'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.className = 'kpi-badge red'; el.textContent = '⚠ No data'; }
    });
    const container = document.getElementById('activeBuildLines');
    if (container) container.innerHTML = '<div class="no-builds">No active builds — Jenkins is disconnected</div>';
    const badge = document.getElementById('activeCountBadge');
    if (badge) badge.textContent = '0 running';
    const wrap = document.getElementById('barsWrap');
    if (wrap) wrap.innerHTML = '<div class="no-builds" style="width:100%;text-align:center;">No build data available</div>';
    const sumRow = document.getElementById('buildSummaryRow');
    if (sumRow) sumRow.innerHTML = '';
}

// ─────────────────────────────────────────────
// BOOT
// ─────────────────────────────────────────────
checkStatus();
setInterval(checkStatus, 30000);