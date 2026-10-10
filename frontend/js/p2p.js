/**
 * SEMS P2P Microgrid Energy Trading & Virtual Power Plant Controller
 */

class P2PController {
    constructor() {
        this.container = document.getElementById('p2p-trading-container');
        this.init();
    }

    async init() {
        if (!this.container) return;
        await this.loadP2PData();
    }

    async loadP2PData() {
        try {
            const data = await window.veraApi._request('/api/p2p/market');
            this.render(data);
        } catch (e) {
            console.error('Error loading P2P market data:', e);
        }
    }

    render(data) {
        if (!this.container || !data) return;
        const vpp = data.vpp_cluster || {};
        const orders = data.recent_orders || [];

        this.container.innerHTML = `
            <div class="p2p-kpi-grid">
                <div class="stat-card">
                    <div class="stat-title">P2P Clearing Rate</div>
                    <div class="stat-value">₹${data.p2p_clearing_price_inr.toFixed(2)}/kWh</div>
                    <div class="stat-desc">Win-Win Midpoint Trade Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Trade Action</div>
                    <div class="stat-value" style="color: #10b981;">${data.trade_action}</div>
                    <div class="stat-desc">${data.description}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Virtual Power Plant (VPP)</div>
                    <div class="stat-value">${vpp.total_vpp_available_kw || 45} kW</div>
                    <div class="stat-desc">${vpp.participating_homes || 18} Participating Homes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Monthly Ancillary Reward</div>
                    <div class="stat-value" style="color: #f59e0b;">₹${vpp.grid_ancillary_reward_inr_month || 4250}</div>
                    <div class="stat-desc">Grid Frequency Support Revenue</div>
                </div>
            </div>

            <div class="card" style="margin-top: 20px;">
                <h3>⚡ Neighborhood Double-Auction Order Book</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Prosumer / Consumer</th>
                            <th>Order Type</th>
                            <th>Volume (kWh)</th>
                            <th>Offered Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${orders.map(o => `
                            <tr>
                                <td><code>${o.id}</code></td>
                                <td>${o.neighbor}</td>
                                <td><span class="badge ${o.type.includes('ASK') ? 'badge-warning' : 'badge-primary'}">${o.type}</span></td>
                                <td>${o.energy_kwh.toFixed(1)} kWh</td>
                                <td>₹${o.price_inr.toFixed(2)}/kWh</td>
                                <td><span class="badge badge-success">${o.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}

window.p2pController = new P2PController();
