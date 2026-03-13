async function loadKPIs() {
    const url = document.body.dataset.kpisUrl;
    const res = await fetch(url);
    const d = await res.json();

    // stat cards
    document.querySelector('.stat-card.total .stat-value').textContent = d.total ?? '--';
    document.querySelector('.stat-card.success .stat-value').textContent = d.successful ?? '--';
    document.querySelector('.stat-card.failed .stat-value').textContent = d.failed ?? '--';
    document.querySelector('.stat-card.aborted .stat-value').textContent = d.aborted ?? '--';

    // KPI circles
    updateCircle('health', d.health_score ?? 0);
    updateCircle('success-rate', d.success_rate ?? 0);
}

function updateCircle(cls, pct) {
    const card = document.querySelector(`.kpi-card.${cls}`);
    if (!card) return;
    card.querySelector('.progress-value').textContent = Math.round(pct);
    const circle = card.querySelector('.circle-progress');
    const offset = 150.796 * (1 - pct / 100);
    circle.style.strokeDashoffset = offset;
}

document.addEventListener('DOMContentLoaded', loadKPIs);