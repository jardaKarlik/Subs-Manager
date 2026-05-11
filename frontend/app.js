// Modified frontend to connect to FastAPI backend
const API_BASE = 'http://localhost:8000';

// Fetch subscriptions from backend
async function fetchSubscriptions() {
    try {
        const response = await fetch(`${API_BASE}/api/subscriptions`);
        if (!response.ok) throw new Error('Failed to fetch subscriptions');
        const data = await response.json();
        return data.items || [];
    } catch (error) {
        console.error('Error fetching subscriptions:', error);
        return [];
    }
}

// Add new subscription
async function addSubscription(subscription) {
    try {
        const response = await fetch(`${API_BASE}/api/subscriptions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subscription)
        });
        if (!response.ok) throw new Error('Failed to add subscription');
        return await response.json();
    } catch (error) {
        console.error('Error adding subscription:', error);
        throw error;
    }
}

// Update subscription
async function updateSubscription(id, subscription) {
    try {
        const response = await fetch(`${API_BASE}/api/subscriptions/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subscription)
        });
        if (!response.ok) throw new Error('Failed to update subscription');
        return await response.json();
    } catch (error) {
        console.error('Error updating subscription:', error);
        throw error;
    }
}

// Delete subscription
async function deleteSubscription(id) {
    try {
        const response = await fetch(`${API_BASE}/api/subscriptions/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete subscription');
        return true;
    } catch (error) {
        console.error('Error deleting subscription:', error);
        throw error;
    }
}

// Trigger email parsing
async function parseEmails() {
    try {
        const response = await fetch(`${API_BASE}/api/parse-emails`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to parse emails');
        return await response.json();
    } catch (error) {
        console.error('Error parsing emails:', error);
        throw error;
    }
}

// Get statistics
async function getStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');
        return await response.json();
    } catch (error) {
        console.error('Error fetching stats:', error);
        return { total_monthly_cost: 0, total_yearly_cost: 0, total_subscriptions: 0, by_category: {} };
    }
}

// Calculate monthly cost accounting for billing cycle
function calculateMonthly(cost, billingCycle) {
    const cycle = (billingCycle || 'monthly').toLowerCase();
    if (cycle === 'yearly') {
        return cost / 12;  // Convert yearly to monthly
    }
    return cost || 0;
}

// Extract plan name from notes field
function extractPlan(notes) {
    if (!notes) return 'Standard';
    const match = notes.match(/Plan:\s*([^\n,]+)/);
    return match ? match[1].trim() : 'Standard';
}

// Transform backend data to frontend format
function transformSubscriptionData(backendSubs) {
    return backendSubs.map(sub => ({
        id: sub.id.toString(),
        name: sub.service_name,
        mono: sub.service_name.substring(0, 2).toUpperCase(),
        color: getServiceColor(sub.category),
        cat: sub.category,
        plan: extractPlan(sub.notes),                                    // ✅ FIX #3: Extract plan
        monthly: calculateMonthly(sub.cost, sub.billing_cycle),          // ✅ FIX #1: Calculate monthly
        billing: (sub.billing_cycle || 'monthly').charAt(0).toUpperCase() + (sub.billing_cycle || 'monthly').slice(1),
        usage: Math.random() * 0.8 + 0.2, // Random usage for demo
        since: sub.start_date ? sub.start_date.substring(0, 7) : '2023-01',  // ✅ FIX #2: Use actual start_date
        status: sub.status || 'active'
    }));
}

function getServiceColor(category) {
    const colors = {
        'cloud': '#7aa9ff',
        'dev_tools': '#a78bfa',
        'ai': '#ffe600',
        'streaming': '#ff6b1a',
        'music': '#5fe39a',
        'music_tools': '#00d4aa',
        'design': '#ff5e99',
        'productivity': '#8a8df0',
        'gaming': '#ff4d4d',
        'security': '#0572ec',
        'other': '#8a8a8e'
    };
    return colors[category] || '#ffffff';
}

// Override the original SERVICES data with backend data
let SERVICES = [];
let STATS = { total_monthly: 0, total_yearly: 0, active_count: 0, idle_count: 0 };

// Initialize app with backend data
async function initializeApp() {
    try {
        const [subscriptions, stats] = await Promise.all([
            fetchSubscriptions(),
            getStats()
        ]);
        
        SERVICES = transformSubscriptionData(subscriptions);
        STATS = stats;
        
        // Trigger React re-render if needed
        if (window.refreshApp) {
            window.refreshApp();
        }
        
        console.log('App initialized with backend data:', { SERVICES, STATS });
    } catch (error) {
        console.error('Failed to initialize app:', error);
    }
}

// Add manual subscription form handler
function showAddSubscriptionForm() {
    const form = document.createElement('div');
    form.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000;">
            <div style="background: #161618; padding: 24px; border-radius: 12px; width: 400px; border: 1px solid rgba(255,255,255,0.1);">
                <h3 style="color: #fff; margin: 0 0 16px 0; font-family: 'Space Grotesk', sans-serif;">Add Subscription</h3>
                <form id="add-subscription-form">
                    <div style="margin-bottom: 12px;">
                        <label style="color: #8a8a8e; font-size: 12px; display: block; margin-bottom: 4px;">Service Name</label>
                        <input type="text" name="service_name" required style="width: 100%; padding: 8px; background: #0a0a0b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff;">
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="color: #8a8a8e; font-size: 12px; display: block; margin-bottom: 4px;">Category</label>
                        <select name="category" required style="width: 100%; padding: 8px; background: #0a0a0b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff;">
                            <option value="cloud">Cloud</option>
                            <option value="dev_tools">Dev Tools</option>
                            <option value="ai">AI</option>
                            <option value="streaming">Streaming</option>
                            <option value="music">Music</option>
                            <option value="music_tools">Music Tools</option>
                            <option value="design">Design</option>
                            <option value="productivity">Productivity</option>
                            <option value="gaming">Gaming</option>
                            <option value="security">Security</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="color: #8a8a8e; font-size: 12px; display: block; margin-bottom: 4px;">Monthly Cost</label>
                        <input type="number" name="monthly_cost" step="0.01" required style="width: 100%; padding: 8px; background: #0a0a0b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff;">
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="color: #8a8a8e; font-size: 12px; display: block; margin-bottom: 4px;">Plan Name</label>
                        <input type="text" name="plan_name" style="width: 100%; padding: 8px; background: #0a0a0b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff;">
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="color: #8a8a8e; font-size: 12px; display: block; margin-bottom: 4px;">Status</label>
                        <select name="status" style="width: 100%; padding: 8px; background: #0a0a0b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff;">
                            <option value="active">Active</option>
                            <option value="idle">Idle</option>
                            <option value="cancelled">Cancelled</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button type="submit" style="flex: 1; padding: 10px; background: #ffe600; color: #000; border: none; border-radius: 6px; font-weight: 500; cursor: pointer;">Add</button>
                        <button type="button" onclick="this.closest('div').remove()" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); color: #fff; border: none; border-radius: 6px; cursor: pointer;">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    form.querySelector('#add-subscription-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const subscription = Object.fromEntries(formData.entries());
        subscription.monthly_cost = parseFloat(subscription.monthly_cost);
        
        try {
            await addSubscription(subscription);
            form.remove();
            await initializeApp(); // Refresh data
        } catch (error) {
            alert('Failed to add subscription: ' + error.message);
        }
    });
    
    document.body.appendChild(form);
}

// Add parse emails button
function showParseEmailsButton() {
    const button = document.createElement('button');
    button.textContent = 'Parse Emails';
    button.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 999;
        padding: 10px 16px; background: #ffe600; color: #000;
        border: none; border-radius: 6px; font-weight: 500; cursor: pointer;
    `;
    button.addEventListener('click', async () => {
        button.textContent = 'Parsing...';
        button.disabled = true;
        try {
            await parseEmails();
            await initializeApp(); // Refresh data
            button.textContent = 'Parse Emails';
        } catch (error) {
            alert('Failed to parse emails: ' + error.message);
            button.textContent = 'Parse Emails';
        }
        button.disabled = false;
    });
    document.body.appendChild(button);
}

// Add manual subscription button
function showAddSubscriptionButton() {
    const button = document.createElement('button');
    button.textContent = '+ Add Subscription';
    button.style.cssText = `
        position: fixed; top: 20px; right: 140px; z-index: 999;
        padding: 10px 16px; background: rgba(255,255,255,0.1); color: #fff;
        border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; font-weight: 500; cursor: pointer;
    `;
    button.addEventListener('click', showAddSubscriptionForm);
    document.body.appendChild(button);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    showParseEmailsButton();
    showAddSubscriptionButton();
});

// Export for use in other scripts
window.SubscriptionAPI = {
    fetchSubscriptions,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    parseEmails,
    getStats,
    initializeApp
};