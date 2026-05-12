const API_BASE = 'http://localhost:8000/api';

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
        const res = await fetch(`${API_BASE}/subscriptions?page_size=100`);
        const data = await res.json();
        const subs = data.items || [];
        
        renderStats(subs);
        renderSubscriptions(subs);
    } catch (err) {
        console.error('Error loading subscriptions:', err);
        document.getElementById('subscriptions').innerHTML = '<div class="loading">Error loading data</div>';
    }
}

function renderStats(subs) {
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
                        sub.currency;
        
        return `
            <div class="sub-card">
                <div class="sub-icon" style="background: ${color};">${initials}</div>
                <div class="sub-name">${sub.service_name}</div>
                <div class="sub-category">${sub.category}</div>
                <div class="sub-cost">${currency}${cost}</div>
                <div class="sub-details">
                    <div class="sub-cycle">${sub.billing_cycle}</div>
                    <div class="status-badge status-${sub.status}">${sub.status}</div>
                </div>
            </div>
        `;
    }).join('');
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
