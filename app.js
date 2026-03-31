/* ── Config ────────────────────────────────────────────────────────────────── */
const API = 'http://localhost:8000';

/* ── API Helpers ───────────────────────────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    return await res.json();
  } catch(e) { throw e; }
}

const api = {
  get:    (path)       => apiFetch(path),
  post:   (path, body) => apiFetch(path, { method: 'POST',  body: JSON.stringify(body) }),
  patch:  (path, body) => apiFetch(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path)       => apiFetch(path, { method: 'DELETE' }),
};

/* ── Auth ──────────────────────────────────────────────────────────────────── */
function getSession(role) {
  try { return JSON.parse(sessionStorage.getItem(`qms_${role}`)); } catch { return null; }
}
function setSession(role, data) {
  sessionStorage.setItem(`qms_${role}`, JSON.stringify(data));
}
function clearSession(role) {
  sessionStorage.removeItem(`qms_${role}`);
}
function requireAuth(role, loginPage) {
  if (!getSession(role)) { window.location.href = loginPage; return false; }
  return true;
}

/* ── Toast ─────────────────────────────────────────────────────────────────── */
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `show ${type}`;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = ''; }, 3000);
}

/* ── Badges ────────────────────────────────────────────────────────────────── */
function priorityBadge(priority) {
  const map = {
    'Normal':            ['priority-normal',    'Normal'],
    'Emergency':         ['priority-emergency', '! Emergency'],
    'Senior Citizen':    ['priority-senior',    'Senior'],
    'Pregnant':          ['priority-pregnant',  'Pregnant'],
    'Differently Abled': ['priority-disabled',  'Diff. Abled'],
  };
  const [cls, label] = map[priority] || map['Normal'];
  return `<span class="priority-badge ${cls}">${label}</span>`;
}

function statusBadge(status) {
  const map = {
    waiting:    ['badge-waiting',   'Waiting'],
    called:     ['badge-called',    'Called'],
    in_consult: ['badge-consult',   'In Consult'],
    completed:  ['badge-completed', 'Completed'],
    skipped:    ['badge-skipped',   'Skipped'],
  };
  const [cls, label] = map[status] || ['badge-waiting', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

/* ── Formatters ────────────────────────────────────────────────────────────── */
function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 60000);
  if (diff < 1)  return 'just now';
  if (diff < 60) return `${diff}m ago`;
  return `${Math.floor(diff/60)}h ${diff%60}m ago`;
}

function formatWait(mins) {
  if (!mins && mins !== 0) return '—';
  if (mins < 60) return `~${Math.round(mins)} min`;
  return `~${Math.floor(mins/60)}h ${Math.round(mins%60)}m`;
}

/* ── Active nav ────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const page = location.pathname.split('/').pop();
  document.querySelectorAll('.navbar nav a').forEach(a => {
    if (a.getAttribute('href') === page) a.classList.add('active');
  });
});
