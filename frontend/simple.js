// Auto-detect API base URL for local and production
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000/api'  // Local development
    : '/api';  // Production (same domain)

// Category colors
const colors = {
    cloud: '#7aa9ff',
    dev_tools: '#a78bfa',
    ai: '#ffe600',
    streaming: '#ff6b1a',
    music: '#5fe39a',
    music_tools: '#00d4aa',
    design: '#ff5e99',
    productivity: '#8a8df0',
    gaming: '#ff4d4d',
    security: '#0572ec',
    other: '#8a8a8e'
};

async function loadSubscriptions() {
    try {
        const [subsRes, statsRes, pendingRes] = await Promise.all([
            fetch(`${API_BASE}/subscriptions?page_size=200`),
            fetch(`${API_BASE}/stats`),
            fetch(`${API_BASE}/subscriptions?approval_status=pending&page_size=50`),
        ]);
        const data = await subsRes.json();
        const stats = await statsRes.json();
        const pendingData = await pendingRes.json();
        const subs = data.items || [];
        const pendingSubs = pendingData.items || [];

        renderStats(subs, stats);
        renderSubscriptions(subs);
        renderPendingSection(pendingSubs);
        loadCandidates();
    } catch (err) {
        console.error('Error loading subscriptions:', err);
        document.getElementById('subscriptions').innerHTML = '<div class="loading">Error loading data</div>';
    }
}

async function loadCandidates() {
    try {
        const res = await fetch(`${API_BASE}/wallet-candidates?min_occurrences=2&min_score=70`);
        const data = await res.json();
        renderCandidates(data.candidates || []);
    } catch (err) {
        console.error('Candidates error:', err);
    }
}

function renderCandidates(candidates) {
    const section = document.getElementById('candidates-section');
    if (!section) return;
    if (candidates.length === 0) {
        section.style.display = 'none';
        return;
    }
    section.style.display = 'block';
    const container = document.getElementById('candidates-grid');
    container.innerHTML = candidates.map(c => `
        <div class="candidate-card">
            <div class="candidate-payee">${c.payee}</div>
            <div class="candidate-meta">
                ${c.occurrences}x · avg ${c.avg_amount.toFixed(0)} ${c.currency}
                · last ${(c.last_seen || '').substring(0, 10)}
            </div>
            <div class="candidate-score">score ${c.score}/100</div>
            <div class="candidate-actions">
                <input class="candidate-name-input" type="text" placeholder="Service name"
                    value="${_capitalize(c.normalized)}" id="name-${btoa(c.payee).substring(0,8)}">
                <button class="btn-confirm" onclick="promoteCandidate('${c.payee.replace(/'/g,"\\'")}', this)">
                    + Add as Sub
                </button>
            </div>
        </div>
    `).join('');
}

function _capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

async function promoteCandidate(payee, btn) {
    const card = btn.closest('.candidate-card');
    const nameInput = card.querySelector('.candidate-name-input');
    const serviceName = nameInput.value.trim();
    if (!serviceName) { nameInput.focus(); return; }

    btn.textContent = 'Adding...';
    btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/wallet-candidates/promote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payee, service_name: serviceName, category: 'other' }),
        });
        const data = await res.json();
        card.innerHTML = `<div class="candidate-promoted">✓ Added: ${data.created}</div>`;
        // Reload main list to show new sub
        setTimeout(loadSubscriptions, 800);
    } catch (err) {
        btn.textContent = '+ Add as Sub';
        btn.disabled = false;
        alert('Failed: ' + err.message);
    }
}

function renderStats(subs, stats) {
    const monthlyTotal = subs.reduce((sum, s) => {
        const cost = s.cost || 0;
        return sum + (s.billing_cycle === 'yearly' ? cost / 12 : cost);
    }, 0);

    const yearlyTotal = monthlyTotal * 12;
    const activeCount = subs.filter(s => s.status === 'active').length;

    document.getElementById('monthly-total').textContent = monthlyTotal.toFixed(2);
    document.getElementById('yearly-total').textContent = yearlyTotal.toFixed(2);
    document.getElementById('active-count').textContent = activeCount;
    document.getElementById('total-count').textContent = subs.length;

    // Wallet-enriched stats
    const confirmedEl = document.getElementById('confirmed-count');
    const actualSpendEl = document.getElementById('actual-spend');
    if (confirmedEl && stats.confirmed_count !== undefined) {
        confirmedEl.textContent = stats.confirmed_count;
    }
    if (actualSpendEl && stats.actual_monthly_spend !== undefined) {
        actualSpendEl.textContent = stats.actual_monthly_spend.toFixed(2);
    }
}

function renderSubscriptions(subs) {
    const container = document.getElementById('subscriptions');

    if (subs.length === 0) {
        container.innerHTML = '<div class="loading">No subscriptions yet</div>';
        return;
    }

    container.innerHTML = subs.map(sub => {
        const color = colors[sub.category] || colors.other;
        const initials = sub.service_name.substring(0, 2).toUpperCase();
        const cost = (sub.cost || 0).toFixed(2);
        const currency = sub.currency === 'USD' ? '$' :
                        sub.currency === 'EUR' ? '€' :
                        sub.currency === 'GBP' ? '£' :
                        (sub.currency || '');

        const verified = sub.confirmed_by_wallet
            ? `<span class="badge-verified" title="Confirmed by bank records">✓</span>`
            : '';

        // Total spent badge (top-right of card)
        const totalSpentHtml = sub.total_spent
            ? `<div class="sub-total-spent" title="Total spent from bank records">${sub.total_spent.toFixed(0)} CZK total</div>`
            : '';

        // Source badge
        const sourceBadge = sub.source && sub.source !== 'manual'
            ? `<span class="badge-source">${sub.source.replace('_', ' ')}</span>`
            : '';

        // Show actual cost from wallet if it differs meaningfully from email-parsed cost
        let actualCostHtml = '';
        if (sub.confirmed_by_wallet && sub.actual_cost && Math.abs(sub.actual_cost - sub.cost) > 1) {
            actualCostHtml = `<div class="sub-actual-cost" title="Actual from bank">actual: ${sub.actual_cost.toFixed(0)} CZK</div>`;
        }

        const lastPayment = sub.last_payment_date
            ? `<div class="sub-last-payment">last: ${sub.last_payment_date.substring(0, 10)}</div>`
            : '';

        return `
            <div class="sub-card${sub.confirmed_by_wallet ? ' sub-card--verified' : ''}">
                <div class="sub-card-top">
                    <div class="sub-icon" style="background: ${color};">${initials}</div>
                    ${totalSpentHtml}
                </div>
                <div class="sub-name">${sub.service_name} ${verified}</div>
                <div class="sub-category">${sub.category} ${sourceBadge}</div>
                <div class="sub-cost">${currency}${cost}</div>
                ${actualCostHtml}
                ${lastPayment}
                <div class="sub-details">
                    <div class="sub-cycle">${sub.billing_cycle}</div>
                    <div class="status-badge status-${sub.status}">${sub.status}</div>
                </div>
            </div>
        `;
    }).join('');
}

function renderPendingSection(pendingSubs) {
    const section = document.getElementById('pending-section');
    if (!section) return;
    if (pendingSubs.length === 0) {
        section.style.display = 'none';
        return;
    }
    section.style.display = 'block';
    const container = document.getElementById('pending-grid');
    container.innerHTML = pendingSubs.map(sub => {
        const color = colors[sub.category] || colors.other;
        const initials = sub.service_name.substring(0, 2).toUpperCase();
        const cost = (sub.cost || 0).toFixed(2);
        const currency = sub.currency === 'USD' ? '$' : sub.currency === 'EUR' ? '€' : (sub.currency || '');
        const totalSpent = sub.total_spent ? `· ${sub.total_spent.toFixed(0)} CZK total` : '';

        return `
            <div class="pending-card" id="pending-${sub.id}">
                <div class="pending-card-header">
                    <input type="checkbox" class="pending-checkbox" value="${sub.id}" id="chk-${sub.id}">
                    <div class="sub-icon" style="background: ${color}; width:36px; height:36px; font-size:13px;">${initials}</div>
                    <div class="pending-info">
                        <div class="pending-name">${sub.service_name}</div>
                        <div class="pending-meta">${sub.category} · ${currency}${cost}/${sub.billing_cycle} ${totalSpent}</div>
                    </div>
                </div>
                <div class="pending-actions">
                    <button class="btn-approve" onclick="approveSub(${sub.id})">✓ Approve</button>
                    <button class="btn-dismiss" onclick="dismissSub(${sub.id})">✕ Dismiss</button>
                </div>
            </div>
        `;
    }).join('');
}

async function approveSub(id) {
    const card = document.getElementById(`pending-${id}`);
    try {
        await fetch(`${API_BASE}/subscriptions/${id}/approve`, { method: 'POST' });
        card.style.opacity = '0.4';
        card.innerHTML = '<div style="color:#5fe39a; padding:8px;">✓ Approved</div>';
        setTimeout(loadSubscriptions, 600);
    } catch (err) {
        alert('Failed: ' + err.message);
    }
}

async function dismissSub(id) {
    const card = document.getElementById(`pending-${id}`);
    try {
        await fetch(`${API_BASE}/subscriptions/${id}/dismiss`, { method: 'POST' });
        card.style.opacity = '0.4';
        card.innerHTML = '<div style="color:#888; padding:8px;">✕ Dismissed</div>';
        setTimeout(loadSubscriptions, 600);
    } catch (err) {
        alert('Failed: ' + err.message);
    }
}

async function approveSelected() {
    const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
    const ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
    if (!ids.length) { alert('Select at least one subscription'); return; }
    await fetch(`${API_BASE}/subscriptions/bulk-approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ids),
    });
    loadSubscriptions();
}

async function dismissSelected() {
    const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
    const ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
    if (!ids.length) { alert('Select at least one subscription'); return; }
    await fetch(`${API_BASE}/subscriptions/bulk-dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ids),
    });
    loadSubscriptions();
}

async function syncData() {
    const btn = event.target;
    btn.textContent = 'Syncing...';
    btn.disabled = true;
    
    try {
        await fetch(`${API_BASE}/parse-emails`, { method: 'POST' });
        await loadSubscriptions();
    } catch (err) {
        console.error('Sync error:', err);
        alert('Sync failed: ' + err.message);
    }
    
    btn.textContent = '↻ Sync';
    btn.disabled = false;
}

// Load on startup
loadSubscriptions();
