const API = {
  books: '/api/books',
  users: '/api/users',
  loans: '/api/loans',
  reco: '/api/recommendations',
};

// ───────────── Navigation ─────────────
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.currentTarget.classList.add('active');
  const loaders = { catalogue: loadBooks, emprunts: loadLoans, utilisateurs: loadUsers, recommandations: loadModelStatus };
  if (loaders[name]) loaders[name]();
}

// ───────────── Toast ─────────────
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3500);
}

// ───────────── Modals ─────────────
function openModal(id) {
  document.getElementById(id).classList.add('open');
  if (id === 'modal-new-loan') populateLoanSelects();
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  const form = document.querySelector(`#${id} form`);
  if (form) form.reset();
}
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal')) {
    e.target.classList.remove('open');
  }
});

// ───────────── API helpers ─────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || data.detail || 'Erreur inconnue');
  return data;
}

// ───────────── BOOKS ─────────────
async function loadBooks() {
  const grid = document.getElementById('books-grid');
  grid.innerHTML = loadingHTML();
  try {
    const books = await apiFetch(API.books);
    renderBooks(books);
  } catch (e) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
  }
}

async function searchBooks() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) { loadBooks(); return; }
  const type = document.getElementById('search-type').value;
  try {
    const books = await apiFetch(`${API.books}/search?q=${encodeURIComponent(q)}&type=${type}`);
    renderBooks(books);
  } catch (e) { showToast(e.message, 'error'); }
}

function renderBooks(books) {
  const grid = document.getElementById('books-grid');
  if (!books.length) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">📚</div><p>Aucun livre trouvé</p></div>';
    return;
  }
  grid.innerHTML = books.map(b => `
    <div class="book-card">
      <div class="book-cover">📖</div>
      <div class="book-title">${esc(b.title)}</div>
      <div class="book-author">par ${esc(b.author)}</div>
      <div class="book-meta">
        ${b.genre ? `<span class="badge badge-genre">${esc(b.genre)}</span>` : ''}
        <span class="badge ${b.available_copies > 0 ? 'badge-available' : 'badge-unavailable'}">
          ${b.available_copies}/${b.total_copies} dispo
        </span>
      </div>
      <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:.75rem">ISBN: ${esc(b.isbn)}</div>
      <div class="book-actions">
        <button class="btn btn-danger btn-sm" onclick="deleteBook(${b.id})">Supprimer</button>
      </div>
    </div>
  `).join('');
}

async function deleteBook(id) {
  if (!confirm('Supprimer ce livre ?')) return;
  try {
    await apiFetch(`${API.books}/${id}`, { method: 'DELETE' });
    showToast('Livre supprimé');
    loadBooks();
  } catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('form-add-book').addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd);
  if (body.published_year) body.published_year = parseInt(body.published_year);
  if (body.total_copies) body.total_copies = parseInt(body.total_copies);
  try {
    await apiFetch(API.books, { method: 'POST', body: JSON.stringify(body) });
    showToast('Livre ajouté avec succès');
    closeModal('modal-add-book');
    loadBooks();
  } catch (e) { showToast(e.message, 'error'); }
});

// ───────────── LOANS ─────────────
let currentLoanFilter = 'all';

async function loadLoans(status = currentLoanFilter) {
  currentLoanFilter = status;
  const list = document.getElementById('loans-list');
  list.innerHTML = loadingHTML();
  try {
    const url = status === 'all' ? API.loans : `${API.loans}?status=${status}`;
    const loans = await apiFetch(url);
    renderLoans(loans);
  } catch (e) {
    list.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
  }
}

function filterLoans(status, btn) {
  document.querySelectorAll('#emprunts .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadLoans(status);
}

function renderLoans(loans) {
  const list = document.getElementById('loans-list');
  if (!loans.length) {
    list.innerHTML = '<div class="empty-state"><div class="icon">📋</div><p>Aucun emprunt trouvé</p></div>';
    return;
  }
  list.innerHTML = loans.map(l => {
    const badgeClass = l.status === 'actif' ? 'badge-actif' : l.status === 'en_retard' ? 'badge-retarde' : 'badge-retourne';
    const statusLabel = l.status === 'actif' ? 'Actif' : l.status === 'en_retard' ? 'En retard' : 'Retourné';
    return `
    <div class="loan-card">
      <div class="loan-info">
        <div class="loan-book-title">📖 Livre #${l.book_id} — Utilisateur #${l.user_id}</div>
        <div class="loan-meta">Emprunté le ${fmtDate(l.loan_date)}</div>
      </div>
      <div class="loan-dates">
        <div>Échéance: <span class="${l.status === 'en_retard' ? 'overdue-text' : ''}">${fmtDate(l.due_date)}</span></div>
        ${l.return_date ? `<div>Retour: ${fmtDate(l.return_date)}</div>` : ''}
      </div>
      <span class="badge ${badgeClass}">${statusLabel}</span>
      ${l.status !== 'retourne' ? `<button class="btn btn-success btn-sm" onclick="returnLoan(${l.id})">Retourner</button>` : ''}
    </div>`;
  }).join('');
}

async function returnLoan(id) {
  try {
    await apiFetch(`${API.loans}/${id}/return`, { method: 'PUT' });
    showToast('Livre retourné avec succès');
    loadLoans();
  } catch (e) { showToast(e.message, 'error'); }
}

async function populateLoanSelects() {
  try {
    const [users, books] = await Promise.all([apiFetch(API.users), apiFetch(API.books)]);
    const uSel = document.getElementById('loan-user-select');
    const bSel = document.getElementById('loan-book-select');
    uSel.innerHTML = users.map(u => `<option value="${u.id}">${esc(u.name)} (${u.user_type})</option>`).join('');
    bSel.innerHTML = books.filter(b => b.available_copies > 0)
      .map(b => `<option value="${b.id}">${esc(b.title)} [${b.available_copies} dispo]</option>`).join('');
  } catch (e) { showToast('Erreur chargement sélects: ' + e.message, 'error'); }
}

document.getElementById('form-new-loan').addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = { user_id: parseInt(fd.get('user_id')), book_id: parseInt(fd.get('book_id')) };
  try {
    await apiFetch(API.loans, { method: 'POST', body: JSON.stringify(body) });
    showToast('Emprunt enregistré avec succès');
    closeModal('modal-new-loan');
    loadLoans();
  } catch (e) { showToast(e.message, 'error'); }
});

// ───────────── USERS ─────────────
async function loadUsers(type = 'all') {
  const grid = document.getElementById('users-grid');
  grid.innerHTML = loadingHTML();
  try {
    const url = type === 'all' ? API.users : `${API.users}?type=${type}`;
    const users = await apiFetch(url);
    renderUsers(users);
  } catch (e) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
  }
}

function filterUsers(type, btn) {
  document.querySelectorAll('#utilisateurs .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadUsers(type);
}

function renderUsers(users) {
  const grid = document.getElementById('users-grid');
  if (!users.length) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">👤</div><p>Aucun utilisateur trouvé</p></div>';
    return;
  }
  grid.innerHTML = users.map(u => `
    <div class="user-card">
      <div class="user-avatar avatar-${u.user_type}">${esc(u.name[0])}</div>
      <div class="user-info">
        <div class="user-name">${esc(u.name)}</div>
        <div class="user-email">${esc(u.email)}</div>
        <span class="badge badge-type badge-${u.user_type}">${typeLabel(u.user_type)}</span>
      </div>
      <button class="btn btn-outline btn-sm" onclick="deleteUser(${u.id})">×</button>
    </div>
  `).join('');
}

async function deleteUser(id) {
  if (!confirm('Désactiver cet utilisateur ?')) return;
  try {
    await apiFetch(`${API.users}/${id}`, { method: 'DELETE' });
    showToast('Utilisateur désactivé');
    loadUsers();
  } catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('form-add-user').addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd);
  try {
    await apiFetch(API.users, { method: 'POST', body: JSON.stringify(body) });
    showToast('Utilisateur ajouté avec succès');
    closeModal('modal-add-user');
    loadUsers();
  } catch (e) { showToast(e.message, 'error'); }
});

// ───────────── RECOMMENDATIONS ─────────────
async function loadModelStatus() {
  try {
    const status = await apiFetch(`${API.reco}/model/info`);
    const el = document.getElementById('model-status');
    if (status.trained) {
      el.innerHTML = `<span class="badge badge-available">✓ Modèle entraîné — ${status.n_users} utilisateurs, ${status.n_books} livres</span>`;
    } else {
      el.innerHTML = `<span class="badge badge-unavailable">⚠ Modèle non entraîné — Cliquez sur Ré-entraîner</span>`;
    }
  } catch (e) {
    document.getElementById('model-status').innerHTML = `<span class="badge badge-unavailable">Service indisponible</span>`;
  }
}

async function getRecommendations() {
  const userId = document.getElementById('reco-user-id').value;
  if (!userId) { showToast('Entrez un ID utilisateur', 'error'); return; }
  const results = document.getElementById('reco-results');
  results.innerHTML = loadingHTML();
  try {
    const data = await apiFetch(`${API.reco}/recommendations/${userId}?n=6`);
    if (!data.recommendations || !data.recommendations.length) {
      results.innerHTML = '<div class="empty-state"><div class="icon">🔍</div><p>Aucune recommandation disponible</p></div>';
      return;
    }
    const stratLabel = data.strategy === 'collaborative_filtering' ? 'Filtrage collaboratif' : 'Livres populaires';
    results.innerHTML = `
      <div style="grid-column:1/-1;margin-bottom:.5rem;color:var(--text-muted);font-size:.85rem">
        Stratégie: <strong>${stratLabel}</strong> — Utilisateur #${data.user_id}
      </div>
      ${data.recommendations.map((r, i) => `
        <div class="reco-card">
          <div class="reco-rank">#${i + 1} recommandation</div>
          <div class="reco-title">${esc(r.title || `Livre #${r.book_id}`)}</div>
          <div class="reco-author">${esc(r.author || '')}</div>
          ${r.genre ? `<span class="badge badge-genre">${esc(r.genre)}</span>` : ''}
        </div>
      `).join('')}
    `;
  } catch (e) {
    results.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
  }
}

async function retrainModel() {
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.textContent = '⏳ Entraînement...';
  try {
    const result = await apiFetch(`${API.reco}/train`, { method: 'POST' });
    showToast(`Modèle entraîné: ${result.n_users} users, ${result.n_books} livres`);
    loadModelStatus();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 Ré-entraîner le modèle';
  }
}

// ───────────── Utils ─────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('fr-FR');
}

function typeLabel(t) {
  return { etudiant: 'Étudiant', professeur: 'Professeur', personnel: 'Personnel' }[t] || t;
}

function loadingHTML() {
  return '<div class="loading"><div class="spinner"></div><div>Chargement...</div></div>';
}

// ───────────── Init ─────────────
document.addEventListener('DOMContentLoaded', () => {
  loadBooks();
});
