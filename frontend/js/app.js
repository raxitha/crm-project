// ---------------------------------------------------------------------------
// Auth guard: redirect to login if not authenticated
// ---------------------------------------------------------------------------
let currentLeadId = null;

async function checkAuth() {
  const res = await fetch(`${API_BASE}/api/me`, { credentials: 'include' });
  const data = await res.json();
  if (!data.authenticated) {
    window.location.href = 'index.html';
    return;
  }
  document.getElementById('whoami').textContent = data.username;
}
checkAuth();

document.getElementById('logoutBtn').onclick = async () => {
  await fetch(`${API_BASE}/api/logout`, { method: 'POST', credentials: 'include' });
  window.location.href = 'index.html';
};

// ---------------------------------------------------------------------------
// Nav switching
// ---------------------------------------------------------------------------
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
    document.getElementById(link.dataset.view).style.display = 'block';
    if (link.dataset.view === 'dashboardView') loadDashboard();
    if (link.dataset.view === 'leadsView') loadLeads();
  });
});

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
async function loadDashboard() {
  const res = await fetch(`${API_BASE}/api/dashboard/stats`, { credentials: 'include' });
  const data = await res.json();

  const statGrid = document.getElementById('statGrid');
  const statuses = Object.entries(data.by_status);
  statGrid.innerHTML = `
    <div class="stat-card stat-total">
      <div class="stat-value">${data.total_leads}</div>
      <div class="stat-label">Total leads</div>
    </div>
    ${statuses.map(([status, count]) => `
      <div class="stat-card">
        <div class="stat-value">${count}</div>
        <div class="stat-label">${status}</div>
      </div>
    `).join('')}
  `;

  const tbody = document.querySelector('#recentTable tbody');
  tbody.innerHTML = data.recent_leads.map(l => `
    <tr>
      <td>${escapeHtml(l.name)}</td>
      <td>${escapeHtml(l.company || '—')}</td>
      <td><span class="badge badge-${l.status}">${l.status}</span></td>
      <td>${new Date(l.created_at).toLocaleDateString()}</td>
    </tr>
  `).join('') || `<tr><td colspan="4" class="muted">No leads yet.</td></tr>`;
}
loadDashboard();

// ---------------------------------------------------------------------------
// Leads list + search + filter
// ---------------------------------------------------------------------------
let searchTimer = null;
document.getElementById('searchInput').addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadLeads, 300);
});
document.getElementById('statusFilter').addEventListener('change', loadLeads);

async function loadLeads() {
  const q = document.getElementById('searchInput').value.trim();
  const status = document.getElementById('statusFilter').value;
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (status) params.set('status', status);

  const res = await fetch(`${API_BASE}/api/leads?${params.toString()}`, { credentials: 'include' });
  const leads = await res.json();

  const tbody = document.querySelector('#leadsTable tbody');
  tbody.innerHTML = leads.map(l => `
    <tr>
      <td>${l.logo_url ? `<img class="row-logo" src="${l.logo_url}" onerror="this.style.display='none'">` : ''}</td>
      <td><a href="#" class="lead-link" data-id="${l.id}">${escapeHtml(l.name)}</a></td>
      <td>${escapeHtml(l.company || '—')}</td>
      <td>${escapeHtml(l.email || '—')}</td>
      <td>${escapeHtml(l.phone || '—')}</td>
      <td><span class="badge badge-${l.status}">${l.status}</span></td>
      <td>${escapeHtml(l.source || '—')}</td>
      <td><button class="btn-ghost small delete-btn" data-id="${l.id}">Delete</button></td>
    </tr>
  `).join('') || `<tr><td colspan="8" class="muted">No leads match your search.</td></tr>`;

  document.querySelectorAll('.lead-link').forEach(a => {
    a.onclick = (e) => { e.preventDefault(); openDetail(a.dataset.id); };
  });
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.onclick = async () => {
      if (!confirm('Delete this lead?')) return;
      await fetch(`${API_BASE}/api/leads/${btn.dataset.id}`, { method: 'DELETE', credentials: 'include' });
      loadLeads();
    };
  });
}

// ---------------------------------------------------------------------------
// Add / Edit lead modal
// ---------------------------------------------------------------------------
const leadModalOverlay = document.getElementById('leadModalOverlay');
document.getElementById('addLeadBtn').onclick = () => {
  document.getElementById('leadModalTitle').textContent = 'Add lead';
  document.getElementById('leadForm').reset();
  document.getElementById('leadId').value = '';
  leadModalOverlay.classList.add('open');
};
document.getElementById('cancelLeadBtn').onclick = () => leadModalOverlay.classList.remove('open');

document.getElementById('leadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = document.getElementById('leadId').value;
  const payload = {
    name: document.getElementById('fName').value,
    company: document.getElementById('fCompany').value,
    website: document.getElementById('fWebsite').value,
    email: document.getElementById('fEmail').value,
    phone: document.getElementById('fPhone').value,
    source: document.getElementById('fSource').value,
    status: document.getElementById('fStatus').value,
  };
  const url = id ? `${API_BASE}/api/leads/${id}` : `${API_BASE}/api/leads`;
  const method = id ? 'PUT' : 'POST';
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  leadModalOverlay.classList.remove('open');
  loadLeads();
  loadDashboard();
});

// ---------------------------------------------------------------------------
// Lead detail + notes modal
// ---------------------------------------------------------------------------
const detailModalOverlay = document.getElementById('detailModalOverlay');
document.getElementById('closeDetailBtn').onclick = () => detailModalOverlay.classList.remove('open');

async function openDetail(id) {
  currentLeadId = id;
  const res = await fetch(`${API_BASE}/api/leads/${id}`, { credentials: 'include' });
  const lead = await res.json();

  document.getElementById('detailName').textContent = lead.name;
  document.getElementById('detailCompany').textContent = lead.company || '';
  document.getElementById('detailEmail').textContent = lead.email || '—';
  document.getElementById('detailPhone').textContent = lead.phone || '—';
  document.getElementById('detailSource').textContent = lead.source || '—';
  document.getElementById('detailStatus').value = lead.status;

  const logoImg = document.getElementById('detailLogo');
  if (lead.logo_url) {
    logoImg.src = lead.logo_url;
    logoImg.style.display = 'block';
  } else {
    logoImg.style.display = 'none';
  }

  renderNotes(lead.notes || []);
  detailModalOverlay.classList.add('open');
}

document.getElementById('detailStatus').addEventListener('change', async (e) => {
  await fetch(`${API_BASE}/api/leads/${currentLeadId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ status: e.target.value }),
  });
  loadLeads();
  loadDashboard();
});

function renderNotes(notes) {
  const list = document.getElementById('notesList');
  list.innerHTML = notes.map(n => `
    <div class="note-item">
      <p>${escapeHtml(n.note_text)}</p>
      <span class="muted small">${new Date(n.created_at).toLocaleString()}</span>
    </div>
  `).join('') || `<p class="muted">No notes yet.</p>`;
}

document.getElementById('noteForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('noteText');
  const res = await fetch(`${API_BASE}/api/leads/${currentLeadId}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ note_text: input.value }),
  });
  if (res.ok) {
    input.value = '';
    openDetail(currentLeadId); // refresh notes
  }
});

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Initial load
loadLeads();
