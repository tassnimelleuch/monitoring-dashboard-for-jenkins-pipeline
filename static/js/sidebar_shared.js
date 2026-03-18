// ═══════════════════════════════════════
// static/js/sidebar_shared.js
// Shared by all dashboard pages
// ═══════════════════════════════════════

// Set correct theme icon on load
(function(){
  const sv = localStorage.getItem('jm-t') || 'dark';
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.textContent = sv === 'dark' ? '☀️' : '🌙';
  });
})();

// Refresh button with spin
function doRefresh() {
  const b = document.getElementById('refBtn');
  if (b) b.classList.add('spin');
  setTimeout(() => window.location.reload(), 700);
}

// Nav active state (for items without server-side active_page)
function setActive(el) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');
}

// Connection status (used by all dashboard pages)
async function checkStatus() {
  try {
    const data = await (await fetch('/jenkins/api/status')).json();
    const dot  = document.getElementById('statusDot');
    const val  = document.getElementById('statusVal');
    if (data.connected) {
      dot.classList.remove('pulse-dot-error');
      val.textContent = 'Connected';
      val.className   = 'ji-val ok';
    } else {
      dot.classList.add('pulse-dot-error');
      val.textContent = 'Disconnected';
      val.className   = 'ji-val error';
    }
  } catch (e) {
    const val = document.getElementById('statusVal');
    if (val) { val.textContent = 'Unreachable'; val.className = 'ji-val error'; }
  }
}

// Shared helpers
function fmtDur(ms) {
  if (!ms) return '0s';
  const s = Math.round(ms / 1000), m = Math.floor(s / 60);
  return m > 0 ? m + 'm ' + String(s % 60).padStart(2, '0') + 's' : s + 's';
}
function resultCls(r)   { return r === 'SUCCESS' ? 'pass' : r === 'FAILURE' ? 'fail' : 'abrt'; }
function resultLabel(r) { return r === 'SUCCESS' ? '✓ SUCCESS' : r === 'FAILURE' ? '✗ FAILURE' : '⊘ ' + (r || 'ABORTED'); }
function openConsole(num) { window.open('/jenkins/console/' + num, '_blank'); }