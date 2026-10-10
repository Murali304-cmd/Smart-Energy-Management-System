/**
 * 'What-If' Solar PV & Battery Storage ROI Simulator Manager
 */

class SimulatorManager {
    constructor() {
        this.chart = null;
    }

    init() {
        const solarSlider = document.getElementById('sim-solar-kw');
        const batSlider = document.getElementById('sim-battery-kwh');
        const loadSlider = document.getElementById('sim-load-kwh');
        const tariffSlider = document.getElementById('sim-tariff-inr');

        const inputs = [solarSlider, batSlider, loadSlider, tariffSlider];
        inputs.forEach(input => {
            if (input) {
                input.addEventListener('input', () => this.debouncedRunSimulation());
            }
        });

        // Run initial default simulation
        this.runSimulation();
    }

    debouncedRunSimulation() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.runSimulation(), 200);
    }

    async runSimulation() {
        const solarKw = Number(document.getElementById('sim-solar-kw')?.value || 3.0);
        const batKwh = Number(document.getElementById('sim-battery-kwh')?.value || 7.0);
        const loadKwh = Number(document.getElementById('sim-load-kwh')?.value || 12.0);
        const tariff = Number(document.getElementById('sim-tariff-inr')?.value || 4.70);

        // Update display labels
        document.getElementById('sim-solar-label').textContent = `${solarKw.toFixed(1)} kW`;
        document.getElementById('sim-battery-label').textContent = `${batKwh.toFixed(1)} kWh`;
        document.getElementById('sim-load-label').textContent = `${loadKwh.toFixed(1)} kWh/day`;
        document.getElementById('sim-tariff-label').textContent = `₹ ${tariff.toFixed(2)} / kWh`;

        try {
            const res = await window.veraApi.evaluateSimulation({
                solar_capacity_kw: solarKw,
                battery_capacity_kwh: batKwh,
                daily_average_load_kwh: loadKwh,
                grid_tariff_inr: tariff,
                system_lifespan_years: 15
            });

            if (res && res.status === 'success') {
                this.renderResults(res.simulation);
            }
        } catch (error) {
            console.error('Simulation evaluation failed:', error);
        }
    }

    renderResults(sim) {
        const fin = sim.financials || {};
        const env = sim.environmental_impact || {};
        const bal = sim.energy_balance || {};

        // Financial KPIs
        const capexEl = document.getElementById('sim-total-capex');
        const monthlySaveEl = document.getElementById('sim-monthly-savings');
        const annualSaveEl = document.getElementById('sim-annual-savings');
        const paybackEl = document.getElementById('sim-payback-years');
        const roiEl = document.getElementById('sim-roi-percent');
        const co2El = document.getElementById('sim-co2-avoided');
        const treesEl = document.getElementById('sim-trees-planted');
        const renewPctEl = document.getElementById('sim-renewable-pct');

        if (capexEl) capexEl.textContent = `₹ ${fin.total_investment_inr.toLocaleString('en-IN')}`;
        if (monthlySaveEl) monthlySaveEl.textContent = `₹ ${fin.monthly_savings_inr.toLocaleString('en-IN')}`;
        if (annualSaveEl) annualSaveEl.textContent = `₹ ${fin.annual_savings_inr.toLocaleString('en-IN')}`;
        if (paybackEl) paybackEl.textContent = `${fin.payback_years} Years`;
        if (roiEl) roiEl.textContent = `+${fin.roi_percentage}% Net ROI`;
        if (co2El) co2El.textContent = `${env.annual_co2_avoided_kg} kg/yr`;
        if (treesEl) treesEl.textContent = `🌲 ~${env.trees_planted_equivalent} Trees / yr`;
        if (renewPctEl) renewPctEl.textContent = `${bal.renewable_fraction_pct}% Clean Solar`;

        // Update Monthly Breakdown Chart
        if (Array.isArray(sim.monthly_breakdown)) {
            this.updateMonthlyChart(sim.monthly_breakdown);
        }
    }

    updateMonthlyChart(breakdown) {
        const ctx = document.getElementById('chart-simulator-monthly')?.getContext('2d');
        if (!ctx) return;

        const labels = breakdown.map(b => b.month);
        const solarGen = breakdown.map(b => b.solar_generation_kwh);
        const loadDemand = breakdown.map(b => b.household_load_kwh);
        const savingsInr = breakdown.map(b => b.bill_savings_inr);

        const colors = window.veraCharts ? window.veraCharts.getThemeColors() : { solar: '#D97706', load: '#4F46E5', cost: '#059669', textColor: '#334155', gridColor: 'rgba(0,0,0,0.06)' };

        if (this.chart) {
            this.chart.data.labels = labels;
            this.chart.data.datasets[0].data = solarGen;
            this.chart.data.datasets[1].data = loadDemand;
            this.chart.data.datasets[2].data = savingsInr;
            this.chart.update();
            return;
        }

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'bar',
                        label: 'Solar PV Gen (kWh)',
                        data: solarGen,
                        backgroundColor: colors.solar,
                        borderRadius: 4,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Household Demand (kWh)',
                        data: loadDemand,
                        backgroundColor: colors.load,
                        borderRadius: 4,
                        yAxisID: 'y'
                    },
                    {
                        type: 'line',
                        label: 'Bill Savings (₹)',
                        data: savingsInr,
                        borderColor: '#059669',
                        backgroundColor: 'rgba(5, 150, 105, 0.1)',
                        fill: true,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor },
                        title: { display: true, text: 'Energy (kWh)', color: colors.textColor }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        ticks: { color: '#059669' },
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Monthly Savings (₹)', color: '#059669' }
                    }
                }
            }
        });
    }
}

window.veraSimulator = new SimulatorManager();
