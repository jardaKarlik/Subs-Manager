const API = 'http://localhost:8000/api';

const colors = {
    cloud: '#4A9EFF',
    dev_tools: '#A78BFA',
    ai: '#FFE600',
    streaming: '#FF6B6B',
    music: '#4ECDC4',
    music_tools: '#45B7D1',
    design: '#FF6BCE',
    productivity: '#95E1D3',
    gaming: '#F38181',
    security: '#3498DB',
    other: '#95A5A6'
};

async function load() {
    try {
        const res = await fetch(`${API}/subscriptions?page_size=100`);
        const data = await res.json();
        const subs = data.items || [];
        
        updateStats(subs);
        render(subs);
    } catch (err) {
        console.error('Error:', err);
        document.getElementById('subs').innerHTML = `
            <div class="empty">
                <div class="empty-icon">⚠️</div>
                <h3>Connection Error</h3>
                <p>Make sure API is running on port 8000</p>
            </div>
        `;
    }
}

function updateStats(subs) {
    const monthly = subs.reduce((sum, s) => {
        const cost = s.cost || 0;
        return sum + (s.billing_cycle === 'yearly' ? cost / 12 : cost);
    }, 0);
    
    const yearly = monthly * 12;
    const active = subs.filter(s => s.status === 'active').length;
    
    document.getElementById('monthly').textContent = `$${monthly.toFixed(0)}`;
    document.getElementById('yearly').textContent = `$${yearly.toFixed(0)}`;
    document.getElementById('active').textContent = active;
    document.getElementById('total').textContent = subs.length;
}

function render(subs) {
    const container = document.getElementById('subs');
    
    if (subs.length === 0) {
        container.innerHTML = `
            <div class="empty">
                <div class="empty-icon">📦</div>
                <h3>No Subscriptions</h3>
                <p>Add your first subscription to get started</p>
                <button class="btn-primary" onclick="add()">+ Add Subscription</button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = subs.map(sub => {
        const color = colors[sub.category] || colors.other;
        const icon = sub.service_name.substring(0, 2).toUpperCase();
        const price = `$${(sub.cost || 0).toFixed(2)}`;
        const cycle = sub.billing_cycle || 'monthly';
        const status = sub.status || 'active';
        
        return `
            <div class="card" style="--card-color: ${color}">
                <div class="card-icon">${icon}</div>
                <div class="card-name">${sub.service_name}</div>
                <div class="card-category">${sub.category}</div>
                <div class="card-price">${price}</div>
                <div class="card-footer">
                    <div class="card-cycle">${cycle}</div>
                    <div class="badge badge-${status}">${status}</div>
                </div>
            </div>
        `;
    }).join('');
}

async function sync() {
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Syncing...';
    btn.disabled = true;
    
    try {
        await fetch(`${API}/parse-emails`, { method: 'POST' });
        await load();
    } catch (err) {
        console.error('Sync error:', err);
    }
    
    btn.textContent = orig;
    btn.disabled = false;
}

function add() {
    alert('Add subscription modal coming soon!');
}

// Load on startup
load();
