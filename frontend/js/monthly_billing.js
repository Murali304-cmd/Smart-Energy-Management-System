/**
 * SEMS Monthly Billing & Tariff Forecasting Manager
 * Connects with /api/billing/month, /api/billing/budget-planner, /api/billing/mom-trends, /api/billing/invoice
 * Provides interactive month selection, telescopic slab breakdown, EOM forecast,
 * next-slab runaway prevention, target budget auto-pacing, and official printable invoices.
 */

class MonthlyBillingManager {
    constructor() {
        this.currentYear = 2026;
        this.currentMonth = 10; // October
        this.cycleMode = 'bimonthly';
        this.billingData = null;
        this.momTrends = [];
        this.momChart = null;

        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadMonthlyData();
        await this.loadMoMTrends();
    }

    bindEvents() {
        // Month Selector
        const monthSelect = document.getElementById('select-billing-month');
        if (monthSelect) {
            monthSelect.addEventListener('change', (e) => {
                this.currentMonth = parseInt(e.target.value, 10);
                this.loadMonthlyData();
            });
        }

        // Cycle Mode Toggle
        const cycleToggleBtn = document.getElementById('btn-toggle-cycle-mode');
        if (cycleToggleBtn) {
            cycleToggleBtn.addEventListener('click', () => {
                this.cycleMode = this.cycleMode === 'bimonthly' ? 'monthly' : 'bimonthly';
                cycleToggleBtn.textContent = this.cycleMode === 'bimonthly' ? '⚡ Cycle: Bi-Monthly (60-Day TNEB)' : '⚡ Cycle: Monthly (30-Day)';
                cycleToggleBtn.classList.toggle('active-mode', this.cycleMode === 'bimonthly');
                this.loadMonthlyData();
            });
        }

        // Target Budget Planner Inputs
        const budgetSlider = document.getElementById('billing-budget-slider');
        const budgetNum = document.getElementById('billing-budget-num');
        const applyBudget = (val) => {
            if (budgetSlider) budgetSlider.value = val;
            if (budgetNum) budgetNum.value = val;
            this.calculateBudgetPacing(parseFloat(val) || 600);
        };

        if (budgetSlider) {
            budgetSlider.addEventListener('input', (e) => applyBudget(e.target.value));
        }
        if (budgetNum) {
            budgetNum.addEventListener('input', (e) => applyBudget(e.target.value));
        }

        // Invoice Modal Open/Close
        const invoiceBtn = document.getElementById('btn-open-eb-invoice');
        if (invoiceBtn) {
            invoiceBtn.addEventListener('click', () => this.openInvoiceModal());
        }

        const invoiceModalClose = document.getElementById('btn-close-invoice-modal');
        if (invoiceModalClose) {
            invoiceModalClose.addEventListener('click', () => {
                const modal = document.getElementById('eb-invoice-modal');
                if (modal) modal.style.display = 'none';
            });
        }

        // Refresh Billing Button
        const refreshBtn = document.getElementById('btn-refresh-billing');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadMonthlyData(true));
        }
    }

    async loadMonthlyData(showToast = false) {
        try {
            const url = `/api/billing/month?year=${this.currentYear}&month=${this.currentMonth}&cycle_mode=${this.cycleMode}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP error ${res.status}`);
            const data = await res.json();
            this.billingData = data;
            this.renderBillingView(data);

            if (showToast && window.veraUI) {
                window.veraUI.showToast(`📊 Monthly billing for ${data.metadata.cycle_label} updated!`, 'success');
            }
        } catch (err) {
            console.error('Failed to load monthly billing data:', err);
        }
    }

    renderBillingView(data) {
        if (!data || !data.metadata) return;

        const meta = data.metadata;
        const mtd = data.mtd_actuals;
        const eom = data.eom_projection;
        const conv = data.conventional_comparison;
        const alert = data.slab_alert;
        const bill = eom.bill;

        // Current Cycle Label
        const cycleLabel = document.getElementById('monthly-current-label');
        if (cycleLabel) {
            cycleLabel.innerHTML = `<span>🗓️ Cycle: <strong>${meta.cycle_label}</strong> (${meta.days_elapsed}/${meta.total_days} Days Elapsed)</span>`;
        }

        // KPI 1: Total Units (MTD & EOM)
        const totalUnitsEl = document.getElementById('val-monthly-total-kwh');
        const gridUnitsEl = document.getElementById('val-monthly-grid-kwh');
        const solarSubEl = document.getElementById('val-monthly-solar-sub');
        if (totalUnitsEl) totalUnitsEl.textContent = `${eom.projected_total_load_kwh.toFixed(1)}`;
        if (gridUnitsEl) gridUnitsEl.textContent = `${eom.projected_grid_kwh.toFixed(1)} kWh (MTD: ${mtd.grid_import_kwh.toFixed(1)})`;
        if (solarSubEl) solarSubEl.textContent = `${eom.projected_solar_kwh.toFixed(1)} kWh`;

        // KPI 2: Projected Net Bill
        const billInrEl = document.getElementById('val-monthly-bill-inr');
        const slabBadgeEl = document.getElementById('val-monthly-slab-badge');
        if (billInrEl) billInrEl.textContent = `₹ ${bill.net_payable_inr.toFixed(2)}`;
        if (slabBadgeEl) slabBadgeEl.textContent = `Active: ${bill.active_slab} (@ ₹${bill.active_rate.toFixed(2)}/u)`;

        // KPI 3: Monthly Solar Generation
        const solarKwhEl = document.getElementById('val-monthly-solar-kwh');
        if (solarKwhEl) solarKwhEl.textContent = `${eom.projected_solar_kwh.toFixed(1)}`;

        // KPI 4: Net Rupee Savings
        const savingsEl = document.getElementById('val-monthly-savings-inr');
        if (savingsEl) savingsEl.textContent = `₹ ${conv.net_savings_inr.toFixed(2)}`;

        // Next Slab Runaway Warning Alert Banner
        const alertBox = document.getElementById('billing-runaway-alert-box');
        if (alertBox) {
            if (alert.will_escalate_slab) {
                alertBox.className = 'slab-warning-banner alert-danger';
                alertBox.innerHTML = `
                    <div class="slab-alert-icon">⚠️</div>
                    <div class="slab-alert-content">
                        <strong>SLAB ESCALATION WARNING:</strong>
                        <span>At your current pace of <strong>${mtd.daily_average_grid_kwh.toFixed(1)} u/day</strong>, you will exceed ${alert.active_slab_name} (${alert.slab_limit_units} units) in <strong>${alert.estimated_days_to_cross.toFixed(0)} days</strong> and enter <strong>${alert.next_slab_name} (@ ₹${alert.next_rate.toFixed(2)}/u)</strong>.</span>
                        <div class="slab-alert-action">
                            💡 Recommended: Keep daily grid draw below <strong>${alert.recommended_daily_cap_units.toFixed(1)} u/day</strong> for the remaining ${meta.days_remaining} days.
                        </div>
                    </div>
                `;
            } else {
                alertBox.className = 'slab-warning-banner alert-success';
                alertBox.innerHTML = `
                    <div class="slab-alert-icon">✅</div>
                    <div class="slab-alert-content">
                        <strong>TARIFF RUNAWAY PREVENTED:</strong>
                        <span>Consumption is on track to stay safely within <strong>${alert.active_slab_name} (@ ₹${alert.active_rate.toFixed(2)}/u)</strong>. You have <strong>${alert.units_remaining_in_slab.toFixed(1)} units</strong> headroom remaining.</span>
                    </div>
                `;
            }
        }

        // Telescopic Slab Progress Meter
        const slabAlertBadge = document.getElementById('monthly-slab-alert-badge');
        if (slabAlertBadge) {
            slabAlertBadge.innerHTML = `<span>${alert.units_remaining_in_slab.toFixed(1)} kWh headroom before next slab</span>`;
        }

        const tier2Sub = document.getElementById('tier2-usage-sub');
        if (tier2Sub) {
            const slab2Units = bill.breakdown.find(b => b.slab_name.includes('Tier 2'))?.units_consumed || 0;
            tier2Sub.textContent = `${slab2Units.toFixed(1)} / 300 kWh (@ ₹4.70) ◀ Current`;
        }

        // Render Itemized Breakdown Table
        this.renderItemizedTable(bill.breakdown);

        // Render Statutory Cost & Credits Summary
        this.renderStatutorySummary(bill, conv, meta);

        // Sync Target Budget Pacing
        const budgetSlider = document.getElementById('billing-budget-slider');
        const targetVal = budgetSlider ? parseFloat(budgetSlider.value) : 800;
        this.calculateBudgetPacing(targetVal);
    }

    renderItemizedTable(breakdown) {
        const tbody = document.getElementById('tbody-monthly-slabs');
        if (!tbody) return;

        let html = '';
        breakdown.forEach(s => {
            const isUsed = s.units_consumed > 0;
            html += `
                <tr class="${isUsed ? 'row-active-slab' : 'row-inactive-slab'}">
                    <td>
                        <strong>${s.slab_name}</strong>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${s.range_label}</div>
                    </td>
                    <td style="text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: ${isUsed ? '#0284c7' : 'inherit'};">
                        ${s.units_consumed.toFixed(2)} kWh
                    </td>
                    <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">
                        ${s.is_free ? '<span class="free-pill">FREE</span>' : `₹ ${s.rate_inr.toFixed(2)}`}
                    </td>
                    <td style="text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 800; color: ${s.cost_inr > 0 ? '#dc2626' : '#16a34a'};">
                        ₹ ${s.cost_inr.toFixed(2)}
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    }

    renderStatutorySummary(bill, conv, meta) {
        const elEnergy = document.getElementById('bill-stat-energy');
        const elFixed = document.getElementById('bill-stat-fixed');
        const elDuty = document.getElementById('bill-stat-duty');
        const elSolarCredit = document.getElementById('bill-stat-solar-credit');
        const elGross = document.getElementById('bill-stat-gross');
        const elNetPayable = document.getElementById('bill-stat-net-payable');
        const elSavings = document.getElementById('bill-stat-savings');

        if (elEnergy) elEnergy.textContent = `₹ ${bill.energy_charges_inr.toFixed(2)}`;
        if (elFixed) elFixed.textContent = `+ ₹ ${bill.fixed_charges_inr.toFixed(2)}`;
        if (elDuty) elDuty.textContent = `+ ₹ ${bill.electricity_duty_inr.toFixed(2)}`;
        if (elSolarCredit) elSolarCredit.textContent = `- ₹ ${bill.solar_export_credit_inr.toFixed(2)}`;
        if (elGross) elGross.textContent = `₹ ${bill.gross_bill_inr.toFixed(2)}`;
        if (elNetPayable) elNetPayable.textContent = `₹ ${bill.net_payable_inr.toFixed(2)}`;
        if (elSavings) {
            elSavings.textContent = `🌿 SEMS Saved: ₹ ${conv.net_savings_inr.toFixed(2)} (${conv.savings_percent}% reduction)`;
        }
    }

    async calculateBudgetPacing(targetBudget) {
        const statusBadge = document.getElementById('budget-pacing-status-badge');
        const adviceBox = document.getElementById('budget-pacing-advice');
        const dailyCapVal = document.getElementById('budget-daily-cap-val');
        const remainingVal = document.getElementById('budget-remaining-inr-val');

        try {
            const res = await fetch('/api/billing/budget-planner', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_budget_inr: targetBudget,
                    year: this.currentYear,
                    month: this.currentMonth,
                    cycle_mode: this.cycleMode
                })
            });
            if (!res.ok) return;
            const data = await res.json();

            if (statusBadge) {
                statusBadge.textContent = data.status_text;
                statusBadge.className = data.is_on_track ? 'pacing-pill pill-success' : 'pacing-pill pill-warning';
            }
            if (adviceBox) adviceBox.textContent = data.advice;
            if (dailyCapVal) dailyCapVal.textContent = `${data.target_daily_limit_units.toFixed(1)} u/day`;
            if (remainingVal) remainingVal.textContent = `₹ ${data.remaining_budget_inr.toFixed(2)}`;
        } catch (err) {
            console.error('Budget planner error:', err);
        }
    }

    async loadMoMTrends() {
        try {
            const res = await fetch('/api/billing/mom-trends');
            if (!res.ok) return;
            const data = await res.json();
            this.momTrends = data.history || [];
            this.renderMoMChart(this.momTrends);
        } catch (err) {
            console.error('MoM trends fetch error:', err);
        }
    }

    renderMoMChart(history) {
        const canvas = document.getElementById('chart-mom-trends');
        if (!canvas || typeof Chart === 'undefined') return;

        if (this.momChart) {
            this.momChart.destroy();
        }

        const labels = history.map(h => h.month);
        const billData = history.map(h => h.bill_inr);
        const savedData = history.map(h => h.saved_inr);
        const solarData = history.map(h => h.solar_gen);

        this.momChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Net Bill (₹)',
                        data: billData,
                        backgroundColor: 'rgba(37, 99, 235, 0.8)',
                        borderRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        label: 'SEMS Savings (₹)',
                        data: savedData,
                        backgroundColor: 'rgba(16, 185, 129, 0.8)',
                        borderRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Solar Gen (kWh)',
                        data: solarData,
                        type: 'line',
                        borderColor: '#f59e0b',
                        backgroundColor: '#f59e0b',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11, family: "'Plus Jakarta Sans', sans-serif" } } },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Cost & Savings (₹)', font: { size: 11 } }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Solar Generation (kWh)', font: { size: 11 } }
                    }
                }
            }
        });
    }

    openInvoiceModal() {
        const modal = document.getElementById('eb-invoice-modal');
        const iframe = document.getElementById('eb-invoice-iframe');
        if (!modal || !iframe) return;

        iframe.src = `/api/billing/invoice?year=${this.currentYear}&month=${this.currentMonth}&cycle_mode=${this.cycleMode}`;
        modal.style.display = 'flex';
    }
}

// Global initialization
window.monthlyBillingManager = null;
document.addEventListener('DOMContentLoaded', () => {
    window.monthlyBillingManager = new MonthlyBillingManager();
});
