/**
 * SEMS Carbon Accounting & Battery Health (SOH) Controller
 */

class CarbonController {
    constructor() {
        this.carbonContainer = document.getElementById('carbon-metrics-container');
        this.batteryContainer = document.getElementById('battery-health-container');
        this.init();
    }

    async init() {
        await this.loadMetrics();
    }

    async loadMetrics() {
        try {
            const carbonData = await window.veraApi._request('/api/carbon/emissions');
            const batteryData = await window.veraApi._request('/api/battery/health');
            this.renderCarbon(carbonData);
            this.renderBattery(batteryData);
        } catch (e) {
            console.error('Error loading carbon/battery data:', e);
        }
    }

    renderCarbon(data) {
        if (!this.carbonContainer || !data) return;
        this.carbonContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-title">Green Energy Index</div>
                <div class="stat-value" style="color: #10b981;">${data.green_energy_index_pct}%</div>
                <div class="stat-desc">ESG Rating: ${data.esg_grade}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Lifetime CO₂ Avoided</div>
                <div class="stat-value">${data.cumulative_co2_offset_kg.toFixed(1)} kg</div>
                <div class="stat-desc">Equivalent to 🌳 ${data.equivalent_trees_planted} Trees Planted</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Cumulative Clean Solar</div>
                <div class="stat-value" style="color: #f59e0b;">${data.cumulative_clean_energy_kwh.toFixed(1)} kWh</div>
                <div class="stat-desc">Zero-emission Rooftop Power</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Grid Carbon Intensity</div>
                <div class="stat-value">${data.emission_factor_g_co2_kwh} g/kWh</div>
                <div class="stat-desc">Regional Grid CEA Average</div>
            </div>
        `;
    }

    renderBattery(data) {
        if (!this.batteryContainer || !data) return;
        this.batteryContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-title">State of Health (SOH)</div>
                <div class="stat-value" style="color: #10b981;">${data.state_of_health_pct}%</div>
                <div class="stat-desc">Grade: ${data.health_grade}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Usable Capacity</div>
                <div class="stat-value">${data.actual_usable_capacity_kwh} / ${data.nominal_capacity_kwh} kWh</div>
                <div class="stat-desc">${data.chemistry}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Equivalent Full Cycles</div>
                <div class="stat-value">${data.equivalent_full_cycles} / ${data.rated_cycles_to_80pct}</div>
                <div class="stat-desc">Estimated ${data.remaining_estimated_years} Years Remaining</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Cell Temperature</div>
                <div class="stat-value">${data.cell_temperature_c}°C</div>
                <div class="stat-desc">Internal: ${data.internal_resistance_mohm} mΩ</div>
            </div>
        `;
    }
}

window.carbonController = new CarbonController();
